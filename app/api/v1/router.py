"""Aggregates all v1 endpoint routers into a single API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, products, stock_movements

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(products.router)
api_router.include_router(stock_movements.router)
