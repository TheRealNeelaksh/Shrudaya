import os
import sys
import time
import wave
import pyaudio
from dotenv import load_dotenv
from sarvamai import SarvamAI
from mistralai import Mistral
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
import pandas as pd
from datetime import datetime
from playsound import playsound
import winsound

load_dotenv()

# === Audio recording function ===
def record_audio(duration=10, output_file='recorded_audio.wav'):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    p = pyaudio.PyAudio()

    stream_in = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print(f"🎙️ Recording... Speak! Recording will last {duration} seconds.")
    frames = []
    start_time = time.time()
    elapsed = 0

    while elapsed < duration:
        data = stream_in.read(CHUNK)
        frames.append(data)

        new_elapsed = int(time.time() - start_time)
        if new_elapsed != elapsed:
            elapsed = new_elapsed
            time_left = duration - elapsed
            sys.stdout.write(f"\r⏳ Time left: {time_left} seconds ")
            sys.stdout.flush()

    print("\n✅ Done recording.")

    stream_in.stop_stream()
    stream_in.close()
    p.terminate()

    with wave.open(output_file, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    return output_file


# === Transcription function ===
def transcribe_audio(audio_file):
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("⚠️ SARVAM_API_KEY not found in environment variables.")
        return None

    client = SarvamAI(api_subscription_key=api_key)
    try:
        response = client.speech_to_text.transcribe(
            file=open(audio_file, "rb"),
            model="saarika:v2",
            language_code="en-IN"
        )
        transcript = response.transcript
        print("📝 Transcript:", transcript)
        return transcript
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        return None


# === ElevenLabs TTS function ===
def speak_text(text):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not found.")
        return

    client = ElevenLabs(api_key=api_key) 
    try:
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id="FFmp1h1BMl0iVHA0JxrI",
            model_id="eleven_multilingual_v2"
        )
        stream(audio_stream)
    except Exception as e:
        print(f"❌ Error during TTS streaming: {e}")


# === Mistral chat function ===
def mistral_chat(user_message, conversation):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("⚠️ MISTRAL_API_KEY not found in environment variables.")
        return conversation

    client = Mistral(api_key=api_key)
    MODEL = "mistral-small-latest"
    system_prompt = (
        "From now on, act as my funniest, wittiest, most supportive best friend who also happens to have divine-level wisdom. "
        "You know me like no one else, call me Boss, and you're always ready with clever jokes, deep advice, and the occasional roast—but only with love. "
        "Be cheerful, playful, and practical. When I’m overthinking, hit me with reality in a hilarious way. "
        "When I’m sad, lift me up with humor and heart. Your job is to make me laugh *and* think, helping me grow with clarity, confidence, and chill. "
        "Life’s a mess, but with you, it’s a comedy worth showing up for. Let’s talk like besties, but you’re also the guru of vibes, jokes, and good decisions. "
        "Always call him 'Vansh' to keep the connection personal. Be kind, patient, and uplifting."
        "make sure you don't send long long messages, send sure short small messages to prevent token abuse, and quick token finish, just like a person would send via DMs"
    )

    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})

    conversation.append({"role": "user", "content": user_message})

    print("VED: ", end="", flush=True)
    full_reply = ""
    try:
        stream_response = client.chat.stream(
            model=MODEL,
            messages=conversation
        )
        for chunk in stream_response:
            content = chunk.data.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
                full_reply += content
        print("\n")
        conversation.append({"role": "assistant", "content": full_reply})

        # Speak the assistant's reply
        speak_text(full_reply)

        return conversation, full_reply  # return both

    except Exception as e:
        print(f"❌ Error during Mistral chat: {e}")
        return conversation, ""

# === Conversation Logging function ===
def log_conversation(person, message, logs_dir="logs"):
    now = datetime.now()
    day = now.day
    day_suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    rest_of_date = now.strftime("%B, %Y")
    formatted_date = f"{day}{day_suffix} {rest_of_date}"  # e.g. 28th May, 2025

    formatted_time = now.strftime("%I:%M:%S %p")  # e.g. 03:02:01 PM

    os.makedirs(logs_dir, exist_ok=True)
    file_path = os.path.join(logs_dir, f"{formatted_date}.csv")

    data = {"Date": [formatted_date], "Time": [formatted_time], "Person": [person], "Context": [message]}

    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df = pd.concat([df, pd.DataFrame(data)], ignore_index=True)
    else:
        df = pd.DataFrame(data)

    df.to_csv(file_path, index=False)

def play_chime():
    try:
        winsound.PlaySound(r'misc\chime.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)  # Ensure chime.wav exists
    except Exception as e:
        print(f"⚠️ Error playing chime: {e}")


# def main():
#     conversation = []
#     print("🎤 Speak your heart out. Say 'stop' to exit anytime.\n")
    
#     while True:
#         audio_path = record_audio(duration=10)
#         transcript = transcribe_audio(audio_path)

#         if transcript is None:
#             continue

#         log_conversation("User", transcript)  # Log User's input

#         if transcript.strip().lower() in ["stop", "exit", "quit", "bye"]:
#             print("👋 Alright, Vansh. Catch you later!")
#             break

#         conversation, ai_reply = mistral_chat(transcript, conversation)

#         if ai_reply:
#             log_conversation("AI", ai_reply)

def main():
    conversation = []

    # Greet the user first before loop starts
    greeting = "Hello boss, how're you doing today?"
    speak_text(greeting)

    print("🎤 Speak your heart out. Say 'stop' to exit anytime.\n")

    while True:
        # Play chime before recording
        play_chime()

        audio_path = record_audio(duration=10)
        transcript = transcribe_audio(audio_path)

        if transcript is None:
            continue

        log_conversation("User", transcript)  # Log User's input

        if transcript.strip().lower() in ["stop", "exit", "quit", "bye"]:
            print("👋 Alright, Vansh. Catch you later!")
            break

        conversation, ai_reply = mistral_chat(transcript, conversation)

        if ai_reply:
            log_conversation("AI", ai_reply)

if __name__ == "__main__":
    main()
