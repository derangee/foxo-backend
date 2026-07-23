"""HTTP middleware.

``RequestContextMiddleware`` assigns each request a correlation id (honoring an
inbound ``X-Request-ID`` if present), echoes it back on the response, and emits
a single structured access-log line with the method, path, status, and latency.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[_REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s (%.1fms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
