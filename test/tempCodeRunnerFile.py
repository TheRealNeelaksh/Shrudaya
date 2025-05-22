
        "make sure you don't send long long messages, send small messages, just like a person would send via DMs"
    )

    if not conversation:
        conversation.append({"role": "system", "content": system_prompt})

    conversation.append({"role": "user", "content": user_message})
