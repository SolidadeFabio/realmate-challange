import uuid
import random
import time
from datetime import datetime, timedelta
from celery import shared_task, group
from django.utils import timezone
import logging

from .services import ConversationService, MessageService
from .models import MessageDirection, Message
from .messaging_service import MessagingProvider, MessagingProviderException

logger = logging.getLogger(__name__)

CUSTOMER_MESSAGES = [
    "Olá, tudo bem?",
    "Oi, boa tarde!",
    "Preciso de ajuda com meu pedido",
    "Qual o status da minha compra?",
    "O produto chegou com defeito",
    "Gostaria de fazer uma reclamação",
    "Como faço para rastrear meu pedido?",
    "Vocês trabalham com entrega expressa?",
    "Qual o prazo de entrega para minha região?",
    "Posso trocar o produto?",
    "O boleto não está aparecendo",
    "Não consigo finalizar a compra",
    "Vocês tem esse produto em estoque?",
    "Qual a política de devolução?",
    "Meu pedido ainda não chegou",
    "Preciso cancelar minha compra",
    "Como faço para parcelar?",
    "Vocês aceitam PIX?",
    "Tem desconto para pagamento à vista?",
    "Quando vai ter promoção?",
    "O produto está disponível em outras cores?",
    "Qual a garantia do produto?",
    "Como funciona a troca?",
    "Vocês emitem nota fiscal?",
    "Posso retirar na loja?",
    "Muito obrigado pela ajuda!",
    "Ok, entendi",
    "Perfeito, vou aguardar",
    "Certo, pode me ajudar?",
    "Sim, é isso mesmo",
]

SUPPORT_MESSAGES = [
    "Olá! Como posso ajudar você hoje?",
    "Boa tarde! Sou do atendimento. Em que posso ser útil?",
    "Claro! Vou verificar isso para você.",
    "Deixe-me consultar seu pedido no sistema.",
    "Um momento, por favor. Estou verificando.",
    "Seu pedido foi localizado. Status: em transporte.",
    "Lamento pelo inconveniente. Vamos resolver isso.",
    "Posso abrir uma solicitação de troca para você.",
    "O prazo de entrega é de 3 a 5 dias úteis.",
    "Sim, trabalhamos com entrega expressa por um custo adicional.",
    "Vou gerar um novo boleto para você.",
    "Pode tentar limpar o cache do navegador?",
    "Sim, o produto está disponível em estoque.",
    "Nossa política permite trocas em até 30 dias.",
    "Vejo que houve um atraso na transportadora.",
    "Cancelamento realizado com sucesso!",
    "Você pode parcelar em até 12x sem juros.",
    "Sim, aceitamos PIX com 5% de desconto.",
    "Para pagamento à vista oferecemos 10% de desconto.",
    "Nossa próxima promoção será na Black Friday.",
    "Disponível nas cores: preto, branco e azul.",
    "Todos os produtos têm garantia de 1 ano.",
    "Para trocar, acesse nossa central de trocas no site.",
    "A nota fiscal é enviada por e-mail após a confirmação.",
    "Sim, você pode retirar em nossa loja do centro.",
    "Por nada! Estamos sempre à disposição.",
    "Algo mais em que posso ajudar?",
    "Agradeço a compreensão!",
    "Vou processar isso imediatamente.",
    "Confirmado! Já está tudo certo.",
]


@shared_task
def create_single_conversation(base_timestamp=None):
    if base_timestamp is None:
        base_timestamp = timezone.now()
    else:
        base_timestamp = datetime.fromisoformat(base_timestamp)

    conversation_service = ConversationService()
    message_service = MessageService()

    conversation_id = str(uuid.uuid4())

    try:
        conversation_service.create_conversation(conversation_id, base_timestamp)
        logger.info(f"Created conversation {conversation_id}")

        num_messages = random.randint(3, 15)
        current_time = base_timestamp

        customer_messages = random.sample(CUSTOMER_MESSAGES, min(len(CUSTOMER_MESSAGES), num_messages//2 + 1))
        support_messages = random.sample(SUPPORT_MESSAGES, min(len(SUPPORT_MESSAGES), num_messages//2 + 1))

        direction = MessageDirection.RECEIVED

        for i in range(num_messages):
            time.sleep(random.uniform(0.1, 0.5))

            current_time += timedelta(seconds=random.randint(30, 180))
            message_id = str(uuid.uuid4())

            if direction == MessageDirection.RECEIVED:
                content = customer_messages.pop(0) if customer_messages else "Obrigado!"
            else:
                content = support_messages.pop(0) if support_messages else "De nada, estamos à disposição!"

            message_service.create_message(
                message_id=message_id,
                conversation_id=conversation_id,
                direction=direction,
                content=content,
                timestamp=current_time
            )

            direction = MessageDirection.SENT if direction == MessageDirection.RECEIVED else MessageDirection.RECEIVED

        if random.random() > 0.3:
            time.sleep(random.uniform(0.5, 2))
            current_time += timedelta(seconds=random.randint(60, 300))
            conversation_service.close_conversation(conversation_id, current_time)
            logger.info(f"Closed conversation {conversation_id}")

        return {'conversation_id': conversation_id, 'messages': num_messages, 'status': 'completed'}

    except Exception as e:
        logger.error(f"Error creating conversation {conversation_id}: {str(e)}")
        return {'conversation_id': conversation_id, 'error': str(e), 'status': 'failed'}


@shared_task
def simulate_conversation_flow(conversation_id, num_messages=10):
    message_service = MessageService()
    current_time = timezone.now()

    customer_messages = random.sample(CUSTOMER_MESSAGES, min(len(CUSTOMER_MESSAGES), num_messages//2 + 1))
    support_messages = random.sample(SUPPORT_MESSAGES, min(len(SUPPORT_MESSAGES), num_messages//2 + 1))

    direction = MessageDirection.RECEIVED
    messages_created = 0

    for i in range(num_messages):
        time.sleep(random.uniform(1, 3))

        current_time += timedelta(seconds=random.randint(15, 60))
        message_id = str(uuid.uuid4())

        try:
            if direction == MessageDirection.RECEIVED:
                content = customer_messages.pop(0) if customer_messages else "..."
            else:
                content = support_messages.pop(0) if support_messages else "..."

            message_service.create_message(
                message_id=message_id,
                conversation_id=conversation_id,
                direction=direction,
                content=content,
                timestamp=current_time
            )
            messages_created += 1

            direction = MessageDirection.SENT if direction == MessageDirection.RECEIVED else MessageDirection.RECEIVED

        except Exception as e:
            logger.error(f"Error creating message in conversation {conversation_id}: {str(e)}")
            break

    return {'conversation_id': conversation_id, 'messages_created': messages_created}


@shared_task
def create_conversation_batch(num_conversations=10, start_time=None):
    if start_time is None:
        start_time = timezone.now() - timedelta(hours=2)
    else:
        start_time = datetime.fromisoformat(start_time)

    tasks = []
    for i in range(num_conversations):
        offset_minutes = random.randint(0, 120)
        timestamp = start_time + timedelta(minutes=offset_minutes)

        tasks.append(create_single_conversation.si(timestamp.isoformat()))

    job = group(tasks)
    result = job.apply_async()

    return {
        'batch_size': num_conversations,
        'task_id': result.id,
        'status': 'dispatched'
    }


@shared_task
def simulate_peak_hour(duration_minutes=60, conversations_per_minute=5):
    start_time = timezone.now()
    end_time = start_time + timedelta(minutes=duration_minutes)
    current_time = start_time

    total_conversations = 0

    while current_time < end_time:
        num_conversations = random.randint(
            max(1, conversations_per_minute - 2),
            conversations_per_minute + 2
        )

        for _ in range(num_conversations):
            create_single_conversation.delay(current_time.isoformat())
            total_conversations += 1

        time.sleep(60)
        current_time += timedelta(minutes=1)

    return {
        'duration_minutes': duration_minutes,
        'total_conversations': total_conversations,
        'average_per_minute': total_conversations / duration_minutes
    }


@shared_task(bind=True, max_retries=3)
def send_external_message(self, message_id: str, provider: str = 'whatsapp'):
    try:
        message = Message.objects.get(id=message_id)

        if not message.conversation.contact or not message.conversation.contact.phone:
            logger.warning(
                f"Message {message_id} has no recipient phone number. Skipping external delivery."
            )
            return {
                'message_id': str(message_id),
                'status': 'skipped',
                'reason': 'no_phone_number'
            }

        if message.direction != MessageDirection.SENT:
            logger.info(
                f"Message {message_id} is RECEIVED, not sending externally."
            )
            return {
                'message_id': str(message_id),
                'status': 'skipped',
                'reason': 'not_outbound'
            }

        messaging_provider = MessagingProvider(provider=provider)

        logger.info(
            f"Sending message {message_id} to {message.conversation.contact.phone} "
            f"via {provider}"
        )

        response = messaging_provider.send_message(
            phone=message.conversation.contact.phone,
            content=message.content,
            message_type='text',
            metadata={
                'conversation_id': str(message.conversation_id),
                'message_id': str(message.id),
                'timestamp': message.timestamp.isoformat()
            }
        )

        logger.info(
            f"Message {message_id} sent successfully. "
            f"Provider message_id: {response.get('message_id')}"
        )

        return {
            'message_id': str(message_id),
            'status': 'sent',
            'provider_response': response,
            'provider': provider
        }

    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found in database")
        return {
            'message_id': str(message_id),
            'status': 'error',
            'reason': 'message_not_found'
        }

    except MessagingProviderException as e:
        logger.error(
            f"Provider error sending message {message_id}: {str(e)}"
        )

        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries * 60,
            max_retries=3
        )

    except Exception as e:
        logger.exception(
            f"Unexpected error sending message {message_id}: {str(e)}"
        )
        return {
            'message_id': str(message_id),
            'status': 'error',
            'reason': str(e)
        }


@shared_task
def check_message_delivery_status(provider_message_id: str, provider: str = 'whatsapp'):
    try:
        messaging_provider = MessagingProvider(provider=provider)

        logger.info(
            f"Checking delivery status for {provider_message_id} on {provider}"
        )

        # TODO: Implement actual status checking
        status_info = messaging_provider.get_message_status(provider_message_id)

        logger.info(
            f"Status for {provider_message_id}: {status_info.get('status')}"
        )

        return {
            'provider_message_id': provider_message_id,
            'status': status_info.get('status'),
            'timestamp': status_info.get('timestamp'),
            'provider': provider
        }

    except Exception as e:
        logger.error(
            f"Error checking status for {provider_message_id}: {str(e)}"
        )
        return {
            'provider_message_id': provider_message_id,
            'status': 'error',
            'reason': str(e)
        }
