import base64
import os
from typing import Dict, Any

import aiohttp
from dotenv import load_dotenv

from Utils.my_logger import configure_logger
from .abstract_base import AbstractTTSService

logger = configure_logger(__name__)
load_dotenv()

class ElevenLabsTTS(AbstractTTSService):
    """
    A class representing the ElevenLabs Text-to-Speech (TTS) service.

    Attributes:
        voice_id (str): The ID of the voice to be used for TTS.
        api_key (str): The API key for accessing the ElevenLabs TTS service.
        model_id (str): The ID of the TTS model to be used.
        speech_buffer (dict): A dictionary to store the generated speech audio.

    Methods:
        set_voice(voice_id): Sets the voice ID for TTS.
        disconnect(): Disconnects from the ElevenLabs TTS service.
        generate(llm_reply, interaction_count): Generates speech audio based on the given partial response.

    """

    def __init__(self):
        super().__init__()
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.model_id = os.getenv("ELEVENLABS_MODEL_ID")
        self.speech_buffer = {}

    def set_voice(self, voice_id):
        """
        Sets the voice ID for TTS.

        Args:
            voice_id (str): The ID of the voice to be used for TTS.

        """
        self.voice_id = voice_id

    async def disconnect(self):
        """
        Disconnects from the ElevenLabs TTS service.

        Note:
            The ElevenLabs client doesn't require explicit disconnection.

        """
        logger.info("ElevenLabs TTS service disconnected")
        return

    async def generate(self, llm_reply: Dict[str, Any], interaction_count: int):
        """
        Generates speech audio based on the given partial response.

        Args:
            llm_reply (Dict[str, Any]): The partial response received from the LLM service.
            interaction_count (int): The count of interactions.

        Returns:
            None

        Raises:
            Exception: If an error occurs in the ElevenLabs TTS service.

        """
        partial_response_index, partial_response = llm_reply['partialResponseIndex'], llm_reply['partialResponse']

        if not partial_response:
            return

        try:
            output_format = "ulaw_8000"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/wav"
            }
            params = {
                "output_format": output_format,
                "optimize_streaming_latency": 4
            }
            data = {
                "model_id": self.model_id,
                "text": partial_response
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, json=data) as response:
                    if response.status == 200:
                        audio_content = await response.read()
                        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                        await self.createEvent('speech', partial_response_index, audio_base64, partial_response,
                                               interaction_count)
        except Exception as err:
            logger.error("Error occurred in ElevenLabs TTS service", exc_info=True)
            logger.error(str(err))
