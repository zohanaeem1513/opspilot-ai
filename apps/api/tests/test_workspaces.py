import uuid
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# The auth.users stub that lets profiles.id's FK resolve (see
# app/db/models/supabase_auth.py) is registered by production code itself —
# importing app.main above already pulls in app.db.models, which registers
# it on this same Base.metadata. Nothing extra is needed here.

_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
_schema_ready = False


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    global _schema_ready
    if not _schema_ready:
        async with _engine.begin() as conn:
            # SQLite has no real "auth" schema/namespace like Postgres — the
            # stub auth.users table above needs an actual attached database
            # named "auth" for "CREATE TABLE auth.users" to resolve at all.
            await conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS auth")
            await conn.run_sync(Base.metadata.create_all)
        _schema_ready = True
    async with _sessionmaker() as session:
        yield session


def _auth_as(user_id: uuid.UUID):
    async def _fake_get_current_user() -> AuthenticatedUser:
        return AuthenticatedUser(id=user_id, email=f"{user_id}@example.com")

    return _fake_get_current_user


client = TestClient(app)

USER_A = uuid.uuid4()
USER_B = uuid.uuid4()


def _as_user(user_id: uuid.UUID) -> None:
    # Re-assigned on every call, not just once at import time: other test
    # modules call app.dependency_overrides.clear() in their own teardown,
    # which would otherwise silently drop this override (and every
    # subsequent workspace request would hit the real production database).
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _auth_as(user_id)


def _clear_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)


def test_authenticated_user_can_create_workspace():
    _as_user(USER_A)
    try:
        response = client.post("/workspaces", json={"name": "Acme Support"})
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Acme Support"
        assert body["role"] == "owner"
        assert uuid.UUID(body["id"])
    finally:
        _clear_auth()


def test_create_workspace_rejects_blank_name():
    _as_user(USER_A)
    try:
        response = client.post("/workspaces", json={"name": "   "})
        assert response.status_code == 422
    finally:
        _clear_auth()


def test_authenticated_user_can_list_their_workspaces():
    _as_user(USER_A)
    try:
        client.post("/workspaces", json={"name": "List Test 1"})
        client.post("/workspaces", json={"name": "List Test 2"})
        response = client.get("/workspaces")
        assert response.status_code == 200
        names = {w["name"] for w in response.json()}
        assert {"List Test 1", "List Test 2"}.issubset(names)
    finally:
        _clear_auth()

    _as_user(USER_B)
    try:
        response = client.get("/workspaces")
        assert response.status_code == 200
        names = {w["name"] for w in response.json()}
        assert "List Test 1" not in names
        assert "List Test 2" not in names
    finally:
        _clear_auth()


def _create_workspace_as(user_id: uuid.UUID, name: str) -> str:
    _as_user(user_id)
    try:
        response = client.post("/workspaces", json={"name": name})
        assert response.status_code == 201
        return response.json()["id"]
    finally:
        _clear_auth()


def test_authenticated_user_can_retrieve_their_workspace():
    workspace_id = _create_workspace_as(USER_A, "Retrievable")
    _as_user(USER_A)
    try:
        response = client.get(f"/workspaces/{workspace_id}")
        assert response.status_code == 200
        assert response.json()["id"] == workspace_id
    finally:
        _clear_auth()


def test_authenticated_user_cannot_retrieve_another_users_workspace():
    workspace_id = _create_workspace_as(USER_A, "Private to A")
    _as_user(USER_B)
    try:
        response = client.get(f"/workspaces/{workspace_id}")
        assert response.status_code == 404
    finally:
        _clear_auth()


def test_get_nonexistent_workspace_returns_404():
    _as_user(USER_A)
    try:
        response = client.get(f"/workspaces/{uuid.uuid4()}")
        assert response.status_code == 404
    finally:
        _clear_auth()


def test_authenticated_user_can_update_their_workspace():
    workspace_id = _create_workspace_as(USER_A, "Old Name")
    _as_user(USER_A)
    try:
        response = client.patch(f"/workspaces/{workspace_id}", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"
    finally:
        _clear_auth()


def test_authenticated_user_cannot_update_another_users_workspace():
    workspace_id = _create_workspace_as(USER_A, "Belongs to A")
    _as_user(USER_B)
    try:
        response = client.patch(f"/workspaces/{workspace_id}", json={"name": "Hijacked"})
        assert response.status_code == 404
    finally:
        _clear_auth()


def test_authenticated_user_can_delete_their_workspace():
    workspace_id = _create_workspace_as(USER_A, "Deletable")
    _as_user(USER_A)
    try:
        response = client.delete(f"/workspaces/{workspace_id}")
        assert response.status_code == 204

        response = client.get(f"/workspaces/{workspace_id}")
        assert response.status_code == 404
    finally:
        _clear_auth()


def test_authenticated_user_cannot_delete_another_users_workspace():
    workspace_id = _create_workspace_as(USER_A, "Protected from B")
    _as_user(USER_B)
    try:
        response = client.delete(f"/workspaces/{workspace_id}")
        assert response.status_code == 404
    finally:
        _clear_auth()

    _as_user(USER_A)
    try:
        response = client.get(f"/workspaces/{workspace_id}")
        assert response.status_code == 200
    finally:
        _clear_auth()


def test_unauthenticated_create_is_rejected():
    response = client.post("/workspaces", json={"name": "Nope"})
    assert response.status_code == 401


def test_unauthenticated_list_is_rejected():
    response = client.get("/workspaces")
    assert response.status_code == 401


def test_unauthenticated_get_is_rejected():
    response = client.get(f"/workspaces/{uuid.uuid4()}")
    assert response.status_code == 401
