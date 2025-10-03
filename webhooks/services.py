"""
Business logic services for webhook processing.

This module contains the business logic separated from views,
making it easier to test and maintain.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from .models import Conversation, Message, ConversationStatus, MessageDirection
from .exceptions import (
    ConversationClosedException,
    ConversationNotFoundException,
    InvalidWebhookDataException
)

logger = logging.getLogger(__name__)


class ConversationService:
    @staticmethod
    @transaction.atomic
    def create_conversation(conversation_id: str, timestamp: datetime) -> Conversation:
        if Conversation.objects.filter(id=conversation_id).exists():
            logger.warning(f"Conversation {conversation_id} already exists")
            raise InvalidWebhookDataException(
                f"Conversation {conversation_id} already exists"
            )

        conversation = Conversation.objects.create(
            id=conversation_id,
            status=ConversationStatus.OPEN
        )

        logger.info(f"Created conversation {conversation_id}")
        return conversation

    @staticmethod
    @transaction.atomic
    def close_conversation(conversation_id: str, timestamp: datetime) -> Conversation:
        try:
            conversation = Conversation.objects.select_for_update().get(
                id=conversation_id
            )
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_id} not found")
            raise ConversationNotFoundException(
                f"Conversation {conversation_id} not found"
            )

        if conversation.is_closed():
            logger.warning(f"Conversation {conversation_id} is already closed")
            raise InvalidWebhookDataException(
                f"Conversation {conversation_id} is already closed"
            )

        conversation.status = ConversationStatus.CLOSED
        conversation.closed_at = timestamp
        conversation.save()

        logger.info(f"Closed conversation {conversation_id}")
        return conversation

    @staticmethod
    def get_conversation_with_messages(conversation_id: str) -> Conversation:
        try:
            return Conversation.objects.prefetch_related('messages').get(
                id=conversation_id
            )
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_id} not found")
            raise ConversationNotFoundException(
                f"Conversation {conversation_id} not found"
            )


class MessageService:
    @staticmethod
    @transaction.atomic
    def create_message(
        message_id: str,
        conversation_id: str,
        direction: str,
        content: str,
        timestamp: datetime
    ) -> Message:
        if Message.objects.filter(id=message_id).exists():
            logger.warning(f"Message {message_id} already exists")
            raise InvalidWebhookDataException(
                f"Message {message_id} already exists"
            )

        try:
            conversation = Conversation.objects.select_for_update().get(
                id=conversation_id
            )
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_id} not found")
            raise ConversationNotFoundException(
                f"Conversation {conversation_id} not found"
            )

        if not conversation.is_open():
            logger.warning(
                f"Cannot add message to closed conversation {conversation_id}"
            )
            raise ConversationClosedException(
                f"Cannot add messages to closed conversation {conversation_id}"
            )

        message = Message.objects.create(
            id=message_id,
            conversation=conversation,
            direction=direction,
            content=content,
            timestamp=timestamp
        )

        conversation.save(update_fields=['updated_at'])

        logger.info(
            f"Created {direction} message {message_id} in conversation {conversation_id}"
        )
        return message


class WebhookProcessor:
    def __init__(self):
        self.conversation_service = ConversationService()
        self.message_service = MessageService()

    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        event_type = event_data['type']
        timestamp = event_data['timestamp']
        data = event_data['data']

        logger.info(f"Processing {event_type} event")

        if event_type == 'NEW_CONVERSATION':
            return self._process_new_conversation(data['id'], timestamp)

        elif event_type == 'NEW_MESSAGE':
            return self._process_new_message(
                message_id=data['id'],
                conversation_id=data['conversation_id'],
                direction=data['direction'],
                content=data['content'],
                timestamp=timestamp
            )

        elif event_type == 'CLOSE_CONVERSATION':
            return self._process_close_conversation(data['id'], timestamp)

        else:
            raise InvalidWebhookDataException(f"Unknown event type: {event_type}")

    def _process_new_conversation(
        self,
        conversation_id: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        conversation = self.conversation_service.create_conversation(
            conversation_id,
            timestamp
        )
        return {
            'status': 'created',
            'entity': 'conversation',
            'id': str(conversation.id)
        }

    def _process_new_message(
        self,
        message_id: str,
        conversation_id: str,
        direction: str,
        content: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        message = self.message_service.create_message(
            message_id,
            conversation_id,
            direction,
            content,
            timestamp
        )
        return {
            'status': 'created',
            'entity': 'message',
            'id': str(message.id)
        }

    def _process_close_conversation(
        self,
        conversation_id: str,
        timestamp: datetime
    ) -> Dict[str, Any]:
        conversation = self.conversation_service.close_conversation(
            conversation_id,
            timestamp
        )
        return {
            'status': 'closed',
            'entity': 'conversation',
            'id': str(conversation.id)
        }