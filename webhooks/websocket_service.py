import logging
from typing import Dict, Any, List, Optional
from django.contrib.auth.models import User, AnonymousUser
from django.utils import timezone
from channels.db import database_sync_to_async
import uuid
import jwt
from django.conf import settings
from urllib.parse import parse_qs

from .models import Conversation, Message, MessageDirection

logger = logging.getLogger(__name__)


class WebSocketService:
    def __init__(self):
        pass

    @database_sync_to_async
    def get_user_from_scope(self, scope: Dict[str, Any]) -> User | AnonymousUser:
        headers = dict(scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode('utf-8')

        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            query_string = scope.get('query_string', b'').decode('utf-8')
            params = parse_qs(query_string)
            token_list = params.get('token', [])
            if token_list:
                token = token_list[0]

        if token:
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                user_id = payload.get('user_id')
                if user_id:
                    return User.objects.get(id=user_id)
            except (jwt.InvalidTokenError, User.DoesNotExist):
                pass

        return AnonymousUser()

    @database_sync_to_async
    def get_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        conversations = Conversation.objects.all().order_by('-created_at')[:limit]
        return [self.serialize_conversation(conv) for conv in conversations]

    @database_sync_to_async
    def get_conversation_detail(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        try:
            conversation = Conversation.objects.prefetch_related('messages').get(id=conversation_id)
            return self.serialize_conversation_with_messages(conversation)
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def get_filtered_conversations(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        queryset = Conversation.objects.all()

        if 'status' in filters:
            queryset = queryset.filter(status=filters['status'])

        if 'search' in filters:
            search_term = filters['search']
            queryset = queryset.filter(
                messages__content__icontains=search_term
            ).distinct()

        if 'date_from' in filters:
            queryset = queryset.filter(created_at__gte=filters['date_from'])

        if 'date_to' in filters:
            queryset = queryset.filter(created_at__lte=filters['date_to'])

        conversations = queryset.order_by('-created_at')[:50]
        return [self.serialize_conversation(conv) for conv in conversations]

    @database_sync_to_async
    def create_message(
        self,
        conversation_id: str,
        content: str,
        user: User,
        is_internal: bool = False
    ) -> Dict[str, Any]:
        conversation = Conversation.objects.get(id=conversation_id)

        if conversation.is_closed():
            raise Exception("Cannot send message to closed conversation")

        author_user = user if isinstance(user, User) else None
        direction = MessageDirection.SENT if author_user else MessageDirection.RECEIVED

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=direction,
            content=content,
            timestamp=timezone.now(),
            author_user=author_user,
            is_internal=is_internal
        )

        result = self.serialize_message(message)
        assert result is not None, "serialize_message should never return None for a valid message"
        return result

    def serialize_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        last_message = conversation.messages.filter(is_internal=False).order_by('-timestamp').first()
        return {
            'id': str(conversation.id),
            'status': conversation.status,
            'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'closed_at': conversation.closed_at.isoformat() if conversation.closed_at else None,
            'message_count': conversation.messages.filter(is_internal=False).count(),
            'last_message': self.serialize_message(last_message) if last_message else None
        }

    def serialize_conversation_with_messages(self, conversation: Conversation, include_internal: bool = False) -> Dict[str, Any]:
        messages_qs = conversation.messages.all()
        if not include_internal:
            messages_qs = messages_qs.filter(is_internal=False)

        return {
            'id': str(conversation.id),
            'status': conversation.status,
            'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'closed_at': conversation.closed_at.isoformat() if conversation.closed_at else None,
            'messages': [self.serialize_message(msg) for msg in messages_qs.order_by('timestamp')]
        }

    def serialize_message(self, message: Optional[Message]) -> Optional[Dict[str, Any]]:
        if not message:
            return None
        return {
            'id': str(message.id),
            'conversation': str(message.conversation_id),
            'direction': message.direction,
            'content': message.content,
            'timestamp': message.timestamp.isoformat() if message.timestamp else None,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'is_internal': message.is_internal,
            'author_user': {
                'id': message.author_user.id,
                'username': message.author_user.username,
                'first_name': message.author_user.first_name,
                'last_name': message.author_user.last_name,
                'full_name': f"{message.author_user.first_name} {message.author_user.last_name}".strip() or message.author_user.username
            } if message.author_user else None
        }

    @database_sync_to_async
    def can_view_internal_messages(self, user: User) -> bool:
        return isinstance(user, User) and user.is_authenticated