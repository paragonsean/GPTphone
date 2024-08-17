import asyncio
from typing import Any, Callable, Dict, List
from openai import AsyncAssistantEventHandler
import time
from Utils.logger_config import logger,log_function_call,get_logger
'''
Author: Sean Baker
Date: 2024-07-22
Description: STANDARD EVENT HANDLER
'''
logger=get_logger(__name__)

class EventHandler:
    """
    A class that represents an event emitter.

    An event emitter allows registering callbacks for specific events and emitting those events
    with optional arguments and keyword arguments.
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


class AssistantEventHandler(EventHandler, AsyncAssistantEventHandler):
    """
    A class that combines the functionality of a general EventHandler
    with the OpenAI-specific AssistantEventHandler.
    """
    @log_function_call
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
        asyncio.run(self.createEvent("text_created", text))
    @log_function_call
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        asyncio.run(self.createEvent("text_delta", delta, snapshot))
    @log_function_call
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)
        asyncio.run(self.createEvent("tool_call_created", tool_call))
    @log_function_call
    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)
        asyncio.run(self.createEvent("tool_call_delta", delta, snapshot))

