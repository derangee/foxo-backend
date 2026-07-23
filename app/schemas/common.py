"""Shared response schemas.

A single envelope keeps every endpoint's payload consistent:
``{ "success": bool, "message": str, "data": <payload> }``. Error responses use
the same shape and are produced by the centralized exception handlers.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard success envelope wrapping a typed data payload."""

    success: bool = True
    message: str = "OK"
    data: T | None = None
