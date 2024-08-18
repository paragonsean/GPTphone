
class TTSFactory:
    from .abstract_base import AbstractTTSService
    @staticmethod
    def get_tts_service(service_name: str) -> AbstractTTSService:
        if service_name.lower() == "elevenlabs":
            from .eleven_labs import ElevenLabsTTS
            return ElevenLabsTTS()
        elif service_name.lower() == "deepgram":
            from .deepgram_tts import DeepgramTTS
            return DeepgramTTS()
        else:
            raise ValueError(f"Unsupported TTS service: {service_name}")

