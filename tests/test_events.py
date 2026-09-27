from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_database
from backend.app.main import app
from backend.app.models import LogEvent


test_engine = create_engine(
    "sqlite://",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)

Base.metadata.create_all(bind=test_engine)


def override_get_database() -> Generator[Session, None, None]:
    database = TestSessionLocal()

    try:
        yield database
    finally:
        database.close()


app.dependency_overrides[get_database] = override_get_database

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_test_database():
    with TestSessionLocal() as database:
        database.execute(delete(LogEvent))
        database.commit()

    yield


def test_create_event():
    response = client.post(
        "/events",
        json={
            "service_name": "checkout-api",
            "level": "error",
            "message": "Payment request timed out",
            "endpoint": "/api/payments",
            "response_time_ms": 2500,
        },
    )

    response_body = response.json()

    assert response.status_code == 201
    assert response_body["id"] == 1
    assert response_body["service_name"] == "checkout-api"
    assert response_body["level"] == "error"


def test_list_and_filter_events():
    client.post(
        "/events",
        json={
            "service_name": "checkout-api",
            "level": "error",
            "message": "Payment failed",
        },
    )

    client.post(
        "/events",
        json={
            "service_name": "profile-api",
            "level": "info",
            "message": "Profile loaded",
        },
    )

    all_events_response = client.get(
        "/events",
    )

    error_events_response = client.get(
        "/events",
        params={
            "level": "error",
        },
    )

    assert all_events_response.status_code == 200
    assert len(all_events_response.json()) == 2

    assert error_events_response.status_code == 200
    assert len(error_events_response.json()) == 1
    assert error_events_response.json()[0]["level"] == "error"


def test_metrics_summary():
    client.post(
        "/events",
        json={
            "service_name": "checkout-api",
            "level": "error",
            "message": "Payment failed",
            "response_time_ms": 1000,
        },
    )

    client.post(
        "/events",
        json={
            "service_name": "checkout-api",
            "level": "warning",
            "message": "Payment was slow",
            "response_time_ms": 500,
        },
    )

    client.post(
        "/events",
        json={
            "service_name": "profile-api",
            "level": "info",
            "message": "Profile loaded",
            "response_time_ms": 100,
        },
    )

    response = client.get(
        "/metrics/summary",
    )

    response_body = response.json()

    assert response.status_code == 200
    assert response_body["total_events"] == 3
    assert response_body["error_count"] == 1
    assert response_body["warning_count"] == 1
    assert response_body["average_response_time_ms"] == 533.33
    assert response_body["monitored_services"] == 2


def test_websocket_receives_new_event():
    with client.websocket_connect(
        "/ws/events"
    ) as websocket:
        response = client.post(
            "/events",
            json={
                "service_name": "notification-api",
                "level": "warning",
                "message": "Email delivery is delayed",
                "response_time_ms": 800,
            },
        )

        websocket_message = websocket.receive_json()

    assert response.status_code == 201
    assert websocket_message["type"] == "new_event"
    assert (
        websocket_message["data"]["service_name"]
        == "notification-api"
    )
    assert websocket_message["data"]["level"] == "warning"