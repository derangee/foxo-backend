"""StockMovement model.

An append-only audit record. Each row captures a single change to a product's
stock: the signed ``quantity_change`` that was applied and the
``resulting_quantity`` after applying it. Rows are never updated or deleted
(immutability is enforced by the service layer, which exposes no such operation).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MovementType

if TYPE_CHECKING:
    from app.models.product import Product


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity_change <> 0", name="ck_stock_movements_quantity_change_nonzero"),
        CheckConstraint(
            "resulting_quantity >= 0", name="ck_stock_movements_resulting_non_negative"
        ),
        # Supports per-product history reads ordered chronologically (Phase 5).
        Index("ix_stock_movements_product_created", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type"), nullable=False
    )
    # Signed effect on stock: positive for RESTOCK, negative for SALE,
    # either sign for ADJUSTMENT. Never zero (enforced by check constraint).
    quantity_change: Mapped[int] = mapped_column(nullable=False)
    # Stock level immediately after this movement was applied.
    resulting_quantity: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    product: Mapped[Product] = relationship(back_populates="movements")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<StockMovement id={self.id} product_id={self.product_id} "
            f"type={self.movement_type} change={self.quantity_change}>"
        )
