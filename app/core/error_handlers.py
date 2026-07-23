"""Centralized exception handling.

Every error path funnels through here so clients always receive the same
:class:`ErrorResponse` shape with an appropriate HTTP status code.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

# Status codes referenced by the handlers. Defined here to stay independent of
# framework constant deprecations.
_HTTP_UNPROCESSABLE_ENTITY = 422
_HTTP_INTERNAL_SERVER_ERROR = 500


def _payload(message: str, code: str, details: list[str] | None = None) -> dict:
    return ErrorResponse(
        message=message, error=ErrorDetail(code=code, details=details)
    ).model_dump()


async def _handle_app_exception(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_payload(exc.message, exc.error_code, exc.details),
    )


async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        f"{'.'.join(str(part) for part in error['loc'][1:])}: {error['msg']}".lstrip(": ")
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=_HTTP_UNPROCESSABLE_ENTITY,
        content=_payload("Request validation failed", "validation_error", details),
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=_HTTP_INTERNAL_SERVER_ERROR,
        content=_payload("Internal server error", "internal_error"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the application."""
    app.add_exception_handler(AppError, _handle_app_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
