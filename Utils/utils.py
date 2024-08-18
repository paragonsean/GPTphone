import asyncio
import copy
import io
import json
import os
from datetime import datetime
from .singleton_logger import configure_logger
import aiofiles
import torch
import torchaudio
from pydub import AudioSegment

logger = configure_logger(__name__)



def format_messages(messages, use_system_prompt=False):
    formatted_string = ""
    for message in messages:
        role = message['role']
        content = message['content']

        if use_system_prompt and role == 'system':
            formatted_string += "system: " + content + "\n"
        if role == 'assistant':
            formatted_string += "assistant: " + content + "\n"
        elif role == 'user':
            formatted_string += "user: " + content + "\n"

    return formatted_string
def load_file(file_path, is_json=False):
    data = None
    with open(file_path, "r") as f:
        if is_json:
            data = json.load(f)
        else:
            data = f.read()

    return data


def write_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

async def write_request_logs(message, run_id):
    component_details = [None, None, None, None, None]
    logger.info(f"Message {message}")
    message_data = message.get('data', '')
    if message_data is None:
        message_data = ''

    row = [message['time'], message["component"], message["direction"], message["leg_id"], message['sequence_id'],
           message['model']]
    if message["component"] == "llm":
        component_details = [message_data, message.get('input_tokens', 0), message.get('output_tokens', 0), None,
                             message.get('latency', None), message['cached'], None]
    elif message["component"] == "transcriber":
        component_details = [message_data, None, None, None, message.get('latency', None), False,
                             message.get('is_final', False)]
    elif message["component"] == "synthesizer":
        component_details = [message_data, None, None, len(message_data), message.get('latency', None),
                             message['cached'], None, message['engine']]
    elif message["component"] == "function_call":
        component_details = [message_data, None, None, None, message.get('latency', None), None, None, None]

    row = row + component_details

    header = "Time,Component,Direction,Leg ID,Sequence ID,Model,Data,Input Tokens,Output Tokens,Characters,Latency,Cached,Final Transcript,Engine\n"
    log_string = ','.join(['"' + str(item).replace('"', '""') + '"' if item is not None else '' for item in row]) + '\n'
    log_dir = f"./logs/{run_id.split('#')[0]}"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = f"{log_dir}/{run_id.split('#')[1]}.csv"
    file_exists = os.path.exists(log_file_path)

    async with aiofiles.open(log_file_path, mode='a') as log_file:
        if not file_exists:
            await log_file.write(header + log_string)
        else:
            await log_file.write(log_string)
def convert_to_request_log(message, meta_info, model, component = "transcriber", direction = 'response', is_cached = False, engine=None, run_id = None):
    log = dict()
    log['direction'] = direction
    log['data'] = message
    log['leg_id'] = meta_info['request_id'] if "request_id" in meta_info else "1234"
    log['time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log['component'] = component
    log['sequence_id'] = meta_info['sequence_id']
    log['model'] = model
    log['cached'] = is_cached
    if component == "llm":
        log['latency'] = meta_info.get('llm_latency', None) if direction == "response" else None
    if component == "synthesizer":
        log['latency'] = meta_info.get('synthesizer_latency', None) if direction == "response" else None
    if component == "transcriber":
        log['latency'] = meta_info.get('transcriber_latency', None) if direction == "response" else None
        if 'is_final' in meta_info and meta_info['is_final']:
            log['is_final'] = True
    if component == "function_call":
        logger.info(f"Logging {message} {log['data']}")
        log['latency'] = None
    else:
        log['is_final'] = False #This is logged only for users to know final transcript from the transcriber
    log['engine'] = engine
    asyncio.create_task(write_request_logs(log, run_id))

def create_ws_data_packet(data, meta_info=None, is_md5_hash=False, llm_generated=False):
    metadata = copy.deepcopy(meta_info)
    if meta_info is not None: #It'll be none in case we connect through dashboard playground
        metadata["is_md5_hash"] = is_md5_hash
        metadata["llm_generated"] = llm_generated
    return {
        'data': data,
        'meta_info': metadata
    }

def pcm_to_wav_bytes(pcm_data, sample_rate = 16000, num_channels = 1, sample_width = 2):
    buffer = io.BytesIO()
    bit_depth = 16
    if len(pcm_data)%2 == 1:
        pcm_data += b'\x00'
    tensor_pcm = torch.frombuffer(pcm_data, dtype=torch.int16)
    tensor_pcm = tensor_pcm.float() / (2**(bit_depth - 1))
    tensor_pcm = tensor_pcm.unsqueeze(0)
    torchaudio.save(buffer, tensor_pcm, sample_rate, format='wav')
    return buffer.getvalue()

def convert_audio_to_wav(audio_bytes, source_format = 'flac'):
    logger.info(f"CONVERTING AUDIO TO WAV {source_format}")
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)
    logger.info(f"GOT audio wav {audio}")
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")
    logger.info(f"SENDING BACK WAV")
    return buffer.getvalue()


def resample(audio_bytes, target_sample_rate, format = "mp3"):
    audio_buffer = io.BytesIO(audio_bytes)
    waveform, orig_sample_rate = torchaudio.load(audio_buffer, format = format)
    if orig_sample_rate == target_sample_rate:
        return audio_bytes
    resampler = torchaudio.transforms.Resample(orig_sample_rate, target_sample_rate)
    audio_waveform = resampler(waveform)
    audio_buffer = io.BytesIO()
    logger.info(f"Resampling from {orig_sample_rate} to {target_sample_rate}")
    torchaudio.save(audio_buffer, audio_waveform, target_sample_rate, format="wav")
    return audio_buffer.getvalue()
