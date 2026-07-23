"""Business logic for stock movements.

Every movement is applied atomically: the product's ``quantity`` is updated and
an immutable movement record is written in the same transaction. Concurrent
movements against the same product are serialized with a row-level lock, so the
read-modify-write of the quantity cannot lose updates or oversell.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientStockError, ProductNotFoundError
from app.models.enums import MovementType
from app.models.stock_movement import StockMovement
from app.repositories.product import ProductRepository
from app.repositories.stock_movement import StockMovementRepository


class StockMovementService:
    def __init__(
        self,
        session: AsyncSession,
        product_repository: ProductRepository,
        movement_repository: StockMovementRepository,
    ):
        self._session = session
        self._products = product_repository
        self._movements = movement_repository

    async def restock(
        self, product_id: int, quantity: int, reason: str | None = None
    ) -> StockMovement:
        return await self._apply_movement(product_id, MovementType.RESTOCK, quantity, reason)

    async def sell(
        self, product_id: int, quantity: int, reason: str | None = None
    ) -> StockMovement:
        # SALE removes stock: the magnitude is applied as a negative change.
        return await self._apply_movement(product_id, MovementType.SALE, -quantity, reason)

    async def adjust(self, product_id: int, quantity_change: int, reason: str) -> StockMovement:
        return await self._apply_movement(
            product_id, MovementType.ADJUSTMENT, quantity_change, reason
        )

    async def _apply_movement(
        self,
        product_id: int,
        movement_type: MovementType,
        quantity_change: int,
        reason: str | None,
    ) -> StockMovement:
        # Lock the product row for the duration of the transaction.
        product = await self._products.get_for_update(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)

        # Capture the pre-movement quantity as a plain int so error reporting
        # never touches the ORM object after a rollback (which would expire it).
        previous_quantity = product.quantity
        requested = abs(quantity_change)
        new_quantity = previous_quantity + quantity_change
        if new_quantity < 0:
            raise InsufficientStockError(
                product_id, available=previous_quantity, requested=requested
            )

        product.quantity = new_quantity
        movement = StockMovement(
            product_id=product.id,
            movement_type=movement_type,
            quantity_change=quantity_change,
            resulting_quantity=new_quantity,
            reason=reason,
        )
        self._movements.add(movement)

        try:
            await self._session.commit()
        except IntegrityError as exc:
            # Backstop: if a concurrent movement slipped past the in-memory check,
            # the non-negative CHECK constraint rejects it here.
            await self._session.rollback()
            raise InsufficientStockError(
                product_id, available=previous_quantity, requested=requested
            ) from exc

        await self._session.refresh(movement)
        return movement
