import importlib
import json
import re
from abc import ABC, abstractmethod

from EventHandlers import EventHandler
from Utils.my_logger import configure_logger
from .call_details import CallContext
from functions import end_call
from functions.tools import TOOL_MAP
'''
Author: Sean Baker
Date: 2024-07-22 
Description: GPT-LIBRARY WITH INTERRUPTS HANDLERS AND EVENT HANDLING 
'''
logger = configure_logger(__name__)

class AbstractLLMService(EventHandler, ABC):
    """
    This class represents an abstract Long-Lived Memory (LLM) service.

    :param context: CallContext object containing system and initial messages
    """
    def __init__(self, context: CallContext):
        super().__init__()
        self.partial_response_index = 0
        self.sentence_buffer = ""

       
    @abstractmethod
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        pass

    def set_call_context(self, context: CallContext):
        self.context = context
        self.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": context.initial_message}
        ]
        self.context.messages = self.messages
        self.system_message = self.context.system_message
        self.initial_message = self.context.initial_message


    def reset(self):
        self.partial_response_index = 0


    def validate_function_args(self, args):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            logger.info('Warning: Invalid function arguments returned by LLM:', args)
            return {}


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
