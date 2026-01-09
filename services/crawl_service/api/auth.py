"""
API Authentication for Crawl Service

Verify bot_id and api_token from BotConfig
"""

from rest_framework.response import Response
from rest_framework import status
from ..models import BotConfig
import logging

logger = logging.getLogger(__name__)


def authenticate_bot(bot_id: str, api_token: str) -> tuple[bool, dict]:
    """
    Authenticate bot using bot_id and api_token.
    
    Args:
        bot_id: Bot identifier from request
        api_token: API token from request
    
    Returns:
        (is_authenticated: bool, bot_config_or_error: BotConfig or error_response_dict)
    
    Example:
        is_auth, result = authenticate_bot(request_data['bot_id'], request_data.get('api_token', ''))
        if not is_auth:
            return Response(result, status=result.get('status'))
        bot_config = result
    """
    # Validate inputs
    if not bot_id or not api_token:
        return False, {
            'success': False,
            'error': 'authentication_error',
            'detail': 'Missing bot_id or api_token',
            'status': status.HTTP_401_UNAUTHORIZED
        }
    
    bot_id = bot_id.strip()
    api_token = api_token.strip()
    
    # Find bot by bot_id
    try:
        bot_config = BotConfig.objects.get(bot_id=bot_id)
    except BotConfig.DoesNotExist:
        logger.warning(f"Authentication failed: bot_id '{bot_id}' not found")
        return False, {
            'success': False,
            'error': 'authentication_error',
            'detail': f'Bot "{bot_id}" not found',
            'status': status.HTTP_401_UNAUTHORIZED
        }
    
    # Check if bot is enabled
    if not bot_config.enabled:
        logger.warning(f"Authentication failed: bot_id '{bot_id}' is disabled")
        return False, {
            'success': False,
            'error': 'authentication_error',
            'detail': f'Bot "{bot_id}" is disabled',
            'status': status.HTTP_403_FORBIDDEN
        }
    
    # Verify API token
    if not bot_config.api_token:
        logger.warning(f"Authentication failed: bot_id '{bot_id}' has no API token configured")
        return False, {
            'success': False,
            'error': 'authentication_error',
            'detail': f'Bot "{bot_id}" has no API token configured',
            'status': status.HTTP_401_UNAUTHORIZED
        }
    
    if api_token != bot_config.api_token:
        logger.warning(f"Authentication failed: invalid api_token for bot_id '{bot_id}'")
        return False, {
            'success': False,
            'error': 'authentication_error',
            'detail': 'Invalid api_token',
            'status': status.HTTP_401_UNAUTHORIZED
        }
    
    # Authentication successful
    logger.info(f"Bot authenticated: {bot_id}")
    return True, bot_config


def auth_error_response(error_dict: dict):
    """Create error response from auth error dict."""
    status_code = error_dict.pop('status', status.HTTP_401_UNAUTHORIZED)
    return Response(error_dict, status=status_code)
