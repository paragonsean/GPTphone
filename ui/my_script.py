import os
import sys
import tempfile
import threading
import queue
import pygame
import gtts
import speech_recognition as sr
from tkinter import Tk, Text, Button, END, Label
from dotenv import load_dotenv
import openai
import websockets
import asyncio

from networking.default_input import WebSocketService

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI API
if not OPENAI_API_KEY:
    print("OpenAI API key not found. Please set it in your environment variables.")
    sys.exit(1)
openai.api_key = OPENAI_API_KEY

async def websocket_handler(uri, response_queue):
    async with websockets.connect(uri) as websocket:
        service = WebSocketService(websocket, response_queue)
        await service.run()

def setup_tts():
    pygame.mixer.init()
    return pygame.mixer

def text_to_speech(text, mixer):
    try:
        tts = gtts.gTTS(text, lang="en")
        with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as fp:
            tts.save(fp.name)
            mixer.music.load(fp.name)
            mixer.music.play()
            while mixer.music.get_busy():
                pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Error in text-to-speech: {e}")

def recognize_speech_from_mic(recognizer, microphone):
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "I'm sorry, I didn't catch that."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"

def listen_and_respond(queue, recognizer, microphone, text_widget):
    while True:
        text_widget.insert(END, "\nJARVIS: I'm listening...")
        user_input = recognize_speech_from_mic(recognizer, microphone)
        text_widget.insert(END, f"\nYou: {user_input}")

        if user_input.lower() in ["quit", "exit", "bye"]:
            text_widget.insert(END, "\nJARVIS: Goodbye, Sir. Have a great day ahead.")
            break

        asyncio.run_coroutine_threadsafe(service.process_gui_input(user_input), asyncio.get_event_loop())

def update_speech(queue, mixer):
    while True:
        response = queue.get()
        if response:
            text_to_speech(response, mixer)

def create_gui():
    root = Tk()
    root.title("JARVIS AI Assistant")

    text_widget = Text(root, height=20, width=80)
    text_widget.pack(padx=10, pady=10)
    text_widget.insert(END, "JARVIS: Hello Sir, I am your assistant. How may I assist you today?")

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    mixer = setup_tts()
    response_queue = queue.Queue()

    threading.Thread(target=listen_and_respond, args=(response_queue, recognizer, microphone, text_widget), daemon=True).start()
    threading.Thread(target=update_speech, args=(response_queue, mixer), daemon=True).start()

    # Start the WebSocket service in the background
    asyncio.get_event_loop().run_until_complete(websocket_handler('ws://localhost:8000/ws', response_queue))

    root.mainloop()

if __name__ == "__main__":
    create_gui()
