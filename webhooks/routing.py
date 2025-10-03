from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/conversations/', consumers.ConversationConsumer.as_asgi()),
]