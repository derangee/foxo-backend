"""Shared API dependencies.

Assembles the repository/service graph for each request. FastAPI caches
``get_session`` within a request, so the repository and service share one
session (and therefore one transaction).
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.product import ProductRepository
from app.repositories.stock_movement import StockMovementRepository
from app.services.product import ProductService
from app.services.stock_movement import StockMovementService


def get_product_service(
    session: AsyncSession = Depends(get_session),
) -> ProductService:
    return ProductService(session, ProductRepository(session))


def get_stock_movement_service(
    session: AsyncSession = Depends(get_session),
) -> StockMovementService:
    return StockMovementService(
        session,
        ProductRepository(session),
        StockMovementRepository(session),
    )
