import importlib
import inspect
import asyncio
from typing import Callable, Any, Dict
from functions.function_manifest import tools  # Import the tools library
from Utils.logger_config import get_logger

logger = get_logger(__name__)


class FunctionHandler:
    def __init__(self):
        self.functions: Dict[str, Callable] = {}
        self.register_functions_from_tools()  # Automatically register functions from the tools library

    def register_function(self, name: str, func: Callable):
        print(name)
        print(inspect.signature(func))

        self.functions[name] = func

    def register_functions_from_tools(self):
        for tool in tools:
            function_name = tool['function']['name']
            module = importlib.import_module(f'functions.{function_name}')
            logger.log(module)
            function = getattr(module, function_name)
            self.register_function(function_name, function)

    async def call_function(self, name: str, *args, **kwargs):
        if name not in self.functions:
            raise ValueError(f"Function {name} not registered")

        func = self.functions[name]
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        logger.log(bound_args)
        bound_args.apply_defaults()

        if asyncio.iscoroutinefunction(func):
            return await func(*bound_args.args, **bound_args.kwargs)
        else:
            return func(*bound_args.args, **bound_args.kwargs)

    def get_function_signature(self, name: str):
        if name not in self.functions:
            raise ValueError(f"Function {name} not registered")

        func = self.functions[name]
        sig = inspect.signature(func)
        return sig


