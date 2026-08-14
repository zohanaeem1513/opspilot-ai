import uuid

from fastapi.testclient import TestClient

from app.api.deps import get_current_profile
from app.db.models.profile import Profile
from app.main import app

client = TestClient(app)


def test_me_returns_200_with_authenticated_profile():
    fake_id = uuid.uuid4()

    async def fake_get_current_profile() -> Profile:
        return Profile(id=fake_id)

    app.dependency_overrides[get_current_profile] = fake_get_current_profile
    try:
        response = client.get("/me")
        assert response.status_code == 200
        assert response.json() == {"id": str(fake_id)}
    finally:
        app.dependency_overrides.clear()


def test_me_returns_401_without_authorization_header():
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_401_with_malformed_authorization_header():
    response = client.get("/me", headers={"Authorization": "not-a-bearer-token"})
    assert response.status_code == 401


def test_me_returns_401_with_invalid_token():
    response = client.get("/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401
