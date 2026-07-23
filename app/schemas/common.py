"""Shared response schemas.

A single envelope keeps every endpoint's payload consistent. Successful
responses use :class:`APIResponse`; failures use :class:`ErrorResponse`, which is
produced centrally by the exception handlers.
"""

import math
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard success envelope wrapping a typed data payload."""

    success: bool = True
    message: str = "OK"
    data: T | None = None


class Page(BaseModel, Generic[T]):
    """A page of results with pagination metadata."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, *, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        pages = math.ceil(total / size) if size else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)


class ErrorDetail(BaseModel):
    """Machine-readable error code plus optional human-readable details."""

    code: str
    details: list[str] | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope. Mirrors :class:`APIResponse` shape."""

    success: bool = False
    message: str
    error: ErrorDetail
