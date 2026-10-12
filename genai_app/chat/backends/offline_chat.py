"""
Backend 2: Offline GenAI Chat (Local Ollama / Zero Internet).
Completely isolated module.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")


def generate_offline_reply(user_input: str, model_name: str = None) -> dict:
    """
    Sends prompt to local Ollama daemon at http://localhost:11434.
    Runs 100% locally with zero internet.
    """
    active_model = model_name or DEFAULT_MODEL
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
                "type": "offline_local"
            }
        else:
            raise RuntimeError(f"Ollama returned error: {response.text}")

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Ollama is not running at {OLLAMA_BASE_URL}. "
            f"Start Ollama in your terminal using: 'ollama run {active_model}' to use offline mode."
        )
    except Exception as e:
        if isinstance(e, (ConnectionError, RuntimeError)):
            raise
        raise RuntimeError(f"Offline execution error: {str(e)}")
