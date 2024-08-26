import asyncio
import os
from signal import SIGINT, SIGTERM
from deepgram import DeepgramClient, DeepgramClientOptions, LiveOptions, LiveTranscriptionEvents, Microphone
from EventHandlers import EventHandler
from Utils.my_logger import configure_logger

logger = configure_logger(__name__)

class DeepgramTranscriber(EventHandler):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        self.deepgram_live = None
        self.final_result = ""
        self.speech_final = False
        self.stream_sid = None
        self.is_finals = []

        config = DeepgramClientOptions(options={"keepalive": "true"})
        self.deepgram = DeepgramClient("", config)
        self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")

    async def on_open(self, *args, **kwargs):
        logger.info("Connection Open")

    def set_stream_sid(self, stream_id):
        self.stream_sid = stream_id

    def get_stream_sid(self):
        return self.stream_sid



    async def handle_metadata(self, *args, **kwargs):
        metadata = kwargs.get('metadata')
        logger.info(f"Metadata: {metadata}")

    async def on_speech_started(self, *args, **kwargs):
        logger.info("Speech Started")


    async def handle_close(self, self_obj, close):
        logger.info("Connection Closed")
        self.is_connected = False

    async def handle_error(self, self_obj, error):
        logger.info(f"Handled Error: {error}")
        self.is_connected = False

    async def on_unhandled(self, self_obj, unhandled):
        logger.info(f"Unhandled Websocket Message: {unhandled}")

    def setup_event_handlers(self):
        self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
        self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.handle_transcription)
        self.dg_connection.on(LiveTranscriptionEvents.Metadata, self.handle_metadata)
        self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, self.on_speech_started)
        self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, self.handle_utterance_end)
        self.dg_connection.on(LiveTranscriptionEvents.Close, self.handle_close)
        self.dg_connection.on(LiveTranscriptionEvents.Error, self.handle_error)
        self.dg_connection.on(LiveTranscriptionEvents.Unhandled, self.on_unhandled)

    async def connect(self):
        try:
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

            addons = {
                "no_delay": "true"
            }

            logger.info("\n\nStart talking! Press Ctrl+C to stop...\n")

            if await self.dg_connection.start(options, addons=addons) is False:
                logger.info("Failed to connect to Deepgram")
                return

            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                self.microphone.finish()
                await self.dg_connection.finish()

            logger.info("Finished")

        except Exception as e:
            logger.info(f"Could not open socket: {e}")
    async def handle_transcription(self, self_obj, result):
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

            # Process final and interim results for logging
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

    async def handle_utterance_end(self, self_obj, utterance_end):
        try:
            if not self.speech_final:
                logger.info(f"UtteranceEnd received before speech was final, emitting collected text: {self.final_result}")
                await self.createEvent('transcription', self.final_result)
                self.final_result = ''
                self.speech_final = True
            else:
                return
        except Exception as e:
            logger.error(f"Error while handling utterance end: {e}")
            e.print_stack()

    async def send(self, payload: bytes):
        if self.deepgram_live:
            await self.deepgram_live.send(payload)

    async def shutdown(self, signal):
        logger.info(f"Received exit signal {signal.name}...")
        self.microphone.finish()
        await self.dg_connection.finish()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()
        logger.info("Shutdown complete.")

def setup_signal_handlers(loop, transcriber):
    for signal in (SIGTERM, SIGINT):
        loop.add_signal_handler(
            signal,
            lambda: asyncio.create_task(transcriber.shutdown(signal))
        )

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    transcriber = DeepgramTranscriber(loop)
    setup_signal_handlers(loop, transcriber)
    loop.run_until_complete(transcriber.connect())
