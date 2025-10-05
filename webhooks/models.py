import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class ConversationStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'


class MessageDirection(models.TextChoices):
    SENT = 'SENT', 'Sent'
    RECEIVED = 'RECEIVED', 'Received'


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contacts'
        ordering = ['-created_at']

    def __str__(self):
        return self.name or self.phone or str(self.id)


class Conversation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    status = models.CharField(
        max_length=10,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN
    )
    contact = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conversations'
    )
    assigned_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_conversations'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'conversations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Conversation {self.id} ({self.status})"

    def is_open(self):
        return self.status == ConversationStatus.OPEN

    def is_closed(self):
        return self.status == ConversationStatus.CLOSED



class Message(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    direction = models.CharField(
        max_length=10,
        choices=MessageDirection.choices,
    )
    content = models.TextField()
    timestamp = models.DateTimeField()
    author_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='authored_messages'
    )
    is_internal = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['direction']),
        ]

    def __str__(self):
        return f"Message {self.id} in {self.conversation_id} ({self.direction})"

    def clean(self):
        """Validate that message can be added to conversation"""
        if self.conversation and not self.conversation.is_open():
            raise ValidationError(
                "Cannot add messages to a closed conversation"
            )
