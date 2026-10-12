"""
Backend 1: Standard Online GenAI Chat (Google Gemini).
Completely isolated module.
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def generate_standard_reply(user_input: str) -> dict:
    """Sends user prompt to Gemini and returns standard text reply."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_input,
    )
    return {
        "reply": response.text or "",
        "model": MODEL_NAME,
        "type": "standard_online"
    }
