import base64
import os

import numpy as np
from deepgram import DeepgramClient
from dotenv import load_dotenv

from Utils.singleton_logger import configure_logger
from .abstract_base import AbstractTTSService

logger = configure_logger(__name__)
load_dotenv()


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
                await self.createEvent('speech', partial_response_index, audio_base64, partial_response,
                                       interaction_count)
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
