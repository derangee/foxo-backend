"""Business logic for products.

The service owns transaction boundaries (commit/rollback) and translates
database-level integrity failures into meaningful domain exceptions. Stock
``quantity`` is deliberately not settable here; it changes only through the
stock-movement workflow.
"""

from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.exceptions import (
    DuplicateSKUError,
    OptimisticLockError,
    ProductHasMovementsError,
    ProductNotFoundError,
)
from app.models.product import Product
from app.repositories.product import ProductRepository
from app.repositories.stock_movement import StockMovementRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ProductRepository,
        movement_repository: StockMovementRepository,
    ):
        self._session = session
        self._repository = repository
        self._movements = movement_repository

    async def create(self, payload: ProductCreate) -> Product:
        product = Product(
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            price=payload.price,
        )
        self._repository.add(product)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateSKUError(payload.sku) from exc

        await self._session.refresh(product)
        return product

    async def get(self, product_id: int) -> Product:
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    async def list(
        self, *, page: int, size: int, active_only: bool = False
    ) -> tuple[Sequence[Product], int]:
        offset = (page - 1) * size
        return await self._repository.list(limit=size, offset=offset, active_only=active_only)

    async def update(self, product_id: int, payload: ProductUpdate) -> Product:
        product = await self.get(product_id)
        changes = payload.model_dump(exclude_unset=True)
        expected_version = changes.pop("expected_version", None)

        if expected_version is not None and product.version != expected_version:
            raise OptimisticLockError(product_id, expected=expected_version, actual=product.version)

        for field, value in changes.items():
            setattr(product, field, value)

        try:
            await self._session.commit()
        except StaleDataError as exc:
            # A concurrent transaction updated the row between our read and write.
            await self._session.rollback()
            raise OptimisticLockError(product_id, expected=expected_version) from exc

        await self._session.refresh(product)
        return product

    async def set_active(self, product_id: int, active: bool) -> Product:
        """Activate or deactivate a product. Idempotent."""
        product = await self.get(product_id)
        if product.is_active != active:
            product.is_active = active
            await self._session.commit()
            await self._session.refresh(product)
        return product

    async def delete(self, product_id: int) -> None:
        product = await self.get(product_id)

        # A product with movement history must not be deleted; deactivate instead.
        if await self._movements.exists_for_product(product_id):
            raise ProductHasMovementsError(product_id)

        await self._repository.delete(product)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            # Backstop for the FK ON DELETE RESTRICT if a movement was added
            # concurrently after the check above.
            await self._session.rollback()
            raise ProductHasMovementsError(product_id) from exc

    async def low_stock(
        self, *, threshold: int, page: int, size: int, active_only: bool = True
    ) -> tuple[Sequence[Product], int]:
        offset = (page - 1) * size
        return await self._repository.list_low_stock(
            threshold=threshold, limit=size, offset=offset, active_only=active_only
        )
