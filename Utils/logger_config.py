import sys
from loguru import logger
import functools
import asyncio
import time
import importlib
import types
from dotenv import load_dotenv
import os

# Configure loguru
logger.remove()  # Remove the default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# Load environment variables from .env file
load_dotenv()
DEBUG_APP = os.getenv("DEBUG_APP", 'False').lower() == 'true'
DEBUG_SERVICES = os.getenv('DEBUG_SERVICES', 'False').lower() == 'true'
OTHER_SERVICES_DEBUG = os.getenv('OTHER_SERVICES_DEBUG', 'False').lower() == 'true'
SERVICES = os.getenv('SERVICES', '').split(',')


def get_logger(name):
    return logger.bind(name=name)


def log_function_call(func, debug=DEBUG_SERVICES):
    if debug:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs}")

            if asyncio.iscoroutinefunction(func):
                # If the function is a coroutine, return an async wrapper
                async def async_wrapper(*args, **kwargs):
                    result = await func(*args, **kwargs)
                    logger.info(f"Function {func.__name__} completed with result: {result}")
                    return result

                return async_wrapper(*args, **kwargs)
            else:
                # If the function is synchronous, call it normally
                result = func(*args, **kwargs)
                logger.info(f"Function {func.__name__} completed with result: {result}")
                return result

        return wrapper
    else:
        return func


def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()  # Start the timer
        result = func(*args, **kwargs)
        end_time = time.perf_counter()  # End the timer
        run_time = end_time - start_time  # Calculate the elapsed time
        logger.info(f"Function {func.__name__!r} took {run_time:.4f} seconds")
        return result

    return wrapper_timer


def wrap_functions_in_module(module_name, debug):
    """
    Imports a module and wraps its functions with the given decorators.

    :param module_name: The name of the module to import.
    :param debug: A boolean flag to control whether to apply the debug-related decorators.
    """
    module = importlib.import_module(module_name)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        print("Wrapping {}".format(attr_name))
        if isinstance(attr, types.FunctionType):
            wrapped_func = log_function_call(attr, debug)
            wrapped_func = timer(wrapped_func)
            setattr(module, attr_name, wrapped_func)
    return module


# Create a function to wrap all specified service modules
def wrap_services():
    for service in SERVICES:
        if DEBUG_SERVICES:
            wrap_functions_in_module(service, DEBUG_SERVICES)
        else:
            wrap_functions_in_module(service, OTHER_SERVICES_DEBUG)

    # Wrap the `app` module if DEBUG_APP is enabled
    if DEBUG_APP:
        wrap_functions_in_module('app', DEBUG_APP)


if __name__ == "__main__":
    wrap_services()
