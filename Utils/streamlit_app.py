import os
import time
import requests
import streamlit as st
import dotenv

dotenv.load_dotenv(verbose=True)

st.set_page_config(page_title="AI Dialer", page_icon="📞", layout="wide")

# Fix: Strip "https://" if it's included in SERVER to avoid double protocol issues.
SERVER = os.getenv("SERVER", "").replace("https://", "").replace("http://", "")

def display_call_interface():
    return st.text_input("Phone Number (format: +1XXXXXXXXXX)", value=os.getenv("YOUR_NUMBER") or "")

def fetch_all_transcripts():
    """Fetches all call transcripts from the backend."""
    try:
        url = f"https://{SERVER}/all_transcripts"
        response = requests.get(url)
        response.raise_for_status()  # Raises an error if request fails
        return response.json().get("transcripts", [])
    except requests.RequestException as e:
        st.error(f"Error fetching call list: {str(e)}")
        return []

if 'call_active' not in st.session_state:
    st.session_state.call_active = False
    st.session_state.call_sid = None
    st.session_state.transcript = []
    st.session_state.system_message = os.getenv("SYSTEM_MESSAGE")
    st.session_state.initial_message = os.getenv("INITIAL_MESSAGE")
    st.session_state.all_transcripts = fetch_all_transcripts()
    st.session_state.recording_info = None
    st.session_state.call_selector = "Current Call"

with st.sidebar:
    st.markdown("<h2 style='text-align: center; font-size: 2.5em;'>📞 AI Dialer</h2>", unsafe_allow_html=True)
    st.divider()

    phone_number = display_call_interface()

    st.session_state.system_message = st.text_area("System Message", value=st.session_state.system_message, disabled=st.session_state.call_active)
    st.session_state.initial_message = st.text_area("Initial Message", value=st.session_state.initial_message, disabled=st.session_state.call_active)

    start_call = st.button("Start Call", disabled=st.session_state.call_active)
    end_call = st.button("End Call", disabled=not st.session_state.call_active)

    if start_call and phone_number:
        with st.spinner(f"Calling {phone_number}..."):
            try:
                response = requests.post(
                    f"https://{SERVER}/start_call",
                    json={
                        "to_number": phone_number,
                        "system_message": st.session_state.system_message,
                        "initial_message": st.session_state.initial_message
                    },
                    timeout=10
                )
                response.raise_for_status()
                call_data = response.json()

                if call_sid := call_data.get("call_sid"):
                    st.session_state.call_sid = call_sid
                    st.session_state.transcript = []
                    st.success(f"Call initiated. SID: {call_sid}")

                    for _ in range(60):
                        time.sleep(1)
                        status = requests.get(f"https://{SERVER}/call_status/{call_sid}").json().get("status")
                        if status == "in-progress":
                            st.session_state.call_active = True
                            st.session_state.call_selector = "Current Call"
                            break
                        if status in ["completed", "failed", "busy", "no-answer"]:
                            st.error(f"Call ended: {status}")
                            break
                    else:
                        st.error("Timeout waiting for call to connect.")
                else:
                    st.error(f"Failed to initiate call: {call_data}")

            except requests.RequestException as e:
                st.error(f"Error: {str(e)}")
    elif start_call:
        st.warning("Please enter a valid phone number.")

    if end_call:
        try:
            response = requests.post(f"https://{SERVER}/end_call", json={"call_sid": st.session_state.call_sid})
            response.raise_for_status()
            st.success("Call ended successfully.")
            st.session_state.call_active = False
            st.session_state.call_sid = None
            st.rerun()
        except requests.RequestException as e:
            st.error(f"Error ending call: {str(e)}")

    if st.session_state.call_active:
        st.success("Call in progress")
    st.divider()

def fetch_recording_info(call_sid):
    """Fetches recording URL for a specific call."""
    try:
        url = f"https://{SERVER}/call_recording/{call_sid}"
        response = requests.get(url)
        response.raise_for_status()

        if media_url := response.json().get("recording_url"):
            return {"url": f"{media_url}.mp3", "duration": 0}  # No duration info provided in the response
    except requests.RequestException as e:
        st.error(f"Error fetching recording info: {str(e)}")
    return None

def on_call_selector_change():
    """Handles user selection of a different call."""
    if st.session_state.call_selector != "Current Call":
        selected_transcript = next((t for t in st.session_state.all_transcripts if f"Call {t['call_sid']}" == st.session_state.call_selector), None)
        if selected_transcript:
            st.session_state.recording_info = fetch_recording_info(selected_transcript["call_sid"])
        else:
            st.warning("No transcript found for the selected call.")
    else:
        st.session_state.recording_info = None

st.selectbox(
    "Select a call",
    options=["Current Call"] + [f"Call {t['call_sid']}" for t in st.session_state.all_transcripts],
    key="call_selector",
    index=0,
    disabled=st.session_state.call_active,
    on_change=on_call_selector_change
)

if st.button("Refresh Call List"):
    try:
        st.session_state.all_transcripts = fetch_all_transcripts()
        on_call_selector_change()
    except requests.RequestException as e:
        st.error(f"Error fetching call list: {str(e)}")

st.divider()

with st.spinner("Loading recording and transcript..."):
    if st.session_state.call_selector != "Current Call" and st.session_state.recording_info:
        st.subheader("Call Recording")
        audio_url = st.session_state.recording_info["url"]
        st.audio(audio_url, format="audio/mp3", start_time=0)
        st.divider()

    if st.session_state.call_active and st.session_state.call_sid:
        st.subheader(f"Transcript for Current Call {st.session_state.call_sid}")
        for entry in st.session_state.transcript:
            st.chat_message(entry["role"]).write(entry["content"])
    elif st.session_state.call_selector != "Current Call":
        transcript = next((t for t in st.session_state.all_transcripts if f"Call {t['call_sid']}" == st.session_state.call_selector), None)
        if transcript:
            st.subheader(f"Transcript for {st.session_state.call_selector}")
            for entry in transcript["transcript"]:
                st.chat_message(entry["role"]).write(entry["content"])

if st.session_state.call_active:
    def update_call_info():
        """Updates call status and transcript information."""
        try:
            status = requests.get(f"https://{SERVER}/call_status/{st.session_state.call_sid}").json().get("status")
            if status not in ["in-progress", "ringing"]:
                st.session_state.call_active = False
                st.warning(f"Call ended: {status}")
                return False

            transcript_data = requests.get(f"https://{SERVER}/transcript/{st.session_state.call_sid}").json()
            if transcript_data.get("call_ended", False):
                st.session_state.call_active = False
                st.info(f"Call ended. Status: {transcript_data.get('final_status', 'Unknown')}")
                return False

            st.session_state.transcript = transcript_data.get("transcript", [])
            return True
        except requests.RequestException as e:
            st.sidebar.error(f"Error updating call info: {str(e)}")
            return False

    if update_call_info():
        time.sleep(1)
        st.rerun()
    else:
        st.session_state.call_active = False
        st.session_state.call_sid = None
        st.sidebar.info("Call has ended. You can start a new call if needed.")
        st.rerun()