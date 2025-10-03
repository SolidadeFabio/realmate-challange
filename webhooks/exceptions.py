class WebhookException(Exception):
    """Base exception for webhook-related errors"""
    pass


class ConversationNotFoundException(WebhookException):
    """Raised when a conversation is not found"""
    pass


class ConversationClosedException(WebhookException):
    """Raised when trying to add messages to a closed conversation"""
    pass


class InvalidWebhookDataException(WebhookException):
    """Raised when webhook data is invalid or malformed"""
    pass


class DuplicateEntityException(WebhookException):
    """Raised when trying to create a duplicate entity"""
    pass