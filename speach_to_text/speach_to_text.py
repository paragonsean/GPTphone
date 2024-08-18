import os

from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from Utils import configure_logger
from EventHandlers import EventHandler

logger = configure_logger("Transcription")

'''
Author: Sean Baker
Date: 2024-07-22 
Description: Transcription service utilizing deepgram helps with logger and user input to pass to gpt 
'''
class TranscriptionService(EventHandler):
    """
    A class that handles live transcription using the Deepgram API.

    Attributes:
        client (DeepgramClient): The Deepgram client used for transcription.
        deepgram_live (DeepgramLive): The Deepgram live transcription instance.
        final_result (str): The final transcription result.
        speech_final (bool): Indicates if the speech is final or not.
        stream_sid (str): The stream ID associated with the transcription.

    Methods:
        set_stream_sid: Sets the stream ID.
        get_stream_sid: Returns the stream ID.
        connect: Connects to the Deepgram API and starts live transcription.
        handle_utterance_end: Handles the event when an utterance ends.
        handle_transcription: Handles the event when a transcription is received.
        handle_error: Handles the event when an error occurs.
        handle_warning: Handles the event when a warning occurs.
        handle_metadata: Handles the event when metadata is received.
        handle_close: Handles the event when the connection is closed.
        send: Sends audio data to the Deepgram API for transcription.
        disconnect: Disconnects from the Deepgram API.
    """

    def __init__(self):
        super().__init__()
        self.client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        self.deepgram_live = None
        self.final_result = ""
        self.speech_final = False
        self.stream_sid = None

    def set_stream_sid(self, stream_id):
        """
        Sets the stream ID associated with the transcription.

        Args:
            stream_id (str): The stream ID.
        """
        self.stream_sid = stream_id

    def get_stream_sid(self):
        """
        Returns the stream ID associated with the transcription.

        Returns:
            str: The stream ID.
        """
        return self.stream_sid

    async def connect(self):
        """
        Connects to the Deepgram API and starts live transcription.
        """
        self.deepgram_live = self.client.listen.asynclive.v("1")
        await self.deepgram_live.start(LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
            punctuate=True,
            interim_results=True,
            endpointing=200,
            utterance_end_ms=1000
        ))

        self.deepgram_live.on(LiveTranscriptionEvents.Transcript, self.handle_transcription)
        self.deepgram_live.on(LiveTranscriptionEvents.Error, self.handle_error)
        self.deepgram_live.on(LiveTranscriptionEvents.Close, self.handle_close)
        self.deepgram_live.on(LiveTranscriptionEvents.Warning, self.handle_warning)
        self.deepgram_live.on(LiveTranscriptionEvents.Metadata, self.handle_metadata)
        self.deepgram_live.on(LiveTranscriptionEvents.UtteranceEnd, self.handle_utterance_end)

    async def handle_utterance_end(self, self_obj, utterance_end):
        """
        Handles the event when an utterance ends.

        Args:
            self_obj: The self object.
            utterance_end: The utterance end event.
        """
        try:
            if not self.speech_final:
                logger.info(
                    f"UtteranceEnd received before speech was final, emit the text collected so far: {self.final_result}")
                await self.createEvent('transcription', self.final_result)
                self.final_result = ''
                self.speech_final = True
                return
            else:
                return
        except Exception as e:
            logger.error(f"Error while handling utterance end: {e}")
            e.print_stack()

    async def handle_transcription(self, self_obj, result):
        """
        Handles the event when a transcription is received.

        Args:
            self_obj: The self object.
            result: The transcription result.
        """
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
                    stream_sid = self.stream_sid
                    await self.createEvent('utterance', text, stream_sid)
        except Exception as e:
            logger.error(f"Error while handling transcription: {e}")
            e.print_stack()

    async def handle_error(self, self_obj, error):
        """
        Handles the event when an error occurs.

        Args:
            self_obj: The self object.
            error: The error message.
        """
        logger.error(f"Deepgram error: {error}")
        self.is_connected = False

    async def handle_warning(self, self_obj, warning):
        """
        Handles the event when a warning occurs.

        Args:
            self_obj: The self object.
            warning: The warning message.
        """
        logger.info('Deepgram warning:', warning)

    async def handle_metadata(self, self_obj, metadata):
        """
        Handles the event when metadata is received.

        Args:
            self_obj: The self object.
            metadata: The metadata.
        """
        logger.info('Deepgram metadata:', metadata)

    async def handle_close(self, self_obj, close):
        """
        Handles the event when the connection is closed.

        Args:
            self_obj: The self object.
            close: The close event.
        """
        logger.info("Deepgram connection closed")
        self.is_connected = False

    async def send(self, payload: bytes):
        """
        Sends audio data to the Deepgram API for transcription.

        Args:
            payload (bytes): The audio data.
        """
        if self.deepgram_live:
            await self.deepgram_live.send(payload)

    async def disconnect(self):
        """
        Disconnects from the Deepgram API.
        """
        if self.deepgram_live:
            await self.deepgram_live.finish()
            self.deepgram_live = None
        self.is_connected = False
        logger.info("Disconnected from Deepgram")