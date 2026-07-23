"""Stock-movement DTOs.

Request semantics per movement type:
- RESTOCK / SALE take a positive ``quantity`` magnitude; the service applies the
  correct sign (+ for restock, - for sale).
- ADJUSTMENT takes a signed, non-zero ``quantity_change`` and a mandatory reason.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import MovementType

_MAX_QUANTITY = 1_000_000


class QuantityMovementRequest(BaseModel):
    """Payload for RESTOCK and SALE (positive magnitude)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    quantity: int = Field(gt=0, le=_MAX_QUANTITY, description="Positive quantity magnitude")
    reason: str | None = Field(default=None, max_length=500)


class AdjustmentRequest(BaseModel):
    """Payload for ADJUSTMENT (signed change, reason required)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    quantity_change: int = Field(
        description="Signed, non-zero change to apply to stock (e.g. -3 or +10)"
    )
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("quantity_change")
    @classmethod
    def _reject_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_change must not be zero")
        return value


class MovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    movement_type: MovementType
    quantity_change: int
    resulting_quantity: int
    reason: str | None
    created_at: datetime
