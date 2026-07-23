"""Data-access layer for stock movements.

Movements are append-only, so the repository exposes creation and read access,
but no update or delete. Like the product repository, it never commits: the
service owns the transaction.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MovementType
from app.models.stock_movement import StockMovement


class StockMovementRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def add(self, movement: StockMovement) -> None:
        self._session.add(movement)

    async def list_by_product(
        self,
        product_id: int,
        *,
        limit: int,
        offset: int,
        movement_type: MovementType | None = None,
        ascending: bool = False,
    ) -> tuple[Sequence[StockMovement], int]:
        query = select(StockMovement).where(StockMovement.product_id == product_id)
        if movement_type is not None:
            query = query.where(StockMovement.movement_type == movement_type)

        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))

        # Order by created_at with id as a stable tie-breaker (timestamps can
        # collide for movements committed in the same instant).
        if ascending:
            ordered = query.order_by(StockMovement.created_at.asc(), StockMovement.id.asc())
        else:
            ordered = query.order_by(StockMovement.created_at.desc(), StockMovement.id.desc())

        result = await self._session.execute(ordered.limit(limit).offset(offset))
        return result.scalars().all(), int(total or 0)
