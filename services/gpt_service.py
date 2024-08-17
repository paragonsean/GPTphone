import importlib
import json
import os
import re
from abc import ABC, abstractmethod
from openai import AsyncOpenAI, OpenAI
from services.call_details import CallContext
from services.event_manager import EventHandler,AsyncAssistantEventHandler
import time
import google.generativeai as genai
from functions.function_manifest import tools
from Utils.logger_config import get_logger, log_function_call

logger = get_logger("LLMService")

'''
Author: Sean Baker
Date: 2024-07-22 
Description: GPT-LIBRARY WITH INTERRUPTS HANDLERS AND EVENT HANDLING 
'''


class AbstractLLMService(EventHandler, ABC):
    def __init__(self, context: CallContext):
        super().__init__()
        self.system_message = context.system_message
        self.initial_message = context.initial_message
        self.context = context
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": self.initial_message}
        ]
        self.partial_response_index = 0
        self.available_functions = {}
        for tool in tools:
            function_name = tool['function']['name']
            module = importlib.import_module(f'functions.{function_name}')
            self.available_functions[function_name] = getattr(module, function_name)
        self.sentence_buffer = ""
        context.user_context = self.user_context

    def set_call_context(self, context: CallContext):
        self.context = context
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": context.initial_message}
        ]
        context.user_context = self.user_context
        self.system_message = context.system_message
        self.initial_message = context.initial_message

    @abstractmethod
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        pass

    def reset(self):
        self.partial_response_index = 0

    @log_function_call
    def validate_function_args(self, args):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            logger.info('Warning: Invalid function arguments returned by LLM:', args)
            return {}

    @log_function_call
    def split_into_sentences(self, text):
        # Split the text into sentences, keeping the separators
        sentences = re.split(r'([.!?])', text)
        # Pair the sentences with their separators
        sentences = [''.join(sentences[i:i + 2]) for i in range(0, len(sentences), 2)]
        return sentences

    @log_function_call
    async def emit_complete_sentences(self, text, interaction_count):
        self.sentence_buffer += text
        sentences = self.split_into_sentences(self.sentence_buffer)

        # Emit all complete sentences
        for sentence in sentences[:-1]:
            await self.createEvent('llmreply', {
                "partialResponseIndex": self.partial_response_index,
                "partialResponse": sentence.strip()
            }, interaction_count)
            self.partial_response_index += 1

        # Keep the last (potentially incomplete) sentence in the buffer
        self.sentence_buffer = sentences[-1] if sentences else ""


class AssistantEventHandler(AsyncAssistantEventHandler):
    async def on_user_input(self, text, role, name):
        return {"role": role, "content": text, "name": name}

    async def on_create_thread(self, client):
        return client.beta.threads.create()

    async def on_submit_message(self, thread, user_message, client, assistant_id):
        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=user_message
        )
        return client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )

    async def on_wait_run(self, run, thread, client):
        while run.status in ["queued", "in_progress"]:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )
            time.sleep(0.5)
        return run

    async def on_response(self, thread, client):
        return client.beta.threads.messages.list(thread_id=thread.id, order="asc")


class AssistantService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = os.getenv("ASSISTANT_ID")
        self.event_handler = AssistantEventHandler()  # Initialize the event handler

    @log_function_call
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                # Handle user input
                user_input = await self.event_handler.on_user_input(text, role, name)
                self.user_context.append(user_input)

                # Create a new thread
                thread = await self.event_handler.on_create_thread(self.client)

                # Submit message and create a run
                run = await self.event_handler.on_submit_message(thread, text, self.client, self.assistant_id)

                # Wait for the run to complete
                run = await self.event_handler.on_wait_run(run, thread, self.client)

                # Get the response
                messages = await self.event_handler.on_response(thread, self.client)

                # Emit the final response
                for message in messages.data:
                    content_block = self._extract_content(message)
                    if content_block:
                        await self.emit_complete_sentences(content_block, interaction_count)

                break  # Exit loop if successful

            except Exception as e:
                logger.error(f"Error in AssistantService completion: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise  # Re-raise the exception if all retries fail

    @log_function_call
    def _extract_content(self, message):
        if isinstance(message.content, list) and len(message.content) > 0:
            content_block = message.content[0]
            if hasattr(content_block, 'text'):
                return content_block.text.value
        return None


class OpenAIService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context

            stream = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                stream=True,
            )

            complete_response = ""
            function_name = ""
            function_args = ""

            async for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                tool_calls = delta.tool_calls

                if tool_calls:
                    for tool_call in tool_calls:
                        if tool_call.function and tool_call.function.name:
                            logger.info(f"Function call detected: {tool_call.function.name}")
                            function_name = tool_call.function.name
                            function_args += tool_call.function.arguments or ""
                else:
                    complete_response += content
                    await self.emit_complete_sentences(content, interaction_count)

                if chunk.choices[0].finish_reason == "tool_calls":
                    logger.info(f"Function call detected: {function_name}")
                    function_to_call = self.available_functions[function_name]
                    function_args = self.validate_function_args(function_args)

                    tool_data = next((tool for tool in tools if tool['function']['name'] == function_name), None)
                    say = tool_data['function']['say']

                    await self.emit('llmreply', {
                        "partialResponseIndex": None,
                        "partialResponse": say
                    }, interaction_count)

                    self.user_context.append({"role": "assistant", "content": say})

                    function_response = await function_to_call(self.context, function_args)

                    logger.info(f"Function {function_name} called with args: {function_args}")

                    if function_name != "end_call":
                        await self.completion(function_response, interaction_count, 'function', function_name)

            # Emit any remaining content in the buffer
            if self.sentence_buffer.strip():
                await self.emit('llmreply', {
                    "partialResponseIndex": self.partial_response_index,
                    "partialResponse": self.sentence_buffer.strip()
                }, interaction_count)
                self.sentence_buffer = ""

            self.user_context.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in OpenAIService completion: {str(e)}")


class GeminiService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        genai.configure(api_key=os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"))

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context
            prompt = "\n".join([msg["content"] for msg in messages])

            response = genai.generate_text(
                model="models/text-bison-001",
                prompt=prompt,
                temperature=0.2,
                top_p=0.95,
                top_k=40,
            )

            # Process response and emit
            complete_response = response.result
            await self.emit_complete_sentences(complete_response, interaction_count)
            self.user_context.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in GeminiService completion: {str(e)}")


class LLMFactory:
    @staticmethod
    def get_llm_service(service_name: str, context: CallContext) -> AbstractLLMService:
        if service_name.lower() == "openai" or service_name.lower() == "assistant":
            return AssistantService(context)
        elif service_name.lower() == "gemini":
            return GeminiService(context)
        else:
            raise ValueError(f"Unsupported LLM service: {service_name}")
