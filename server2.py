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

def load_or_download_model(model_dir="models", model_name="silero_vad"):
    """
    Loads Silero VAD model from local folder if available.
    Otherwise downloads via torch.hub and saves into `models/`.
    """
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"{model_name}.pt")

    if os.path.exists(model_path):
        logging.info(f"Loading Silero VAD model from {model_path}...")
        checkpoint = torch.load(model_path, map_location="cpu")
        model = checkpoint["model"]
        utils = checkpoint["utils"]
    else:
        logging.info("Downloading Silero VAD model (first time only)...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=True
        )
        # Save model + utils in dictionary so torch.load works correctly
        torch.save({"model": model, "utils": utils}, model_path)
        logging.info(f"Model saved to {model_path}")

    return model, utils

# ===============================
# Routes
# ===============================
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def safe_send(websocket: WebSocket, message: dict):
    try:
        await websocket.send_text(json.dumps(message))
    except RuntimeError:
        logging.warning("WebSocket is closed, cannot send message.")

async def tts_consumer(websocket: WebSocket, text_queue: asyncio.Queue):
    await safe_send(websocket, {"type": "tts_start"})
    while True:
        try:
            sentence = await text_queue.get()
            if sentence is None:
                break
            if not sentence.strip():
                continue
            logging.info(f"Streaming TTS for sentence: '{sentence}'")
            async for audio_chunk in stream_tts_audio(sentence):
                await websocket.send_bytes(audio_chunk)
            text_queue.task_done()
        except RuntimeError:
            break
        except Exception as e:
            logging.error(f"Error in TTS consumer: {e}")
            break
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
                    if sentence_to_tts:
                        await text_queue.put(sentence_to_tts)
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
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_bytes)
        transcript = await asyncio.to_thread(transcribe_audio, tmp_wav_path)
        if not transcript or not transcript.strip():
            return
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
        if not speech_audio_buffer:
            return
        is_speaking = False
        logging.info("Processing full utterance after pause.")
        full_utterance_tensor = torch.cat(speech_audio_buffer)
        speech_audio_buffer = []
        speech_bytes = (full_utterance_tensor * 32767).to(torch.int16).numpy().tobytes()
        asyncio.create_task(_process_audio_chunk(websocket, speech_bytes, conversation_history))

    async def start_end_speech_timer():
        await asyncio.sleep(0.8)  # Pause detection time
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
                speech_dict = vad_iterator(current_window, return_seconds=True)

                if is_speaking:
                    speech_audio_buffer.append(current_window)

                if speech_dict:
                    if 'start' in speech_dict:
                        is_speaking = True
                        logging.info("Speech start detected.")
                        if end_speech_timer and not end_speech_timer.done():
                            end_speech_timer.cancel()
                        speech_audio_buffer.append(current_window)

                    if 'end' in speech_dict and is_speaking:
                        if not end_speech_timer or end_speech_timer.done():
                            end_speech_timer = asyncio.create_task(start_end_speech_timer())

    except WebSocketDisconnect:
        logging.info("WebSocket connection closed by client.")
    except Exception as e:
        logging.error(f"An error occurred in WebSocket: {e}", exc_info=True)
