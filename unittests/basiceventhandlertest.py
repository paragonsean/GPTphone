import unittest
from unittest.mock import AsyncMock
import asyncio
from services.event_manager import EventHandler
from Utils.logger_config import get_logger, log_function_call
import random
logger = get_logger(__name__)

class TestEventHandler(unittest.TestCase):
    def setUp(self):
        # Set up the event handler with mocked callbacks
        self.event_handler = EventHandler()
        self.mock_callback_1 = AsyncMock()
        self.mock_callback_2 = AsyncMock()
    @log_function_call
    async def trigger_event(self, event_name, *args, **kwargs):
        await self.event_handler.createEvent(event_name, *args, **kwargs)
    @log_function_call
    def test_on_event_registration(self):
        # Register a callback
        self.event_handler.on("test_event", self.mock_callback_1)

        # Check if the event is registered correctly
        self.assertIn("test_event", self.event_handler._events)
        self.assertIn(self.mock_callback_1, self.event_handler._events["test_event"])
    @log_function_call
    def test_on_event_multiple_callbacks(self):
        # Register multiple callbacks for the same event
        self.event_handler.on("test_event", self.mock_callback_1)
        self.event_handler.on("test_event", self.mock_callback_2)

        # Check if both callbacks are registered correctly
        self.assertIn(self.mock_callback_1, self.event_handler._events["test_event"])
        self.assertIn(self.mock_callback_2, self.event_handler._events["test_event"])
    @log_function_call
    def test_trigger_event(self):
        # Register the callback
        self.event_handler.on("test_event", self.mock_callback_1)

        # Trigger the event and verify if the callback was called
        asyncio.run(self.trigger_event("test_event", "arg1", key="value"))
        self.mock_callback_1.assert_called_once_with("arg1", key="value")
    @log_function_call
    def test_trigger_event_with_multiple_callbacks(self):
        # Register multiple callbacks
        self.event_handler.on("test_event", self.mock_callback_1)
        self.event_handler.on("test_event", self.mock_callback_2)

        # Trigger the event and verify if both callbacks were called
        asyncio.run(self.trigger_event("test_event", "arg1", key="value"))
        self.mock_callback_1.assert_called_once_with("arg1", key="value")
        self.mock_callback_2.assert_called_once_with("arg1", key="value")



# Assume the EventHandler class is already defined as provided


class ExampleUsage:
    def __init__(self):
        self.handler = EventHandler()
        self.handler.on('roll_number', self.roll_number)
        self.handler.on('pick_number', self.pick_number)

    async def roll_number(self):
        # Simulate rolling a number between 1 and 100
        number = random.randint(1, 100)
        print(f"Rolled a number: {number}")
        await asyncio.sleep(1)  # Simulate async work

    def pick_number(self):
        # Simulate picking a number between 1 and 10
        number = random.randint(1, 10)
        print(f"Picked a number: {number}")

    async def randomly_trigger_event(self):
        # Randomly choose one of the events to trigger
        events = ['roll_number', 'pick_number']
        chosen_event = random.choice(events)
        print(f"Triggering event: {chosen_event}")
        await self.handler.createEvent(chosen_event)


# Running the example
async def main():
    example = ExampleUsage()

    # Trigger events randomly 5 times
    for _ in range(5):
        await example.randomly_trigger_event()

# Running the example
async def main():
    example = ExampleUsage()
    run = ''
    while run == '':
        await example.randomly_trigger_event()
        run = input("Press Enter to continue...")
        if run != '':
            break

# Run the main function
asyncio.run(main())

if __name__ == '__main__':
    unittest.main()

