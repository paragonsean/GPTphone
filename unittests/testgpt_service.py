# import unittest
# from unittest.mock import patch, MagicMock
# import os
# from dotenv import load_dotenv
# import asyncio
# from llms.call_details import CallContext
#
# from Utils.logger_config import configure_logger, log_function_call
# from llms.gpt_service import AbstractLLMService, LLMFactory
# from llms.google_bard import GeminiService
# from llms.openai_assistant import AssistantService
#
# logger = configure_logger(__name__)
#
# class TestLLMServices(unittest.TestCase):
#
#     @classmethod
#     def setUpClass(cls):
#         load_dotenv()
#
#     def setUp(self):
#         self.context = CallContext()
#         self.context.system_message = "You are a helpful assistant."
#         self.context.initial_message = "Hello! How can I help you today?"
#         os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
#
#     @patch('openai.OpenAI')
#     async def test_assistant_service_completion(self, mock_openai):
#         # Mock the OpenAI client and its methods
#         mock_client = MagicMock()
#         mock_openai.return_value = mock_client
#
#         service = AssistantService(self.context)
#
#         # Set up mocks for thread creation and message submission
#         mock_thread = MagicMock()
#         mock_run = MagicMock()
#         mock_messages = MagicMock()
#
#         mock_client.beta.threads.create.return_value = mock_thread
#         mock_client.beta.threads.messages.create.return_value = None
#         mock_client.beta.threads.runs.create.return_value = mock_run
#         mock_client.beta.threads.runs.retrieve.side_effect = [mock_run, mock_run]  # Simulate run status changes
#         mock_client.beta.threads.messages.list.return_value = mock_messages
#
#         # Simulate the interaction
#         text = "What is 2 + 2?"
#         interaction_count = 1
#
#         await service.completion(text, interaction_count)
#
#         # Assertions to ensure the expected flow occurred
#         mock_client.beta.threads.create.assert_called_once()
#         mock_client.beta.threads.messages.create.assert_called_once_with(
#             thread_id=mock_thread.id, role="user", content=text
#         )
#         mock_client.beta.threads.runs.create.assert_called_once_with(
#             thread_id=mock_thread.id, assistant_id=service.assistant_id
#         )
#         mock_client.beta.threads.messages.list.assert_called_once_with(
#             thread_id=mock_thread.id, order="asc"
#         )
#
#     @patch('llms.event_manager.EventHandler.createEvent')
#     async def test_emit_complete_sentences(self, mock_create_event):
#         # Test emit_complete_sentences
#         class DummyService(AbstractLLMService):
#             async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
#                 pass
#
#         service = DummyService(self.context)
#         await service.emit_complete_sentences("Hello world.", 1)
#
#         mock_create_event.assert_called()
#
#
#
#     def test_abstract_llm_service_methods(self):
#         # Create a dummy subclass to test AbstractLLMService methods
#         class DummyService(AbstractLLMService):
#             async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
#                 pass
#
#         service = DummyService(self.context)
#
#         # Test the validate_function_args method
#         valid_args = '{"key": "value"}'
#         invalid_args = '{"key": value}'  # Missing quotes around value
#
#         self.assertEqual(service.validate_function_args(valid_args), {"key": "value"})
#         self.assertEqual(service.validate_function_args(invalid_args), {})
#
#         # Test the split_into_sentences method
#         text = "Hello! How are you? I'm fine."
#         sentences = service.split_into_sentences(text)
#         self.assertEqual(sentences, ["Hello!", " How are you?", " I'm fine.",''])
#
#
#
