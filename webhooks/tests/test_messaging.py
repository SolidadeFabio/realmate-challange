import uuid
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from webhooks.messaging_service import MessagingProvider, MessagingProviderException
from webhooks.models import Conversation, Message, MessageDirection, Contact
from webhooks.tasks import send_external_message, check_message_delivery_status


class MessagingProviderTestCase(TestCase):
    def setUp(self):
        self.provider = MessagingProvider(provider='whatsapp')

    def test_provider_initialization(self):
        self.assertEqual(self.provider.provider, 'whatsapp')

    def test_send_message_returns_mock_response(self):
        response = self.provider.send_message(
            phone='+5511999999999',
            content='Test message',
            message_type='text'
        )

        self.assertIn('message_id', response)
        self.assertIn('status', response)
        self.assertEqual(response['provider'], 'whatsapp')
        self.assertEqual(response['status'], 'queued')

    def test_send_message_with_metadata(self):
        metadata = {
            'conversation_id': str(uuid.uuid4()),
            'user_id': '123'
        }

        response = self.provider.send_message(
            phone='+5511888888888',
            content='Message with metadata',
            metadata=metadata
        )

        self.assertIsNotNone(response)
        self.assertEqual(response['status'], 'queued')

    def test_send_template_message(self):
        template_params = {
            'name': 'John Doe',
            'order_number': '12345'
        }

        response = self.provider.send_template_message(
            phone='+5511777777777',
            template_name='order_confirmation',
            template_params=template_params
        )

        self.assertIn('message_id', response)
        self.assertIn('template', response)
        self.assertEqual(response['template'], 'order_confirmation')
        self.assertEqual(response['status'], 'queued')

    def test_get_message_status(self):
        message_id = 'whatsapp_test_123'

        response = self.provider.get_message_status(message_id)

        self.assertIn('message_id', response)
        self.assertIn('status', response)
        self.assertEqual(response['message_id'], message_id)

    def test_different_provider_initialization(self):
        sms_provider = MessagingProvider(provider='sms')
        self.assertEqual(sms_provider.provider, 'sms')

        twilio_provider = MessagingProvider(provider='twilio')
        self.assertEqual(twilio_provider.provider, 'twilio')


class SendExternalMessageTaskTestCase(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            name='Test Contact',
            phone='+5511999999999',
            email='contact@example.com'
        )

        self.conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN',
            contact=self.contact
        )

    def test_send_external_message_sent_direction(self):
        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=self.conversation,
            direction=MessageDirection.SENT,
            content='Outbound message',
            timestamp=timezone.now()
        )

        result = send_external_message(str(message.id), provider='whatsapp')

        self.assertEqual(result['status'], 'sent')
        self.assertEqual(result['message_id'], str(message.id))
        self.assertEqual(result['provider'], 'whatsapp')
        self.assertIn('provider_response', result)

    def test_send_external_message_received_direction_skipped(self):
        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=self.conversation,
            direction=MessageDirection.RECEIVED,
            content='Inbound message',
            timestamp=timezone.now()
        )

        result = send_external_message(str(message.id), provider='whatsapp')

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'not_outbound')

    def test_send_external_message_no_phone_number(self):
        conversation_no_contact = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN',
            contact=None
        )

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation_no_contact,
            direction=MessageDirection.SENT,
            content='Message without phone',
            timestamp=timezone.now()
        )

        result = send_external_message(str(message.id), provider='whatsapp')

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no_phone_number')

    def test_send_external_message_contact_without_phone(self):
        contact_no_phone = Contact.objects.create(
            name='Contact No Phone',
            email='nophone@example.com'
        )

        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN',
            contact=contact_no_phone
        )

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Message to contact without phone',
            timestamp=timezone.now()
        )

        result = send_external_message(str(message.id), provider='whatsapp')

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no_phone_number')

    def test_send_external_message_nonexistent_message(self):
        fake_message_id = str(uuid.uuid4())

        result = send_external_message(fake_message_id, provider='whatsapp')

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['reason'], 'message_not_found')

    def test_send_external_message_with_sms_provider(self):
        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=self.conversation,
            direction=MessageDirection.SENT,
            content='SMS message',
            timestamp=timezone.now()
        )

        result = send_external_message(str(message.id), provider='sms')

        self.assertEqual(result['status'], 'sent')
        self.assertEqual(result['provider'], 'sms')

    @patch('webhooks.tasks.MessagingProvider')
    def test_send_external_message_provider_exception_triggers_retry(self, mock_provider_class):
        mock_provider = MagicMock()
        mock_provider.send_message.side_effect = MessagingProviderException('API Error')
        mock_provider_class.return_value = mock_provider

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=self.conversation,
            direction=MessageDirection.SENT,
            content='Message that will fail',
            timestamp=timezone.now()
        )

        with self.assertRaises(Exception):
            from celery import current_app
            current_app.conf.task_always_eager = True
            send_external_message(str(message.id), provider='whatsapp')


class CheckMessageDeliveryStatusTaskTestCase(TestCase):
    def test_check_delivery_status_success(self):
        provider_message_id = 'whatsapp_msg_12345'

        result = check_message_delivery_status(
            provider_message_id,
            provider='whatsapp'
        )

        self.assertEqual(result['provider_message_id'], provider_message_id)
        self.assertIn('status', result)
        self.assertEqual(result['provider'], 'whatsapp')

    def test_check_delivery_status_different_providers(self):
        result_whatsapp = check_message_delivery_status(
            'wa_123',
            provider='whatsapp'
        )
        self.assertEqual(result_whatsapp['provider'], 'whatsapp')

        result_sms = check_message_delivery_status(
            'sms_456',
            provider='sms'
        )
        self.assertEqual(result_sms['provider'], 'sms')

    @patch('webhooks.tasks.MessagingProvider')
    def test_check_delivery_status_error_handling(self, mock_provider_class):
        mock_provider = MagicMock()
        mock_provider.get_message_status.side_effect = Exception('Network error')
        mock_provider_class.return_value = mock_provider

        result = check_message_delivery_status('msg_789', provider='whatsapp')

        self.assertEqual(result['status'], 'error')
        self.assertIn('reason', result)


class MessagingIntegrationTestCase(TestCase):
    def test_complete_message_sending_flow(self):
        contact = Contact.objects.create(
            name='Integration Test',
            phone='+5511999999999',
            email='integration@test.com'
        )

        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN',
            contact=contact
        )

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Integration test message',
            timestamp=timezone.now()
        )

        send_result = send_external_message(str(message.id), provider='whatsapp')

        self.assertEqual(send_result['status'], 'sent')
        self.assertIn('provider_response', send_result)

        provider_message_id = send_result['provider_response']['message_id']

        status_result = check_message_delivery_status(
            provider_message_id,
            provider='whatsapp'
        )

        self.assertIn('status', status_result)
        self.assertEqual(status_result['provider_message_id'], provider_message_id)

    def test_conversation_without_contact_flow(self):
        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN'
        )

        message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.SENT,
            content='Message without contact',
            timestamp=timezone.now()
        )

        result = send_external_message(str(message.id))

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'no_phone_number')

    def test_received_message_not_sent_externally(self):
        contact = Contact.objects.create(
            name='Customer',
            phone='+5511888888888'
        )

        conversation = Conversation.objects.create(
            id=uuid.uuid4(),
            status='OPEN',
            contact=contact
        )

        inbound_message = Message.objects.create(
            id=uuid.uuid4(),
            conversation=conversation,
            direction=MessageDirection.RECEIVED,
            content='Customer inbound message',
            timestamp=timezone.now()
        )

        result = send_external_message(str(inbound_message.id))

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'not_outbound')
