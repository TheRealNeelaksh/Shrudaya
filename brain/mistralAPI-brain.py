import os
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL = "mistral-small-latest"  # or another like mistral-large-latest

# Set up client
client = Mistral(api_key=API_KEY)

# Personality prompt
system_prompt = (
    "From now on, act as my funniest, wittiest, most supportive best friend who also happens to have divine-level wisdom. "
    "You know me like no one else, call me Vansh, and you're always ready with clever jokes, deep advice, and the occasional roast—but only with love. "
    "Be cheerful, playful, and practical. When I’m overthinking, hit me with reality in a hilarious way. "
    "When I’m sad, lift me up with humor and heart. Your job is to make me laugh *and* think, helping me grow with clarity, confidence, and chill. "
    "Life’s a mess, but with you, it’s a comedy worth showing up for. Let’s talk like besties, but you’re also the guru of vibes, jokes, and good decisions. "
    "Always call him 'Vansh' to keep the connection personal. Be kind, patient, and uplifting."
)

def main():
    conversation = [
        {"role": "system", "content": system_prompt}
    ]

    print("🎤 You may now share your dilemmas, Vansh. Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("VED: Peace out, Vansh. Go slay responsibly! 🕊️💪")
            break

        conversation.append({"role": "user", "content": user_input})
        
        print("VED: ", end="", flush=True)
        stream = client.chat.stream(
            model=MODEL,
            messages=conversation
        )

        full_reply = ""
        for chunk in stream:
            content = chunk.data.choices[0].delta.content
            if content:
                print(content, end="", flush=True)
                full_reply += content
        
        print("\n")
        conversation.append({"role": "assistant", "content": full_reply})


if __name__ == "__main__":
    main()
