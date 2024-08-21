import asyncio
import os

from openai import AsyncOpenAI
from openai.lib.streaming import AssistantEventHandler

from EventHandlers.assitant_event_manager import AssitantsEventHandler
from .call_details import CallContext
from .gpt_service import AbstractLLMService
from Utils import my_logger

logger = my_logger.configure_logger(__name__)

class AssistantService(AbstractLLMService, AssitantsEventHandler):

    def __init__(self, context: CallContext):
        super().__init__(context)  # This initializes both AbstractLLMService and AssistantEventHandler

        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = os.getenv("ASSISTANT_ID")
        self.event_handler = AssistantEventHandler()

    def create_thread(client, content, file=None):
        return client.beta.threads.create()

    def create_message(client, thread, content, file=None):
        attachments = []
        if file is not None:
            attachments.append(
                {"file_id": file.id, "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]}
            )
        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=content, attachments=attachments
        )

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                # Handle user input using inherited method from AssistantEventHandler
                print(f'getting user input for')
                user_input = await self.on_user_input(text, role, name)
                self.messages.append(user_input)

                # Create a new thread
                thread = await self.on_create_thread(self.client)

                # Submit message and handle streaming response
                self.handle_streaming_response(thread, text, interaction_count)

                break  # Exit loop if successful

            except Exception as e:
                logger.error(f"Error in AssistantService completion: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise  # Re-raise the exception if all retries fail

    def handle_streaming_response(self, thread, text, interaction_count):
        try:
            event_handler = AssistantEventHandler()

            with self.client.beta.threads.runs.stream(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id,
                    instructions="Please address the user as Jane Doe. The user has a premium account.",
                    event_handler=event_handler
            ) as stream:

                final_response = event_handler.get_responses()
                self.emit_complete_sentences(final_response, interaction_count)
            # After streaming, process the collected responses

        except Exception as e:
            logger.error(f"Error in handle_streaming_response: {str(e)}")
            raise e

    def _extract_content(self, message):
        if isinstance(message.content, list) and len(message.content) > 0:
            content_block = message.content[0]
            if hasattr(content_block, 'text'):
                return content_block.text.value
        return None
