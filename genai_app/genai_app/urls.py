from django.contrib import admin
from django.urls import path, include
from chat import views as chat_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),
    
    # Direct top-level shortcuts
    path('', chat_views.standard_ui, name='home'),
    path('offline/', chat_views.offline_ui, name='offline_direct'),
    path('limited-agent/', chat_views.limited_agent_ui, name='limited_agent_direct'),
    path('agent/', chat_views.universal_agent_ui, name='universal_agent_direct'),
    path('universal-agent/', chat_views.universal_agent_ui, name='universal_agent_full_direct'),
]
