import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from threading import Timer
from typing import List, Optional, Dict, Callable, Any
import importlib
import logging
from datetime import datetime
from Utils.utils import convert_to_request_log, write_json_file, write_request_logs, format_messages
from functions import get_tools, get_current_weather
from Utils import log_function_call
logger = logging.getLogger(__name__)

@dataclass
class CallContext:
    """Store context for the current call."""
    phone_number: Optional[str] = ""
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    business_name: Optional[str] = ""
    from_phone: Optional[str] = ""
    call_duration: Optional[Any] = None
    summary: Optional[Any] = None
    emotion: Optional[Any] = None
    stream_sid: Optional[str] = None
    call_sid: Optional[str] = None
    call_ended: bool = False
    messages: List[Dict[str, Any]] = field(default_factory=list)
    system_message: Optional[str] = None
    initial_message: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    final_status: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    available_functions: Dict[str, Callable] = field(default_factory=dict)
    _write_timer = None
    _last_write_time = 0
    @log_function_call
    def set_tools(self, tools: Optional[List[Dict[str, Any]]] = None):
        """Set the tools for the current context."""
        self.tools = tools if tools is not None else get_tools()
        self.validate_and_load_tools()

    def write_none_values_to_json(self, file_path: str):
        # Convert the dataclass to a dictionary
        context_dict = asdict(self)

        # Filter out keys with None values
        none_values_dict = {k: v for k, v in context_dict.items() if v is None}

        # Write the filtered dictionary to a JSON file
        with open(file_path, 'w') as json_file:
            json.dump(none_values_dict, json_file, indent=4)
    @log_function_call
    def validate_and_load_tools(self):
        """Validate and load functions corresponding to the tools."""
        if not self.tools:
            self.tools = get_tools()

        missing_functions = []
        for tool in self.tools:
            function_name = tool['function']['name']
            if not self.load_function(function_name):
                missing_functions.append(function_name)

        if missing_functions:
            raise ValueError(
                f"The following functions are missing or could not be loaded: {', '.join(missing_functions)}")

        logger.info("All tools are correctly validated and loaded.")

    def load_function(self, function_name: str) -> bool:
        """Dynamically load a function by its name."""
        try:
            # Load the module from the 'functions' directory
            module = importlib.import_module(f"functions.{function_name}")
            # Retrieve the function from the module and store it in available_functions
            self.available_functions[function_name] = getattr(module, function_name)
            return True
        except ImportError as e:
            logger.error(f"Function module '{function_name}' could not be imported: {str(e)}")
        except AttributeError as e:
            logger.error(f"Function '{function_name}' could not be found in the module: {str(e)}")
        return False

    @log_function_call
    def add_to_user_context(self, message: Dict[str, Any]):
        """Add a message to the user context."""
        self.messages.append(message)

    def _debounced_write(self, delay=2):
        """Write messages to a file after a short delay."""
        if self._write_timer:
            self._write_timer.cancel()

        self._write_timer = Timer(delay, self.write_messages_to_file)
        self._write_timer.start()

    @log_function_call
    def add_to_user_context(self, message: Dict[str, Any]):
        self.messages.append(message)
        self._debounced_write()

    def write_messages_to_file(self):
        """Write the current messages to a JSON file."""
        current_time = time.time()
        if current_time - self._last_write_time < 2:
            return  # Prevent frequent writes

        file_name = f"{self.call_sid or 'default_call_sid'}.json"
        write_json_file(file_name, self.messages)
        self._last_write_time = current_time
        print(f"Messages written to {file_name}")

    def __del__(self):
        formatted_log = format_messages(self.messages, use_system_prompt=True)
        with open(f"{self.call_sid}_log.txt", 'w') as log_file:
            log_file.write(formatted_log)
        print(f"Logs written to {self.call_sid}_log.txt")

        # Optionally log additional details asynchronously
        log_entry = convert_to_request_log(
            message="Final summary or another message",
            meta_info={'sequence_id': '1', 'request_id': self.call_sid},
            model='openai',
            component='llm',
            run_id=self.call_sid
        )
        asyncio.create_task(write_request_logs(log_entry, self.call_sid))