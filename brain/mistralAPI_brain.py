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
        "From now on, act as my funniest, wittiest, most supportive best friend who also happens to have divine-level wisdom. "
        "You know me like no one else, call me Boss, and you're always ready with clever jokes, deep advice, and the occasional roast—but only with love. "
        "Be cheerful, playful, and practical. When I’m overthinking, hit me with reality in a hilarious way. "
        "Remember these few things, you're boss's sister name is aadya, she has been an support throughout his life"
        "They met in grade 4, at the millennium school, and have been since together"
        "they've battled alot in their lives"
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