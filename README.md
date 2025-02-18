Canvas Skip to main content
Sean Baker


Building GPTPhone

July,30 2024
8 minute read

TL;DR

I built GPTPhone, a full-stack Python application for interruptible and near-human quality AI phone calls by integrating Large Language Models (LLMs), speech processing, text-to-speech services, and Twilio’s phone API. This post is a companion piece to the GitHub repository and highlights how GPTPhone leverages AI function calling to dynamically handle tasks and instructions mid-call.

![GPTPhone Screenshot]
GPTPhone's web user interface

Example audio recording with GPTPhone

Background

Phone calls are both time-consuming and anxiety-inducing, yet they persist due to their immediacy and reliability. They remain integral to “back-office” tasks, especially in industries like healthcare, which invest heavily in phone-based workflows.

In recent years, AI technologies for text and speech processing have made significant strides, enabling new ways to automate phone communications. This project is my personal journey into building such a system—one that not only generates near-human quality audio but can also invoke specialized functions (function calling) within LLMs for tasks like appointment scheduling, data lookups, or knowledge retrieval, all while maintaining a continuous, real-time conversation.

How it works

![Simplified architecture of GPTPhone]

Inspired by a Twilio Labs project, this application consists of several key components:

Phone Service

Manages incoming and outgoing calls through a virtual phone number.

Speech-to-Text Service

Transcribes the caller’s voice into text in real time.

Detects when the caller finishes speaking or interrupts.

Text-to-text LLM

Understands and steers the conversation based on a "system" message.

Capable of function calling to perform specific tasks (e.g., retrieving data from an external API, scheduling an appointment) on demand, right within the context of the call.

Text-to-Speech Service

Converts the LLM output into high-quality, human-like speech.

Python Web Server

Exposes endpoints for Twilio’s Markup Language (TwiML) to handle call events.

Streams audio to and from Twilio over a WebSocket.

Integrates with a simple Streamlit UI.

Python Web UI

Provides controls to initiate calls, configure the system/initial messages, monitor calls in real time, and replay call recordings.

Why it’s complicated

1. Streaming

Each component (Twilio, LLM, TTS, etc.) adds latency. We minimize delays by streaming data from one service to the next in chunks. For example, we break up LLM-generated text by sentences as they become available. However, the system must wait for the user to stop talking before sending that input to the LLM, ensuring that the AI’s response doesn’t overlap with the user’s speech.

2. Parallelism

Because the caller and callee can talk simultaneously, the architecture must be fully parallel. The original TypeScript version leverages Node’s event-driven paradigm. In Python, I achieved a similar effect using asyncio, ensuring no service remains idle while others work.

3. Interruptions

Current solutions don’t fully utilize GPT-4o’s audio-to-audio capability (which wasn’t available at the time). Instead, we detect speech mid-response and interrupt the AI’s audio generation if the user speaks over it. This abrupt cutoff can make the AI sound less human, but it allows for more natural conversation flows where the user can interject.

4. AI Function Calling

Function calling adds another dimension: the LLM can dynamically decide to call an external function—like scheduling an appointment or retrieving real-time information—before continuing its conversation. This requires well-defined prompts and carefully structured system messages to control how and when these functions are invoked.

Open Challenges and Opportunities

Though this first version shows promise, several challenges and opportunities emerged:

Challenges

Lossy Phone Audio: Twilio calls use G.711 (8 kHz, 8-bit). Noise and compression often degrade audio quality, complicating speech recognition.

Unavoidable Delays: Generating an initial LLM response and chunked TTS output can take 0.5–2 seconds, minimum.

Latency Distributions: In tests, Claude Sonnet 3.5 took an average of ~763 ms for a short response, while GPT-4o averaged ~460 ms. Additional TTS and networking overhead raise these delays further.

Real-time Speech vs. Quality Tradeoff: Speed is critical, so speech recognition accuracy may suffer. Misinterpretations can lead to awkward call moments.

Lost Emotional Cues: Tones and emotions aren’t captured in transcribed text, complicating empathetic or sensitive interactions.

Limited TTS Speed Control: Changing speech pace (e.g., reading a number slowly) isn’t supported.

Varying LLM Behaviors: Different LLMs respond differently to prompts, with diverse function-calling APIs, verbosity, and formats.

Ethical Use: Automated calls, especially near-human sounding ones, can facilitate robocall abuse. Twilio’s Acceptable Use Policy aims to address this, but risks remain.

Opportunities

Future GPT-4o: Possibly replacing STT/TTS if a future GPT audio model can handle speech bi-directionally. However, controlling the AI’s tone and limiting malicious use remain concerns.

Better Audio Chunking: More fine-grained streaming could further reduce latency.

Enhanced UI: Adding function calls visually in the interface, storing conversation logs in a database, and building more robust session management.

API Extensibility: More advanced function-calling workflows could handle appointment bookings, credit card payments, or data retrieval on the fly.

Code Analysis

Below is a high-level overview of the GPTPhone repository’s structure and code logic, based on the GitHub code:

Project Structure

app.py/main.py (or similarly named): Contains the primary application logic, including setup for Flask or FastAPI endpoints, Twilio webhook handling, and orchestration of the speech-to-text (STT) and text-to-speech (TTS) pipelines. This script typically sets up websockets for call audio streaming and coordinates input/output with the LLM.

requirements.txt/Pipfile: Lists Python dependencies such as openai, twilio, numpy, and streamlit. These libraries provide the foundation for LLM queries, phone APIs, numeric computation, and the web user interface.
UI (e.g., streamlit run streamlit_app.py).

Configure Twilio’s Voice webhook for the purchased phone number to point to the server’s public URL (using something like ngrok for local dev).

Future Extensions

Additional function-calling endpoints for tasks like retrieving user account data or performing transactions mid-call.

More flexible, chunked audio strategies for improved real-time performance.

Enhanced user interface with conversation logs and session management.

Acknowledgement

This project draws heavily from a great TypeScript example by Twilio Labs. Massive thanks to Claude Sonnet 3.5, GPT-4o, and Aider for coding assistance. Special shout-out to Mona for testing the code and providing editorial feedback.

GPTPhone—and its function-calling capability—showcases the growing potential to redefine how we handle phone-based tasks. While challenges around latency, ethics, and varied LLM behaviors persist, this project offers a glimpse into a more automated, AI-driven future for phone calls.

