"""Pure unit tests for schemas (no database)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.common import Page
from app.schemas.product import ProductCreate
from app.schemas.stock_movement import AdjustmentRequest, QuantityMovementRequest


class TestPage:
    def test_pages_rounds_up(self):
        page = Page.create(items=[], total=25, page=1, size=10)
        assert page.pages == 3

    def test_pages_zero_total(self):
        page = Page.create(items=[], total=0, page=1, size=10)
        assert page.pages == 0


class TestProductCreateValidation:
    def test_valid(self):
        product = ProductCreate(sku="ABC-1", name="Widget", price=Decimal("9.99"))
        assert product.sku == "ABC-1"

    def test_rejects_negative_price(self):
        with pytest.raises(ValidationError):
            ProductCreate(sku="ABC-1", name="Widget", price=Decimal("-1"))

    def test_rejects_bad_sku(self):
        with pytest.raises(ValidationError):
            ProductCreate(sku="has spaces!", name="Widget", price=Decimal("1"))

    def test_rejects_too_many_decimals(self):
        with pytest.raises(ValidationError):
            ProductCreate(sku="ABC-1", name="Widget", price=Decimal("1.999"))

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            ProductCreate(sku="ABC-1", name="", price=Decimal("1"))


class TestMovementValidation:
    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            QuantityMovementRequest(quantity=0)

    def test_adjustment_rejects_zero(self):
        with pytest.raises(ValidationError):
            AdjustmentRequest(quantity_change=0, reason="x")

    def test_adjustment_requires_reason(self):
        with pytest.raises(ValidationError):
            AdjustmentRequest(quantity_change=5)
