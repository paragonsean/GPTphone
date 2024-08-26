import asyncio
import os
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents, Microphone
from EventHandlers import EventHandler
from Utils.my_logger import configure_logger

logger = configure_logger(__name__)


class BaseTranscriber(EventHandler):
    def __init__(self):
        super().__init__()
        self.client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        self.deepgram_live = None
        self.final_result = ""
        self.speech_final = False
        self.stream_sid = None
        self.is_finals = []

    def set_stream_sid(self, stream_id):
        self.stream_sid = stream_id

    def get_stream_sid(self):
        return self.stream_sid

    async def handle_transcription(self, *args, **kwargs):
        result = kwargs.get('result', args[0] if args else None)
        if result is None:
            logger.error("No result provided to handle_transcription")
            return

        try:
            alternatives = result.channel.alternatives if hasattr(result, 'channel') else []
            text = alternatives[0].transcript if alternatives else ""

            if result.is_final and text.strip():
                self.final_result += f" {text}"
                if result.speech_final:
                    self.speech_final = True
                    await self.createEvent('transcription', self.final_result)
                    self.final_result = ''
                else:
                    self.speech_final = False
            else:
                if text.strip():
                    stream_sid = self.get_stream_sid()
                    await self.createEvent('utterance', text, stream_sid)

            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            if result.is_final:
                self.is_finals.append(sentence)
                if result.speech_final:
                    utterance = " ".join(self.is_finals)
                    logger.info(f"Speech Final: {utterance}")
                    self.is_finals = []
                else:
                    logger.info(f"Is Final: {sentence}")
            else:
                logger.info(f"Interim Results: {sentence}")

        except Exception as e:
            logger.error(f"Error while handling transcription: {e}")
            e.print_stack()

    async def handle_utterance_end(self, *args, **kwargs):
        utterance_end = kwargs.get('utterance_end', args[0] if args else None)
        if utterance_end is None:
            logger.error("No utterance_end provided to handle_utterance_end")
            return

        try:
            if not self.speech_final:
                logger.info(
                    f"UtteranceEnd received before speech was final, emitting collected text: {self.final_result}")
                await self.createEvent('transcription', self.final_result)
                self.final_result = ''
                self.speech_final = True
            else:
                return
        except Exception as e:
            logger.error(f"Error while handling utterance end: {e}")
            e.print_stack()

    async def handle_error(self, error):
        logger.error(f"Deepgram error: {error}")

    async def handle_metadata(self, metadata):
        logger.info(f'Deepgram metadata: {metadata}')

    async def handle_close(self, close):
        logger.info("Deepgram connection closed")

    def setup_event_handlers(self):
        self.deepgram_live.on(LiveTranscriptionEvents.Transcript, self.handle_transcription)
        self.deepgram_live.on(LiveTranscriptionEvents.Error, self.handle_error)
        self.deepgram_live.on(LiveTranscriptionEvents.Close, self.handle_close)
        self.deepgram_live.on(LiveTranscriptionEvents.Metadata, self.handle_metadata)
        self.deepgram_live.on(LiveTranscriptionEvents.UtteranceEnd, self.handle_utterance_end)

    async def send(self, payload: bytes):
        if self.deepgram_live:
            await self.deepgram_live.send(payload)

    async def disconnect(self):
        if self.deepgram_live:
            await self.deepgram_live.finish()
            self.deepgram_live = None
        logger.info("Disconnected from Deepgram")


from deepgram import Microphone


class MicrophoneTranscriber(BaseTranscriber):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.microphone = None

    async def connect(self):
        try:
            self.deepgram_live = self.client.listen.asyncwebsocket.v("1")
            self.setup_event_handlers()

            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                endpointing=300,
            )

            addons = {"no_delay": "true"}

            logger.info("\n\nStart talking! Press Ctrl+C to stop...\n")

            if await self.deepgram_live.start(options, addons=addons) is False:
                logger.info("Failed to connect to Deepgram")
                return

            self.microphone = Microphone(self.deepgram_live.send)
            self.microphone.start()

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                self.microphone.finish()
                await self.deepgram_live.finish()

            logger.info("Finished")

        except Exception as e:
            logger.error(f"Could not open socket: {e}")

    async def shutdown(self, signal):
        logger.info(f"Received exit signal {signal.name}...")
        if self.microphone:
            self.microphone.finish()
        await self.disconnect()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()
        logger.info("Shutdown complete.")


# class WebSocketTranscriber(BaseTranscriber):
#     def __init__(self):
#         super().__init__()
#
#     async def connect(self):
#         self.deepgram_live = self.client.listen.asynclive.v("1")
#         self.setup_event_handlers()
#
#         options = LiveOptions(
#             model="nova-2",
#             language="en-US",
#             encoding="mulaw",
#             sample_rate=8000,
#             channels=1,
#             punctuate=True,
#             interim_results=True,
#             endpointing=200,
#             utterance_end_ms="1000"
#         )
#
#         if await self.deepgram_live.start(options) is False:
#             logger.info("Failed to connect to Deepgram")
#
#     async def shutdown(self):
#         await self.disconnect()


class TranscriberFactory:
    @staticmethod
    def get_transcriber(transcriber_type, loop=None):
        if transcriber_type == "microphone":
            return MicrophoneTranscriber(loop)
        elif transcriber_type == "websocket":
            return WebSocketTranscriber()
        else:
            raise ValueError("Unknown transcriber type")
