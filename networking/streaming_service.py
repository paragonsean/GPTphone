import uuid
from typing import Dict

from fastapi import WebSocket

from EventHandlers.event_manager import EventHandler
from Utils.singleton_logger import configure_logger

logger = configure_logger(__name__)
'''
Author: Sean Baker
Date: 2024-07-22 
Description: streaming service class with chunk based audio feed allowing for near seemless commnication  
'''
class StreamService(EventHandler):
    """
    A class that handles streaming audio data over a WebSocket connection.

    Args:
        websocket (WebSocket): The WebSocket connection to use for streaming.

    Attributes:
        ws (WebSocket): The WebSocket connection.
        expected_audio_index (int): The expected index of the next audio chunk.
        audio_buffer (Dict[int, str]): A dictionary to store buffered audio chunks.
        stream_sid (str): The stream session ID.

    """

    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.ws = websocket
        self.expected_audio_index = 0
        self.audio_buffer: Dict[int, str] = {}
        self.stream_sid = ''

    def set_stream_sid(self, stream_sid: str):
        """
        Set the stream session ID.

        Args:
            stream_sid (str): The stream session ID.

        """
        self.stream_sid = stream_sid

    async def buffer(self, index: int, audio: str):
        """
        Buffer the audio chunk for streaming.

        If the index is None, the audio chunk is sent immediately.
        If the index matches the expected index, the audio chunk is sent and the expected index is incremented.
        If the index does not match the expected index, the audio chunk is buffered.

        Args:
            index (int): The index of the audio chunk.
            audio (str): The audio chunk to buffer.

        """
        if index is None:
            await self.send_audio(audio)
        elif index == self.expected_audio_index:
            await self.send_audio(audio)
            self.expected_audio_index += 1

            while self.expected_audio_index in self.audio_buffer:
                buffered_audio = self.audio_buffer[self.expected_audio_index]
                await self.send_audio(buffered_audio)
                del self.audio_buffer[self.expected_audio_index]
                self.expected_audio_index += 1
        else:
            self.audio_buffer[index] = audio

    def reset(self):
        """
        Reset the expected audio index and clear the audio buffer.

        """
        self.expected_audio_index = 0
        self.audio_buffer = {}

    async def send_audio(self, audio: str):
        """
        Send the audio chunk over the WebSocket connection.

        Args:
            audio (str): The audio chunk to send.

        """
        await self.ws.send_json({
            "streamSid": self.stream_sid,
            "event": "media",
            "media": {
                "payload": audio
            }
        })

        mark_label = str(uuid.uuid4())

        await self.ws.send_json({
            "streamSid": self.stream_sid,
            "event": "mark",
            "mark": {
                "name": mark_label
            }
        })

        await self.createEvent('audiosent', mark_label)