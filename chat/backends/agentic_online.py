"""
Group 2: Agentic AI Online (Cloud Gemini with Autonomous Function Calling).
Includes:
- Limited Agent: Predefined safe tools (Clock, Calculator, Weather, Screen Brightness, Reverse Text).
- Universal Agent: Full OS PowerShell control with Human-in-the-Loop Confirmation & Password.
"""

import os
import datetime
import subprocess
from google import genai
from google.genai import types

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
UNIVERSAL_AGENT_PASSWORD = os.getenv("UNIVERSAL_AGENT_PASSWORD", "admin123")


# =====================================================================
# SUBSECTION A: LIMITED AGENT (Predefined Safe Tools)
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


ONLINE_LIMITED_TOOLS = [
    get_current_time,
    calculate,
    get_weather,
    get_screen_brightness,
    set_screen_brightness,
    reverse_text
]

ONLINE_LIMITED_TOOLS_METADATA = [
    {"name": "get_current_time", "icon": "🕒", "description": "System clock & date", "example": "What time is it now?"},
    {"name": "calculate", "icon": "🧮", "description": "Safe math calculator", "example": "Calculate (45 * 18) + 120"},
    {"name": "get_weather", "icon": "🌤️", "description": "City weather lookup", "example": "What is the weather in Tokyo?"},
    {"name": "get_screen_brightness", "icon": "💡", "description": "Check screen brightness", "example": "What is my screen brightness?"},
    {"name": "set_screen_brightness", "icon": "🔆", "description": "Adjust screen brightness", "example": "Set screen brightness to 50%"},
    {"name": "reverse_text", "icon": "🔤", "description": "Reverses words/strings", "example": "Reverse the word 'Antigravity'"},
]


def run_online_limited_agent(user_input: str) -> dict:
    """Executes the online agent with limited specific tools."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    client = genai.Client(api_key=api_key)
    chat = client.chats.create(
        model=MODEL_NAME,
        config={"tools": ONLINE_LIMITED_TOOLS}
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
        "mode": "agentic_online_limited"
    }


# =====================================================================
# SUBSECTION B: UNIVERSAL AGENT (Full OS PowerShell Control + Password)
# =====================================================================

def verify_agent_password(password: str) -> bool:
    """Verifies password for Universal Agent execution."""
    return bool(password and password == UNIVERSAL_AGENT_PASSWORD)


def run_system_command(command: str) -> str:
    """Executes a Windows PowerShell command on the laptop with 15s timeout."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode == 0:
            return stdout or "Command completed successfully with no text output."
        return f"Command exit code {result.returncode}: {stderr or stdout}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 15 seconds."
    except Exception as e:
        return f"Execution error: {str(e)}"


SYSTEM_TOOL_DECLARATION = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="run_system_command",
            description=(
                "Executes a Windows PowerShell command directly on the user's laptop. "
                "Use this to inspect hardware (battery, disk, ram), control settings, "
                "open apps (notepad, calc), or check networks."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "command": types.Schema(
                        type="STRING",
                        description="The exact Windows PowerShell command to execute."
                    )
                },
                required=["command"]
            )
        )
    ]
)


def propose_universal_action(user_prompt: str) -> dict:
    """Step 1: Ask Gemini what to do. If it proposes a command, ask for confirmation & password."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(tools=[SYSTEM_TOOL_DECLARATION])
    )

    if response.function_calls:
        call = response.function_calls[0]
        if call.name == "run_system_command":
            return {
                "needs_confirmation": True,
                "command": call.args.get("command", ""),
                "prompt": user_prompt,
                "tool": "run_system_command",
                "requires_password": True,
                "mode": "agentic_online_universal"
            }

    return {
        "needs_confirmation": False,
        "reply": response.text or "Done.",
        "steps": [],
        "mode": "agentic_online_universal"
    }


def execute_confirmed_command(user_prompt: str, command: str, password: str = "") -> dict:
    """Step 2: Password confirmed! Run command and return explanation."""
    if not verify_agent_password(password):
        raise PermissionError("Access Denied: Incorrect password for Universal Agent execution.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    client = genai.Client(api_key=api_key)
    output = run_system_command(command)

    prompt_with_output = (
        f"User question: {user_prompt}\n"
        f"Executed PowerShell command: {command}\n"
        f"Laptop output:\n```\n{output}\n```\n"
        f"Please provide a clear and helpful explanation to the user."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt_with_output
        )
        reply = response.text or f"Command output:\n{output}"
    except Exception:
        # Graceful fallback to real laptop output if API rate limits
        reply = f"System Command Output:\n```\n{output}\n```"

    return {
        "needs_confirmation": False,
        "reply": reply,
        "steps": [
            {
                "tool": "run_system_command",
                "args": {"command": command},
                "output": output
            }
        ],
        "mode": "agentic_online_universal"
    }
