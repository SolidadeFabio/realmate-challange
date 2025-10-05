import json
import logging
from typing import Any, Dict
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder
from .websocket_service import WebSocketService

logger = logging.getLogger(__name__)


class ConversationConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = WebSocketService()
        self.user = None

    async def connect(self) -> None:
        self.room_group_name: str = 'conversations'
        self.user = await self.service.get_user_from_scope(self.scope)

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        logger.info(f"WebSocket connected: {self.channel_name} as {self.user}")

        conversations = await self.service.get_conversations()
        await self.send(text_data=json.dumps({
            'type': 'conversations_list',
            'conversations': conversations
        }, cls=DjangoJSONEncoder))

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'get_conversations':
                conversations = await self.service.get_conversations()
                await self.send(text_data=json.dumps({
                    'type': 'conversations_list',
                    'conversations': conversations
                }, cls=DjangoJSONEncoder))

            elif message_type == 'get_conversation':
                conversation_id = data.get('conversation_id')
                can_view_internal = await self.service.can_view_internal_messages(self.user)
                conversation = await self.service.get_conversation_detail(conversation_id)
                await self.send(text_data=json.dumps({
                    'type': 'conversation_detail',
                    'conversation': conversation,
                    'can_view_internal': can_view_internal
                }, cls=DjangoJSONEncoder))

            elif message_type == 'send_message':
                conversation_id = data.get('conversation_id')
                content = data.get('content')
                is_internal = data.get('is_internal', False)

                message = await self.service.create_message(
                    conversation_id,
                    content,
                    self.user,
                    is_internal
                )

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'new_message',
                        'message': message
                    }
                )

            elif message_type == 'filter_conversations':
                filters = data.get('filters', {})
                conversations = await self.service.get_filtered_conversations(filters)
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

    async def new_message(self, event: Dict[str, Any]) -> None:
        can_view_internal = await self.service.can_view_internal_messages(self.user)
        message = event.get('message', {})

        if message.get('is_internal') and not can_view_internal:
            return

        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
        }, cls=DjangoJSONEncoder))

    async def new_conversation(self, event: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            'type': 'new_conversation',
            'conversation': event['conversation']
        }, cls=DjangoJSONEncoder))

    async def conversation_updated(self, event: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            'type': 'conversation_updated',
            'conversation': event['conversation']
        }, cls=DjangoJSONEncoder))

    async def get_conversation_with_internal(self, conversation_id: str) -> Dict[str, Any]:
        return await self.service.get_conversation_detail(conversation_id)