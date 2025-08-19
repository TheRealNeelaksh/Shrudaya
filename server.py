# server.py

import asyncio
import base64
import json
import logging
import numpy as np
import torch
import tempfile
import wave
import os
import re
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# --- Your Project's Modules ---
from brain.mistralAPI_brain import stream_mistral_chat_async
from stt.sarvamSTT import transcribe_audio
from logs.logger import log_conversation
from tts.elevenLabs.xiTTS import stream_tts_audio

# ==============================================================================
# 1. CONFIGURATION & SETUP
# ==============================================================================

load_dotenv()
logging.basicConfig(level=logging.INFO)
app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")
SAMPLE_RATE = 16000

# ==============================================================================
# 2. VAD MODULE (PyTorch, loaded from local project)
# ==============================================================================
try:
    model, utils = torch.hub.load(
        repo_or_dir='vad_model/silero-vad-master',
        model='silero_vad',
        source='local',
        trust_repo=True
    )
    (get_speech_timestamps, _, _, VADIterator, _) = utils
    logging.info("Local PyTorch VAD model loaded successfully.")
except Exception as e:
    logging.error(f"FATAL: Could not load local VAD model. Ensure 'vad_model/silero-vad-master' exists. Error: {e}")
    exit()

# ==============================================================================
# 3. FASTAPI SERVER LOGIC
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def safe_send(websocket: WebSocket, message: dict):
    try: await websocket.send_text(json.dumps(message))
    except RuntimeError: logging.warning("WebSocket is closed.")

# --- Processing Pipelines ---
async def tts_consumer(websocket: WebSocket, text_queue: asyncio.Queue):
    await safe_send(websocket, {"type": "tts_start"})
    while True:
        try:
            sentence = await text_queue.get()
            if sentence is None: break
            if not sentence.strip(): continue
            async for audio_chunk in stream_tts_audio(sentence):
                await websocket.send_bytes(audio_chunk)
            text_queue.task_done()
        except RuntimeError: break
        except Exception as e: logging.error(f"Error in TTS consumer: {e}"); break
    await safe_send(websocket, {"type": "tts_end"})

async def llm_producer(websocket: WebSocket, transcript: str, conversation_history: list, text_queue: asyncio.Queue):
    full_reply, sentence_buffer = "", ""
    sentence_delimiters = re.compile(r'(?<=[.?!])\s*')
    try:
        async for text_chunk in stream_mistral_chat_async(transcript, conversation_history):
            full_reply += text_chunk
            sentence_buffer += text_chunk
            await safe_send(websocket, {"type": "ai_text_chunk", "data": text_chunk})
            parts = sentence_delimiters.split(sentence_buffer)
            if len(parts) > 1:
                for i in range(len(parts) - 1):
                    if parts[i].strip(): await text_queue.put(parts[i].strip())
                sentence_buffer = parts[-1]
        if sentence_buffer.strip(): await text_queue.put(sentence_buffer.strip())
        log_conversation("AI", full_reply)
    except Exception as e:
        logging.error(f"Error in LLM producer: {e}")
        await text_queue.put("I'm sorry, I'm having a little trouble connecting right now.")
    finally:
        await text_queue.put(None)

async def _process_voice_message(websocket: WebSocket, audio_bytes: bytes, conversation_history: list):
    tmp_wav_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name
            with wave.open(tmp_wav, 'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_bytes)
        transcript = await asyncio.to_thread(transcribe_audio, tmp_wav_path)
        if not transcript or not transcript.strip(): return
        await safe_send(websocket, {"type": "user_transcript", "data": transcript})
        log_conversation("User (voice)", transcript)
        text_queue = asyncio.Queue()
        tts_task = asyncio.create_task(tts_consumer(websocket, text_queue))
        llm_task = asyncio.create_task(llm_producer(websocket, transcript, conversation_history, text_queue))
        await asyncio.gather(llm_task, tts_task)
    finally:
        if tmp_wav_path and os.path.exists(tmp_wav_path): os.remove(tmp_wav_path)

# CORRECTED VERSION of the text message processor
async def _process_text_message(websocket: WebSocket, transcript: str, conversation_history: list):
    log_conversation("User (text)", transcript)
    # The JS has already displayed the user's message, so we don't send it back.
    full_reply = ""
    try:
        async for text_chunk in stream_mistral_chat_async(transcript, conversation_history):
            full_reply += text_chunk
            await safe_send(websocket, {"type": "ai_text_chunk", "data": text_chunk})
        log_conversation("AI (text)", full_reply)
    except Exception as e:
        logging.error(f"Error in text message LLM producer: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # RE-ADDED: Password Protection Logic
    app_password = os.getenv("APP_PASSWORD")
    password_from_client = websocket.query_params.get("password")

    if app_password and password_from_client != app_password:
        logging.warning("WebSocket connection rejected due to incorrect password.")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    await websocket.accept()
    conversation_history: List[dict] = []
    
    vad_iterator = VADIterator(model, threshold=0.5)
    
    audio_buffer = torch.empty(0, dtype=torch.float32)
    speech_audio_buffer = []
    is_speaking = False
    end_speech_timer = None
    
    async def process_utterance():
        nonlocal is_speaking, speech_audio_buffer
        if not speech_audio_buffer: 
            is_speaking = False
            return
        is_speaking = False
        logging.info("Processing full utterance after pause.")
        full_utterance_tensor = torch.cat(speech_audio_buffer)
        speech_audio_buffer = []
        speech_bytes = (full_utterance_tensor * 32767).to(torch.int16).numpy().tobytes()
        asyncio.create_task(_process_voice_message(websocket, speech_bytes, conversation_history))

    async def start_end_speech_timer():
        await asyncio.sleep(0.8)
        if is_speaking:
            await process_utterance()

    try:
        while True:
            message_text = await websocket.receive_text()
            message = json.loads(message_text)
            if message['type'] == 'audio_chunk':
                audio_data_bytes = base64.b64decode(message['data'])
                new_audio_tensor = torch.from_numpy(np.frombuffer(audio_data_bytes, dtype=np.float32).copy())
                audio_buffer = torch.cat([audio_buffer, new_audio_tensor])
                VAD_WINDOW_SIZE = 512
                while audio_buffer.shape[0] >= VAD_WINDOW_SIZE:
                    current_window = audio_buffer[:VAD_WINDOW_SIZE]
                    audio_buffer = audio_buffer[VAD_WINDOW_SIZE:]
                    if is_speaking:
                        speech_audio_buffer.append(current_window)
                    speech_dict = vad_iterator(current_window, return_seconds=True)
                    if speech_dict:
                        if 'start' in speech_dict:
                            if not is_speaking:
                                is_speaking = True
                                speech_audio_buffer = [current_window]
                                logging.info("Speech start detected.")
                            if end_speech_timer and not end_speech_timer.done():
                                end_speech_timer.cancel()
                        if 'end' in speech_dict and is_speaking:
                            if not end_speech_timer or end_speech_timer.done():
                               end_speech_timer = asyncio.create_task(start_end_speech_timer())
            elif message['type'] == 'text_message':
                asyncio.create_task(_process_text_message(websocket, message['data'], conversation_history))
    except WebSocketDisconnect:
        logging.info("WebSocket connection closed.")