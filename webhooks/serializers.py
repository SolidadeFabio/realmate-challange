from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Conversation, Message, MessageDirection, Contact


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'phone', 'email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    author_user = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'direction',
            'content',
            'timestamp',
            'author_user',
            'is_internal',
            'created_at'
        ]
        read_only_fields = ['created_at', 'author_user']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    assigned_user = UserSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'status',
            'contact',
            'assigned_user',
            'created_at',
            'updated_at',
            'closed_at',
            'messages'
        ]
        read_only_fields = ['created_at', 'updated_at', 'contact', 'assigned_user']


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)
    assigned_user = UserSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'status',
            'contact',
            'assigned_user',
            'created_at',
            'updated_at',
            'closed_at',
            'message_count',
            'last_message'
        ]
        read_only_fields = ['created_at', 'updated_at', 'contact', 'assigned_user']

    def get_last_message(self, obj):
        last_message = obj.messages.filter(is_internal=False).order_by('-timestamp').first()
        if last_message:
            return MessageSerializer(last_message).data
        return None

    def get_message_count(self, obj):
        return obj.messages.filter(is_internal=False).count()


class WebhookDataSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    direction = serializers.ChoiceField(
        choices=MessageDirection.choices,
        required=False
    )
    content = serializers.CharField(required=False, allow_blank=False)
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

            content = data.get('content', '')
            if not content or not content.strip():
                raise serializers.ValidationError(
                    "Message content cannot be empty or contain only whitespace"
                )

        elif event_type == 'CLOSE_CONVERSATION':
            if any(key in data for key in ['direction', 'content', 'conversation_id']):
                raise serializers.ValidationError(
                    "CLOSE_CONVERSATION should only contain 'id' field"
                )

        return attrs