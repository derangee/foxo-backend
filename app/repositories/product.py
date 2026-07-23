"""Data-access layer for products.

The repository owns *how* products are queried and persisted; it holds no
business rules and never commits. Transaction boundaries belong to the service
layer. Methods flush where they need server-generated values (e.g. the primary
key) so callers can react to integrity errors before commit.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def add(self, product: Product) -> None:
        self._session.add(product)

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self._session.get(Product, product_id)

    async def get_for_update(self, product_id: int) -> Product | None:
        """Fetch a product with a row-level lock (SELECT ... FOR UPDATE).

        Serializes concurrent stock movements against the same product so that
        the read-modify-write of ``quantity`` cannot lose updates. On backends
        without row locking (e.g. SQLite) this degrades to a plain read.
        """
        result = await self._session.execute(
            select(Product).where(Product.id == product_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self._session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def list(
        self, *, limit: int, offset: int, active_only: bool = False
    ) -> tuple[Sequence[Product], int]:
        query = select(Product)
        if active_only:
            query = query.where(Product.is_active.is_(True))

        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        result = await self._session.execute(query.order_by(Product.id).limit(limit).offset(offset))
        return result.scalars().all(), int(total or 0)

    async def delete(self, product: Product) -> None:
        await self._session.delete(product)
