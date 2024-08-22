import os
import json
import asyncio
import base64
import logging
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)
from dotenv import load_dotenv


from llms import CallContext, LLMFactory
from networking import StreamService
from speach_to_text import TranscriptionService
from text_to_speach import TTSFactory

load_dotenv()
logger = logging.getLogger("app")


class WebSocketService:
    def __init__(self, websocket: WebSocket, response_queue):
        self.websocket = websocket
        self.llm_service_name = os.getenv("LLM_SERVICE", "openai")
        self.tts_service_name = os.getenv("TTS_SERVICE", "deepgram")
        self.llm_service = None
        self.stream_service = None
        self.transcription_service = None
        self.tts_service = None
        self.marks = deque()
        self.interaction_count = 0
        self.message_queue = asyncio.Queue()
        self.response_queue = response_queue  # Queue to send TTS responses to GUI

    async def setup_services(self):
        logger.info(f"Using LLM service: {self.llm_service_name}")
        logger.info(f"Using TTS service: {self.tts_service_name}")

        self.llm_service = LLMFactory.get_llm_service(self.llm_service_name, CallContext())
        self.stream_service = StreamService(self.websocket)
        self.transcription_service = TranscriptionService()
        self.tts_service = TTSFactory.get_tts_service(self.tts_service_name)

        await self.transcription_service.connect()

        self.transcription_service.on('utterance', self.handle_utterance)
        self.transcription_service.on('transcription', self.handle_transcription)
        self.llm_service.on('llmreply', self.handle_llm_reply)
        self.tts_service.on('speech', self.handle_speech)
        self.stream_service.on('audiosent', self.handle_audio_sent)

    async def websocket_listener(self):
        try:
            while True:
                data = await self.websocket.receive_text()
                await self.message_queue.put(json.loads(data))
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    async def process_gui_input(self, user_input):
        logger.info(f"GUI -> Received input: {user_input}")
        response = await self.llm_service.completion(user_input, self.interaction_count)
        self.response_queue.put(response)  # Send response back to GUI for TTS
        self.interaction_count += 1

    async def microphone_stream(self):
        try:
            microphone = Microphone(self.transcription_service.send)
            microphone.start()

            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            microphone.finish()
        finally:
            await self.transcription_service.disconnect()

    async def message_processor(self):
        while True:
            msg = await self.message_queue.get()
            if msg['event'] == 'start':
                await self.handle_start_event(msg)
            elif msg['event'] == 'media':
                asyncio.create_task(self.process_media(msg))
            elif msg['event'] == 'mark':
                self.handle_mark_event(msg)
            elif msg['event'] == 'stop':
                logger.info(f"Twilio -> Media stream ended.")
                break
            self.message_queue.task_done()

    async def process_media(self, msg):
        await self.transcription_service.send(base64.b64decode(msg['media']['payload']))

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
                await self.websocket.send_json({
                    "streamSid": stream_sid,
                    "event": "clear"
                })

                # reset states
                self.stream_service.reset()
                self.llm_service.reset()

        except Exception as e:
            logger.error(f"Error while handling utterance: {e}")
            e.print_stack()

    async def handle_start_event(self, msg):
        stream_sid = msg['start']['streamSid']
        call_sid = msg['start']['callSid']

        call_contexts = CallContext()


        call_sid = "microphones"
        if call_sid not in call_contexts:
            call_context.system_message = os.getenv("SYSTEM_MESSAGE")
            call_context.initial_message = os.getenv("INITIAL_MESSAGE")
            call_context.call_sid = call_sid
            call_contexts[call_sid] = call_context
        else:
            call_context = call_contexts[call_sid]

        self.llm_service.set_call_context(call_context)

        self.stream_service.set_stream_sid(stream_sid)
        self.transcription_service.set_stream_sid(stream_sid)

        logger.info(f"Twilio -> Starting Media Stream for {stream_sid}")
        await self.tts_service.generate({
            "partialResponseIndex": None,
            "partialResponse": call_context.initial_message
        }, 1)

    def handle_mark_event(self, msg):
        label = msg['mark']['name']
        if label in self.marks:
            self.marks.remove(label)

    async def run(self):
        await self.websocket.accept()
        await self.setup_services()

        try:
            listener_task = asyncio.create_task(self.websocket_listener())
            processor_task = asyncio.create_task(self.message_processor())

            await asyncio.gather(listener_task, processor_task)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")
        finally:
            await self.transcription_service.disconnect()

