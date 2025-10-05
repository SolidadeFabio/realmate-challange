import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Conversation, ConversationStatus, Contact
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    WebhookEventSerializer,
    MessageSerializer,
    UserSerializer,
    ContactSerializer
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
        contact_id = request.data.get('contact_id')

        if not content:
            return Response(
                {'error': 'Content is required for first message'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not contact_id:
            return Response(
                {'error': 'Contact is required for new conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation_id = uuid.uuid4()
        message_id = uuid.uuid4()

        author_user = request.user if request.user.is_authenticated else None

        try:
            conversation = ConversationService.create_conversation(
                str(conversation_id),
                timezone.now()
            )

            if author_user:
                conversation.assigned_user = author_user

            if contact_id:
                try:
                    contact = Contact.objects.get(id=contact_id)
                    conversation.contact = contact
                except Contact.DoesNotExist:
                    pass

            conversation.save()

            direction = 'SENT' if author_user else 'RECEIVED'

            MessageService.create_message(
                str(message_id),
                str(conversation_id),
                direction,
                content,
                timezone.now(),
                author_user=author_user
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


class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if email and User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(password)
        except DjangoValidationError as e:
            return Response(
                {'error': 'Password validation failed', 'details': list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ContactListCreateView(ListCreateAPIView):
    queryset = Contact.objects.all().order_by('-created_at')
    serializer_class = ContactSerializer
    permission_classes = []


class AssignContactToConversationView(APIView):
    def patch(self, request, conversation_id):
        contact_id = request.data.get('contact_id')

        try:
            conversation = Conversation.objects.get(id=conversation_id)

            if contact_id:
                contact = Contact.objects.get(id=contact_id)
                conversation.contact = contact
            else:
                conversation.contact = None

            conversation.save()

            serializer = ConversationSerializer(conversation)
            return Response(serializer.data)

        except Conversation.DoesNotExist:
            return Response(
                {'error': f'Conversation {conversation_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Contact.DoesNotExist:
            return Response(
                {'error': f'Contact {contact_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )