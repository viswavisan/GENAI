"""
Group 3: Agentic AI Offline (Local Ollama with Autonomous Tool Calling - Zero Internet).
Uses local Ollama daemon to reason, invoke tools, and synthesize final answers completely offline.
Completely isolated module.
"""

import os
import json
import datetime
import subprocess
import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")


# =====================================================================
# 1. OFFLINE LOCAL TOOLS
# =====================================================================

def get_current_time() -> str:
    """Returns the current real-time date and time on this machine."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate(expression: str) -> str:
    """Calculates any arithmetic expression like '25 * 40' or '(100 + 50) / 2'."""
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression).issubset(allowed):
            return "Error: Expression contains invalid characters."
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


def get_screen_brightness() -> str:
    """Gets current laptop screen brightness percentage via WMI."""
    try:
        cmd = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop).CurrentBrightness"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
        val = res.stdout.strip()
        if val:
            return f"Current screen brightness is {val}%"
        return "Could not read brightness."
    except Exception as e:
        return f"Error: {str(e)}"


def reverse_text(text: str) -> str:
    """Reverses the given text string."""
    return text[::-1]


OFFLINE_TOOLS_MAP = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "get_screen_brightness": get_screen_brightness,
    "reverse_text": reverse_text,
}

OFFLINE_TOOLS_DECLARATIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Returns current date and time. Use when user asks for time or date.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculates math expressions safely. Use for arithmetic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression like 25 * 4"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_screen_brightness",
            "description": "Gets laptop screen brightness level.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reverse_text",
            "description": "Reverses any text string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The string to reverse"}
                },
                "required": ["text"]
            }
        }
    }
]

OFFLINE_TOOLS_METADATA = [
    {"name": "get_current_time", "icon": "🕒", "description": "Local system clock", "example": "What time is it right now?"},
    {"name": "calculate", "icon": "🧮", "description": "Local math evaluator", "example": "Calculate (45 * 18) + 120"},
    {"name": "get_screen_brightness", "icon": "💡", "description": "Check screen brightness", "example": "What is my screen brightness?"},
    {"name": "reverse_text", "icon": "🔤", "description": "Reverses words/strings", "example": "Reverse the word 'Antigravity'"},
]


# =====================================================================
# 2. RUN OFFLINE AGENT LOOP
# =====================================================================

def run_offline_agent(user_input: str, model_name: str = None) -> dict:
    """
    Executes a 100% offline agent loop using Ollama's local tool calling API.
    Zero internet required.
    """
    active_model = model_name or OLLAMA_DEFAULT_MODEL
    endpoint = f"{OLLAMA_BASE_URL}/api/chat"

    messages = [
        {"role": "user", "content": user_input}
    ]

    payload = {
        "model": active_model,
        "messages": messages,
        "tools": OFFLINE_TOOLS_DECLARATIONS,
        "stream": False
    }

    try:
        # Step 1: Send request to local Ollama with tools
        res = requests.post(endpoint, json=payload, timeout=60)
        if res.status_code != 200:
            raise RuntimeError(f"Ollama returned HTTP {res.status_code}: {res.text}")

        data = res.json()
        message = data.get("message", {})
        tool_calls = message.get("tool_calls", [])

        steps = []

        # If model called tools, execute them locally
        if tool_calls:
            for call in tool_calls:
                func_info = call.get("function", {})
                func_name = func_info.get("name")
                func_args = func_info.get("arguments", {})

                # If arguments is JSON string, parse it
                if isinstance(func_args, str):
                    try:
                        func_args = json.loads(func_args)
                    except Exception:
                        pass

                func = OFFLINE_TOOLS_MAP.get(func_name)
                output = "Tool not found"
                if func:
                    try:
                        if func_args and isinstance(func_args, dict):
                            output = func(**func_args)
                        else:
                            output = func()
                    except Exception as e:
                        output = f"Tool execution error: {str(e)}"

                steps.append({
                    "tool": func_name,
                    "args": func_args,
                    "output": str(output)
                })

            # Step 2: Feed tool observation back to local Ollama
            messages.append(message)
            for s in steps:
                messages.append({
                    "role": "tool",
                    "content": str(s["output"])
                })

            followup_payload = {
                "model": active_model,
                "messages": messages,
                "stream": False
            }
            followup_res = requests.post(endpoint, json=followup_payload, timeout=60)
            if followup_res.status_code == 200:
                final_text = followup_res.json().get("message", {}).get("content", "")
            else:
                final_text = f"Tool output: {steps[0]['output'] if steps else ''}"
        else:
            final_text = message.get("content", "")

        return {
            "reply": final_text,
            "steps": steps,
            "tools_count": len(steps),
            "model": active_model,
            "mode": "agentic_offline"
        }

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Ollama is not running at {OLLAMA_BASE_URL}. "
            f"Start Ollama in your terminal: 'ollama run {active_model}' to use the offline agent."
        )
    except Exception as e:
        if isinstance(e, (ConnectionError, RuntimeError)):
            raise
        raise RuntimeError(f"Offline agent error: {str(e)}")
