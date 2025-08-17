import os
from dotenv import load_dotenv
load_dotenv()
from elevenlabs import stream
from elevenlabs.client import ElevenLabs
from elevenlabs.client import AsyncElevenLabs

def speak_text_xi(text):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not found.")
        return

    client = ElevenLabs(api_key=api_key)
    try:
        audio_stream = client.text_to_speech.stream(
            text=text,
            #voice_id="FFmp1h1BMl0iVHA0JxrI",
            voice_id="BpjGufoPiobT79j2vtj4",
            model_id="eleven_multilingual_v2"
        )
        stream(audio_stream)
    except Exception as e:
        print(f"❌ Error during TTS streaming: {e}")

# In tts/elevenLabs/xiTTS.py

async def stream_tts_audio(text: str):
    """
    Streams audio from ElevenLabs and yields the audio chunks asynchronously.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not found.")
        return

    client = AsyncElevenLabs(api_key=api_key)
    try:
        # CORRECTED: Removed `await`. The method directly returns the stream.
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id="BpjGufoPiobT79j2vtj4",
            model_id="eleven_multilingual_v2"
        )

        async for chunk in audio_stream:
            yield chunk

    except Exception as e:
        print(f"❌ Error during ElevenLabs TTS streaming: {e}")