import os
from django.shortcuts import render
from django.http import JsonResponse
from dotenv import load_dotenv
from google import genai

load_dotenv()

def chat_ui(request):
    return render(request, "chat/index.html")

def chat_api(request):
    user_input = request.GET.get("q", "").strip()
    if not user_input:
        return JsonResponse({"error": "No input provided"}, status=400)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return JsonResponse({
            "error": "GEMINI_API_KEY not found. Please set GEMINI_API_KEY in your .env file or environment variables."
        }, status=500)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_input,
        )
        return JsonResponse({"reply": response.text})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

