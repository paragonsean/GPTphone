from abc import ABC, abstractmethod
import asyncio

class BaseInputHandler(ABC):
    def __init__(self, queues=None, websocket=None, input_types=None, mark_set=None, turn_based_conversation=False):
        self.queues = queues
        self.websocket = websocket
        self.input_types = input_types
        self.mark_set = mark_set
        self.turn_based_conversation = turn_based_conversation
        self.websocket_listen_task = None
        self.running = True

    @abstractmethod
    async def call_start(self, packet):
        """Handle the start of a call."""
        pass

    @abstractmethod
    async def process_message(self, message):
        """Process a received message."""
        pass

    async def stop_handler(self):
        """Stop the handler gracefully."""
        self.running = False
        try:
            if self.websocket:
                await self.websocket.close()
        except Exception as e:
            self.log_error("Error closing WebSocket", e)

    @abstractmethod
    async def handle(self):
        """Start handling incoming messages."""
        pass

    def log_error(self, message, error):
        """Log an error."""
        print(f"{message}: {error}")


class BaseOutputHandler(ABC):
    def __init__(self, io_provider='default', websocket=None):
        self.websocket = websocket
        self.io_provider = io_provider
        self.is_chunking_supported = True

    @abstractmethod
    async def handle(self, packet):
        """Handle sending a message through the output."""
        pass

    @abstractmethod
    async def handle_interruption(self):
        """Handle interruption in the output stream."""
        pass

    @abstractmethod
    async def form_media_message(self, audio_data, audio_format):
        """Form a media message for sending audio data."""
        pass

    @abstractmethod
    async def form_mark_message(self, mark_id):
        """Form a mark message for sending marks in the stream."""
        pass

    def get_provider(self):
        """Get the provider name."""
        return self.io_provider

    def process_in_chunks(self, yield_chunks=False):
        """Determine if the output should be processed in chunks."""
        return self.is_chunking_supported and yield_chunks

    def log_error(self, message, error):
        """Log an error."""
        print(f"{message}: {error}")

