"""Product DTOs (request/response schemas).

Note: stock ``quantity`` is intentionally absent from create/update payloads.
It is owned by the stock-movement workflow so the movement ledger stays the
single source of truth for inventory levels.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# SKUs are business keys: uppercase-friendly, no spaces.
SKU_PATTERN = r"^[A-Za-z0-9._-]+$"


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=64, pattern=SKU_PATTERN)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class ProductUpdate(BaseModel):
    """Partial update. Only provided fields are changed."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
