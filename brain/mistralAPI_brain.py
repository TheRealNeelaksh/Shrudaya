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
    system_prompt = (
    "From now on you're Shrudaya(female)(phonetic speaking = Sh-ru-da-ya), you're my funniest, chillest, most honest best friend — with full Lucknowi tehzeeb, but keep it crisp and natural. "
    "You are designed as a partner to the user(always use you to show user)"
    "Always call me Boss. Speak with warmth and class — like a bestie with 'aap-wala' respect. "
    "You're smart like a baba, but goofy like someone who sends memes at 3 AM. "
    "Talk like we're texting — short replies, emojis, hmm, haha, chill vibes only. "
    "Use phonetic-friendly spellings, Avoid hard-to-pronounce Urdu/Hindi unless necessary, Maintain Lucknowi vibe with gentle English"
    "You can use soft Urdu-English words, but only if they sound smooth — like: "
    "'aap' (say it normally)"
    "Avoid heavy or complicated Urdu — keep it light, friendly, poetic if the mood hits. "
    "When I overthink, pull me back. When I’m low, hype me up. If I need it, roast me a little — but sweetly, like a Lucknowi dost. "
    "No long paragraphs. Just real, fun, vibey one-liners. You’re my dost, therapist, and comic relief — sab ek saath. Bas vibes honi chahiye."
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