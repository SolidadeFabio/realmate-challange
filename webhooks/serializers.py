from rest_framework import serializers
from .models import Conversation, Message, MessageDirection


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'direction',
            'content',
            'timestamp',
            'created_at'
        ]
        read_only_fields = ['created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'status',
            'created_at',
            'updated_at',
            'closed_at',
            'messages'
        ]
        read_only_fields = ['created_at', 'updated_at']


class WebhookDataSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    direction = serializers.ChoiceField(
        choices=MessageDirection.choices,
        required=False
    )
    content = serializers.CharField(required=False)
    conversation_id = serializers.UUIDField(required=False)


class WebhookEventSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=[
            ('NEW_CONVERSATION', 'NEW_CONVERSATION'),
            ('NEW_MESSAGE', 'NEW_MESSAGE'),
            ('CLOSE_CONVERSATION', 'CLOSE_CONVERSATION')
        ]
    )
    timestamp = serializers.DateTimeField()
    data = WebhookDataSerializer()

    def validate(self, attrs):
        event_type = attrs['type']
        data = attrs.get('data', {})

        if event_type == 'NEW_CONVERSATION':
            # Only id is required
            if any(key in data for key in ['direction', 'content', 'conversation_id']):
                raise serializers.ValidationError(
                    "NEW_CONVERSATION should only contain 'id' field"
                )

        elif event_type == 'NEW_MESSAGE':
            required_fields = ['direction', 'content', 'conversation_id']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise serializers.ValidationError(
                    f"NEW_MESSAGE requires these fields: {', '.join(missing_fields)}"
                )

        elif event_type == 'CLOSE_CONVERSATION':
            if any(key in data for key in ['direction', 'content', 'conversation_id']):
                raise serializers.ValidationError(
                    "CLOSE_CONVERSATION should only contain 'id' field"
                )

        return attrs