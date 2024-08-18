import asyncio
import copy
import json
import os
from datetime import datetime
import loguru as logger
import aiofiles



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