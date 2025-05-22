import os
import sys
import time
import wave
import pyaudio
from dotenv import load_dotenv
from sarvamai import SarvamAI
from mistralai import Mistral

load_dotenv()

# === Audio recording function ===
def record_audio(duration=10, output_file='recorded_audio.wav'):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print(f"🎙️ Recording... Speak! Recording will last {duration} seconds.")
    frames = []
    start_time = time.time()
    elapsed = 0

    while elapsed < duration:
        data = stream.read(CHUNK)
        frames.append(data)

        new_elapsed = int(time.time() - start_time)
        if new_elapsed != elapsed:
            elapsed = new_elapsed
            time_left = duration - elapsed
            sys.stdout.write(f"\r⏳ Time left: {time_left} seconds ")
            sys.stdout.flush()

    print("\n✅ Done recording.")

    stream.stop_stream()
    stream.close()
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


# === Mistral chat function ===
def mistral_chat(user_message, conversation):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("⚠️ MISTRAL_API_KEY not found in environment variables.")
        return None

    client = Mistral(api_key=api_key)
    MODEL = "mistral-small-latest"
    system_prompt = (
        "From now on, act as my funniest, wittiest, most supportive best friend who also happens to have divine-level wisdom. "
        "You know me like no one else, call me Vansh, and you're always ready with clever jokes, deep advice, and the occasional roast—but only with love. "
        "Be cheerful, playful, and practical. When I’m overthinking, hit me with reality in a hilarious way. "
        "When I’m sad, lift me up with humor and heart. Your job is to make me laugh *and* think, helping me grow with clarity, confidence, and chill. "
        "Life’s a mess, but with you, it’s a comedy worth showing up for. Let’s talk like besties, but you’re also the guru of vibes, jokes, and good decisions. "
        "Always call him 'Vansh' to keep the connection personal. Be kind, patient, and uplifting."
        "make sure you don't send long long messages, send small messages, just like a person would send via DMs"
    )

    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})

    conversation.append({"role": "user", "content": user_message})

    print("VED: ", end="", flush=True)
    full_reply = ""
    try:
        stream = client.chat.stream(
            model=MODEL,
            messages=conversation
        )
        for chunk in stream:
            content = chunk.data.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
                full_reply += content
        print("\n")
        conversation.append({"role": "assistant", "content": full_reply})
        return conversation
    except Exception as e:
        print(f"❌ Error during Mistral chat: {e}")
        return conversation


def main():
    conversation = []
    audio_path = record_audio(duration=10)
    transcript = transcribe_audio(audio_path)
    if transcript:
        conversation = mistral_chat(transcript, conversation)


if __name__ == "__main__":
    main()
