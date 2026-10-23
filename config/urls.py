from django.contrib import admin
from django.urls import path, include
from chat import views as chat_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),

    # Direct shortcuts
    path('', chat_views.chat_online_ui, name='home'),
    path('offline/', chat_views.chat_offline_ui, name='offline_direct'),
    path('agent/limited/', chat_views.agent_online_limited_ui, name='agent_limited_direct'),
    path('agent/universal/', chat_views.agent_online_universal_ui, name='agent_universal_direct'),
    path('agent/offline/', chat_views.agent_offline_ui, name='agent_offline_direct'),
    path('mcp/', chat_views.gmail_mcp_ui, name='mcp_direct'),
    path('mcp/gmail/', chat_views.gmail_mcp_ui, name='mcp_gmail_direct'),
    path('rag/', chat_views.rag_ui, name='rag_direct'),

    # Aliases
    path('agent/', chat_views.agent_online_universal_ui),
    path('universal-agent/', chat_views.agent_online_universal_ui),
    path('limited-agent/', chat_views.agent_online_limited_ui),
]
