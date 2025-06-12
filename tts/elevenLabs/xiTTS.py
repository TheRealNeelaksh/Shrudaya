import os
from dotenv import load_dotenv
load_dotenv()
from elevenlabs import stream
from elevenlabs.client import ElevenLabs

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