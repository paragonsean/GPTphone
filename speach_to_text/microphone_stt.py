from deepgram import Microphone

from speach_to_text.base_stt import BaseTranscriber


class MicrophoneTranscriber(BaseTranscriber):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.microphone = None

    async def connect(self):
        try:
            self.deepgram_live = self.client.listen.asyncwebsocket.v("1")
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

            addons = {"no_delay": "true"}

            logger.info("\n\nStart talking! Press Ctrl+C to stop...\n")

            if await self.deepgram_live.start(options, addons=addons) is False:
                logger.info("Failed to connect to Deepgram")
                return

            self.microphone = Microphone(self.deepgram_live.send)
            self.microphone.start()

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                self.microphone.finish()
                await self.deepgram_live.finish()

            logger.info("Finished")

        except Exception as e:
            logger.error(f"Could not open socket: {e}")

    async def shutdown(self, signal):
        logger.info(f"Received exit signal {signal.name}...")
        if self.microphone:
            self.microphone.finish()
        await self.disconnect()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()
        logger.info("Shutdown complete.")
