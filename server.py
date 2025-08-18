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
from pathlib import Path
from typing import List
from urllib.request import urlretrieve

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from brain.mistralAPI_brain import stream_mistral_chat_async
from stt.sarvamSTT import transcribe_audio
from logs.logger import log_conversation
from tts.elevenLabs.xiTTS import stream_tts_audio

app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")
logging.basicConfig(level=logging.INFO)
SAMPLE_RATE = 16000

# --- VAD MODEL SETUP WITH INTEGRATED DOWNLOAD ---

# 1. Define the local path for the model repository
VAD_REPO_PATH = Path("vad_model/silero-vad-master")

# 2. Check if the model directory exists, download and unzip if it doesn't
if not VAD_REPO_PATH.exists():
    logging.info("VAD model repository not found locally. Downloading...")
    import zipfile
    import io
    
    # URL to the ZIP file of the repository
    zip_url = "https://github.com/snakers4/silero-vad/archive/refs/heads/master.zip"
    
    try:
        # Download the zip file into memory
        response = urlretrieve(zip_url)
        zip_path = response[0]
        
        # Create the parent directory
        VAD_REPO_PATH.parent.mkdir(exist_ok=True)
        
        # Unzip the contents
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(VAD_REPO_PATH.parent)
        
        logging.info("VAD model repository downloaded and unzipped successfully.")
        os.remove(zip_path) # Clean up the downloaded zip file
        
    except Exception as e:
        logging.error(f"FATAL: Failed to download and unzip VAD model. Error: {e}")
        exit()

# 3. Load the model from the now-guaranteed local path
try:
    model, utils = torch.hub.load(
        repo_or_dir=str(VAD_REPO_PATH),
        model='silero_vad',
        source='local',
        force_reload=True 
    )
    (get_speech_timestamps, _, _, VADIterator, _) = utils
    logging.info("Local PyTorch VAD model loaded successfully.")
except Exception as e:
    logging.error(f"FATAL: Could not load local VAD model. Error: {e}")
    exit()

# --- END VAD MODEL SETUP ---

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def safe_send(websocket: WebSocket, message: dict):
    try: await websocket.send_text(json.dumps(message))
    except RuntimeError: logging.warning("WebSocket is closed, cannot send message.")

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
    full_reply = ""
    sentence_buffer = ""
    sentence_delimiters = re.compile(r'(?<=[.?!])\s*')
    try:
        async for text_chunk in stream_mistral_chat_async(transcript, conversation_history):
            full_reply += text_chunk
            sentence_buffer += text_chunk
            await safe_send(websocket, {"type": "ai_text_chunk", "data": text_chunk})
            parts = sentence_delimiters.split(sentence_buffer)
            if len(parts) > 1:
                for i in range(len(parts) - 1):
                    sentence_to_tts = parts[i].strip()
                    if sentence_to_tts: await text_queue.put(sentence_to_tts)
                sentence_buffer = parts[-1]
        if sentence_buffer.strip():
            await text_queue.put(sentence_buffer.strip())
        log_conversation("AI", full_reply)
    except Exception as e:
        logging.error(f"Error in LLM producer: {e}")
        await text_queue.put("I'm sorry, I'm having a little trouble connecting right now.")
    finally:
        await text_queue.put(None)

async def _process_audio_chunk(websocket: WebSocket, audio_bytes: bytes, conversation_history: list):
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
        log_conversation("User", transcript)
        text_queue = asyncio.Queue()
        tts_task = asyncio.create_task(tts_consumer(websocket, text_queue))
        llm_task = asyncio.create_task(llm_producer(websocket, transcript, conversation_history, text_queue))
        await asyncio.gather(llm_task, tts_task)
        logging.info("Finished processing utterance.")
    except Exception as e:
        logging.error(f"Error processing audio chunk: {e}", exc_info=True)
    finally:
        if tmp_wav_path and os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection established.")
    conversation_history = []
    
    vad_iterator = VADIterator(model, threshold=0.5)
    
    audio_buffer = torch.empty(0, dtype=torch.float32)
    speech_audio_buffer = []
    is_speaking = False
    end_speech_timer = None
    
    async def process_utterance():
        nonlocal is_speaking, speech_audio_buffer
        if not speech_audio_buffer: return
        
        is_speaking = False
        logging.info("Processing full utterance after pause.")
        full_utterance_tensor = torch.cat(speech_audio_buffer)
        speech_audio_buffer = []
        
        speech_bytes = (full_utterance_tensor * 32767).to(torch.int16).numpy().tobytes()
        asyncio.create_task(_process_audio_chunk(websocket, speech_bytes, conversation_history))

    async def start_end_speech_timer():
        await asyncio.sleep(0.8) # Wait for 800ms of silence
        if is_speaking:
            await process_utterance()

    try:
        while True:
            audio_data_b64 = await websocket.receive_text()
            audio_data_bytes = base64.b64decode(audio_data_b64)
            audio_numpy = np.frombuffer(audio_data_bytes, dtype=np.float32).copy()
            new_audio_tensor = torch.from_numpy(audio_numpy)
            audio_buffer = torch.cat([audio_buffer, new_audio_tensor])
            VAD_WINDOW_SIZE = 512

            while audio_buffer.shape[0] >= VAD_WINDOW_SIZE:
                current_window = audio_buffer[:VAD_WINDOW_SIZE]
                audio_buffer = audio_buffer[VAD_WINDOW_SIZE:]
                
                # Always add audio to the buffer if we are in a speaking state
                if is_speaking:
                    speech_audio_buffer.append(current_window)
                    
                speech_dict = vad_iterator(current_window, return_seconds=True)

                if speech_dict:
                    if 'start' in speech_dict:
                        if not is_speaking:
                            is_speaking = True
                            speech_audio_buffer = [current_window] # Start new buffer
                            logging.info("Speech start detected.")
                        # If user starts talking again, cancel any pending timer
                        if end_speech_timer and not end_speech_timer.done():
                            end_speech_timer.cancel()
                    
                    if 'end' in speech_dict and is_speaking:
                        # User has paused. Start a timer.
                        if not end_speech_timer or end_speech_timer.done():
                           end_speech_timer = asyncio.create_task(start_end_speech_timer())
    except WebSocketDisconnect:
        logging.info("WebSocket connection closed by client.")
    except Exception as e:
        logging.error(f"An error occurred in WebSocket: {e}", exc_info=True)