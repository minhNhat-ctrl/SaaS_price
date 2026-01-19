"""Product domain DTOs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateProductCommand:
    """Command to create a product."""
    name: str
    url: str
    tenant_id: str


@dataclass(frozen=True)
class CreateProductResult:
    """Result of product creation."""
    product_id: str
    status: str
