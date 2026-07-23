"""Product model.

``quantity`` is the authoritative on-hand stock level, kept denormalized on the
product for O(1) reads. Every change to it is recorded as an immutable
``StockMovement``, so the movement log is a full audit trail and the two can be
reconciled. Non-negative stock and price are enforced at the database level as a
backstop to the service-layer business rules.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.stock_movement import StockMovement


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_products_quantity_non_negative"),
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    quantity: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Optimistic-lock counter: SQLAlchemy increments it on every UPDATE and adds
    # "WHERE version = <old>" so a concurrent write is detected (StaleDataError).
    version: Mapped[int] = mapped_column(nullable=False, server_default=text("1"))

    movements: Mapped[list[StockMovement]] = relationship(
        back_populates="product",
        # No delete cascade: products with movement history must not be deleted
        # (enforced by the FK's RESTRICT and the service layer).
        passive_deletes="all",
    )

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Product id={self.id} sku={self.sku!r} qty={self.quantity}>"
