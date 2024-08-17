import base64
import os
from abc import ABC, abstractmethod
from typing import Any, Dict

import aiohttp
import numpy as np
from deepgram import DeepgramClient
from dotenv import load_dotenv

from Utils.logger_config import get_logger
from services.event_manager import EventHandler

load_dotenv()
logger = get_logger("TTS")
'''
Author: Sean Baker
Date: 2024-07-08 
Description: TTS text to speach currently implemented elevenlabs still need to finish deepgram if necessary
'''

class AbstractTTSService(EventHandler, ABC):
    """Abstract base class for Text-to-Speech (TTS) services."""

    @abstractmethod
    async def generate(self, llm_reply: Dict[str, Any], interaction_count: int):
        """Generate speech from the given LLM reply and interaction count.

        Args:
            llm_reply (Dict[str, Any]): The LLM reply containing the text to be converted to speech.
            interaction_count (int): The count of interactions.

        Returns:
            None
        """

        pass

    @abstractmethod
    async def set_voice(self, voice_id: str):
        """Set the voice for speech generation.

        Args:
            voice_id (str): The ID of the voice to be set.

        Returns:
            None
        """

        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from the TTS service.

        Returns:
            None
        """

        pass


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


class DeepgramTTS(AbstractTTSService):
    def __init__(self):
        super().__init__()
        self.client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

    async def generate(self, llm_reply, interaction_count):
        """
        Generate text-to-speech audio based on the given partial response.

        Args:
            llm_reply (dict): The partial response received from the LLM.
            interaction_count (int): The count of interactions.

        Returns:
            None

        Raises:
            Exception: If there is an error in the TTS generation process.
        """
        partial_response_index = llm_reply['partialResponseIndex']
        partial_response = llm_reply['partialResponse']

        if not partial_response:
            return

        try:
            source = {
                "text": partial_response
            }

            options = {
                "model": "aura-asteria-en",
                "encoding": "mulaw",
                "sample_rate": 8000
            }

            response = await self.client.asyncspeak.v("1").stream(
                source={"text": partial_response},
                options=options
            )

            if response.stream:
                audio_content = response.stream.getvalue()

                # Convert audio to numpy array
                audio_array = np.frombuffer(audio_content, dtype=np.uint8)

                # Trim the first 10ms (80 samples at 8000Hz) to remove the initial noise
                trim_samples = 80
                trimmed_audio = audio_array[trim_samples:]

                # Convert back to bytes
                trimmed_audio_bytes = trimmed_audio.tobytes()

                audio_base64 = base64.b64encode(trimmed_audio_bytes).decode('utf-8')
                await self.createEvent('speech', partial_response_index, audio_base64, partial_response, interaction_count)
            else:
                logger.error("Error in TTS generation: No audio stream returned")

        except Exception as e:
            logger.error(f"Error in TTS generation: {str(e)}")

    async def set_voice(self, voice_id):
        """
        Sets the voice for the TTS service.

        Args:
            voice_id (str): The ID of the voice to set.

        Returns:
            None

        Raises:
            NotImplementedError: If voice selection is not implemented for the Deepgram TTS service.
        """
        logger.info(f"Attempting to set voice to {voice_id}")


    async def disconnect(self):
        """
        Disconnects the DeepgramTTS service.

        This method is used to disconnect the DeepgramTTS service. Since the Deepgram client
        doesn't require explicit disconnection, this method serves as a logging statement to
        indicate that the service has been disconnected.

        """
        # Deepgram client doesn't require explicit disconnection
        logger.info("DeepgramTTS service disconnected")


class TTSFactory:
    """
    Factory class for creating Text-to-Speech (TTS) services.
    """

    @staticmethod
    def get_tts_service(service_name: str) -> AbstractTTSService:
        """
        Returns an instance of the specified TTS service.

        Args:
            service_name (str): The name of the TTS service.

        Returns:
            AbstractTTSService: An instance of the specified TTS service.

        Raises:
            ValueError: If the specified TTS service is not supported.
        """
        if service_name.lower() == "elevenlabs":
            return ElevenLabsTTS()
        elif service_name.lower() == "deepgram":
            return DeepgramTTS()
        else:
            raise ValueError(f"Unsupported TTS service: {service_name}")


# Usage in your main application
tts_service_name = os.getenv("TTS_SERVICE", "deepgram")
tts_service = TTSFactory.get_tts_service(tts_service_name)