import unittest
from unittest.mock import AsyncMock, patch
from services.event_manager import AssistantEventHandler,EventHandler

class TestAssistantEventHandler(unittest.TestCase):
    def setUp(self):
        # Set up the event handler with mocked callbacks
        self.event_handler = AssistantEventHandler()
        self.mock_text_created_callback = AsyncMock()
        self.mock_text_delta_callback = AsyncMock()
        self.mock_tool_call_created_callback = AsyncMock()
        self.mock_tool_call_delta_callback = AsyncMock()

        # Register the mocked callbacks
        self.event_handler.on("text_created", self.mock_text_created_callback)
        self.event_handler.on("text_delta", self.mock_text_delta_callback)
        self.event_handler.on("tool_call_created", self.mock_tool_call_created_callback)
        self.event_handler.on("tool_call_delta", self.mock_tool_call_delta_callback)

    @patch("builtins.print")  # Patch print to avoid actual printing during tests
    def test_on_text_created(self, mock_print):
        # Trigger the on_text_created event
        self.event_handler.on_text_created("Test text")

        # Verify the callback was called with the correct arguments
        self.mock_text_created_callback.assert_called_once_with("Test text")
        mock_print.assert_called_with("\nassistant > ", end="", flush=True)

    @patch("builtins.print")
    def test_on_text_delta(self, mock_print):
        # Create a mock delta and snapshot
        mock_delta = AsyncMock()
        mock_snapshot = AsyncMock()
        mock_delta.value = "Delta text"

        # Trigger the on_text_delta event
        self.event_handler.on_text_delta(mock_delta, mock_snapshot)

        # Verify the callback was called with the correct arguments
        self.mock_text_delta_callback.assert_called_once_with(mock_delta, mock_snapshot)
        mock_print.assert_called_with("Delta text", end="", flush=True)

    @patch("builtins.print")
    def test_on_tool_call_created(self, mock_print):
        # Create a mock tool_call
        mock_tool_call = AsyncMock()
        mock_tool_call.type = "Test tool call"

        # Trigger the on_tool_call_created event
        self.event_handler.on_tool_call_created(mock_tool_call)

        # Verify the callback was called with the correct arguments
        self.mock_tool_call_created_callback.assert_called_once_with(mock_tool_call)
        mock_print.assert_called_with("\nassistant > Test tool call\n", flush=True)

    @patch("builtins.print")
    def test_on_tool_call_delta(self, mock_print):
        # Create a mock delta and snapshot with code_interpreter data
        mock_delta = AsyncMock()
        mock_snapshot = AsyncMock()
        mock_delta.type = "code_interpreter"
        mock_delta.code_interpreter.input = "Interpreter input"
        mock_delta.code_interpreter.outputs = [
            {"type": "logs", "logs": "Log output"}
        ]

        # Trigger the on_tool_call_delta event
        self.event_handler.on_tool_call_delta(mock_delta, mock_snapshot)

        # Verify the callback was called with the correct arguments
        self.mock_tool_call_delta_callback.assert_called_once_with(mock_delta, mock_snapshot)
        mock_print.assert_any_call("Interpreter input", end="", flush=True)
        mock_print.assert_any_call("\n\noutput >", flush=True)
        mock_print.assert_any_call("\nLog output", flush=True)




if __name__ == '__main__':
    unittest.main()

