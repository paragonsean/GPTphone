from abc import ABC, abstractmethod
from typing import Any, Dict

from EventHandlers.event_manager import EventHandler
from Utils.my_logger import configure_logger

logger = configure_logger(__name__)
'''
Author: Sean Baker
Date: 2024-07-08 
Description: TTS text to speach currently implemented elevenlabs still need to finish deepgram if necessary
'''


class AbstractTTSService(EventHandler, ABC):
    """Abstract base class for Text-to-Speech (TTS) llms."""

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

# Usage in your main application
