from fastapi.testclient import TestClient

from app.api.routes.ready import get_database_ping
from app.main import app

client = TestClient(app)


def test_ready_returns_200_when_database_reachable():
    async def fake_ping() -> None:
        return None

    app.dependency_overrides[get_database_ping] = lambda: fake_ping
    try:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}
    finally:
        app.dependency_overrides.clear()


def test_ready_returns_503_when_database_unreachable():
    async def fake_ping() -> None:
        raise ConnectionError("could not connect to server")

    app.dependency_overrides[get_database_ping] = lambda: fake_ping
    try:
        response = client.get("/ready")
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_ready_error_body_does_not_leak_exception_details():
    async def fake_ping() -> None:
        raise ConnectionError("password authentication failed for user 'postgres'")

    app.dependency_overrides[get_database_ping] = lambda: fake_ping
    try:
        response = client.get("/ready")
        body = response.text
        assert "password" not in body
        assert "postgres" not in body
    finally:
        app.dependency_overrides.clear()


def test_ready_returns_503_when_database_not_configured():
    from app.db.session import DatabaseNotConfiguredError

    async def fake_ping() -> None:
        raise DatabaseNotConfiguredError("DATABASE_URL is not set")

    app.dependency_overrides[get_database_ping] = lambda: fake_ping
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        assert "DATABASE_URL" not in response.text
    finally:
        app.dependency_overrides.clear()
