"""ORM models.

Importing the models here registers them on ``Base.metadata`` so that Alembic
autogeneration and ``create_all`` see the full schema from a single import.
"""

from app.models.enums import MovementType
from app.models.product import Product
from app.models.stock_movement import StockMovement

__all__ = ["MovementType", "Product", "StockMovement"]
