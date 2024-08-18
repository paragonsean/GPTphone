import os

from twilio.rest import Client
from fastapi import HTTPException

from services import CallContext
from .telephone_base import TelephonyInputHandler

class Twilio(TelephonyInputHandler):
    def __init__(self, logger):
        super().__init__(logger)
        self.client = self.get_twilio_client()

    def get_twilio_client(self):
        return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

    def initiate_call(self, to_number, service_url, system_message=None, initial_message=None):
        try:
            self.logger.info(f"Initiating call to {to_number} via {service_url}")
            call = self.client.calls.create(
                to=to_number,
                from_=os.getenv("APP_NUMBER"),
                url=service_url
            )
            call_sid = call.sid

            # Create CallContext instance
            call_context = CallContext(
                call_sid=call_sid,
                system_message=system_message or os.getenv("SYSTEM_MESSAGE"),
                initial_message=initial_message or os.getenv("Config.INITIAL_MESSAGE"),
                to_number=to_number,
                from_number=os.getenv("APP_NUMBER")
            )


            return {"call_sid": call_sid}
        except Exception as e:
            self.log_error("Error initiating call", e)

    def get_call_status(self, call_sid):
        try:
            call = self.client.calls(call_sid).fetch()
            return {"status": call.status}
        except Exception as e:
            self.log_error("Error fetching call status", e)

    def end_call(self, call_sid):
        try:
            self.client.calls(call_sid).update(status='completed')
            return {"status": "success"}
        except Exception as e:
            self.log_error("Error ending call", e)

    def get_recording(self, call_sid):
        try:
            recording = self.client.calls(call_sid).recordings.list()
            if recording:
                return {"recording_url": f"https://api.twilio.com/{recording[0].uri}"}
            return {"error": "Recording not found"}
        except Exception as e:
            self.log_error("Error fetching recording", e)
from .telephone_base import TelephonyInputHandler
from dotenv import load_dotenv
from Utils.logger_config import configure_logger

logger = configure_logger(__name__)
load_dotenv()


class TwilioInputHandler(TelephonyInputHandler):
    def __init__(self, queues, websocket=None, input_types=None, mark_set=None, turn_based_conversation=False):
        super().__init__(queues, websocket, input_types, mark_set, turn_based_conversation)
        self.io_provider = 'twilio'

    async def call_start(self, packet):
        start = packet['start']
        self.call_sid = start['callSid']
        self.stream_sid = start['streamSid']
