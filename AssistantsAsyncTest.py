import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from EventHandlers.assitant_event_manager import AssitantsEventHandler
from Utils.logger_config import configure_logger, log_function_call

load_dotenv()
logger = configure_logger(__name__)

# Load environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY")
azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.environ.get("AZURE_OPENAI_KEY")

client = AsyncOpenAI(api_key=openai_api_key)

def str_to_bool(str_input):
    if not isinstance(str_input, str):
        return False
    return str_input.lower() == "true"


@log_function_call
async def create_thread(content, file):
    return await client.beta.threads.create()

@log_function_call
async def create_message(thread, content, file):
    attachments = []
    if file is not None:
        attachments.append(
            {"file_id": file.id, "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]}
        )
    await client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=content, attachments=attachments
    )


async def run_stream(user_input, file, selected_assistant_id):
    thread = await create_thread(user_input, file)
    await create_message(thread, user_input, file)
    event_handler = AssitantsEventHandler()  # Create an instance of the event handler with session state

    # Use the AsyncAssistantStreamManager to manage the stream asynchronously
    async with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=selected_assistant_id,
        event_handler=event_handler,
    ) as stream:
        async for event in stream:
            # Process each event as it arrives
            pass

    # Access the session state from the event handler if needed
    session_state = event_handler.session_state
    print("\nFinal Chat Log:")
    for log in session_state["chat_log"]:
        print(f"{log['name']}: {log['msg']}")

