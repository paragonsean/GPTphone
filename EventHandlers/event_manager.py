import asyncio
from typing import Any, Callable, Dict, List
from Utils.logger_config import logger, log_function_call, get_logger
import re
import json

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





