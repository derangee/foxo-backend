"""Data-access layer for stock movements.

Movements are append-only, so the repository exposes creation and (from Phase 5)
read access, but no update or delete. Like the product repository, it never
commits: the service owns the transaction.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_movement import StockMovement


class StockMovementRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def add(self, movement: StockMovement) -> None:
        self._session.add(movement)
