import importlib
import json
import openai
from openai import AsyncOpenAI, AsyncStream
import aiohttp
import openmeteo_requests
import requests_cache
from typing import Literal, Any, Callable, Dict, List, Optional
import time
import asyncio
import os

from pygments.lexers import q

from debugging_helper import log_function_call
import re
from loguru import logger

DEPLOYMENT_NAME = os.getenv("OPENAI_MODEL")

logger = logger.bind(name=__name__)


def get_user_input() -> str:
    try:
        user_input = input("User:> ")

    except KeyboardInterrupt:
        print("\n\nExiting chat...")
        return ""
    except EOFError:
        print("\n\nExiting chat...")
        return ""

    # Handle exit command
    if user_input == "exit":
        print("\n\nExiting chat...")
        return ""

    return user_input


class EventHandler:
    def __init__(self):
        self._events: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)

    async def createEvent(self, event: str, *args: Any, **kwargs: Any):
        if event in self._events:
            for callback in self._events[event]:
                await self._run_callback(callback, *args, **kwargs)

    async def _run_callback(self, callback: Callable, *args: Any, **kwargs: Any):
        if asyncio.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        else:
            callback(*args, **kwargs)


def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time} seconds to execute.\n")
        return result

    return wrapper


def get_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_random_numbers",
                "description": "Generates a list of random numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "integer", "description": "Lower bound on the generated number"},
                        "max": {"type": "integer", "description": "Upper bound on the generated number"},
                        "count": {"type": "integer", "description": "How many numbers should be calculated"}
                    },
                    "required": ["min", "max", "count"],
                },

            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Gives the temperature for a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "The latitude of the location"},
                        "longitude": {"type": "number", "description": "The longitude of the location"},
                    },
                    "required": ["latitude", "longitude"],
                },

            }
        }
    ]


@log_function_call()
async def get_random_numbers(min: int, max: int, count: int) -> str:
    url = "http://www.randomnumberapi.com/api/v1.0/random"
    params = {'min': min, 'max': max, 'count': count}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            return json.dumps({"random numbers": data})


@log_function_call()
async def get_current_weather(latitude: float, longitude: float) -> str:
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    openmeteo = openmeteo_requests.Client(session=cache_session)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": latitude, "longitude": longitude, "current": "temperature_2m"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, params=params) as response:
            data = await response.json()
            temperature = data['current']['temperature_2m']
            return json.dumps({"temperature": str(temperature)})


class CallContext:
    """Store context for the current call."""

    def __init__(self):
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.call_ended: bool = False
        self.initial_message: str = "hey how are you"
        self.system_message: str = "you "
        self.name: Optional[str] = 'user'
        self.role: Optional[str] = 'user'
        self.messages: List = [
            {"role": self.role, "content": "Hello"},
            {"role": "assistant", "content": self.initial_message}
        ]
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.final_status: Optional[str] = None
        self.tools: Optional[List[Dict[str, Any]]] = None
        self.available_functions: Dict[str, Callable] = {}
        self.interaction_count = 0
        self.user_context: List = []


@log_function_call()
@log_function_call()
async def call_function(tool_call, available_functions):
    logger.warning("I am here")
    functions_name = tool_call['function']['name']
    function_args = json.loads(tool_call['function']['arguments'])  # Convert JSON string to dict

    if functions_name not in available_functions:
        return "Function " + functions_name + " does not exist"

    function = available_functions[functions_name]  # Get the actual function object
    logger.info(f"Function args: {function_args}")
    logger.info(f"Function name: {functions_name}")

    # Call the function and ensure the result is awaited if necessary
    function_response = function(**function_args)  # Call the function using the correct reference
    if asyncio.iscoroutine(function_response):
        function_response = await function_response

    return function_response, functions_name


# {'role': 'assistant', 'content': 'The capital of Mexico is Mexico City.'}
# User:> what is the temp there
# Assistant:>{'tool_call_id': 'call_fdDFJybcdzbsx7GTXLDRujyh', 'role': 'tool', 'name': 'get_current_weather', 'content': '{"location": "Mexico City", "temperature": "unknown"}'}
# User:>  I apologize, but I am unable to retrieve the current temperature in Mexico City at the moment.
# Assistant:> The current temperature in San Francisco is 72 degrees Fahrenheit.{'tool_call_id': 'call_TF3i5ecwyhGJ2YMdtyPlFUCa', 'role': 'tool', 'name': 'get_current_weather', 'content': '{"location": "San Francisco", "temperature": "72", "unit": "fahrenheit"}'}


class OpenAIService(EventHandler):
    def __init__(self, context: CallContext):
        super().__init__()
        self.system_message = context.system_message
        self.initial_message = context.initial_message
        self.context = context
        self.partial_response_index = 0
        self.available_functions = {}
        self.tools = get_tools()
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": self.initial_message}
        ]

        self.sentence_buffer = ""
        context.user_context = self.user_context
        self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.available_functions = self.get_available_functions()
        self.messages = self.context.messages

    def get_available_functions(self):
        return {"get_current_weather": get_current_weather, "get_random_numbers": get_random_numbers}

    def split_into_sentences(self, text):
        sentences = re.split(r'([.!?])', text)
        sentences = [''.join(sentences[i:i + 2]) for i in range(0, len(sentences), 2)]
        return sentences

    async def emit_complete_sentences(self, text, interaction_count):
        self.sentence_buffer += text
        sentences = self.split_into_sentences(self.sentence_buffer)

        for sentence in sentences[:-1]:
            logger.info(f'Emitting complete sentence: {sentence}')
            await self.createEvent('llmreply', {
                "partialResponseIndex": self.context.interaction_count,
                "partialResponse": sentence.strip()
            }, interaction_count)
            self.context.interaction_count += 1
            logger.info(f'Interaction count: {self.context.interaction_count}')

        self.sentence_buffer = sentences[-1] if sentences else ""

    @log_function_call()
    async def get_tool_calls(self, stream, interaction_count):
        tool_calls = []
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices and chunk.choices[0].delta is not None else None

            if delta and delta.content:
                await self.emit_complete_sentences(delta.content, interaction_count)

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
        if len(tool_calls) > 0:
            return tool_calls
        else:
            return None

    @log_function_call()
    async def print_stream_chunks(self, stream):
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="", flush=True)
                await asyncio.sleep(0.1)

    @log_function_call()
    async def process_tool_calls(self, tool_calls, available_functions):

        if tool_calls:
            self.user_context.append(
                {
                    "tool_calls": tool_calls,
                    "role": 'assistant',
                }
            )

            for tool_call in tool_calls:
                for key,value in tool_call.items():
                    logger.info(f"Here is the key value pairs for tool_call {key}: {value}")
                function_response,name = await call_function(tool_call, available_functions)
                # Append the tool's output to the conversation
                self.user_context.append(
                    {
                        "tool_call_id": tool_call['id'],
                        "role": "tool",
                        "name": tool_call['function']['name'],
                        "content": function_response,
                    }
                )
                interaction_count = self.context.interaction_count
                return function_response, name
        else:
            return None, None
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:

            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context

            stream = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.tools,
                stream=True,
            )
            available_functions = self.get_available_functions()
            complete_response = ""


            tool_calls = []
            tool_calls = await self.get_tool_calls(stream, interaction_count)
            if tool_calls:
                response, name = await self.process_tool_calls(tool_calls, available_functions)
                if response:
                    await self.completion(response, interaction_count, 'function', name)

            message = ''

            message = get_user_input()
            await self.completion(message, interaction_count, role='system', name='user')

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




def init_messages():
    return [
        {
            "role": "system",
            "content": """You are a helpful assistant. You have access to a function that can get the current weather in a given location. Determine a reasonable Unit of Measurement (Celsius or Fahrenheit) for the temperature based on the location.
            """
        }
    ]


if __name__ == "__main__":
    initial_messages = init_messages()
    initial_user_message = get_user_input()
    start_time = time.time()
    call_context = CallContext()

    call_context.tools = get_tools()
    call_context.user_message = initial_user_message
    call_context.start_time = start_time
    call_context.role = initial_messages[0]['role']
    call_context.system_message = initial_messages[0]['content']

    llmservice = OpenAIService(call_context)
    asyncio.run(llmservice.completion(call_context.user_message, 1))
