import os
import base64
import re
import json
import openai
from tools import TOOL_MAP
from typing_extensions import override
from dotenv import load_dotenv
from Utils.logger_config import get_logger,log_function_call
load_dotenv()
logger = get_logger(__name__)
def str_to_bool(str_input):
    """
    Convert a string to a boolean value.

    :param str_input: The string to convert.
    :return: The boolean value converted from the string.
    """
    if not isinstance(str_input, str):
        return False
    return str_input.lower() == "true"


# Load environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY")
azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.environ.get("AZURE_OPENAI_KEY")

client = None
if azure_openai_endpoint and azure_openai_key:
    client = openai.AzureOpenAI(
        api_key=azure_openai_key,
        api_version="2024-05-01-preview",
        azure_endpoint=azure_openai_endpoint,
    )
else:
    client = openai.OpenAI(api_key=openai_api_key)


class EventHandler(openai.AssistantEventHandler):
    """

    Class EventHandler

    This class is a subclass of the openai.AssistantEventHandler class and contains various methods that handle different events related to the OpenAI Assistant.

    Attributes:
    - session_state (dict): A dictionary that stores the current state of the session, including chat log, tool calls, current message, current markdown, current tool input, and current tool input markdown.

    Methods:
    - on_event(event): Handles the general event. This method is not implemented in the EventHandler class and needs to be overridden in a subclass.
    - on_text_created(text): Handles the event when a new text is created. It sets the current message to empty and prints "Assistant:".
    - on_text_delta(delta, snapshot): Handles the event when a delta change is made to the text. It updates the current message in the session state and prints the updated text.
    - on_text_done(text): Handles the event when the text is complete. It formats the annotation in the text, prints the formatted text, and appends it to the chat log in the session state.
    - on_tool_call_created(tool_call): Handles the event when a tool call is created. If the tool call is of type "code_interpreter", it sets the current tool input to empty and prints "Assistant:".
    - on_tool_call_delta(delta, snapshot): Handles the event when a delta change is made to the tool call. If the delta is of type "code_interpreter", it updates the current tool input in the session state and prints the input code.
    - on_tool_call_done(tool_call): Handles the event when the tool call is complete. It appends the tool call to the tool calls list in the session state. If the tool call is of type "code_interpreter", it prints the input code and outputs.
    - format_annotation(text): Formats the annotation in the given text by replacing annotation texts with numbered references and creating download links for file citations. Returns the formatted text.
    - create_file_link(file_name, file_id): Creates a download link for the given file name and file ID. Returns the link tag.

    Note: This class needs to be subclassed and the on_event() method needs to be implemented in the subclass.

    """
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
    def on_event(self, event):
        pass

    @override
    @log_function_call
    def on_text_created(self, text):
        self.session_state["current_message"] = ""
        print("Assistant:")

    @override
    @log_function_call
    def on_text_delta(self, delta, snapshot):
        if snapshot.value:
            text_value = re.sub(
                r"\[(.*?)\]\s*\(\s*(.*?)\s*\)", "Download Link", snapshot.value
            )
            self.session_state["current_message"] = text_value
            print(text_value, end="", flush=True)
    @log_function_call
    @override
    def on_text_done(self, text):
        format_text = self.format_annotation(text)
        print("\n" + format_text)
        self.session_state["chat_log"].append({"name": "assistant", "msg": format_text})

    @override
    def on_tool_call_created(self, tool_call):
        if tool_call.type == "code_interpreter":
            self.session_state["current_tool_input"] = ""
            print("Assistant:")

    @override
    def on_tool_call_delta(self, delta, snapshot):
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
    def on_tool_call_done(self, tool_call):
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

            with client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=thread.id,
                    run_id=self.current_run.id,
                    tool_outputs=tool_outputs,
                    event_handler=EventHandler(),
            ) as stream:
                stream.until_done()
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
def create_thread(content, file):
    """

    :param content: The content of the thread.
    :param file: The file associated with the thread.
    :return: The created thread.

    """
    return client.beta.threads.create()

@log_function_call
def create_message(thread, content, file):
    """
    :param thread: A Thread object representing the thread where the message will be created.
    :param content: A string representing the content of the message.
    :param file: An optional File object representing a file attachment for the message.
    :return: None

    This method creates a message in a given thread using the provided content and file attachment, if any. If a file attachment is provided, it is added to the message as an attachment with specific tools associated with it. The message is created using the client.beta.threads.messages.create() method, specifying the thread id, role, content, and attachments parameters.
    """
    attachments = []
    if file is not None:
        attachments.append(
            {"file_id": file.id, "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]}
        )
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=content, attachments=attachments
    )

@log_function_call
def run_stream(user_input, file, selected_assistant_id):
    """
    :param user_input: The input from the user.
    :param file: The file to be processed.
    :param selected_assistant_id: The ID of the selected assistant.
    :return: None

    This method runs a stream for a chat session using the given user input, file, and selected assistant ID. It creates a thread, sends messages to the thread, and handles events using the event handler. The chat log is printed at the end of the session.
    """
    thread = create_thread(user_input, file)
    create_message(thread, user_input, file)
    event_handler = EventHandler()  # Create an instance of the event handler with session state
    with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=selected_assistant_id,
            event_handler=event_handler,
    ) as stream:
        stream.until_done()

    # Access the session state from the event handler if needed
    session_state = event_handler.session_state
    print("\nFinal Chat Log:")
    for log in session_state["chat_log"]:
        print(f"{log['name']}: {log['msg']}")


def main():
    """
    Entry point for the program.

    :return: None
    """
    # Simulate user input and assistant interaction
    user_input = input("You: ")
    assistant_id = os.environ.get("ASSISTANT_ID", "default_assistant")

    # Simulate a file upload (disabled in this example)
    uploaded_file = None

    # Run the stream
    while user_input != "q":
        run_stream(user_input, uploaded_file, assistant_id)
        user_input = input("You: ")

if __name__ == "__main__":
    main()
