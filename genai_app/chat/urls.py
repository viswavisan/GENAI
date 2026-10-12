from django.urls import path
from . import views

urlpatterns = [
    # 1. Standard Chat (Online Gemini)
    path('', views.standard_ui, name='standard_ui'),
    path('api', views.standard_api, name='standard_api'),

    # 2. Offline Chat (Local Ollama)
    path('offline/', views.offline_ui, name='offline_ui'),
    path('offline/api', views.offline_api, name='offline_api'),

    # 3. Limited Agent (Safe Specific Tools)
    path('limited-agent/', views.limited_agent_ui, name='limited_agent_ui'),
    path('limited-agent/api', views.limited_agent_api, name='limited_agent_api'),

    # 4. Universal Agent (Full OS Control + Confirmation)
    path('universal-agent/', views.universal_agent_ui, name='universal_agent_ui'),
    path('universal-agent/api', views.universal_agent_api, name='universal_agent_api'),

    # Backward-compatible shortcuts
    path('agent/', views.universal_agent_ui, name='agent_ui'),
    path('agent/api', views.universal_agent_api, name='agent_api'),
]
