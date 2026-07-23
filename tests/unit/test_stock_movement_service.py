"""Unit tests for StockMovementService — business rules and transaction behavior."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.exceptions import InsufficientStockError, ProductNotFoundError
from app.models.enums import MovementType
from app.models.stock_movement import StockMovement
from app.schemas.product import ProductCreate


async def _product(service, sku="SKU-1"):
    return await service.create(ProductCreate(sku=sku, name="W", price=Decimal("1.00")))


class TestApplyMovements:
    async def test_restock_increases_stock(self, product_service, movement_service):
        product = await _product(product_service)
        movement = await movement_service.restock(product.id, 100)
        assert movement.movement_type == MovementType.RESTOCK
        assert movement.quantity_change == 100
        assert movement.resulting_quantity == 100

    async def test_sale_decreases_stock(self, product_service, movement_service):
        product = await _product(product_service)
        await movement_service.restock(product.id, 100)
        movement = await movement_service.sell(product.id, 30)
        assert movement.quantity_change == -30
        assert movement.resulting_quantity == 70

    async def test_adjustment_records_reason(self, product_service, movement_service):
        product = await _product(product_service)
        await movement_service.restock(product.id, 10)
        movement = await movement_service.adjust(product.id, -4, "stock count")
        assert movement.quantity_change == -4
        assert movement.resulting_quantity == 6
        assert movement.reason == "stock count"

    async def test_movement_on_missing_product_raises(self, movement_service):
        with pytest.raises(ProductNotFoundError):
            await movement_service.restock(999, 5)


class TestNegativeStockRejection:
    async def test_sale_beyond_stock_raises(self, product_service, movement_service):
        product = await _product(product_service)
        await movement_service.restock(product.id, 10)
        with pytest.raises(InsufficientStockError):
            await movement_service.sell(product.id, 50)

    async def test_adjustment_below_zero_raises(self, product_service, movement_service):
        product = await _product(product_service)
        await movement_service.restock(product.id, 5)
        with pytest.raises(InsufficientStockError):
            await movement_service.adjust(product.id, -10, "shrinkage")


class TestTransactionBehavior:
    async def test_rejected_sale_leaves_state_unchanged(
        self, product_service, movement_service, session
    ):
        """A rejected movement must not change stock or write a movement row."""
        product = await _product(product_service)
        await movement_service.restock(product.id, 10)

        with pytest.raises(InsufficientStockError):
            await movement_service.sell(product.id, 50)

        refreshed = await product_service.get(product.id)
        assert refreshed.quantity == 10

        count = await session.scalar(select(func.count()).select_from(StockMovement))
        assert count == 1  # only the restock committed

    async def test_ledger_sum_equals_quantity(self, product_service, movement_service, session):
        product = await _product(product_service)
        await movement_service.restock(product.id, 100)
        await movement_service.sell(product.id, 30)
        await movement_service.adjust(product.id, -5, "count")

        total_change = await session.scalar(
            select(func.sum(StockMovement.quantity_change)).where(
                StockMovement.product_id == product.id
            )
        )
        refreshed = await product_service.get(product.id)
        assert total_change == refreshed.quantity == 65


class TestHistory:
    async def test_orders_newest_first_and_filters(self, product_service, movement_service):
        product = await _product(product_service)
        await movement_service.restock(product.id, 50)
        await movement_service.sell(product.id, 10)
        await movement_service.restock(product.id, 5)

        items, total = await movement_service.history(product.id, page=1, size=20)
        assert total == 3
        assert items[0].quantity_change == 5  # newest first

        items, total = await movement_service.history(
            product.id, page=1, size=20, movement_type=MovementType.RESTOCK
        )
        assert total == 2
        assert all(item.movement_type == MovementType.RESTOCK for item in items)

    async def test_history_missing_product_raises(self, movement_service):
        with pytest.raises(ProductNotFoundError):
            await movement_service.history(999, page=1, size=20)
