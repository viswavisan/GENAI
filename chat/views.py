"""
Clean, modular views for GenAI Studio.
Separated into 3 clear functional groups:
1. GenAI Chat (Online Gemini & Offline Ollama)
2. Agentic AI Online (Limited Tools & Universal Terminal with Confirmation/Password)
3. Agentic AI Offline (Local Ollama Tool-Calling Agent)
"""

from django.shortcuts import render
from django.http import JsonResponse

# Group 1: GenAI Chat
from .backends.genai_chat import (
    generate_online_chat,
    generate_offline_chat
)

# Group 2: Agentic AI Online
from .backends.agentic_online import (
    run_online_limited_agent,
    ONLINE_LIMITED_TOOLS_METADATA,
    propose_universal_action,
    execute_confirmed_command
)

# Group 3: Agentic AI Offline
from .backends.agentic_offline import (
    run_offline_agent,
    OFFLINE_TOOLS_METADATA
)


# =====================================================================
# GROUP 1: GENAI CHAT (Conversational LLM - No Tools)
# =====================================================================

def chat_online_ui(request):
    """GenAI Online Chat interface (Google Gemini)."""
    return render(request, "chat/genai_online.html")


def chat_online_api(request):
    """API for GenAI Online Chat."""
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "No input provided"}, status=400)
    try:
        return JsonResponse(generate_online_chat(q))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def chat_offline_ui(request):
    """GenAI Offline Chat interface (Local Ollama)."""
    return render(request, "chat/genai_offline.html")


def chat_offline_api(request):
    """API for GenAI Offline Chat."""
    q = request.GET.get("q", "").strip()
    model = request.GET.get("model", "llama3.2").strip()
    if not q:
        return JsonResponse({"error": "No input provided"}, status=400)
    try:
        return JsonResponse(generate_offline_chat(q, model_name=model))
    except ConnectionError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# GROUP 2: AGENTIC AI ONLINE (Cloud Gemini with Autonomous Tools)
# =====================================================================

def agent_online_limited_ui(request):
    """Agentic AI Online (Limited safe tools: clock, calc, weather, brightness)."""
    return render(request, "chat/agent_online_limited.html", {
        "tools": ONLINE_LIMITED_TOOLS_METADATA
    })


def agent_online_limited_api(request):
    """API for Agentic AI Online (Limited Tools)."""
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        return JsonResponse(run_online_limited_agent(q))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def agent_online_universal_ui(request):
    """Agentic AI Online (Universal PowerShell terminal with confirmation & password)."""
    return render(request, "chat/agent_online_universal.html")


def agent_online_universal_api(request):
    """API for Agentic AI Online (Universal Terminal with Human Confirmation)."""
    q = request.GET.get("q", "").strip()
    confirmed = request.GET.get("confirmed", "false").lower() == "true"
    command = request.GET.get("command", "").strip()
    password = request.GET.get("password", "").strip()

    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        if confirmed and command:
            return JsonResponse(execute_confirmed_command(q, command, password=password))
        return JsonResponse(propose_universal_action(q))
    except PermissionError as e:
        return JsonResponse({"error": str(e), "auth_error": True}, status=403)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# GROUP 3: AGENTIC AI OFFLINE (Local Ollama Autonomous Tool Calling)
# =====================================================================

def agent_offline_ui(request):
    """Agentic AI Offline (Local Ollama tool-calling agent, zero internet)."""
    return render(request, "chat/agent_offline.html", {
        "tools": OFFLINE_TOOLS_METADATA
    })


def agent_offline_api(request):
    """API for Agentic AI Offline."""
    q = request.GET.get("q", "").strip()
    model = request.GET.get("model", "llama3.2").strip()
    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        return JsonResponse(run_offline_agent(q, model_name=model))
    except ConnectionError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
