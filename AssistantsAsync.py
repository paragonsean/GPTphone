import os
import base64
import re
import json
from tools import TOOL_MAP
from typing_extensions import override
from dotenv import load_dotenv
from Utils.logger_config import get_logger, log_function_call
import asyncio
from openai import AsyncOpenAI, AsyncAssistantEventHandler

load_dotenv()
logger = get_logger(__name__)

# Load environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY")
azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.environ.get("AZURE_OPENAI_KEY")

client = AsyncOpenAI(api_key=openai_api_key)

def str_to_bool(str_input):
    if not isinstance(str_input, str):
        return False
    return str_input.lower() == "true"

class EventHandler(AsyncAssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.session_state = {
            "chat_log": [],
            "tool_calls": [],
            "current_message": "",
            "current_markdown": "",
            "current_tool_input": "",
            "current_tool_input_markdown": ""
        }

    @override
    async def on_event(self, event):
        pass

    @override
    @log_function_call
    async def on_text_created(self, text):
        self.session_state["current_message"] = ""
        print("Assistant:")

    @override
    async def on_text_delta(self, delta, snapshot):
        if snapshot.value:
            text_value = re.sub(
                r"\[(.*?)\]\s*\(\s*(.*?)\s*\)", "Download Link", snapshot.value
            )
            self.session_state["current_message"] = text_value
            print(text_value, end="", flush=True)

    @override
    @log_function_call
    async def on_text_done(self, text):
        format_text = self.format_annotation(text)
        print("\n" + format_text)
        self.session_state["chat_log"].append({"name": "assistant", "msg": format_text})

    @override
    async def on_tool_call_created(self, tool_call):
        if tool_call.type == "code_interpreter":
            self.session_state["current_tool_input"] = ""
            print("Assistant:")

    @override
    async def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                self.session_state["current_tool_input"] += delta.code_interpreter.input
                input_code = f"### code interpreter\ninput:\n```python\n{self.session_state['current_tool_input']}\n```"
                print(input_code, end="", flush=True)

            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        pass

    @override
    async def on_tool_call_done(self, tool_call):
        self.session_state["tool_calls"].append(tool_call)
        if tool_call.type == "code_interpreter":
            input_code = f"### code interpreter\ninput:\n```python\n{tool_call.code_interpreter.input}\n```"
            print(input_code)
            for output in tool_call.code_interpreter.outputs:
                if output.type == "logs":
                    output = f"### code interpreter\noutput:\n```\n{output.logs}\n```"
                    print(output)

        elif (
            tool_call.type == "function"
            and self.current_run.status == "requires_action"
        ):
            msg = f"### Function Calling: {tool_call.function.name}"
            print(msg)
            self.session_state["chat_log"].append({"name": "assistant", "msg": msg})
            tool_calls = self.current_run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []
            for submit_tool_call in tool_calls:
                tool_function_name = submit_tool_call.function.name
                tool_function_arguments = json.loads(
                    submit_tool_call.function.arguments
                )
                tool_function_output = TOOL_MAP[tool_function_name](
                    **tool_function_arguments
                )
                tool_outputs.append(
                    {
                        "tool_call_id": submit_tool_call.id,
                        "output": tool_function_output,
                    }
                )

            async with client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=thread.id,
                run_id=self.current_run.id,
                tool_outputs=tool_outputs,
                event_handler=EventHandler(),
            ) as stream:
                await stream.until_done()

    @log_function_call
    def format_annotation(self, text):
        citations = []
        text_value = text.value
        for index, annotation in enumerate(text.annotations):
            text_value = text_value.replace(annotation.text, f" [{index}]")

            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(
                    f"[{index}] {file_citation.quote} from {cited_file.filename}"
                )
            elif file_path := getattr(annotation, "file_path", None):
                link_tag = self.create_file_link(
                    annotation.text.split("/")[-1],
                    file_path.file_id,
                )
                text_value = re.sub(r"\[(.*?)\]\s*\(\s*(.*?)\s*\)", link_tag, text_value)
        text_value += "\n\n" + "\n".join(citations)
        return text_value

    def create_file_link(self, file_name, file_id):
        content = client.files.content(file_id)
        content_type = content.response.headers["content-type"]
        b64 = base64.b64encode(content.text.encode(content.encoding)).decode()
        link_tag = f'<a href="data:{content_type};base64,{b64}" download="{file_name}">Download Link</a>'
        return link_tag

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
    event_handler = EventHandler()  # Create an instance of the event handler with session state

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

async def main():
    # Simulate user input and assistant interaction
    user_input = input("You: ")
    assistant_id = os.environ.get("ASSISTANT_ID", "default_assistant")

    # Simulate a file upload (disabled in this example)
    uploaded_file = None

    # Run the stream
    while user_input != "q":
        await run_stream(user_input, uploaded_file, assistant_id)  # Await the async run_stream
        user_input = input("You: ")

if __name__ == "__main__":
    asyncio.run(main())  # Run the main function in the event loop
