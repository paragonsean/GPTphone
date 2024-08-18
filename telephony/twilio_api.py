import os

from dotenv import load_dotenv
from twilio.rest import Client

from Utils.singleton_logger import configure_logger
from services import CallContext
from .telephony_input_ouput_handler import TelephonyInputHandler

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
APP_NUMBER = os.getenv("APP_NUMBER")
SYSTEM_MESSAGE = os.getenv("SYSTEM_MESSAGE") or "Default System Message"
INITIAL_MESSAGE = os.getenv("Config.INITIAL_MESSAGE") or "Default Initial Message"
RECORDING_URL_PREFIX = "https://api.twilio.com/"
load_dotenv()

logger = configure_logger(__name__)

class TwilioTelephonyHandler(TelephonyInputHandler):
    def __init__(self, logger_class):
        super().__init__(logger_class)
        self.client = self._create_twilio_client()
        self.logger = basic_logger(__name__)

    def _create_twilio_client(self):
        return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    def initiate_call(self, to_number, service_url, system_message=SYSTEM_MESSAGE, initial_message=INITIAL_MESSAGE):
        try:
            self.logger.info(f"Initiating call to {to_number} via {service_url}")
            call = self.client.calls.create(
                to=to_number,
                from_=APP_NUMBER,
                url=service_url
            )
            call_sid = call.sid
            call_context = self.create_call_context(call_sid, system_message, initial_message, to_number, APP_NUMBER)
            return {"call_sid": call_sid}
        except Exception as error:
            self.log_error("Error initiating call", error)

    def create_call_context(self, call_sid, system_message, initial_message, to_number, from_number):
        return CallContext(
            call_sid=call_sid,
            system_message=system_message,
            initial_message=initial_message,
            to_number=to_number,
            from_number=from_number
        )

    def get_call_status(self, call_sid):
        try:
            call_status = self.client.calls(call_sid).fetch()
            return {"status": call_status}
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
            return {"recording_url": RECORDING_URL_PREFIX + recording[0].uri} if recording else {
                "error": "Recording not found"}
        except Exception as e:
            self.log_error("Error fetching recording", e)
