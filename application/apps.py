"""Application configuration and initialization."""
from django.apps import AppConfig


class ApplicationConfig(AppConfig):
    """
    Application layer configuration.
    
    Responsible for:
    - Orchestrating multi-module flows
    - Managing DTOs and response contracts
    - Initializing runtime toggles
    - Exposing HTTP/CLI/Celery interfaces
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'application'
    verbose_name = 'Application Layer - Orchestration & Adapters'

    def ready(self):
        """
        Initialize application layer components.
        
        This runs after all apps are loaded. We wire up:
        - Flow instances with handlers from core modules
        - Flow rule toggles
        - API adapters
        """
        # Import here to avoid circular imports
        from .api.provisioning.providers import create_onboarding_flow, set_onboarding_flow

        # For now, create with minimal handlers (actual handlers will be wired by modules)
        # This allows the application to load even if module handlers aren't ready
        try:
            # Create onboarding flow with placeholder handler
            # In production, wire actual handlers from core modules
            flow = create_onboarding_flow(
                signup_handler=self._default_signup_handler,
            )
            set_onboarding_flow(flow)
        except Exception as e:
            # Log but don't fail - app should still load
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize onboarding flow: {e}")

    @staticmethod
    def _default_signup_handler(cmd):
        """
        Placeholder signup handler (for development/testing).
        
        In production, replace with actual handler from core.identity module:
        from core.identity.services.providers import get_signup_handler
        """
        from application.dto.identity import SignupResult
        import uuid
        
        # Temporary mock response for testing
        return SignupResult(
            user_id=str(uuid.uuid4()),
            verify_required=True
        )
