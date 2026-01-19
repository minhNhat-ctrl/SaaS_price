"""Business flow contracts - Protocol definitions for business operations."""
from __future__ import annotations

from typing import Protocol

from ..dto.product import CreateProductCommand, CreateProductResult


class CreateProductHandler(Protocol):
    """Handler for product creation."""
    
    def __call__(self, command: CreateProductCommand) -> CreateProductResult:
        """Create a product."""
        ...
