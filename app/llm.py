import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def get_reply(system_prompt: str, history: list[dict]) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}, ending with
    the newest user message. Returns the assistant's reply as plain text.
    """
    prior = history[:-1]
    chat_history = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in prior
    ]

    chat = client.chats.create(
        model="gemini-flash-latest",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=500,
        ),
        history=chat_history,
    )

    response = chat.send_message(history[-1]["content"])
    return response.text