from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    WebhookView,
    ConversationDetailView,
    ConversationListAPIView,
    ConversationMessagesAPIView,
    CloseConversationAPIView,
    ContactListCreateView,
    RegisterView,
    CurrentUserView,
    AssignContactToConversationView
)

app_name = 'webhooks'

urlpatterns = [
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('conversations/<uuid:id>/', ConversationDetailView.as_view(), name='conversation-detail'),

    path('api/auth/login/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/me/', CurrentUserView.as_view(), name='current-user'),

    path('api/contacts/', ContactListCreateView.as_view(), name='contact-list-create'),

    path('api/conversations/', ConversationListAPIView.as_view(), name='api-conversation-list'),
    path('api/conversations/<uuid:conversation_id>/messages/', ConversationMessagesAPIView.as_view(), name='api-conversation-messages'),
    path('api/conversations/<uuid:conversation_id>/close/', CloseConversationAPIView.as_view(), name='api-conversation-close'),
    path('api/conversations/<uuid:conversation_id>/assign-contact/', AssignContactToConversationView.as_view(), name='api-assign-contact'),
]