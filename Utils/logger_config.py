import asyncio
import functools
import importlib
import inspect
import os
import pkgutil
import sys
import time
import types

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Define valid logging levels
VALID_LOGGING_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Environment flags for debugging
DEBUG_APP = os.getenv("DEBUG_APP", 'True').lower() == 'true'
DEBUG_SERVICES = os.getenv('DEBUG_SERVICES', 'True').lower() == 'true'
OTHER_SERVICES_DEBUG = os.getenv('OTHER_SERVICES_DEBUG', 'True').lower() == 'true'
SERVICES = os.getenv('SERVICES', '').split(',')





loguru_logger = logger.bind(name='loguru')









def wrap_function_with_loguru(func):
    """
    Wrap a function with Loguru's loguru_logger.catch decorator.

    :param func: The function to wrap.
    :return: Wrapped function.
    """

    @logger.catch
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def wrap_functions_in_module(module):
    """
    Wrap all functions in a module with Loguru's logger.catch.

    :param module: The module to wrap functions in.
    """
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, types.FunctionType):
            setattr(module, attr_name, wrap_function_with_loguru(attr))


def recursively_wrap_functions_in_directory(directory_path):
    """
    Recursively wrap all functions in all Python modules within a directory.

    :param directory_path: The path of the directory to search through.
    """
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


def log_function_call(func, debug=DEBUG_SERVICES):
    """
    Log the call and duration of a function.

    :param func: The function to wrap and log.
    :param debug: Whether logging is enabled.
    :return: Wrapped function with logging.
    """
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
    """
    Time the execution of a function and log the duration.

    :param func: The function to time.
    :return: Wrapped function with timing.
    """

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        logger.info(f"Function {func.__name__!r} took {run_time:.4f} seconds")
        return result

    return wrapper_timer


def wrap_functions_in_module(module_name, debug):
    """
    Import a module and wrap its functions with the given decorators.

    :param module_name: The name of the module to import.
    :param debug: Whether to enable debug mode.
    :return: Wrapped module.
    """
    module = importlib.import_module(module_name)
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        print(f"Wrapping {attr_name}")
        if isinstance(attr, types.FunctionType):
            wrapped_func = log_function_call(attr, debug)
            wrapped_func = timer(wrapped_func)
            setattr(module, attr_name, wrapped_func)
    return module


def wrap_services():
    """
    Wrap all specified service modules with decorators.
    """
    for service in SERVICES:
        if DEBUG_SERVICES:
            wrap_functions_in_module(service, DEBUG_SERVICES)
        else:
            wrap_functions_in_module(service, OTHER_SERVICES_DEBUG)

    # Wrap the `app` module if DEBUG_APP is enabled
    if DEBUG_APP:
        wrap_functions_in_module('app', DEBUG_APP)






def find_functions_in_package(package_name):
    """Search through every module in a package and pull out every function."""
    all_functions = {}

    package = importlib.import_module(package_name)
    for importer, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module = importlib.import_module(modname)
        functions = {}

        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj):
                functions[name] = obj

        if functions:
            all_functions[modname] = functions

    return all_functions


# Example usage:
package_name = "services"
functions = find_functions_in_package(package_name)
for module_name, funcs in functions.items():
    print(f"Module: {module_name}")
    for func_name in funcs:
        print(f"  Function: {func_name}")
