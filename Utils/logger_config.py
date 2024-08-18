import sys
from loguru import logger
import functools
import asyncio
import time
import importlib
import types
from dotenv import load_dotenv
import os
import logging

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


def get_logger(name):
    """Get a logger object."""
    return logger.bind(name=name)


VALID_LOGGING_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


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


def configure_logger(file_name, enabled=True, logging_level='INFO'):
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


def timer(func):
    """Time the execution of a function."""
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()  # Start the timer
        result = func(*args, **kwargs)
        end_time = time.perf_counter()  # End the timer
        run_time = end_time - start_time  # Calculate the elapsed time
        logger.info(f"Function {func.__name__!r} took {run_time:.4f} seconds")
        return result

    return wrapper_timer


def wrap_functions_in_module(module, debug):
    """Wrap Functions in the Provided Module."""
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, types.FunctionType):
            wrapped_func = log_function_call(attr, debug)
            wrapped_func = timer(wrapped_func)
            setattr(module, attr_name, wrapped_func)


def wrap_services_in_root_dir():
    """Wrap All Functions in Python Files in the Root Directory."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    for file_name in os.listdir(root_dir):
        if file_name.endswith(".py"):
            module_name = os.path.splitext(file_name)[0]
            if module_name == os.path.splitext(os.path.basename(__file__))[0]:
                # Skip this file (app.py) on this pass to avoid issues during import
                continue
            module = importlib.import_module(module_name)
            wrap_functions_in_module(module, DEBUG_SERVICES)

    # Finally, wrap functions in app.py itself
    wrap_functions_in_module(importlib.import_module(os.path.splitext(os.path.basename(__file__))[0]), DEBUG_APP)


if __name__ == "__main__":
    wrap_services_in_root_dir()
    logger.info("Starting the application...")
