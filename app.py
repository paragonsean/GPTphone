import asyncio
import base64
import json
import os
from collections import deque
from typing import Dict

import dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, VoiceResponse

from Utils.logger_config import get_logger
from services.call_context import CallContext
from services.gpt_service import LLMFactory
from services.gpt_service import AbstractLLMService
from networking.streaming_service import StreamService
from speach_to_text import TranscriptionService
from text_to_speach.tts_factory import TTSFactory

dotenv.load_dotenv()
app = FastAPI()
logger = get_logger("App")

# Global dictionary to store active call contexts (memory only)
call_contexts: Dict[str, CallContext] = {}

# WebSocket connection route
@app.websocket("/connection")
async def websocket_endpoint(websocket: WebSocket):
    """Handles real-time media streaming from Twilio via WebSockets."""
    await websocket.accept()

    llm_service_name = os.getenv("LLM_SERVICE", "openai")
    tts_service_name = os.getenv("TTS_SERVICE", "deepgram")

    logger.info(f"Using LLM service: {llm_service_name}")
    logger.info(f"Using TTS service: {tts_service_name}")

    llm_service = LLMFactory.get_llm_service(llm_service_name, CallContext())
    stream_service = StreamService(websocket)
    transcription_service = TranscriptionService()
    tts_service = TTSFactory.get_tts_service(tts_service_name)

    marks = deque()
    interaction_count = 0

    await transcription_service.connect()

    async def process_media(msg):
        await transcription_service.send(base64.b64decode(msg['media']['payload']))

    async def handle_transcription(text):
        nonlocal interaction_count
        if text:
            logger.info(f"Interaction {interaction_count} – STT -> LLM: {text}")
            await llm_service.completion(text, interaction_count)
            interaction_count += 1

    async def handle_llm_reply(llm_reply, icount):
        logger.info(f"Interaction {icount}: LLM -> TTS: {llm_reply['partialResponse']}")
        await tts_service.generate(llm_reply, icount)

    async def handle_speech(response_index, audio, label, icount):
        logger.info(f"Interaction {icount}: TTS -> TWILIO: {label}")
        await stream_service.buffer(response_index, audio)

    async def handle_audio_sent(mark_label):
        marks.append(mark_label)

    async def handle_utterance(text, stream_sid):
        if marks and text.strip():
            logger.info("Interruption detected, clearing system.")
            await websocket.send_json({"streamSid": stream_sid, "event": "clear"})
            stream_service.reset()
            llm_service.reset()

    transcription_service.on('utterance', handle_utterance)
    transcription_service.on('transcription', handle_transcription)
    llm_service.on('llmreply', handle_llm_reply)
    tts_service.on('speech', handle_speech)
    stream_service.on('audiosent', handle_audio_sent)

    message_queue = asyncio.Queue()

    async def websocket_listener():
        try:
            while True:
                data = await websocket.receive_text()
                await message_queue.put(json.loads(data))
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    async def message_processor():
        while True:
            msg = await message_queue.get()
            event_type = msg.get('event')

            if event_type == 'start':
                stream_sid = msg['start']['streamSid']
                call_sid = msg['start']['callSid']

                call_context = call_contexts.get(call_sid, CallContext())
                call_context.call_sid = call_sid
                call_contexts[call_sid] = call_context

                llm_service.set_call_context(call_context)
                stream_service.set_stream_sid(stream_sid)
                transcription_service.set_stream_sid(stream_sid)

                logger.info(f"Twilio -> Starting Media Stream for {stream_sid}")
                await tts_service.generate({"partialResponseIndex": None, "partialResponse": call_context.initial_message}, 1)

            elif event_type == 'media':
                asyncio.create_task(process_media(msg))

            elif event_type == 'mark':
                label = msg['mark']['name']
                if label in marks:
                    marks.remove(label)

            elif event_type == 'stop':
                logger.info(f"Twilio -> Media stream ended.")
                call_contexts.pop(call_sid, None)  # Cleanup completed calls
                break

            message_queue.task_done()

    try:
        await asyncio.gather(websocket_listener(), message_processor())
    except asyncio.CancelledError:
        logger.info("Tasks cancelled")
    finally:
        await transcription_service.disconnect()


@app.post("/incoming")
async def incoming_call() -> HTMLResponse:
    """Handles inbound Twilio calls and establishes a WebSocket connection."""
    server = os.getenv("SERVER", "").replace("https://", "")
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f"wss://{server}/connection")
    response.append(connect)
    return HTMLResponse(content=str(response), status_code=200)


@app.post("/start_call")
async def start_call(request: Dict[str, str]):
    """Initiates an outbound call using Twilio."""
    to_number = request.get("to_number")
    if not to_number:
        raise HTTPException(status_code=400, detail="Missing 'to_number' in request")

 
    server_url = os.getenv("SERVER", "").replace("https://", "").replace("http://", "")
    service_url = f"https://{server_url}/incoming"
    try:
        client = get_twilio_client()
        call = client.calls.create(
            to=to_number,
            from_=os.getenv("APP_NUMBER"),
            url=service_url
        )
        call_sid = call.sid
        call_contexts[call_sid] = CallContext(call_sid=call_sid)
        return {"call_sid": call_sid}
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")


@app.get("/call_status/{call_sid}")
async def get_call_status(call_sid: str):
    """Retrieves the current status of a call."""
    try:
        call = get_twilio_client().calls(call_sid).fetch()
        return {"status": call.status}
    except Exception as e:
        logger.error(f"Error fetching call status: {str(e)}")
        return {"error": f"Failed to fetch call status: {str(e)}"}


@app.post("/end_call")
async def end_call(request: Dict[str, str]):
    """Ends an active call."""
    call_sid = request.get("call_sid")
    if not call_sid:
        raise HTTPException(status_code=400, detail="Missing 'call_sid' in request")

    try:
        get_twilio_client().calls(call_sid).update(status='completed')
        call_contexts.pop(call_sid, None)  # Cleanup call context
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error ending call: {str(e)}")
        return {"error": f"Failed to end requested call: {str(e)}"}


@app.get("/transcript/{call_sid}")
async def get_transcript(call_sid: str):
    """Retrieves the transcript for a specific call."""
    call_context = call_contexts.get(call_sid)
    if not call_context:
        return {"error": "Call not found"}
    return {"transcript": call_context.user_context}


@app.get("/all_transcripts")
async def get_all_transcripts():
    """Retrieves all call transcripts."""
    return {"transcripts": [{"call_sid": sid, "transcript": ctx.user_context} for sid, ctx in call_contexts.items()]}


def get_twilio_client():
    """Returns an instance of the Twilio Client."""
    return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))