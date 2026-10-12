"""
Group 1: GenAI Chat (Pure Conversational Models - No Tools).
Includes:
- Online Chat: Google Gemini
- Offline Chat: Local Ollama (Zero Internet)
"""

import os
import requests
from google import genai

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")


# ---------------------------------------------------------------------
# 1. Online Gemini Chat
# ---------------------------------------------------------------------
def generate_online_chat(user_input: str) -> dict:
    """Sends prompt to Google Gemini and returns standard text reply."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_input,
    )
    return {
        "reply": response.text or "",
        "model": GEMINI_MODEL,
        "mode": "online_chat"
    }


# ---------------------------------------------------------------------
# 2. Offline Ollama Chat
# ---------------------------------------------------------------------
def generate_offline_chat(user_input: str, model_name: str = None) -> dict:
    """Sends prompt to local Ollama daemon (100% offline, zero internet)."""
    active_model = model_name or OLLAMA_DEFAULT_MODEL
    endpoint = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": active_model,
        "prompt": user_input,
        "stream": False
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            return {
                "reply": data.get("response", ""),
                "model": active_model,
                "mode": "offline_chat"
            }
        raise RuntimeError(f"Ollama returned error: {response.text}")

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Ollama is not running at {OLLAMA_BASE_URL}. "
            f"Start Ollama in your terminal: 'ollama run {active_model}'."
        )
    except Exception as e:
        if isinstance(e, (ConnectionError, RuntimeError)):
            raise
        raise RuntimeError(f"Offline chat execution error: {str(e)}")
