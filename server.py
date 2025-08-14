# server.py

import asyncio
import base64
import json
import logging
import numpy as np
import torch # NEW

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# --- Your Existing Modules (Placeholders) ---
from brain.mistralAPI_brain import mistral_chat
from tts.elevenLabs.xiTTS import stream_tts_audio
from stt.sarvamSTT import transcribe_audio_from_bytes
from logs.logger import log_conversation

# --- FastAPI Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")
logging.basicConfig(level=logging.INFO)

# --- Silero VAD Setup (REPLACING WebRTC VAD) ---
# Load the Silero VAD model
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False) # Set to True for first run if needed

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

SAMPLE_RATE = 16000 # 16kHz, must match what Silero expects
VAD_THRESHOLD = 0.5 # Speech confidence threshold
MIN_SILENCE_DURATION_MS = 250 # Minimum silence duration to consider an utterance end
SPEECH_PAD_MS = 100 # Add padding to the start/end of speech chunks

# --- WebSocket Logic ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection established.")
    
    conversation_history = []
    
    try:
        # 1. Greet the user upon connection
        greeting_text = "Hello boss, how're you doing today?"
        log_conversation("AI_greeting", greeting_text)
        async for audio_chunk in stream_tts_audio(greeting_text):
            await websocket.send_bytes(audio_chunk)
        await websocket.send_text(json.dumps({"type": "tts_end"}))

        # 2. Main loop to listen for user audio
        audio_buffer = []
        
        while True:
            # Receive base64 encoded audio data from the client
            audio_data_b64 = await websocket.receive_text()
            audio_data_bytes = base64.b64decode(audio_data_b64)
            
            # The JS sends Float32, so we interpret the bytes as such
            audio_float32 = np.frombuffer(audio_data_bytes, dtype=np.float32)
            
            # Convert to a torch tensor as required by Silero VAD
            audio_tensor = torch.from_numpy(audio_float32)
            audio_buffer.append(audio_tensor)

            # Process buffer when it has a reasonable amount of audio
            # A 4096 buffer from JS is ~0.25s. We can process every 4 chunks (~1s).
            if len(audio_buffer) < 4:
                continue

            # Combine chunks into a single tensor
            combined_tensor = torch.cat(audio_buffer)
            audio_buffer.clear()

            # Get speech timestamps from the VAD
            speech_timestamps = get_speech_timestamps(
                combined_tensor, 
                model, 
                sampling_rate=SAMPLE_RATE,
                threshold=VAD_THRESHOLD,
                min_silence_duration_ms=MIN_SILENCE_DURATION_MS,
                speech_pad_ms=SPEECH_PAD_MS
            )

            if not speech_timestamps:
                continue # No speech detected in this chunk

            logging.info(f"Detected speech chunks: {speech_timestamps}")

            # Process each detected speech chunk
            for chunk_ts in speech_timestamps:
                start, end = chunk_ts['start'], chunk_ts['end']
                speech_chunk_tensor = combined_tensor[start:end]

                # Convert tensor to 16-bit PCM bytes for transcription
                # This is the format most STT engines expect
                speech_chunk_tensor_int16 = (speech_chunk_tensor * 32767).to(torch.int16)
                speech_bytes = speech_chunk_tensor_int16.numpy().tobytes()

                # a. Transcribe user's speech
                transcript = await transcribe_audio_from_bytes(speech_bytes, sample_rate=SAMPLE_RATE)
                if not transcript or not transcript.strip():
                    continue

                log_conversation("User", transcript)
                await websocket.send_text(json.dumps({"type": "user_transcript", "data": transcript}))
                
                # b. Get AI response
                conversation_history, ai_reply_text = await mistral_chat(transcript, conversation_history)
                log_conversation("AI", ai_reply_text)
                await websocket.send_text(json.dumps({"type": "ai_text", "data": ai_reply_text}))
                
                # c. Stream AI response as audio (TTS)
                async for audio_chunk in stream_tts_audio(ai_reply_text):
                   await websocket.send_bytes(audio_chunk)
                
                await websocket.send_text(json.dumps({"type": "tts_end"}))


    except WebSocketDisconnect:
        logging.info("WebSocket connection closed by client.")
    except Exception as e:
        logging.error(f"An error occurred in WebSocket: {e}", exc_info=True)
    finally:
        logging.info("Closing WebSocket connection.")

# To run the server:
# uvicorn server:app --reload