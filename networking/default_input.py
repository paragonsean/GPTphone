import asyncio
import base64
import json
import os
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect
from llms import CallContext, LLMFactory
from networking import StreamService
from speach_to_text import TranscriptionService
from text_to_speach.tts_factory import TTSFactory
from Utils.my_logger import configure_logger

logger = configure_logger(__name__)

class WebSocketService:
    def __init__(self,
                 websocket: WebSocket,
                 twilio_service,
                 llm_service,
                 stream_service,
                 transcription_service,
                 tts_service) -> None:
        self.websocket = websocket
        self.twilio_service = twilio_service
        self.llm_service = llm_service
        self.stream_service = stream_service
        self.transcription_service = transcription_service
        self.tts_service = tts_service
        self.marks: deque = deque()
        self.interaction_count = 0
        self.message_queue = asyncio.Queue()

    async def accept_connection(self):
        await self.websocket.accept()
        await self.transcription_service.connect()

    async def process_media(self, msg):
        await self.transcription_service.send(base64.b64decode(msg['media']['payload']))

    async def handle_transcription(self, text):
        if not text:
            return
        await self.llm_service.completion(text, self.interaction_count)
        self.interaction_count += 1

    async def handle_llm_reply(self, llm_reply, icount):
        await self.tts_service.generate(llm_reply, icount)

    async def handle_speech(self, response_index, audio, label, icount):
        await self.stream_service.buffer(response_index, audio)

    async def handle_audio_sent(self, mark_label):
        self.marks.append(mark_label)

    async def handle_utterance(self, text, stream_sid):
        try:
            if len(self.marks) > 0 and text.strip():
                logger.info("Interruption detected, clearing system.")
                await self.websocket.send_json({
                    "streamSid": stream_sid,
                    "event": "clear"
                })

                # Reset states
                self.stream_service.reset()
                self.llm_service.reset()

        except Exception as e:
            logger.error(f"Error while handling utterance: {e}")
            e.print_stack()

    async def websocket_listener(self):
        try:
            while True:
                data = await self.websocket.receive_text()
                await self.message_queue.put(json.loads(data))
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    async def message_processor(self):
        while True:
            msg = await self.message_queue.get()
            if msg['event'] == 'start':
                await self.handle_start(msg)
            elif msg['event'] == 'media':
                asyncio.create_task(self.process_media(msg))
            elif msg['event'] == 'mark':
                self.handle_mark(msg)
            elif msg['event'] == 'stop':
                logger.info(f"Twilio -> Media stream {msg['stop']['streamSid']} ended.")
                break
            self.message_queue.task_done()

    async def handle_start(self, msg):
        stream_sid = msg['start']['streamSid']
        call_sid = msg['start']['callSid']

        call_context = CallContext()

        if os.getenv("RECORD_CALLS") == "true":
            self.twilio_service.get_twilio_client().calls(call_sid).recordings.create({"recordingChannels": "dual"})

        # Decide if the call was initiated from the UI or is an inbound
        if call_sid not in self.twilio_service.call_contexts:
            call_context.system_message = os.environ.get("SYSTEM_MESSAGE")
            call_context.initial_message = os.environ.get("INITIAL_MESSAGE")
            call_context.call_sid = call_sid
            self.twilio_service.call_contexts[call_sid] = call_context
        else:
            call_context = self.twilio_service.call_contexts[call_sid]

        self.llm_service.set_call_context(call_context)

        self.stream_service.set_stream_sid(stream_sid)
        self.transcription_service.set_stream_sid(stream_sid)

        logger.info(f"Twilio -> Starting Media Stream for {stream_sid}")
        await self.tts_service.generate({
            "partialResponseIndex": None,
            "partialResponse": call_context.initial_message
        }, 1)

    def handle_mark(self, msg):
        label = msg['mark']['name']
        if label in self.marks:
            self.marks.remove(label)

    async def run(self):
        try:
            listener_task = asyncio.create_task(self.websocket_listener())
            processor_task = asyncio.create_task(self.message_processor())
            await asyncio.gather(listener_task, processor_task)
        finally:
            await self.transcription_service.disconnect()
