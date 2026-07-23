"""Schemas for the health endpoint."""

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Reports service liveness and database connectivity."""

    status: str
    database: str
    environment: str
