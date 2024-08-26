import asyncio
import os
import importlib
import json
import time
from openai import AsyncOpenAI
from functions.tools import TOOL_MAP
from .call_details import CallContext
from .gpt_service import AbstractLLMService
from Utils import log_function_call, configure_logger
from functions import transfer_call, end_call,get_current_weather
from Utils.debugging_helper import DEBUG_APP
import json
import aiohttp
import openmeteo_requests
import requests_cache
from Utils import log_function_call

logger = configure_logger(__name__)


# @log_function_call()
# async def get_current_weather( latitude: float, longitude: float) -> str:
#     logger.warning(f"inside get_current_weather")
#     url = "https://api.open-meteo.com/v1/forecast"
#     params = {"latitude": latitude, "longitude": longitude, "current": "temperature_2m"}
#
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url=url, params=params) as response:
#             data = await response.json()
#             temperature = data['current']['temperature_2m']
#             return json.dumps({"temperature": str(temperature)})


DEBUG = DEBUG_APP


def get_available_functions():
    return {"get_current_weather": get_current_weather, "transfer_call": transfer_call, "end_call": end_call}


class OpenAIService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.available_functions = get_available_functions()
        self.system_message = context.system_message
        self.initial_message = context.initial_message
        self.context = context
        self.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": self.initial_message}
        ]

        context.messages = self.messages
        self.tools = TOOL_MAP
        self.context.start_time = time.time()
        logger.info(f'tools {self.tools}')
        logger.info(f'context {self.available_functions}')




    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):

        try:
            self.messages.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.messages

            stream = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOL_MAP,
                stream=True,
            )

            complete_response = ""
            tool_calls = []

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices and chunk.choices[0].delta is not None else None

                if delta and delta.content:
                    await self.emit_complete_sentences(delta.content, interaction_count)
                    complete_response += delta.content
                elif delta and delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        if len(tool_calls) <= tc_chunk.index:
                            tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                        tc = tool_calls[tc_chunk.index]

                        if tc_chunk.id:
                            tc["id"] += tc_chunk.id

                        if tc_chunk.function.name:
                            tc["function"]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tc["function"]["arguments"] += tc_chunk.function.arguments

            # Process tool calls after stream ends
            for tool_call in tool_calls:
                function_name = tool_call['function']['name']
                try:
                    function_args = json.loads(tool_call['function']['arguments'])  # Convert JSON string to dict
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse function arguments: {str(e)}")
                    continue

                if function_name not in self.available_functions:
                    logger.error(f"Function {function_name} does not exist")
                    continue
                function = self.available_functions[function_name]

                if function_name == "end_call" or function_name == "transfer_call":
                    function_response = function(self.context, function_args)
                    if asyncio.iscoroutine(function_response):
                        function_response = await function_response

                function_response = function(**function_args)
                if asyncio.iscoroutine(function_response):
                    function_response = await function_response

                logger.info(f'{function_name}: {function_response}')

                if function_name != "end_call" or function_name != "transfer_call":
                    await self.completion(function_response, interaction_count, 'function', function_name)

            # Emit any remaining content in the buffer
            if self.sentence_buffer.strip():
                await self.createEvent('llmreply', {
                    "partialResponseIndex": self.partial_response_index,
                    "partialResponse": self.sentence_buffer.strip()
                }, interaction_count)
                self.sentence_buffer = ""

            self.messages.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in OpenAIService completion: {str(e)}")
