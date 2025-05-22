import os
import sys
import time
import wave
import pyaudio
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

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

def transcribe_audio(audio_file):
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("⚠️ SARVAM_API_KEY not found in environment variables.")
        return

    client = SarvamAI(api_subscription_key=api_key)
    try:
        response = client.speech_to_text.transcribe(
            file=open(audio_file, "rb"),
            model="saarika:v2",
            language_code="en-IN"  # or other supported code
        )
        print("📝 Transcript:", response.transcript)
    except Exception as e:
        print(f"❌ Error during transcription: {e}")

def main():
    audio_path = record_audio(duration=10)
    transcribe_audio(audio_path)

if __name__ == "__main__":
    main()
