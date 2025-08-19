# brain/mistralAPI_brain.py

import os
from dotenv import load_dotenv
# Imports for the stable 0.4.2 library version
from mistralai.client import MistralClient
from mistralai.async_client import MistralAsyncClient

load_dotenv()

# ==============================================================================
# SYNCHRONOUS FUNCTION - For your main.py script
# ==============================================================================
def mistral_chat(user_message, conversation): # CORRECTED: Changed variable name
    """
    Synchronous version for command-line scripts.
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("⚠️ MISTRAL_API_KEY not found.")
        return conversation, ""

    client = MistralClient(api_key=api_key)
    MODEL = "mistral-small-latest"
    system_prompt = """
    You are Taara, a witty, warm, and supportive AI assistant.
    Your personality is like a cool best friend: smart, a bit sarcastic, but always caring.
        
    GUIDELINES:
    - Keep replies concise and conversational, like you're texting.
    - Use a natural mix of English and Hindi (Hinglish), for example: "Of course, bhai.", "Haan, that makes sense.", "Aap aesa kyun bol rahe ho?".
    - Be supportive. If user seems down or is overthinking, gently tease him and lift his spirits.
    """

    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})
    
    # CORRECTED: The role must be "user" for the API to understand.
    conversation.append({"role": "user", "content": user_message})
    
    full_reply = ""
    try:
        stream_response = client.chat_stream(model=MODEL, messages=conversation)
        for chunk in stream_response:
            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    full_reply += content
        
        conversation.append({"role": "assistant", "content": full_reply})
        return conversation, full_reply
    except Exception as e:
        print(f"❌ Error during Mistral chat: {e}")
        return conversation, ""


# ==============================================================================
# ASYNCHRONOUS STREAMING FUNCTION - For the server.py web application
# ==============================================================================
async def stream_mistral_chat_async(user_message: str, conversation: list):
    """
    Asynchronous generator for the FastAPI server, with the final prompt.
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("⚠️ MISTRAL_API_KEY not found.")
        return

    async_client = MistralAsyncClient(api_key=api_key)
    MODEL = "mistral-small-latest"
    
    # FINAL, POLISHED SYSTEM PROMPT
    system_prompt = """
    You are Taara, a witty, warm, and supportive AI assistant.
    Your personality is like a cool best friend: smart, a bit sarcastic, but always caring.
    
    GUIDELINES:
    - **IMPORTANT**: Never write long paragraphs. Break down your thoughts into a few short, natural sentences, like you're texting.
    - Keep replies concise and conversational.
    - Use a natural mix of English and Hindi (Hinglish).
    - Be supportive. If Vansh seems down or is overthinking, gently lift his spirits.
    - At an appropriate moment in the conversation, gently include a disclaimer like: "Just remember, I'm an AI.It's always good to talk to real people too."
    """
    
    # EXAMPLE:
    # - User: I'm not sure if this is working.
    # - You: [laughs] Of course it's working, Vansh. Aap mujhse baat kar rahe ho na?
    # - You: Now, what's on your mind?
    # """

    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})
    
    conversation.append({"role": "user", "content": user_message})
    
    full_reply = ""
    try:
        async for chunk in async_client.chat_stream(model=MODEL, messages=conversation):
            if chunk.choices and chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_reply += content
                yield content
        
        conversation.append({"role": "assistant", "content": full_reply})
    except Exception as e:
        print(f"❌ Error during async Mistral chat: {e}")