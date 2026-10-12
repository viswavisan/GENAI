"""
Backend 3: Agentic AI with Limited / Safe Functionality.
Equipped only with specific pre-defined tools (Clock, Calculator, Weather, Screen Brightness).
Completely isolated module.
"""

import os
import datetime
import subprocess
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


# =====================================================================
# 1. LIMITED SPECIFIC TOOLS
# =====================================================================

def get_current_time() -> str:
    """Returns the current real-time date and time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate(expression: str) -> str:
    """Calculates any basic arithmetic expression like '25 * 40' or '(100 + 50) / 2'."""
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression).issubset(allowed):
            return "Error: Expression contains invalid characters."
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


def get_weather(city: str) -> str:
    """Gets the weather forecast for a given city."""
    sample_weather = {
        "tokyo": "Sunny, 18°C",
        "london": "Rainy, 11°C",
        "paris": "Cloudy, 14°C",
        "new york": "Clear skies, 16°C",
        "chennai": "Warm and sunny, 31°C",
        "delhi": "Pleasant, 26°C",
    }
    return sample_weather.get(city.lower().strip(), f"Clear and pleasant, 22°C in {city}")


def get_screen_brightness() -> str:
    """Gets current laptop screen brightness percentage."""
    try:
        cmd = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop).CurrentBrightness"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
        val = res.stdout.strip()
        if val:
            return f"Current screen brightness is {val}%"
        return "Could not read brightness."
    except Exception as e:
        return f"Error: {str(e)}"


def set_screen_brightness(level: int) -> str:
    """Sets laptop screen brightness between 0 and 100%."""
    try:
        val = max(0, min(100, int(level)))
        cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {val})"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
        if res.returncode == 0:
            return f"Screen brightness successfully set to {val}%"
        return f"Failed: {res.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"


def reverse_text(text: str) -> str:
    """Reverses the provided text string."""
    return text[::-1]


LIMITED_TOOLS = [
    get_current_time,
    calculate,
    get_weather,
    get_screen_brightness,
    set_screen_brightness,
    reverse_text
]

LIMITED_TOOLS_METADATA = [
    {"name": "get_current_time", "icon": "🕒", "description": "System clock & date", "example": "What time is it now?"},
    {"name": "calculate", "icon": "🧮", "description": "Safe math calculator", "example": "Calculate (45 * 18) + 120"},
    {"name": "get_weather", "icon": "🌤️", "description": "City weather lookup", "example": "What is the weather in Tokyo?"},
    {"name": "get_screen_brightness", "icon": "💡", "description": "Check screen brightness", "example": "What is my screen brightness?"},
    {"name": "set_screen_brightness", "icon": "🔆", "description": "Adjust screen brightness", "example": "Set screen brightness to 50%"},
    {"name": "reverse_text", "icon": "🔤", "description": "Reverses words/strings", "example": "Reverse the word 'Antigravity'"},
]


# =====================================================================
# 2. RUN LIMITED AGENT
# =====================================================================

def run_limited_agent(user_input: str) -> dict:
    """Executes the agent with limited specific tools."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    client = genai.Client(api_key=api_key)

    chat = client.chats.create(
        model=MODEL_NAME,
        config={"tools": LIMITED_TOOLS}
    )

    response = chat.send_message(user_input)
    history = chat.get_history()

    steps = []
    tool_calls = []
    tool_responses = {}

    for msg in history:
        for part in msg.parts:
            if hasattr(part, "function_call") and part.function_call:
                tool_calls.append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args or {})
                })
            if hasattr(part, "function_response") and part.function_response:
                res = dict(part.function_response.response or {})
                tool_responses[part.function_response.name] = res.get("result", str(res))

    for call in tool_calls:
        output = tool_responses.get(call["name"], "Executed successfully")
        steps.append({
            "tool": call["name"],
            "args": call["args"],
            "output": output
        })

    return {
        "reply": response.text or "",
        "steps": steps,
        "tools_count": len(steps),
        "type": "limited_agent"
    }
