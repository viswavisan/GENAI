from django.urls import path
from . import views

urlpatterns = [
    # =================================================================
    # GROUP 1: GenAI Chat (Pure Conversational)
    # =================================================================
    path('', views.chat_online_ui, name='chat_online_ui'),
    path('api', views.chat_online_api, name='chat_online_api'),
    path('offline/', views.chat_offline_ui, name='chat_offline_ui'),
    path('offline/api', views.chat_offline_api, name='chat_offline_api'),

    # =================================================================
    # GROUP 2: Agentic AI Online (Cloud with Autonomous Tools)
    # =================================================================
    path('agent/limited/', views.agent_online_limited_ui, name='agent_online_limited_ui'),
    path('agent/limited/api', views.agent_online_limited_api, name='agent_online_limited_api'),
    path('agent/universal/', views.agent_online_universal_ui, name='agent_online_universal_ui'),
    path('agent/universal/api', views.agent_online_universal_api, name='agent_online_universal_api'),

    # =================================================================
    # GROUP 3: Agentic AI Offline (Local Ollama Tool Calling)
    # =================================================================
    path('agent/offline/', views.agent_offline_ui, name='agent_offline_ui'),
    path('agent/offline/api', views.agent_offline_api, name='agent_offline_api'),

    # Backward-compatible routes
    path('limited-agent/', views.agent_online_limited_ui),
    path('limited-agent/api', views.agent_online_limited_api),
    path('universal-agent/', views.agent_online_universal_ui),
    path('universal-agent/api', views.agent_online_universal_api),
    path('agent/', views.agent_online_universal_ui),
    path('agent/api', views.agent_online_universal_api),
]
