import base64
import json
import os
import re
import sys

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.lib.streaming import AsyncAssistantEventHandler
from typing_extensions import override
from functions.tools import TOOL_MAP


# Load environment variables from a .env file
load_dotenv()

class AssitantsEventHandler(AsyncAssistantEventHandler):
    def __init__(self, client=None):
        super().__init__()
        if client is None:
            # Load the API key from the environment
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")

            # Initialize the AsyncOpenAI client with the API key
            client = AsyncOpenAI(api_key=api_key)

        self.client = client  # Store the client instance
        self.session_state = {
            "chat_log": [],
            "tool_calls": [],
            "current_message": "",
            "current_markdown": "",
            "current_tool_input": TOOL_MAP,
            "current_tool_input_markdown": ""
        }

    @override
    async def on_event(self, event):
        pass

    @override
 
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

            async with self.client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=self.thread.id,
                run_id=self.current_run.id,
                tool_outputs=tool_outputs,
                event_handler=AssitantsEventHandler(),
            ) as stream:
                await stream.until_done()


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

class AssitantEventHandler(AsyncAssistantEventHandler):

    def __init__(self, client):
        self.client = client

    @override
    def on_event(self, event):
        pass

    @override
    def on_text_created(self, text):
        print("Assistant started generating text.")
        # Logic to handle when the text is first created

    @override
    def on_text_delta(self, delta, snapshot):
        if snapshot.value:
            text_value = re.sub(
                r"\[(.*?)\]\s*\(\s*(.*?)\s*\)", "Download Link", snapshot.value
            )
            print(f"Current message: {text_value}")

    @override
    def on_text_done(self, text):
        print(f"Final message: {text}")
        # Here you could store the final text, log it, etc.

    @override
    def on_tool_call_created(self, tool_call):
        if tool_call.type == "code_interpreter":
            print("Code Interpreter tool is being called.")
            # Logic to handle when a tool call is created

    @override
    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "code_interpreter":
            if delta.code_interpreter.input:
                input_code = delta.code_interpreter.input
                print(f"Code Interpreter input:\n{input_code}")

            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"Code Interpreter output logs:\n{output.logs}")

    @override
    def on_tool_call_done(self, tool_call):
        print(f"Tool call {tool_call.type} completed.")
        if tool_call.type == "code_interpreter":
            input_code = f"Input code:\n{tool_call.code_interpreter.input}"
            print(input_code)
            for output in tool_call.code_interpreter.outputs:
                if output.type == "logs":
                    print(f"Code Interpreter output:\n{output.logs}")
        elif tool_call.type == "function":
            print(f"Function {tool_call.function.name} called.")
            tool_calls = self.current_run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []
            for submit_tool_call in tool_calls:
                tool_function_name = submit_tool_call.function.name
                tool_function_arguments = json.loads(submit_tool_call.function.arguments)
                tool_function_output = TOOL_MAP[tool_function_name](
                    **tool_function_arguments
                )
                tool_outputs.append(
                    {
                        "tool_call_id": submit_tool_call.id,
                        "output": tool_function_output,
                    }
                )

            self.submit_tool_outputs(tool_outputs)

    def submit_tool_outputs(self, tool_outputs):
        with self.client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=self,
        ) as stream:
            stream.until_done()