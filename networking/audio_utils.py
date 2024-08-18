import copy
import io

import torchaudio
from pydub import AudioSegment

from Utils.my_logger import configure_logger

logger = configure_logger(__name__)

def convert_audio_to_wav(audio_bytes, source_format='flac'):
    logger.info(f"CONVERTING AUDIO TO WAV {source_format}")
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)
    logger.info(f"GOT audio wav {audio}")
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")
    logger.info(f"SENDING BACK WAV")
    return buffer.getvalue()

def create_ws_data_packet(data, meta_info=None, is_md5_hash=False, llm_generated=False):
    metadata = copy.deepcopy(meta_info)
    if meta_info is not None:  # It'll be none in case we connect through dashboard playground
        metadata["is_md5_hash"] = is_md5_hash
        metadata["llm_generated"] = llm_generated
    return {
        'data': data,
        'meta_info': metadata
    }

def resample(audio_bytes, target_sample_rate, format="mp3"):
    audio_buffer = io.BytesIO(audio_bytes)
    waveform, orig_sample_rate = torchaudio.load(audio_buffer, format=format)
    if orig_sample_rate == target_sample_rate:
        return audio_bytes
    resampler = torchaudio.transforms.Resample(orig_sample_rate, target_sample_rate)
    audio_waveform = resampler(waveform)
    audio_buffer = io.BytesIO()
    logger.info(f"Resampling from {orig_sample_rate} to {target_sample_rate}")
    torchaudio.save(audio_buffer, audio_waveform, target_sample_rate, format="wav")
    return audio_buffer.getvalue()
