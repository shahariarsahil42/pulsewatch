from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LogLevel = Literal[
    "debug",
    "info",
    "warning",
    "error",
    "critical",
]


class LogEventCreate(BaseModel):
    service_name: str = Field(
        min_length=1,
        max_length=100,
    )

    level: LogLevel = "info"

    message: str = Field(
        min_length=1,
        max_length=2000,
    )

    endpoint: str | None = Field(
        default=None,
        max_length=255,
    )

    response_time_ms: float | None = Field(
        default=None,
        ge=0,
    )


class LogEventResponse(LogEventCreate):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    created_at: datetime


class MetricsSummary(BaseModel):
    total_events: int
    error_count: int
    warning_count: int
    average_response_time_ms: float | None
    monitored_services: int