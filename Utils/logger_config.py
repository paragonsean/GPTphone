import loguru
import functools
import asyncio
import time
import importlib
import types
import os
from dotenv import load_dotenv
from loguru import logger
import logging
import sys

load_dotenv()

VALID_LOGGING_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
# Load environment variables from .env file
DEBUG_APP = os.getenv("DEBUG_APP", 'False').lower() == 'true'
DEBUG_SERVICES = os.getenv('DEBUG_SERVICES', 'False').lower() == 'true'
OTHER_SERVICES_DEBUG = os.getenv('OTHER_SERVICES_DEBUG', 'False').lower() == 'true'


logger.remove()

# Add a new handler with INFO level
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

def get_logger(name):
    return logger.bind(name=name)
logger = get_logger(__name__)

def configure_logger(level="INFO"):
    if not  DEBUG_APP:
        loguru.logger.remove()
        loguru.logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True
    )
        loguru.logger.enable("GPTphone")
    else:
        print("toobad")

DEBUG_APP=True

def configured_logger():
    loguru.logger.remove()
    loguru.logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True)
    return loguru.logger

def basic_logger(file_name, enabled=True, logging_level='INFO'):
    """Configure the logger."""
    if logging_level not in VALID_LOGGING_LEVELS:
        logging_level = "INFO"

    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger_debug = logging.getLogger(file_name)

    if not enabled:
        logger_debug.disabled = True
    return logger_debug





class EventHandlingDecorator:
    def __init__(self, event_handler, event_name):
        self.event_handler = event_handler
        self.event_name = event_name

    def __call__(self, func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            await self.event_handler.createEvent(f"{self.event_name}_before_call", func.__name__, args, kwargs)
            result = await func(*args, **kwargs)
            await self.event_handler.createEvent(f"{self.event_name}_after_call", func.__name__, result)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Run the asynchronous createEvent method in the background without blocking
            asyncio.ensure_future(
                self.event_handler.createEvent(f"{self.event_name}_before_call", func.__name__, args, kwargs))

            result = func(*args, **kwargs)

            asyncio.ensure_future(
                self.event_handler.createEvent(f"{self.event_name}_after_call", func.__name__, result))

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


def log_function_call(func, debug=DEBUG_SERVICES):
    """Log Function Call with Duration."""
    if debug:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs}")
            start_time = time.time()

            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds")
                    return result

                return async_wrapper(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds")
                return result

        return wrapper
    else:
        return func


def timer(func):
    """Time the execution of a function."""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        logger.info(f"Function {func.__name__!r} took {run_time:.4f} seconds")
        return result

    return wrapper_timer


def wrap_function_with_loguru(func):
    @logger.catch
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def wrap_functions_in_module(module):
    """Wraps all functions in the module with Loguru's logger.catch."""
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, types.FunctionType):
            setattr(module, attr_name, wrap_function_with_loguru(attr))


def recursively_wrap_functions_in_directory(directory_path):
    """Recursively wraps all functions in all Python modules within a directory."""
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".py"):
                module_path = os.path.join(root, file)
                module_name = os.path.relpath(module_path, directory_path).replace(os.sep, ".")[:-3]

                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    wrap_functions_in_module(module)
                except Exception as e:
                    logger.error(f"Failed to import or wrap module {module_name}: {e}")


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





def log_function_call(func, debug=DEBUG_SERVICES):
    """
    Log Function Call

    This function is used to log the call and duration of a given function. It wraps the function with a logging mechanism.

    :param func: The function to be wrapped and logged.
    :param debug: Boolean indicating whether logging is enabled or not. Default is `DEBUG_SERVICES`.
    :return: Wrapped function with logging mechanism.

    Example Usage:
    ```
    @log_function_call
    def my_function():
        return "Hello World"

    logged_func = log_function_call(my_function, debug=True)
    logged_func()
    ```
    """
    if debug:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs}")

            start_time = time.time()

            if asyncio.iscoroutinefunction(func):
                # If the function is a coroutine, return an async wrapper
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    duration = end_time - start_time
                    logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds")
                    return result

                return async_wrapper(*args, **kwargs)
            else:
                # If the function is synchronous, call it normally
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Function {func.__name__} completed with result: {result} in {duration:.4f} seconds")
                return result

        return wrapper
    else:
        return func


def timer(func):
    """
    :param func: The function to be timed.
    :return: The result of the function.

    This method is a decorator that times the execution of a given function. It wraps the function with a timer and logs the elapsed time using the logger module. The timer uses the `perf_counter()` method from the `time` module to measure the elapsed time.

    Usage:
        @timer
        def my_function():
            # code to be timed

    Example:
        @timer
        def fibonacci(n):
            if n <= 1:
                return n
            else:
                return fibonacci(n-1) + fibonacci(n-2)

    Note: The logger module must be properly configured before using the `timer` decorator. It's recommended to initialize the logger in the calling module before using this decorator.
    """
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
    Wrap Functions in Module

    :param module_name: The name of the module to import.
    :param debug: A boolean flag to control whether to apply the debug-related decorators.
    :param module_name: The name of the module to be wrapped.
    :type module_name: str
    :param debug: Whether to enable debug mode.
    :type debug: bool
    :return: The wrapped module.
    :rtype: module

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
    """
    Wrap Services Function
    =====================

    This function is used to wrap services.

    Returns:
        None
    """
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

