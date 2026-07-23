"""Health check endpoint.

Reports service liveness and verifies database connectivity with a lightweight
``SELECT 1``. A failing database check returns a degraded payload rather than
raising, so orchestrators can distinguish "process up" from "fully healthy".
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.common import APIResponse
from app.schemas.health import HealthStatus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=APIResponse[HealthStatus],
    summary="Service health check",
)
async def health_check(
    session: AsyncSession = Depends(get_session),
) -> APIResponse[HealthStatus]:
    settings = get_settings()
    database_state = "up"

    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - a health probe must never raise, only report
        logger.exception("Database health check failed")
        database_state = "down"

    healthy = database_state == "up"
    return APIResponse(
        success=healthy,
        message="Service is healthy" if healthy else "Service degraded",
        data=HealthStatus(
            status="ok" if healthy else "degraded",
            database=database_state,
            environment=settings.app_env,
        ),
    )
