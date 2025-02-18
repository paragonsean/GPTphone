import asyncio
from typing import Any, Callable, Dict, List
from Utils.logger_config import log_function_call, configure_logger
import re
import json


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


    def on(self, event: str, callback: Callable):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)


    async def createEvent(self, event: str, *args: Any, **kwargs: Any):
        if event in self._events:
            for callback in self._events[event]:
                await self._run_callback(callback, *args, **kwargs)


    async def _run_callback(self, callback: Callable, *args: Any, **kwargs: Any):
        if asyncio.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        else:
            callback(*args, **kwargs)





