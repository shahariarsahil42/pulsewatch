from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "PulseWatch API is running",
    }


def test_health_endpoint():
    response = client.get("/health")
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["status"] == "healthy"
    assert "timestamp" in response_body