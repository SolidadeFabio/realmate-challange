from django.urls import path
from .views import (
    WebhookView,
    ConversationDetailView,
    ConversationListAPIView,
    ConversationMessagesAPIView,
    CloseConversationAPIView
)

app_name = 'webhooks'

urlpatterns = [
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('conversations/<uuid:id>/', ConversationDetailView.as_view(), name='conversation-detail'),

    path('api/conversations/', ConversationListAPIView.as_view(), name='api-conversation-list'),
    path('api/conversations/<uuid:conversation_id>/messages/', ConversationMessagesAPIView.as_view(), name='api-conversation-messages'),
    path('api/conversations/<uuid:conversation_id>/close/', CloseConversationAPIView.as_view(), name='api-conversation-close'),
]