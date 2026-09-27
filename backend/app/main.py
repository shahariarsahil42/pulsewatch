from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.app.database import Base, engine, get_database
from backend.app.models import LogEvent
from backend.app.schemas import (
    LogEventCreate,
    LogEventResponse,
    LogLevel,
    MetricsSummary,
)


@asynccontextmanager
async def lifespan(
    _application: FastAPI,
) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="PulseWatch API",
    description="Real-time application monitoring platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {
        "message": "PulseWatch API is running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post(
    "/events",
    response_model=LogEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event: LogEventCreate,
    database: Session = Depends(get_database),
):
    database_event = LogEvent(
        **event.model_dump(),
    )

    database.add(database_event)
    database.commit()
    database.refresh(database_event)

    return database_event


@app.get(
    "/events",
    response_model=list[LogEventResponse],
)
def list_events(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    level: LogLevel | None = None,
    service_name: str | None = None,
    database: Session = Depends(get_database),
):
    statement = (
        select(LogEvent)
        .order_by(LogEvent.created_at.desc())
        .limit(limit)
    )

    if level is not None:
        statement = statement.where(
            LogEvent.level == level,
        )

    if service_name is not None:
        statement = statement.where(
            LogEvent.service_name == service_name,
        )

    return database.scalars(statement).all()


@app.get(
    "/metrics/summary",
    response_model=MetricsSummary,
)
def get_metrics_summary(
    database: Session = Depends(get_database),
):
    statement = select(
        func.count(LogEvent.id),
        func.sum(
            case(
                (LogEvent.level == "error", 1),
                else_=0,
            )
        ),
        func.sum(
            case(
                (LogEvent.level == "warning", 1),
                else_=0,
            )
        ),
        func.avg(LogEvent.response_time_ms),
        func.count(
            func.distinct(LogEvent.service_name)
        ),
    )

    (
        total_events,
        error_count,
        warning_count,
        average_response_time,
        monitored_services,
    ) = database.execute(statement).one()

    return MetricsSummary(
        total_events=total_events or 0,
        error_count=error_count or 0,
        warning_count=warning_count or 0,
        average_response_time_ms=(
            round(float(average_response_time), 2)
            if average_response_time is not None
            else None
        ),
        monitored_services=monitored_services or 0,
    )