
from .telephone_base import TelephonyBaseInputHandler,TelephonyBaseOutputHandler


class TelephonyInputHandler(TelephonyBaseInputHandler):
    async def handle(self, packet):
        await super().handle(packet)

    async def call_start(self, packet):
        await super().call_start(packet)

    async def process_message(self, message):
        await super().process_message(message)


class TelephonyOutputHandler(TelephonyBaseOutputHandler):
    async def handle(self, packet):
        await super().handle(packet)

    async def handle_interruption(self):
        await super().handle_interruption()

    async def form_media_message(self, audio_data, audio_format):
        await super().form_media_message(audio_data, audio_format)

    async def form_mark_message(self, mark_id):
        await super().form_mark_message(mark_id)
