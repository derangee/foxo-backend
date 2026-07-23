"""Declarative base for all ORM models.

Every model inherits from ``Base`` so that Alembic and SQLAlchemy share a single
metadata registry.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
