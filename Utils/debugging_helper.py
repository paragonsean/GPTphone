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
import ast
import os
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

# Define valid logging levels
VALID_LOGGING_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Environment flags for debugging
DEBUG_APP = os.getenv("DEBUG_APP", 'True').lower() == 'true'
DEBUG_SERVICES = os.getenv('DEBUG_SERVICES', 'True').lower() == 'true'
OTHER_SERVICES_DEBUG = os.getenv('OTHER_SERVICES_DEBUG', 'True').lower() == 'true'
SERVICES = os.getenv('SERVICES', '').split(',')

loguru_logger = logger.bind(name=__name__)



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







def log_function_call(func=None, debug=DEBUG_SERVICES):
    """
    Decorator to log the call and duration of a function, and automatically log the wrapping of the function.

    :param func: The function to wrap and log.
    :param debug: Whether logging is enabled.
    :return: Wrapped function with logging.
    """
    if func is None:
        # This allows the decorator to be used with or without parentheses
        return functools.partial(log_function_call, debug=debug)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if debug:
            logger.info(f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs}")
            start_time = time.time()

            if asyncio.iscoroutinefunction(func):
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
        else:
            return func(*args, **kwargs)

    # Automatically log the wrapping of the function
    logger.info(f"Wrapping function: {func.__name__} with log_function_call")

    return wrapper


def wrap_all_functions_in_module(module):
    """
    Wrap all functions in the provided module with the log_function_call decorator,
    ensuring it is applied before any existing decorators.

    :param module: The module to wrap functions in.
    """
    for attr_name in dir(module):
        attr = getattr(module, attr_name)

        # Check if the attribute is a function or coroutine function
        if isinstance(attr, types.FunctionType) or asyncio.iscoroutinefunction(attr):

            # Check if the function has already been wrapped with log_function_call
            if getattr(attr, "_is_logged", False):
                continue

            # Apply the log_function_call decorator first
            wrapped = log_function_call(attr)
            wrapped._is_logged = True  # Mark the function as wrapped

            # Reapply any existing decorators, ensuring log_function_call is applied first
            setattr(module, attr_name, wrapped)





# app_root = os.path.dirname(os.path.abspath(__file__))


# def trace_calls(frame, event, arg):
#     if event != 'call':
#         return
#     co = frame.f_code
#     func_name = co.co_name
#     line_no = frame.f_lineno
#     filename = co.co_filename
#
#     # Only trace calls within the application root directory
#     if filename.startswith(app_root):
#         print(f"Call to {func_name} in {filename}:{line_no}")
#     return trace_calls
#
#
# # Set the trace function
# sys.settrace(trace_calls)


def find_imports_in_file(filepath):
    """Parse a Python file and return a list of imported modules."""
    with open(filepath, "r", encoding="utf-8") as file:
        node = ast.parse(file.read(), filename=filepath)

    imports = []

    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.append(alias.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                imports.append(n.module)

    return imports


def build_import_graph(directory):
    """Build an import graph from the directory structure."""
    graph = defaultdict(list)
    module_file_map = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                filepath = os.path.join(root, file)
                module_name = os.path.splitext(filepath.replace(directory, "").replace(os.path.sep, "."))[0].strip(".")
                imported_modules = find_imports_in_file(filepath)
                for imported_module in imported_modules:
                    graph[module_name].append(imported_module)
                module_file_map[module_name] = filepath

    return graph, module_file_map


def detect_cycles(graph):
    """Detect cycles in the import graph using DFS."""

    def dfs(node, visited, stack):
        visited.add(node)
        stack.add(node)
        for neighbor in graph.get(node, []):  # Use .get to avoid KeyError
            if neighbor not in visited:
                cycle = dfs(neighbor, visited, stack)
                if cycle:
                    return cycle
            elif neighbor in stack:
                return list(stack) + [neighbor]  # Return the cycle as a list
        stack.remove(node)
        return None

    visited = set()
    for node in list(graph.keys()):
        if node not in visited:
            cycle = dfs(node, visited, set())
            if cycle:
                return cycle
    return None


def move_import_to_function(filepath, import_name):
    """Move an import statement inside a function in the file to break a circular dependency."""
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    new_lines = []
    import_moved = False

    for line in lines:
        if not import_moved and (f"import {import_name}" in line or f"from {import_name}" in line):
            # Move this import into the first function or method
            import_moved = True
            for i, l in enumerate(lines):
                print(line, end="")
                if l.strip().startswith("def ") or l.strip().startswith("class "):
                    indent = ' ' * (len(l) - len(l.lstrip()))
                    new_lines.append(f"{indent}{line.strip()}\n")
                    break
        else:
            new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as file:
        file.writelines(new_lines)


def fix_circular_imports(directory):
    """Detect and attempt to fix circular imports in the given directory."""
    graph, module_file_map = build_import_graph(directory)
    cycle = detect_cycles(graph)

    if cycle:
        print("Circular import detected between the following modules:")
        for node in cycle:
            print(f"  {node}")
        print("Attempting to fix the circular import...")

        # Attempt to break the cycle by moving imports inside functions
        for module in cycle:
            filepath = module_file_map[module]
            for neighbor in graph[module]:
                if neighbor in cycle:
                    print(f"  Moving import of {neighbor} in {module}")
                    move_import_to_function(filepath, neighbor)

        print("Fix applied. Please review the changes manually.")

    else:
        print("No circular imports detected.")


