"""
Views for GenAI Studio.
Each feature is cleanly separated into its own backend module in `backends/`
to allow adding, removing, or modifying features independently.
"""

from django.shortcuts import render
from django.http import JsonResponse

from .backends.standard_chat import generate_standard_reply
from .backends.offline_chat import generate_offline_reply
from .backends.limited_agent import run_limited_agent, LIMITED_TOOLS_METADATA
from .backends.universal_agent import propose_universal_action, execute_confirmed_command


# =====================================================================
# 1. STANDARD CHAT (Online Gemini)
# =====================================================================

def standard_ui(request):
    return render(request, "chat/standard.html")


def standard_api(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "No input provided"}, status=400)
    try:
        result = generate_standard_reply(q)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# 2. OFFLINE CHAT (Local Ollama / Zero Internet)
# =====================================================================

def offline_ui(request):
    return render(request, "chat/offline.html")


def offline_api(request):
    q = request.GET.get("q", "").strip()
    model = request.GET.get("model", "llama3.2").strip()
    if not q:
        return JsonResponse({"error": "No input provided"}, status=400)
    try:
        result = generate_offline_reply(q, model_name=model)
        return JsonResponse(result)
    except ConnectionError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# 3. LIMITED AGENT (Safe & Specific Tools)
# =====================================================================

def limited_agent_ui(request):
    return render(request, "chat/limited_agent.html", {"tools": LIMITED_TOOLS_METADATA})


def limited_agent_api(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        result = run_limited_agent(q)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# 4. UNIVERSAL AGENT (Full OS Control + Confirmation)
# =====================================================================

def universal_agent_ui(request):
    return render(request, "chat/universal_agent.html")


def universal_agent_api(request):
    q = request.GET.get("q", "").strip()
    confirmed = request.GET.get("confirmed", "false").lower() == "true"
    command = request.GET.get("command", "").strip()
    password = request.GET.get("password", "").strip()

    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        if confirmed and command:
            result = execute_confirmed_command(q, command, password=password)
        else:
            result = propose_universal_action(q)
        return JsonResponse(result)
    except PermissionError as e:
        return JsonResponse({"error": str(e), "auth_error": True}, status=403)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
