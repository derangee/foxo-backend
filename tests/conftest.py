"""Shared test fixtures.

Each test runs against a fresh in-memory SQLite database. A StaticPool keeps a
single underlying connection so the schema created in the ``engine`` fixture is
visible to every session (and to the app via the ``get_session`` override).
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.repositories.product import ProductRepository
from app.repositories.stock_movement import StockMovementRepository
from app.services.product import ProductService
from app.services.stock_movement import StockMovementService


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def product_service(session):
    return ProductService(session, ProductRepository(session), StockMovementRepository(session))


@pytest_asyncio.fixture
async def movement_service(session):
    return StockMovementService(
        session, ProductRepository(session), StockMovementRepository(session)
    )


@pytest_asyncio.fixture
async def client(session_factory):
    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
