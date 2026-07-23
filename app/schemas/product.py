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
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "sku": "WIDGET-001",
                    "name": "Standard Widget",
                    "description": "A dependable widget.",
                    "price": "19.99",
                }
            ]
        },
    )

    sku: str = Field(min_length=1, max_length=64, pattern=SKU_PATTERN)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class ProductUpdate(BaseModel):
    """Partial update. Only provided fields are changed.

    Activation state is not changed here; use the activate/deactivate endpoints.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    expected_version: int | None = Field(
        default=None,
        ge=1,
        description="If provided, the update fails with 409 unless it matches the "
        "product's current version (optimistic locking).",
    )


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    quantity: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
