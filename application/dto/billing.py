"""Billing domain DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateQuoteResult:
    """Result of quote creation."""
    quote_id: str
    amount: float
    currency: str


@dataclass(frozen=True)
class ChargePaymentResult:
    """Result of payment charge."""
    success: bool
    transaction_id: Optional[str]
