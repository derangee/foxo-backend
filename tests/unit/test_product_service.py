"""Unit tests for ProductService (service layer over a real session)."""

from decimal import Decimal

import pytest

from app.core.exceptions import (
    DuplicateSKUError,
    OptimisticLockError,
    ProductHasMovementsError,
    ProductNotFoundError,
)
from app.schemas.product import ProductCreate, ProductUpdate


async def _create(service, sku="SKU-1", name="Widget", price="9.99"):
    return await service.create(ProductCreate(sku=sku, name=name, price=Decimal(price)))


class TestCreate:
    async def test_starts_at_zero_quantity_and_version_one(self, product_service):
        product = await _create(product_service)
        assert product.quantity == 0
        assert product.version == 1
        assert product.is_active is True

    async def test_duplicate_sku_raises(self, product_service):
        await _create(product_service)
        with pytest.raises(DuplicateSKUError):
            await _create(product_service)


class TestGet:
    async def test_missing_raises(self, product_service):
        with pytest.raises(ProductNotFoundError):
            await product_service.get(999)


class TestUpdate:
    async def test_changes_fields_and_bumps_version(self, product_service):
        product = await _create(product_service)
        updated = await product_service.update(
            product.id, ProductUpdate(name="Renamed", price=Decimal("5.00"))
        )
        assert updated.name == "Renamed"
        assert updated.price == Decimal("5.00")
        assert updated.version == 2

    async def test_matching_expected_version_succeeds(self, product_service):
        product = await _create(product_service)
        updated = await product_service.update(
            product.id, ProductUpdate(name="A", expected_version=1)
        )
        assert updated.version == 2

    async def test_stale_expected_version_raises(self, product_service):
        product = await _create(product_service)
        await product_service.update(product.id, ProductUpdate(name="A", expected_version=1))
        with pytest.raises(OptimisticLockError):
            await product_service.update(product.id, ProductUpdate(name="B", expected_version=1))


class TestDelete:
    async def test_without_movements_removes_product(self, product_service):
        product = await _create(product_service)
        await product_service.delete(product.id)
        with pytest.raises(ProductNotFoundError):
            await product_service.get(product.id)

    async def test_with_movements_is_blocked(self, product_service, movement_service):
        product = await _create(product_service)
        await movement_service.restock(product.id, 5)
        with pytest.raises(ProductHasMovementsError):
            await product_service.delete(product.id)


class TestActivation:
    async def test_deactivate_then_activate(self, product_service):
        product = await _create(product_service)
        deactivated = await product_service.set_active(product.id, active=False)
        assert deactivated.is_active is False
        activated = await product_service.set_active(product.id, active=True)
        assert activated.is_active is True

    async def test_deactivate_is_idempotent(self, product_service):
        product = await _create(product_service)
        await product_service.set_active(product.id, active=False)
        again = await product_service.set_active(product.id, active=False)
        assert again.is_active is False


class TestLowStock:
    async def test_filters_and_orders_by_quantity(self, product_service, movement_service):
        low = await _create(product_service, sku="LOW")
        await movement_service.restock(low.id, 3)
        mid = await _create(product_service, sku="MID")
        await movement_service.restock(mid.id, 8)
        high = await _create(product_service, sku="HIGH")
        await movement_service.restock(high.id, 100)

        items, total = await product_service.low_stock(threshold=10, page=1, size=20)
        assert total == 2
        # Most urgent (lowest quantity) first.
        assert [item.id for item in items] == [low.id, mid.id]

    async def test_excludes_inactive_by_default(self, product_service, movement_service):
        low = await _create(product_service, sku="LOW")
        await movement_service.restock(low.id, 3)
        await product_service.set_active(low.id, active=False)

        _, total = await product_service.low_stock(threshold=10, page=1, size=20)
        assert total == 0
