from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_ui, name='chat_ui'),
    path('api', views.chat_api, name='chat_api'),
]
