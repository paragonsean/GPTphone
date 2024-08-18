from typing import List, Optional, Dict, Any, Callable
import importlib
from Utils import log_function_call
from loguru import logger
from functions import get_tools, get_current_weather, end_call, transfer_call
logger = logger.bind(name=__name__)

class CallContext:
    """Store context for the current call."""

    def __init__(self):
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.call_ended: bool = False
        self.user_context: List = []
        self.system_message: str = ""
        self.initial_message: str = ""
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.final_status: Optional[str] = None
        self.tools: Optional[List[Dict[str, Any]]] = None
        self.available_functions: Dict[str, Callable] = {}  # Store loaded functions

    @log_function_call
    def set_tools(self, tools: Optional[List[Dict[str, Any]]] = None):
        """Set the tools for the current context and load the corresponding functions."""
        if tools is None:
            self.tools = get_tools()
        else:
            self.tools = tools
        self.validate_and_load_tools()
        logger.info(self.available_functions)

    @log_function_call
    def validate_and_load_tools(self):
        """Validate that each tool in the tools list has a corresponding function in available_functions."""
        if not self.tools:
            self.tools = get_tools()


        missing_functions = []
        for tool in self.tools:
            function_name = tool['function']['name']
            try:
                # Dynamically import the module based on the function name
                module = importlib.import_module(f'{function_name}')
                # Get the function from the module and store it in available_functions
                self.available_functions[function_name] = getattr(module, function_name)

            except (ImportError, AttributeError) as e:
                missing_functions.append(function_name)
                logger.error(f"Function '{function_name}' could not be loaded: {str(e)}")

        if missing_functions:
            raise ValueError(
                f"The following functions are missing or could not be loaded: {', '.join(missing_functions)}")

        logger.info("All tools are correctly validated and loaded.")

    @log_function_call
    def add_to_user_context(self, message: Dict[str, Any]):
        """Add a message to the user context."""
        self.user_context.append(message)