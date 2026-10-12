"""
Backend 4: Universal Terminal Agent (Full OS Control with Confirmation & Password).
Uses dynamic PowerShell command generation with Human-in-the-Loop approval
and password authorization.
Completely isolated module.
"""

import os
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
UNIVERSAL_AGENT_PASSWORD = os.getenv("UNIVERSAL_AGENT_PASSWORD", "admin123")


def verify_agent_password(password: str) -> bool:
    """Verifies user provided password against UNIVERSAL_AGENT_PASSWORD."""
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
                "type": "universal_agent"
            }

    return {
        "needs_confirmation": False,
        "reply": response.text or "Done.",
        "steps": [],
        "type": "universal_agent"
    }


def execute_confirmed_command(user_prompt: str, command: str, password: str = "") -> dict:
    """
    Step 2: User confirmed with password!
    1. Authenticate password.
    2. Run command on laptop.
    3. Return final Gemini response.
    """
    # Verify password before running any system command
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
    except Exception as e:
        # Fallback to direct laptop output if model API hits quota
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
        "type": "universal_agent"
    }
