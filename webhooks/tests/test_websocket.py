import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from webhooks.models import Conversation, Message, MessageDirection, Contact
from webhooks.websocket_service import WebSocketService


class WebSocketServiceTestCase(TestCase):
    def setUp(self):
        self.service = WebSocketService()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_serialize_conversation(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.RECEIVED,
            content='Test message',
            timestamp=timezone.now()
        )

        serialized = self.service.serialize_conversation(conversation)

        self.assertEqual(serialized['id'], str(conversation.id))
        self.assertEqual(serialized['status'], 'OPEN')
        self.assertIsNotNone(serialized['last_message'])
        self.assertEqual(serialized['message_count'], 1)

    def test_serialize_conversation_excludes_internal_messages(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Regular message',
            timestamp=timezone.now(),
            is_internal=False
        )

        Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Internal message',
            timestamp=timezone.now(),
            is_internal=True
        )

        serialized = self.service.serialize_conversation(conversation)

        self.assertEqual(serialized['message_count'], 1)
        self.assertEqual(serialized['last_message']['content'], 'Regular message')

    def test_serialize_conversation_with_contact(self):
        contact = Contact.objects.create(
            name='John Doe',
            phone='+5511999999999',
            email='john@example.com'
        )

        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN',
            contact=contact
        )

        Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.RECEIVED,
            content='Hello',
            timestamp=timezone.now()
        )

        serialized = self.service.serialize_conversation(conversation)

        self.assertEqual(serialized['id'], str(conversation.id))
        self.assertIsNotNone(serialized['last_message'])

    def test_serialize_message_with_author(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Test message',
            timestamp=timezone.now(),
            author_user=self.user
        )

        serialized = self.service.serialize_message(message)

        self.assertEqual(serialized['id'], str(message.id))
        self.assertEqual(serialized['content'], 'Test message')
        self.assertEqual(serialized['direction'], MessageDirection.SENT)
        self.assertIsNotNone(serialized['author_user'])
        self.assertEqual(serialized['author_user']['username'], 'testuser')
        self.assertEqual(serialized['author_user']['full_name'], 'Test User')

    def test_serialize_message_without_author(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.RECEIVED,
            content='Customer message',
            timestamp=timezone.now(),
            author_user=None
        )

        serialized = self.service.serialize_message(message)

        self.assertEqual(serialized['id'], str(message.id))
        self.assertEqual(serialized['content'], 'Customer message')
        self.assertIsNone(serialized['author_user'])

    def test_serialize_message_null_returns_none(self):
        result = self.service.serialize_message(None)
        self.assertIsNone(result)

    def test_serialize_conversation_with_messages(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        msg1 = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.RECEIVED,
            content='First message',
            timestamp=timezone.now()
        )

        msg2 = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Second message',
            timestamp=timezone.now(),
            author_user=self.user
        )

        serialized = self.service.serialize_conversation_with_messages(conversation)

        self.assertEqual(serialized['id'], str(conversation.id))
        self.assertEqual(len(serialized['messages']), 2)
        self.assertEqual(serialized['messages'][0]['content'], 'First message')
        self.assertEqual(serialized['messages'][1]['content'], 'Second message')

    def test_serialize_conversation_with_messages_include_internal(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.RECEIVED,
            content='Regular message',
            timestamp=timezone.now(),
            is_internal=False
        )

        Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Internal message',
            timestamp=timezone.now(),
            is_internal=True,
            author_user=self.user
        )

        serialized_without = self.service.serialize_conversation_with_messages(
            conversation,
            include_internal=False
        )
        self.assertEqual(len(serialized_without['messages']), 1)

        serialized_with = self.service.serialize_conversation_with_messages(
            conversation,
            include_internal=True
        )
        self.assertEqual(len(serialized_with['messages']), 2)

    def test_can_view_internal_messages_method_exists(self):
        """Verify WebSocket service has permission checking method"""
        self.assertTrue(hasattr(self.service, 'can_view_internal_messages'))


class WebSocketAuthenticationTestCase(TestCase):
    def setUp(self):
        self.service = WebSocketService()

    def test_authentication_service_exists(self):
        self.assertTrue(hasattr(self.service, 'get_user_from_scope'))

    def test_serialization_methods_exist(self):
        self.assertTrue(hasattr(self.service, 'serialize_conversation'))
        self.assertTrue(hasattr(self.service, 'serialize_message'))
        self.assertTrue(hasattr(self.service, 'serialize_conversation_with_messages'))


class WebSocketDataRetrievalTestCase(TestCase):

    def setUp(self):
        self.service = WebSocketService()

    def test_service_has_data_retrieval_methods(self):
        self.assertTrue(hasattr(self.service, 'get_conversations'))
        self.assertTrue(hasattr(self.service, 'get_conversation_detail'))
        self.assertTrue(hasattr(self.service, 'get_filtered_conversations'))
        self.assertTrue(hasattr(self.service, 'create_message'))
        self.assertTrue(hasattr(self.service, 'can_view_internal_messages'))
