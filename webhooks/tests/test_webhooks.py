import uuid
from datetime import datetime
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from webhooks.models import Conversation, Message, ConversationStatus, MessageDirection
from webhooks.services import ConversationService, MessageService, WebhookProcessor
from webhooks.exceptions import (
    ConversationNotFoundException,
    ConversationClosedException,
    InvalidWebhookDataException
)


class ConversationServiceTestCase(TestCase):
    def setUp(self):
        self.service = ConversationService()

    def test_create_conversation_success(self):
        conversation_id = str(uuid.uuid4())
        timestamp = timezone.now()

        conversation = self.service.create_conversation(conversation_id, timestamp)

        self.assertEqual(str(conversation.id), conversation_id)
        self.assertEqual(conversation.status, ConversationStatus.OPEN)
        self.assertIsNone(conversation.closed_at)

    def test_create_duplicate_conversation_raises_exception(self):
        conversation_id = str(uuid.uuid4())
        timestamp = timezone.now()

        self.service.create_conversation(conversation_id, timestamp)

        with self.assertRaises(InvalidWebhookDataException):
            self.service.create_conversation(conversation_id, timestamp)

    def test_close_conversation_success(self):
        conversation_id = str(uuid.uuid4())
        timestamp = timezone.now()

        self.service.create_conversation(conversation_id, timestamp)
        conversation = self.service.close_conversation(conversation_id, timestamp)

        self.assertEqual(conversation.status, ConversationStatus.CLOSED)
        self.assertIsNotNone(conversation.closed_at)

    def test_close_nonexistent_conversation_raises_exception(self):
        conversation_id = str(uuid.uuid4())
        timestamp = timezone.now()

        with self.assertRaises(ConversationNotFoundException):
            self.service.close_conversation(conversation_id, timestamp)

    def test_close_already_closed_conversation_raises_exception(self):
        conversation_id = str(uuid.uuid4())
        timestamp = timezone.now()

        self.service.create_conversation(conversation_id, timestamp)
        self.service.close_conversation(conversation_id, timestamp)

        with self.assertRaises(InvalidWebhookDataException):
            self.service.close_conversation(conversation_id, timestamp)


class MessageServiceTestCase(TransactionTestCase):
    def setUp(self):
        self.message_service = MessageService()
        self.conversation_service = ConversationService()

    def test_create_message_in_open_conversation(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        timestamp = timezone.now()

        self.conversation_service.create_conversation(conversation_id, timestamp)

        message = self.message_service.create_message(
            message_id=message_id,
            conversation_id=conversation_id,
            direction=MessageDirection.RECEIVED,
            content="Test message",
            timestamp=timestamp
        )

        self.assertEqual(str(message.id), message_id)
        self.assertEqual(message.direction, MessageDirection.RECEIVED)
        self.assertEqual(message.content, "Test message")

    def test_create_message_in_closed_conversation_raises_exception(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        timestamp = timezone.now()

        self.conversation_service.create_conversation(conversation_id, timestamp)
        self.conversation_service.close_conversation(conversation_id, timestamp)

        with self.assertRaises(ConversationClosedException):
            self.message_service.create_message(
                message_id=message_id,
                conversation_id=conversation_id,
                direction=MessageDirection.RECEIVED,
                content="Test message",
                timestamp=timestamp
            )

    def test_create_message_in_nonexistent_conversation_raises_exception(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        timestamp = timezone.now()

        with self.assertRaises(ConversationNotFoundException):
            self.message_service.create_message(
                message_id=message_id,
                conversation_id=conversation_id,
                direction=MessageDirection.RECEIVED,
                content="Test message",
                timestamp=timestamp
            )

    def test_create_duplicate_message_raises_exception(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        timestamp = timezone.now()

        self.conversation_service.create_conversation(conversation_id, timestamp)
        self.message_service.create_message(
            message_id=message_id,
            conversation_id=conversation_id,
            direction=MessageDirection.RECEIVED,
            content="Test message",
            timestamp=timestamp
        )

        with self.assertRaises(InvalidWebhookDataException):
            self.message_service.create_message(
                message_id=message_id,
                conversation_id=conversation_id,
                direction=MessageDirection.SENT,
                content="Another message",
                timestamp=timestamp
            )


class WebhookViewTestCase(APITestCase):
    def test_create_new_conversation(self):
        conversation_id = str(uuid.uuid4())
        data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {
                "id": conversation_id
            }
        }

        response = self.client.post('/webhook/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')

        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.status, ConversationStatus.OPEN)

    def test_create_new_message(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        msg_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": message_id,
                "direction": "RECEIVED",
                "content": "Hello, world!",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', msg_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        message = Message.objects.get(id=message_id)
        self.assertEqual(message.content, "Hello, world!")
        self.assertEqual(message.direction, MessageDirection.RECEIVED)

    def test_close_conversation(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        
        self.client.post('/webhook/', conv_data, format='json')

        close_data = {
            "type": "CLOSE_CONVERSATION",
            "timestamp": "2025-02-21T10:20:45.349308",
            "data": {"id": conversation_id}
        }

        response = self.client.post('/webhook/', close_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.status, ConversationStatus.CLOSED)

    def test_message_to_closed_conversation_returns_400(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        close_data = {
            "type": "CLOSE_CONVERSATION",
            "timestamp": "2025-02-21T10:20:45.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', close_data, format='json')

        msg_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:46.349308",
            "data": {
                "id": message_id,
                "direction": "RECEIVED",
                "content": "This should fail",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', msg_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Conversation is closed')
        self.assertIn(f'closed conversation {conversation_id}', response.data['details'])

    def test_invalid_webhook_data_returns_400(self):
        data = {
            "type": "INVALID_TYPE",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": str(uuid.uuid4())}
        }

        response = self.client.post('/webhook/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_message_with_sent_direction(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        
        self.client.post('/webhook/', conv_data, format='json')

        msg_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:44.349308",
            "data": {
                "id": message_id,
                "direction": "SENT",
                "content": "Tudo ótimo e você?",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', msg_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        message = Message.objects.get(id=message_id)
        self.assertEqual(message.direction, MessageDirection.SENT)
        self.assertEqual(message.content, "Tudo ótimo e você?")

    def test_message_to_nonexistent_conversation_returns_404(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        msg_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": message_id,
                "direction": "RECEIVED",
                "content": "This should fail",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', msg_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Conversation not found')
        self.assertIn(f'Conversation {conversation_id} not found', response.data['details'])

    def test_close_nonexistent_conversation_returns_404(self):
        conversation_id = str(uuid.uuid4())

        close_data = {
            "type": "CLOSE_CONVERSATION",
            "timestamp": "2025-02-21T10:20:45.349308",
            "data": {"id": conversation_id}
        }

        response = self.client.post('/webhook/', close_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Conversation not found')
        self.assertIn(f'Conversation {conversation_id} not found', response.data['details'])

    def test_close_already_closed_conversation_returns_400(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        close_data = {
            "type": "CLOSE_CONVERSATION",
            "timestamp": "2025-02-21T10:20:45.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', close_data, format='json')

        response = self.client.post('/webhook/', close_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid webhook data')
        self.assertIn(f'Conversation {conversation_id} is already closed', response.data['details'])

    def test_duplicate_conversation_returns_400(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }

        response1 = self.client.post('/webhook/', conv_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        response2 = self.client.post('/webhook/', conv_data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.data['error'], 'Invalid webhook data')
        self.assertIn(f'Conversation {conversation_id} already exists', response2.data['details'])

    def test_duplicate_message_returns_400(self):
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        msg_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": message_id,
                "direction": "RECEIVED",
                "content": "First message",
                "conversation_id": conversation_id
            }
        }

        response1 = self.client.post('/webhook/', msg_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        msg_data['data']['content'] = "Different content"
        response2 = self.client.post('/webhook/', msg_data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.data['error'], 'Invalid webhook data')
        self.assertIn(f'Message {message_id} already exists', response2.data['details'])


class ConversationDetailViewTestCase(APITestCase):
    def test_get_conversation_with_messages(self):
        conversation_id = str(uuid.uuid4())
        message1_id = str(uuid.uuid4())
        message2_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        msg1_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": message1_id,
                "direction": "RECEIVED",
                "content": "Hello!",
                "conversation_id": conversation_id
            }
        }
        
        self.client.post('/webhook/', msg1_data, format='json')

        msg2_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:43.349308",
            "data": {
                "id": message2_id,
                "direction": "SENT",
                "content": "Hi there!",
                "conversation_id": conversation_id
            }
        }
        
        self.client.post('/webhook/', msg2_data, format='json')

        response = self.client.get(f'/conversations/{conversation_id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], conversation_id)
        self.assertEqual(response.data['data']['status'], 'OPEN')
        self.assertEqual(len(response.data['data']['messages']), 2)

    def test_get_nonexistent_conversation_returns_404(self):
        conversation_id = str(uuid.uuid4())

        response = self.client.get(f'/conversations/{conversation_id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)


class WebhookDataValidationTestCase(APITestCase):
    def test_new_message_missing_required_fields(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        msg_data_no_content = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', msg_data_no_content, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        msg_data_no_direction = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "content": "Test message",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', msg_data_no_direction, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        msg_data_no_conversation_id = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": "Test message"
            }
        }

        response = self.client.post('/webhook/', msg_data_no_conversation_id, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_uuid_format(self):
        invalid_uuid_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": "not-a-valid-uuid"}
        }

        response = self.client.post('/webhook/', invalid_uuid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

        conversation_id = str(uuid.uuid4())
        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        invalid_message_id = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": "invalid-uuid-123",
                "direction": "RECEIVED",
                "content": "Test",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', invalid_message_id, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_timestamp_format(self):
        invalid_timestamp_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "not-a-timestamp",
            "data": {"id": str(uuid.uuid4())}
        }

        response = self.client.post('/webhook/', invalid_timestamp_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invalid_timestamp_data2 = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-13-45T25:70:99",
            "data": {"id": str(uuid.uuid4())}
        }

        response = self.client.post('/webhook/', invalid_timestamp_data2, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_message_direction(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        invalid_direction_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "INVALID_DIRECTION",
                "content": "Test message",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', invalid_direction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_empty_content_message(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        empty_content_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": "",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', empty_content_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        whitespace_content_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:43.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": "   \t\n  ",
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', whitespace_content_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extremely_long_content(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        long_content = "A" * 10000
        long_content_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": long_content,
                "conversation_id": conversation_id
            }
        }

        response = self.client.post('/webhook/', long_content_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        message = Message.objects.get(id=long_content_data['data']['id'])
        self.assertEqual(message.content, long_content)

    def test_missing_type_field(self):
        data_without_type = {
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": str(uuid.uuid4())}
        }

        response = self.client.post('/webhook/', data_without_type, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_timestamp_field(self):
        data_without_timestamp = {
            "type": "NEW_CONVERSATION",
            "data": {"id": str(uuid.uuid4())}
        }

        response = self.client.post('/webhook/', data_without_timestamp, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_data_field(self):
        data_without_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308"
        }

        response = self.client.post('/webhook/', data_without_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extra_fields_in_new_conversation(self):
        data_with_extra_fields = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": "Should not be here"
            }
        }

        response = self.client.post('/webhook/', data_with_extra_fields, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extra_fields_in_close_conversation(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        close_with_extra_fields = {
            "type": "CLOSE_CONVERSATION",
            "timestamp": "2025-02-21T10:20:45.349308",
            "data": {
                "id": conversation_id,
                "content": "Should not be here",
                "direction": "SENT"
            }
        }

        response = self.client.post('/webhook/', close_with_extra_fields, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ConversationDetailValidationTestCase(APITestCase):
    def test_get_conversation_with_invalid_uuid(self):
        invalid_uuid = "not-a-valid-uuid-format"
        response = self.client.get(f'/conversations/{invalid_uuid}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_message_order_in_conversation(self):
        conversation_id = str(uuid.uuid4())

        conv_data = {
            "type": "NEW_CONVERSATION",
            "timestamp": "2025-02-21T10:20:41.349308",
            "data": {"id": conversation_id}
        }
        self.client.post('/webhook/', conv_data, format='json')

        msg1_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:45.000000",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": "Third message",
                "conversation_id": conversation_id
            }
        }

        msg2_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:42.000000",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "SENT",
                "content": "First message",
                "conversation_id": conversation_id
            }
        }

        msg3_data = {
            "type": "NEW_MESSAGE",
            "timestamp": "2025-02-21T10:20:43.000000",
            "data": {
                "id": str(uuid.uuid4()),
                "direction": "RECEIVED",
                "content": "Second message",
                "conversation_id": conversation_id
            }
        }

        self.client.post('/webhook/', msg1_data, format='json')
        self.client.post('/webhook/', msg2_data, format='json')
        self.client.post('/webhook/', msg3_data, format='json')

        response = self.client.get(f'/conversations/{conversation_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        messages = response.data['data']['messages']
        self.assertEqual(len(messages), 3)

        self.assertEqual(messages[0]['content'], "First message")
        self.assertEqual(messages[1]['content'], "Second message")
        self.assertEqual(messages[2]['content'], "Third message")