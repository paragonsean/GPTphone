import sys
from loguru import logger
import functools
import asyncio

# Configure loguru
logger.remove()  # Remove the default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

def get_logger(name):
    return logger.bind(name=name)


def log_function_call(func):
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
