import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Conversation, ConversationStatus
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    WebhookEventSerializer,
    MessageSerializer
)
from .services import WebhookProcessor, ConversationService, MessageService
from .exceptions import (
    ConversationNotFoundException,
    ConversationClosedException,
    InvalidWebhookDataException,
    DuplicateEntityException
)
import uuid

logger = logging.getLogger(__name__)


class ConversationPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class WebhookView(APIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = WebhookProcessor()

    def post(self, request, *args, **kwargs):
        logger.info(f"Received webhook: {request.data}")

        serializer = WebhookEventSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            logger.error(f"Webhook validation error: {e}")
            return Response(
                {"error": "Invalid webhook data", "details": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = self.processor.process_event(serializer.validated_data)

            return Response(
                {
                    "status": "success",
                    "message": f"Event processed successfully",
                    "result": result
                },
                status=status.HTTP_200_OK
            )

        except ConversationNotFoundException as e:
            logger.warning(f"Conversation not found: {e}")
            return Response(
                {"error": "Conversation not found", "details": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        except ConversationClosedException as e:
            logger.warning(f"Conversation closed: {e}")
            return Response(
                {"error": "Conversation is closed", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except (InvalidWebhookDataException, DuplicateEntityException) as e:
            logger.warning(f"Invalid webhook data: {e}")
            return Response(
                {"error": "Invalid webhook data", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.exception(f"Unexpected error processing webhook: {e}")
            return Response(
                {"error": "Internal server error", "details": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversationDetailView(RetrieveAPIView):
    queryset = Conversation.objects.prefetch_related('messages')
    serializer_class = ConversationSerializer
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return Response(
                {
                    "status": "success",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Conversation.DoesNotExist:
            conversation_id = kwargs.get('id')
            logger.warning(f"Conversation {conversation_id} not found")
            return Response(
                {
                    "error": "Conversation not found",
                    "details": f"Conversation with id {conversation_id} does not exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )


class ConversationListAPIView(ListAPIView):
    queryset = Conversation.objects.prefetch_related('messages').all().order_by('-created_at')
    serializer_class = ConversationListSerializer
    pagination_class = ConversationPagination

    def post(self, request, *args, **kwargs):
        content = request.data.get('content', '').strip()
        client_id = request.data.get('client_id')

        if not content:
            return Response(
                {'error': 'Content is required for first message'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation_id = uuid.uuid4()
        message_id = uuid.uuid4()

        try:
            conversation = ConversationService.create_conversation(
                str(conversation_id),
                timezone.now()
            )

            message = MessageService.create_message(
                str(message_id),
                str(conversation_id),
                'SENT',
                content,
                timezone.now()
            )

            if client_id:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'conversations',
                    {
                        'type': 'new_message',
                        'message': {
                            'id': str(message.id),
                            'conversation_id': str(message.conversation_id),
                            'direction': message.direction,
                            'content': message.content,
                            'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                            'created_at': message.created_at.isoformat() if message.created_at else None,
                            'client_id': client_id
                        },
                        'client_id': client_id
                    }
                )

            serializer = ConversationSerializer(conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversationMessagesAPIView(APIView):
    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.prefetch_related('messages').get(id=conversation_id)
            messages = conversation.messages.all().order_by('timestamp')
            message_serializer = MessageSerializer(messages, many=True)

            return Response({
                'status': conversation.status,
                'created_at': conversation.created_at,
                'updated_at': conversation.updated_at,
                'closed_at': conversation.closed_at,
                'messages': message_serializer.data
            })
        except Conversation.DoesNotExist:
            return Response(
                {'error': f'Conversation {conversation_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CloseConversationAPIView(APIView):
    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)

            if conversation.is_closed():
                return Response(
                    {'error': 'Conversation is already closed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            conversation.status = ConversationStatus.CLOSED
            conversation.closed_at = timezone.now()
            conversation.save()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'conversations',
                {
                    'type': 'conversation_updated',
                    'conversation': {
                        'id': str(conversation.id),
                        'status': conversation.status,
                        'closed_at': conversation.closed_at.isoformat() if conversation.closed_at else None
                    }
                }
            )

            serializer = ConversationSerializer(conversation)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Conversation.DoesNotExist:
            return Response(
                {'error': f'Conversation {conversation_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )