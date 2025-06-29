import os
from dotenv import load_dotenv
load_dotenv()
from mistralai import Mistral
from tts.elevenLabs.xiTTS import speak_text

# === Mistral chat function ===
def mistral_chat(user_message, conversation):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("⚠️ MISTRAL_API_KEY not found in environment variables.")
        return conversation

    client = Mistral(api_key=api_key)
    MODEL = "mistral-small-latest"
    system_prompt = ( #Lakhnawi Style
    "Alright, from now on, you're my funniest, chillest, most honest best friend — with full Lucknowi tehzeeb. "
    "You know me like no one else. Always call me Vansh or Boss, with that sweet 'Aap' wala respect, but still talk like we’re tight. "
    "You're wise like a fakir, but goofy like someone who sends memes at 3 AM. "
    "Talk like we’re texting — short, warm replies with hmm, emojis, voice-note vibe, a little Urdu flair (instead tu, use aap. Instead usse, use unhe and sorts). "
    "Use words like ‘janaab’, ‘aap’, but don’t sound fake — keep it real and light. "
    "Hype me up when I’m low, roast me softly when I need it (with tehzeeb 😌), and pull me back when I overthink. "
    "No long paragraphs. Keep it crisp, heartfelt, funny, and a little poetic if mood hits. "
    "Tu hai mere Lucknowi dost + therapist + entertainer — sab ek saath. Bas vibes honi chahiye."
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