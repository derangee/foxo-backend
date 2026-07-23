"""Business logic for products.

The service owns transaction boundaries (commit/rollback) and translates
database-level integrity failures into meaningful domain exceptions. Stock
``quantity`` is deliberately not settable here; it changes only through the
stock-movement workflow.
"""

from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateSKUError,
    ProductHasMovementsError,
    ProductNotFoundError,
)
from app.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    def __init__(self, session: AsyncSession, repository: ProductRepository):
        self._session = session
        self._repository = repository

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
        for field, value in changes.items():
            setattr(product, field, value)

        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def delete(self, product_id: int) -> None:
        product = await self.get(product_id)
        await self._repository.delete(product)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            # FK ON DELETE RESTRICT: the product still has movement history.
            await self._session.rollback()
            raise ProductHasMovementsError(product_id) from exc
