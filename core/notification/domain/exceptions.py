"""Notification domain exceptions."""


class NotificationException(Exception):
    """Base exception for notification module."""
    pass


class TemplateNotFoundError(NotificationException):
    """Template not found for given key, channel, language."""
    
    def __init__(self, template_key: str, channel: str = None, language: str = None):
        msg = f"Template not found: {template_key}"
        if channel:
            msg += f" (channel={channel}"
            if language:
                msg += f", language={language}"
            msg += ")"
        super().__init__(msg)


class SenderNotFoundError(NotificationException):
    """Sender not found for given channel or key."""
    
    def __init__(self, channel: str = None, sender_key: str = None):
        if sender_key:
            msg = f"Sender not found: {sender_key}"
        else:
            msg = f"No active sender configured for channel: {channel}"
        super().__init__(msg)


class InvalidTemplateKeyError(NotificationException):
    """Invalid template key format."""
    
    def __init__(self, template_key: str):
        super().__init__(f"Invalid template key format: {template_key}")


class TemplateRenderError(NotificationException):
    """Failed to render template (Jinja2 error)."""
    pass


class NotificationSendError(NotificationException):
    """Failed to send notification via provider."""
    
    def __init__(self, channel: str, recipient: str, reason: str):
        msg = f"Failed to send {channel} to {recipient}: {reason}"
        super().__init__(msg)
