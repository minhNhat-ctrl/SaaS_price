"""Flow context for managing state across flow steps."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class FlowContext:
    """
    Universal context for managing state across multi-step flows.
    
    Acts as a shared state bag that flows can use to accumulate
    data as they execute steps. Supports metadata for ad-hoc data.
    """
    
    # Core identifiers
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Subscription/billing
    plan_code: Optional[str] = None
    subscription_status: Optional[str] = None
    quote_id: Optional[str] = None
    requires_payment: bool = False
    
    # Business entities
    product_id: Optional[str] = None
    
    # Flexible metadata for domain-specific data
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def set_meta(self, key: str, value: Any) -> FlowContext:
        """Set a metadata value (immutable-style)."""
        self.metadata[key] = value
        return self
    
    def get_meta(self, key: str, default: Any = None) -> Any:
        """Get a metadata value."""
        return self.metadata.get(key, default)
