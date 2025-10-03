import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Conversation
from .serializers import (
    ConversationSerializer,
    WebhookEventSerializer
)
from .services import WebhookProcessor
from .exceptions import (
    ConversationNotFoundException,
    ConversationClosedException,
    InvalidWebhookDataException,
    DuplicateEntityException
)

logger = logging.getLogger(__name__)


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
