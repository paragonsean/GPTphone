import importlib
import json
import re
from abc import ABC, abstractmethod
from .call_details import CallContext
from EventHandlers import EventHandler
from functions.function_manifest import tools
from Utils import configure_logger, log_function_call



logger = configure_logger("LLMService")

'''
Author: Sean Baker
Date: 2024-07-22 
Description: GPT-LIBRARY WITH INTERRUPTS HANDLERS AND EVENT HANDLING 
'''


class AbstractLLMService(EventHandler, ABC):
    """
    This class represents an abstract Long-Lived Memory (LLM) service.

    :param context: CallContext object containing system and initial messages
    """
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
    @abstractmethod
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        pass

    def set_call_context(self, context: CallContext):
        self.context = context
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": context.initial_message}
        ]
        context.user_context = self.user_context
        self.system_message = context.system_message
        self.initial_message = context.initial_message


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


class LLMFactory:
    @staticmethod
    def get_llm_service(service_name: str, context: CallContext) -> AbstractLLMService:
        if service_name.lower() == "openai" or service_name.lower() == "assistant":
            from .openai_service import OpenAIService  # Local import
            return OpenAIService(context)
        elif service_name.lower() == "gemini":
            from .google_bard import GeminiService  # Local import
            return GeminiService(context)
        else:
            raise ValueError(f"Unsupported LLM service: {service_name}")
