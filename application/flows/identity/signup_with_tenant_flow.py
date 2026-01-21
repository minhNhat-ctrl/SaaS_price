"""
Signup flow with optional auto-tenant creation.

This flow coordinates:
1. User signup (create account)
2. Email verification (optional)
3. Auto-tenant creation (optional)
4. Onboarding (optional - welcome email, sample data)
"""
from dataclasses import dataclass
from typing import Optional
import yaml
from pathlib import Path

from ...dto.identity import SignupCommand, SignupContext
from ...services.flow_context import FlowContext


@dataclass
class SignupFlowConfig:
    """Configuration for signup flow loaded from YAML."""
    
    email_verification_enabled: bool
    auto_create_tenant_enabled: bool
    tenant_slug_pattern: str
    tenant_name_pattern: str
    plan_code: str
    auto_activate_tenant: bool
    welcome_email_enabled: bool
    require_email_verified_to_signin: bool
    
    @classmethod
    def load_from_yaml(cls) -> "SignupFlowConfig":
        """Load configuration from identity.yaml."""
        config_path = Path(__file__).parent.parent.parent / "config" / "identity.yaml"
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        identity_config = config.get("identity", {})
        access_config = config.get("access", {})
        
        return cls(
            email_verification_enabled=identity_config.get("email_verification", {}).get("enabled", True),
            auto_create_tenant_enabled=access_config.get("auto_create_tenant", {}).get("enabled", True),
            tenant_slug_pattern=access_config.get("auto_create_tenant", {}).get("tenant_slug_pattern", "{email_prefix}-{uuid4_short}"),
            tenant_name_pattern=access_config.get("auto_create_tenant", {}).get("tenant_name_pattern", "{email_prefix} Workspace"),
            plan_code=access_config.get("auto_create_tenant", {}).get("plan_code", "free"),
            auto_activate_tenant=access_config.get("auto_create_tenant", {}).get("auto_activate", True),
            welcome_email_enabled=identity_config.get("welcome_email", {}).get("enabled", True),
            require_email_verified_to_signin=identity_config.get("signin", {}).get("require_email_verified", True),
        )


@dataclass
class SignupWithTenantFlow:
    """
    Flow: User Signup with Optional Auto-Tenant Creation
    
    Steps (configurable):
        1. Create user account (identity module)
        2. Send verification email (if enabled)
        3. Auto-create tenant (if enabled)
        4. Assign default role (if enabled)
        5. Send welcome email (if enabled)
    
    Configuration:
        - auto_create_tenant.enabled: true/false
        - email_verification.enabled: true/false
        - welcome_email.send_on_verify: true/false
        - access.default_role.assign_on_signup: true/false
    """
    
    signup_handler=None              # core.identity.services.SignupService
    verification_handler=None        # core.notification.services.EmailService
    tenant_handler=None              # core.tenants.services.TenantService
    access_handler=None              # core.access.services.MembershipService
    config: Optional[SignupFlowConfig] = None
    
    def __post_init__(self):
        """Load config if not provided."""
        if self.config is None:
            self.config = SignupFlowConfig.load_from_yaml()
    
    def execute(self, command: SignupCommand) -> FlowContext:
        """Execute signup flow with auto-tenant creation."""
        context = FlowContext(flow_code="identity.signup_with_tenant")
        
        # Step 1: Create user account
        context = self._execute_create_user_step(context, command)
        if context.get_meta("error"):
            return context
        
        # Step 2: Send verification email (if enabled)
        if self.config.email_verification_enabled:
            context = self._execute_send_verification_step(context)
        
        # Step 3: Auto-create tenant (if enabled)
        if self.config.auto_create_tenant_enabled:
            context = self._execute_create_tenant_step(context)
        
        # Step 4: Assign default role (if enabled)
        # TODO: Check access config
        context = self._execute_assign_role_step(context)
        
        # Step 5: Send welcome email (if enabled)
        if self.config.welcome_email_enabled:
            context = self._execute_send_welcome_email_step(context)
        
        return context
    
    def _execute_create_user_step(self, context: FlowContext, command: SignupCommand) -> FlowContext:
        """Step 1: Create user account via identity module."""
        # TODO: Import and call identity service
        # from core.identity.services.providers import get_signup_service
        # signup_service = self.signup_handler or get_signup_service()
        # user = signup_service.create_user(email=command.email, password=command.password)
        # context.user_id = user.id
        # context.metadata["user_created_at"] = user.created_at
        
        # Placeholder for now
        import uuid
        context.user_id = str(uuid.uuid4())
        context.set_meta("user_created_at", "2026-01-20T00:00:00Z")
        context.set_meta("step", "user_created")
        
        return context
    
    def _execute_send_verification_step(self, context: FlowContext) -> FlowContext:
        """Step 2: Send email verification."""
        # TODO: Import and call notification service
        # from core.notification.services.providers import get_email_service
        # email_service = self.verification_handler or get_email_service()
        # token = email_service.send_verification_email(
        #     user_id=context.user_id,
        #     email=...,
        #     template_key=...,
        #     sender_key=...
        # )
        # context.set_meta("verification_token", token)
        # context.set_meta("verification_sent_at", ...)
        
        context.set_meta("verification_sent", True)
        context.set_meta("step", "verification_email_sent")
        return context
    
    def _execute_create_tenant_step(self, context: FlowContext) -> FlowContext:
        """Step 3: Auto-create tenant."""
        # TODO: Import and call tenants service
        # from core.tenants.services.providers import get_tenant_service
        # tenant_service = self.tenant_handler or get_tenant_service()
        #
        # slug = self._generate_tenant_slug(context.user_id)
        # name = self._generate_tenant_name(slug)
        #
        # tenant = tenant_service.create_tenant(
        #     owner_user_id=context.user_id,
        #     slug=slug,
        #     name=name,
        #     plan_code=self.config.plan_code,
        # )
        # context.tenant_id = tenant.id
        # context.set_meta("tenant_auto_created", True)
        # context.set_meta("tenant_created_at", tenant.created_at)
        #
        # if self.config.auto_activate_tenant:
        #     tenant_service.activate_tenant(tenant.id)
        #     context.set_meta("tenant_activated", True)
        
        context.tenant_id = str(__import__("uuid").uuid4())
        context.set_meta("tenant_auto_created", True)
        context.set_meta("step", "tenant_created")
        
        return context
    
    def _execute_assign_role_step(self, context: FlowContext) -> FlowContext:
        """Step 4: Assign default role to user in tenant."""
        # TODO: Import and call access service
        # from core.access.services.providers import get_membership_service
        # membership_service = self.access_handler or get_membership_service()
        # membership_service.assign_role(
        #     tenant_id=context.tenant_id,
        #     user_id=context.user_id,
        #     role_slug="admin",  # From config
        # )
        # context.set_meta("role_assigned", True)
        
        context.set_meta("role_assigned", True)
        context.set_meta("step", "role_assigned")
        
        return context
    
    def _execute_send_welcome_email_step(self, context: FlowContext) -> FlowContext:
        """Step 5: Send welcome email."""
        # TODO: Import and call notification service
        # from core.notification.services.providers import get_email_service
        # email_service = self.verification_handler or get_email_service()
        # email_service.send_welcome_email(
        #     user_id=context.user_id,
        #     email=...,
        #     tenant_name=context.get_meta("tenant_name"),
        #     template_key="welcome_email",
        #     sender_key="sendgrid_primary",
        # )
        
        context.set_meta("welcome_email_sent", True)
        context.set_meta("step", "welcome_email_sent")
        
        return context
    
    def _generate_tenant_slug(self, user_id: str) -> str:
        """Generate tenant slug from pattern and user data."""
        # TODO: Extract email prefix and generate slug
        # Pattern: {email_prefix}-{uuid4_short}
        # Example: "john.doe-a1b2c3d4"
        
        import uuid
        uuid_short = str(uuid.uuid4())[:8]
        slug = f"tenant-{uuid_short}"
        return slug
    
    def _generate_tenant_name(self, slug: str) -> str:
        """Generate tenant name from pattern."""
        # Pattern: {email_prefix} Workspace
        # Example: "john.doe Workspace"
        
        return f"{slug} Workspace"
