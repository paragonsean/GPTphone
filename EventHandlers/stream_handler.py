import asyncio
import base64
import json
import os
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect
from Utils.logger_config import configure_logger
from services import LLMFactory
from text_to_speach import TTSFactory
from services import CallContext
from speach_to_text import TranscriptionService
from telephony import get_twilio_client

logger = configure_logger("WebSocketEndpoint")


class WebSocketManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.message_queue = asyncio.Queue()

    async def accept(self):
        await self.websocket.accept()

    async def receive_messages(self):
        try:
            while True:
                data = await self.websocket.receive_text()
                await self.message_queue.put(json.loads(data))
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    async def send_json(self, data):
        await self.websocket.send_json(data)


class StreamHandler:
    def __init__(self, websocket_manager: WebSocketManager, llm_service, tts_service, transcription_service,
                 stream_service, call_contexts):
        self.websocket_manager = websocket_manager
        self.llm_service = llm_service
        self.tts_service = tts_service
        self.transcription_service = transcription_service
        self.stream_service = stream_service
        self.call_contexts = call_contexts
        self.marks = deque()
        self.interaction_count = 0

    async def start(self):
        await self.transcription_service.connect()

        self.transcription_service.on('utterance', self.handle_utterance)
        self.transcription_service.on('transcription', self.handle_transcription)
        self.llm_service.on('llmreply', self.handle_llm_reply)
        self.tts_service.on('speech', self.handle_speech)
        self.stream_service.on('audiosent', self.handle_audio_sent)

        await asyncio.gather(self.websocket_manager.receive_messages(), self.process_messages())

    async def process_messages(self):
        while True:
            msg = await self.websocket_manager.message_queue.get()
            if msg['event'] == 'start':
                await self.handle_start(msg)
            elif msg['event'] == 'media':
                asyncio.create_task(self.process_media(msg))
            elif msg['event'] == 'mark':
                await self.handle_mark(msg)
            elif msg['event'] == 'stop':
                logger.info(f"Twilio -> Media stream ended.")
                break
            self.websocket_manager.message_queue.task_done()

    async def handle_start(self, msg):
        stream_sid = msg['start']['streamSid']
        call_sid = msg['start']['callSid']

        call_context = CallContext()

        if os.getenv("RECORD_CALLS") == "true":
            get_twilio_client.calls(call_sid).recordings.create({"recordingChannels": "dual"})

        if call_sid not in self.call_contexts:
            call_context.system_message = os.environ.get("SYSTEM_MESSAGE")
            call_context.initial_message = os.environ.get("INITIAL_MESSAGE")
            call_context.call_sid = call_sid
            self.call_contexts[call_sid] = call_context
        else:
            call_context = self.call_contexts[call_sid]

        self.llm_service.set_call_context(call_context)
        self.stream_service.set_stream_sid(stream_sid)
        self.transcription_service.set_stream_sid(stream_sid)

        logger.info(f"Twilio -> Starting Media Stream for {stream_sid}")
        await self.tts_service.generate({
            "partialResponseIndex": None,
            "partialResponse": call_context.initial_message
        }, 1)

    async def process_media(self, msg):
        await self.transcription_service.send(base64.b64decode(msg['media']['payload']))

    async def handle_mark(self, msg):
        label = msg['mark']['name']
        if label in self.marks:
            self.marks.remove(label)

    async def handle_transcription(self, text):
        if not text:
            return
        logger.info(f"Interaction {self.interaction_count} – STT -> LLM: {text}")
        await self.llm_service.completion(text, self.interaction_count)
        self.interaction_count += 1

    async def handle_llm_reply(self, llm_reply, icount):
        logger.info(f"Interaction {icount}: LLM -> TTS: {llm_reply['partialResponse']}")
        await self.tts_service.generate(llm_reply, icount)

    async def handle_speech(self, response_index, audio, label, icount):
        logger.info(f"Interaction {icount}: TTS -> TWILIO: {label}")
        await self.stream_service.buffer(response_index, audio)

    async def handle_audio_sent(self, mark_label):
        self.marks.append(mark_label)

    async def handle_utterance(self, text, stream_sid):
        try:
            if len(self.marks) > 0 and text.strip():
                logger.info("Interruption detected, clearing system.")
                await self.websocket_manager.send_json({
                    "streamSid": stream_sid,
                    "event": "clear"
                })

                self.stream_service.reset()
                self.llm_service.reset()
        except Exception as e:
            logger.error(f"Error while handling utterance: {e}")
            e.print_stack()


@app.websocket("/connection")
async def websocket_endpoint(websocket: WebSocket):
    websocket_manager = WebSocketManager(websocket)
    await websocket_manager.accept()

    llm_service_name = os.getenv("LLM_SERVICE", "openai")
    tts_service_name = os.getenv("TTS_SERVICE", "deepgram")

    logger.info(f"Using LLM service: {llm_service_name}")
    logger.info(f"Using TTS service: {tts_service_name}")

    llm_service = LLMFactory.get_llm_service(llm_service_name, CallContext())
    transcription_service = TranscriptionService()
    tts_service = TTSFactory.get_tts_service(tts_service_name)
    stream_service = StreamService(websocket)

    call_contexts = {}

    stream_handler = StreamHandler(
        websocket_manager,
        llm_service,
        tts_service,
        transcription_service,
        stream_service,
        call_contexts
    )

    try:
        await stream_handler.start()
    except asyncio.CancelledError:
        logger.info("Tasks cancelled")
    finally:
        await transcription_service.disconnect()
