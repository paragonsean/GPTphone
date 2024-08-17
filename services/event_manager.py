import asyncio
from typing import Any, Callable, Dict, List
from Utils.logger_config import logger, log_function_call, get_logger
from typing import re
import json
import openai
from openai import AssistantEventHandler
from typing_extensions import override
logger = get_logger(__name__)
from functions.function_manifest import tools as TOOL_MAP

class EventHandler:
    """
    .. module:: event_handler
       :synopsis: This module contains the EventHandler class.

    .. moduleauthor:: Your Name

    .. autoclass:: EventHandler
       :members:
       :undoc-members:
       :show-inheritance:
       :private-members:
       :special-members:

    """

    def __init__(self):
        """
        Initializes an instance of the EventEmitter class.
        """
        self._events: Dict[str, List[Callable]] = {}

    @log_function_call
    def on(self, event: str, callback: Callable):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)

    @log_function_call
    async def createEvent(self, event: str, *args: Any, **kwargs: Any):
        if event in self._events:
            for callback in self._events[event]:
                await self._run_callback(callback, *args, **kwargs)

    @log_function_call
    async def _run_callback(self, callback: Callable, *args: Any, **kwargs: Any):
        if asyncio.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        else:
            callback(*args, **kwargs)



class EventHandler(AssistantEventHandler):
    """

    This class is an implementation of the AssistantEventHandler abstract class. It handles various events that occur during the execution of an Assistant.

    :ivar client: The Assistant client used to interact with the Assistant API.
    :type client: AssistantClient

    Methods:
    ---------

    __init__(self, client)
        Initializes a new instance of the EventHandler class.

        :param client: The Assistant client used to interact with the Assistant API.
        :type client: AssistantClient

    on_event(self, event)
        This method is called when an event occurs. Subclasses should override this method to handle specific events.

        :param event: The event that occurred.
        :type event: Event

    on_text_created(self, text)
        This method is called when a new text is created by the Assistant.

        :param text: The newly created text.
        :type text: str

    on_text_delta(self, delta, snapshot)
        This method is called when a delta update is received for a text.

        :param delta: The delta update.
        :type delta: TextDelta
        :param snapshot: The current snapshot of the text.
        :type snapshot: TextSnapshot

    on_text_done(self, text)
        This method is called when the Assistant has finished generating the final text.

        :param text: The final generated text.
        :type text: str

    on_tool_call_created(self, tool_call)
        This method is called when a tool call is created by the Assistant.

        :param tool_call: The tool call that was created.
        :type tool_call: ToolCall

    on_tool_call_delta(self, delta, snapshot)
        This method is called when a delta update is received for a tool call.

        :param delta: The delta update.
        :type delta: ToolCallDelta
        :param snapshot: The current snapshot of the tool call.
        :type snapshot: ToolCallSnapshot

    on_tool_call_done(self, tool_call)
        This method is called when a tool call has completed.

        :param tool_call: The tool call that has completed.
        :type tool_call: ToolCall

    submit_tool_outputs(self, tool_outputs)
        Submits the outputs of tool calls to the Assistant API.

        :param tool_outputs: The outputs of the tool calls.
        :type tool_outputs: List[dict]
    """
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
        format_text = format_annotation(self.client, text)
        print(f"Final message: {format_text}")
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


