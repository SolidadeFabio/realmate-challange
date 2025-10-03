import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
import uuid
from .models import Conversation, Message
from django.utils import timezone
from .models import MessageDirection

logger = logging.getLogger(__name__)


class ConversationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'conversations'

        self.persona_id = str(uuid.uuid4())
        self.persona_name = f"User_{self.persona_id[:8]}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected: {self.channel_name} as {self.persona_name}")

        conversations = await self.get_conversations()
        await self.send(text_data=json.dumps({
            'type': 'conversations_list',
            'conversations': conversations,
            'persona_id': self.persona_id,
            'persona_name': self.persona_name
        }, cls=DjangoJSONEncoder))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'get_conversations':
                conversations = await self.get_conversations()
                await self.send(text_data=json.dumps({
                    'type': 'conversations_list',
                    'conversations': conversations
                }, cls=DjangoJSONEncoder))

            elif message_type == 'get_conversation':
                conversation_id = data.get('conversation_id')
                conversation = await self.get_conversation_detail(conversation_id)
                await self.send(text_data=json.dumps({
                    'type': 'conversation_detail',
                    'conversation': conversation
                }, cls=DjangoJSONEncoder))

            elif message_type == 'send_message':
                conversation_id = data.get('conversation_id')
                content = data.get('content')
                client_id = data.get('client_id')

                message = await self.create_message(conversation_id, content)

                message['persona_id'] = self.persona_id
                message['persona_name'] = self.persona_name
                message['client_id'] = client_id

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'new_message',
                        'message': message,
                        'persona_id': self.persona_id,
                        'persona_name': self.persona_name,
                        'client_id': client_id
                    }
                )

            elif message_type == 'filter_conversations':
                filters = data.get('filters', {})
                conversations = await self.get_filtered_conversations(filters)
                await self.send(text_data=json.dumps({
                    'type': 'conversations_list',
                    'conversations': conversations
                }, cls=DjangoJSONEncoder))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def new_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }, cls=DjangoJSONEncoder))

    async def new_conversation(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_conversation',
            'conversation': event['conversation']
        }, cls=DjangoJSONEncoder))

    async def conversation_updated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'conversation_updated',
            'conversation': event['conversation']
        }, cls=DjangoJSONEncoder))

    @database_sync_to_async
    def get_conversations(self):
        conversations = Conversation.objects.all().order_by('-created_at')[:50]
        return [self.serialize_conversation(conv) for conv in conversations]

    @database_sync_to_async
    def get_conversation_detail(self, conversation_id):
        try:
            conversation = Conversation.objects.prefetch_related('messages').get(id=conversation_id)
            return self.serialize_conversation_with_messages(conversation)
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def get_filtered_conversations(self, filters):
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
    def create_message(self, conversation_id, content):
        conversation = Conversation.objects.get(id=conversation_id)

        if conversation.is_closed():
            raise Exception("Cannot send message to closed conversation")

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content=content,
            timestamp=timezone.now()
        )

        return self.serialize_message(message)

    def serialize_conversation(self, conversation):
        last_message = conversation.messages.order_by('-timestamp').first()
        return {
            'id': str(conversation.id),
            'status': conversation.status,
            'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'closed_at': conversation.closed_at.isoformat() if conversation.closed_at else None,
            'message_count': conversation.messages.count(),
            'last_message': self.serialize_message(last_message) if last_message else None
        }

    def serialize_conversation_with_messages(self, conversation):
        return {
            'id': str(conversation.id),
            'status': conversation.status,
            'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'closed_at': conversation.closed_at.isoformat() if conversation.closed_at else None,
            'messages': [self.serialize_message(msg) for msg in conversation.messages.order_by('timestamp')]
        }

    def serialize_message(self, message):
        if not message:
            return None
        return {
            'id': str(message.id),
            'conversation_id': str(message.conversation_id),
            'direction': message.direction,
            'content': message.content,
            'timestamp': message.timestamp.isoformat() if message.timestamp else None,
            'created_at': message.created_at.isoformat() if message.created_at else None
        }