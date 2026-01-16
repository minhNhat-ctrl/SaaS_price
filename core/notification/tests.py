"""Notification module tests."""
import pytest
from django.test import TestCase
from uuid import uuid4

from ..domain.value_objects import Channel, SendCommand, SendStatus
from ..domain.entities import NotificationSender, NotificationTemplate, NotificationLog
from ..domain.exceptions import TemplateNotFoundError, SenderNotFoundError


class NotificationDomainTests(TestCase):
    """Test notification domain entities."""
    
    def test_send_command_validation(self):
        """Test SendCommand validates required fields."""
        # Valid command
        cmd = SendCommand(
            template_key='welcome',
            channel=Channel.EMAIL,
            recipient='test@example.com',
            context={'name': 'John'}
        )
        assert cmd.template_key == 'welcome'
        assert cmd.channel == Channel.EMAIL
    
    def test_template_render_jinja2(self):
        """Test template rendering with Jinja2."""
        template = NotificationTemplate(
            template_key='welcome',
            channel=Channel.EMAIL,
            language='en',
            subject='Welcome {{ name }}!',
            body='Hello {{ name }},\n\nWelcome to our platform.'
        )
        
        context = {'name': 'Alice'}
        
        rendered = template.render({'subject': template.subject}, context)
        assert 'Welcome Alice!' in rendered
    
    def test_notification_log_status_transitions(self):
        """Test notification log status transitions."""
        log = NotificationLog(
            template_key='welcome',
            channel=Channel.EMAIL,
            recipient='test@example.com',
            status=SendStatus.PENDING,
            context={'name': 'Bob'}
        )
        
        assert log.status == SendStatus.PENDING
        log.status = SendStatus.SENT
        assert log.status == SendStatus.SENT


# TODO: Add repository, service, and API tests after integration testing
