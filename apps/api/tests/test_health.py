from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_status_ok():
    response = client.get("/health")
    assert response.json()["status"] == "ok"


def test_health_service_name():
    response = client.get("/health")
    assert response.json()["service"] == "opspilot-api"


def test_health_response_shape():
    response = client.get("/health")
    body = response.json()
    assert set(body.keys()) == {"status", "service", "version", "environment"}
    assert all(isinstance(value, str) for value in body.values())
