import datetime
import os
from typing import Dict

from twilio.rest import Client
from twilio.rest.insights.v1.call import CallContext as TwilioCallContext




class TwilioService:
    def __init__(self, call_contexts: Dict[str, TwilioCallContext]):
        self.client = self.get_twilio_client()
        self.call_contexts  = call_contexts

    def get_twilio_client(self):
        return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

    def initiate_call(self, to_number: str, system_message: str, initial_message: str) -> str:
        service_url = f"https://{os.getenv('SERVER')}/incoming"
        call = self.client.calls.create(
            to=to_number,
            from_=os.getenv("APP_NUMBER"),
            url=service_url
        )
        call_sid = call.sid

        # Create CallContext instance
        call_context = TwilioCallContext(
            call_sid=call_sid,
            system_message=system_message or os.getenv("SYSTEM_MESSAGE"),
            initial_message=initial_message or os.getenv("Config.INITIAL_MESSAGE"),
            to_number=to_number,
            from_number=os.getenv("APP_NUMBER"),
            start_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            date=datetime.datetime.now().strftime("%Y-%m-%d")
        )
        self.call_contexts[call_sid] = call_context

        return call_sid

    def get_call_status(self, call_sid: str) -> str:
        call = self.client.calls(call_sid).fetch()
        return call.status

    def end_call(self, call_sid: str):
        self.client.calls(call_sid).update(status='completed')

    def get_call_recording(self, call_sid: str) -> str:
        recordings = self.client.calls(call_sid).recordings.list()
        if recordings:
            return f"https://api.twilio.com/{recordings[0].uri}"
        return None

    def get_transcript(self, call_sid: str) -> Dict:
        return self.call_contexts.get(call_sid)

    def get_all_transcripts(self) -> Dict:
        transcripts = []
        for call_sid, context in self.call_contexts.items():
            transcripts.append({
                "call_sid": call_sid,
                "transcript": context.messages,
            })
        return transcripts
