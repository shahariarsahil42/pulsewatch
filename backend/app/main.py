from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import Base, engine, get_database
from backend.app.models import LogEvent
from backend.app.schemas import (
    LogEventCreate,
    LogEventResponse,
    LogLevel,
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