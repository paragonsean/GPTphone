import asyncio
from typing import Dict, List, Callable, Any
from abc import ABC, abstractmethod

class EventHandler:
    """
    A class that represents an event emitter.

    An event emitter allows registering callbacks for specific events and emitting those events
    with optional arguments and keyword arguments.
    """

    def __init__(self, debug: bool = False):
        """
        Initializes an instance of the EventEmitter class.
        
        Parameters:
            debug (bool): If True, prints debug information.
        """
        self._events: Dict[str, List[Callable]] = {}
        self.debug = debug

    def on(self, event: str, callback: Callable):
        """
        Registers a callback for a specific event.
        
        Parameters:
            event (str): The name of the event.
            callback (Callable): The callback function to register.
        """
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)
        if self.debug:
            print(f"Registered callback for event: {event}")

    async def createEvent(self, event: str, *args: Any, **kwargs: Any):
        """
        Emits an event, calling all registered callbacks with the provided arguments.
        
        Parameters:
            event (str): The name of the event.
            *args: Positional arguments to pass to the callback functions.
            **kwargs: Keyword arguments to pass to the callback functions.
        """
        if self.debug:
            print(f"Emitting event: {event} with args: {args} and kwargs: {kwargs}")
            
        if event in self._events:
            print(f'Event is: {event}')
            for callback in self._events[event]:
                print(f'callback is {callback}') 
                await self._run_callback(callback, *args, **kwargs)

    async def _run_callback(self, callback: Callable, *args: Any, **kwargs: Any):
        """
        Runs a callback, awaiting it if it is a coroutine.
        
        Parameters:
            callback (Callable): The callback function to run.
            *args: Positional arguments to pass to the callback function.
            **kwargs: Keyword arguments to pass to the callback function.
        """
        if self.debug:
            print(f"Running callback: {callback.__name__} with args: {args} and kwargs: {kwargs}")
            
        if asyncio.iscoroutinefunction(callback):
            if self.debug:
                print(f"Running coroutine callback: {callback.__name__} with args: {args} and kwargs: {kwargs}")
            
                await callback(*args, **kwargs)
        else:
            print(f"Running non_coroutine callback: {callback.__name__} with args: {args} and kwargs: {kwargs}")
            callback(*args, **kwargs)
