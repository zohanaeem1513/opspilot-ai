import io
import uuid
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import AuthenticatedUser, get_current_user, get_storage
from app.api.routes.documents import MAX_UPLOAD_SIZE_BYTES
from app.core.storage import DocumentStorage
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# The auth.users stub that lets profiles.id's FK resolve is registered by
# production code itself — importing app.main above already pulls in
# app.db.models, which registers it on this same Base.metadata.

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
            await conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS auth")
            await conn.run_sync(Base.metadata.create_all)
        _schema_ready = True
    async with _sessionmaker() as session:
        yield session


class _FakeStorage(DocumentStorage):
    """In-memory stand-in for Supabase Storage.

    No real credentials or network access are needed to test
    upload/download/list/get/delete.
    """

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def upload(self, path: str, content: bytes, content_type: str) -> None:
        self.objects[path] = content

    async def download(self, path: str) -> bytes:
        return self.objects[path]

    async def delete(self, path: str) -> None:
        self.objects.pop(path, None)


_fake_storage = _FakeStorage()


def _auth_as(user_id: uuid.UUID):
    async def _fake_get_current_user() -> AuthenticatedUser:
        return AuthenticatedUser(id=user_id, email=f"{user_id}@example.com")

    return _fake_get_current_user


client = TestClient(app)

USER_A = uuid.uuid4()
USER_B = uuid.uuid4()


def _as_user(user_id: uuid.UUID) -> None:
    # Re-assigned on every call — see test_workspaces.py for why this can't
    # be set once at import time.
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _auth_as(user_id)
    app.dependency_overrides[get_storage] = lambda: _fake_storage


def _clear_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_storage, None)


def _create_workspace_as(user_id: uuid.UUID, name: str) -> str:
    _as_user(user_id)
    try:
        response = client.post("/workspaces", json={"name": name})
        assert response.status_code == 201
        return response.json()["id"]
    finally:
        _clear_auth()


def _upload(
    workspace_id: str,
    filename: str = "notes.txt",
    content: bytes = b"hello world",
    content_type: str = "text/plain",
):
    return client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_member_can_upload_document():
    workspace_id = _create_workspace_as(USER_A, "Docs WS")
    _as_user(USER_A)
    try:
        response = _upload(workspace_id)
        assert response.status_code == 201
        body = response.json()
        assert body["filename"] == "notes.txt"
        assert body["content_type"] == "text/plain"
        assert body["size_bytes"] == len(b"hello world")
        assert uuid.UUID(body["id"])
    finally:
        _clear_auth()


def test_upload_rejects_disallowed_content_type():
    workspace_id = _create_workspace_as(USER_A, "Docs WS 2")
    _as_user(USER_A)
    try:
        response = _upload(
            workspace_id, filename="virus.exe", content_type="application/x-msdownload"
        )
        assert response.status_code == 415
    finally:
        _clear_auth()


def test_upload_rejects_oversized_file():
    workspace_id = _create_workspace_as(USER_A, "Docs WS 3")
    _as_user(USER_A)
    try:
        oversized = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)
        response = _upload(workspace_id, content=oversized)
        assert response.status_code == 413
    finally:
        _clear_auth()


def test_upload_rejects_empty_file():
    workspace_id = _create_workspace_as(USER_A, "Docs WS 4")
    _as_user(USER_A)
    try:
        response = _upload(workspace_id, content=b"")
        assert response.status_code == 422
    finally:
        _clear_auth()


def test_non_member_cannot_upload_document():
    workspace_id = _create_workspace_as(USER_A, "Private WS")
    _as_user(USER_B)
    try:
        response = _upload(workspace_id)
        assert response.status_code == 404
    finally:
        _clear_auth()


def test_member_can_list_and_get_document():
    workspace_id = _create_workspace_as(USER_A, "List WS")
    _as_user(USER_A)
    try:
        upload_response = _upload(workspace_id)
        document_id = upload_response.json()["id"]

        list_response = client.get(f"/workspaces/{workspace_id}/documents")
        assert list_response.status_code == 200
        assert any(d["id"] == document_id for d in list_response.json())

        get_response = client.get(f"/workspaces/{workspace_id}/documents/{document_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == document_id
    finally:
        _clear_auth()


def test_non_member_cannot_list_or_get_document():
    workspace_id = _create_workspace_as(USER_A, "Hidden WS")
    _as_user(USER_A)
    try:
        upload_response = _upload(workspace_id)
        document_id = upload_response.json()["id"]
    finally:
        _clear_auth()

    _as_user(USER_B)
    try:
        list_response = client.get(f"/workspaces/{workspace_id}/documents")
        assert list_response.status_code == 404

        get_response = client.get(f"/workspaces/{workspace_id}/documents/{document_id}")
        assert get_response.status_code == 404
    finally:
        _clear_auth()


def test_get_nonexistent_document_returns_404():
    workspace_id = _create_workspace_as(USER_A, "Empty WS")
    _as_user(USER_A)
    try:
        response = client.get(f"/workspaces/{workspace_id}/documents/{uuid.uuid4()}")
        assert response.status_code == 404
    finally:
        _clear_auth()


def test_member_can_delete_document_and_it_is_removed_from_storage():
    workspace_id = _create_workspace_as(USER_A, "Delete WS")
    _as_user(USER_A)
    try:
        existing_paths = set(_fake_storage.objects)
        upload_response = _upload(workspace_id)
        document_id = upload_response.json()["id"]
        new_paths = set(_fake_storage.objects) - existing_paths
        assert len(new_paths) == 1
        storage_path = next(iter(new_paths))

        delete_response = client.delete(f"/workspaces/{workspace_id}/documents/{document_id}")
        assert delete_response.status_code == 204
        assert storage_path not in _fake_storage.objects

        get_response = client.get(f"/workspaces/{workspace_id}/documents/{document_id}")
        assert get_response.status_code == 404
    finally:
        _clear_auth()


def test_non_member_cannot_delete_document():
    workspace_id = _create_workspace_as(USER_A, "Protected Docs WS")
    _as_user(USER_A)
    try:
        upload_response = _upload(workspace_id)
        document_id = upload_response.json()["id"]
    finally:
        _clear_auth()

    _as_user(USER_B)
    try:
        response = client.delete(f"/workspaces/{workspace_id}/documents/{document_id}")
        assert response.status_code == 404
    finally:
        _clear_auth()

    _as_user(USER_A)
    try:
        response = client.get(f"/workspaces/{workspace_id}/documents/{document_id}")
        assert response.status_code == 200
    finally:
        _clear_auth()


def test_unauthenticated_upload_is_rejected():
    workspace_id = _create_workspace_as(USER_A, "Auth Required WS")
    response = _upload(workspace_id)
    assert response.status_code == 401


def test_unauthenticated_list_is_rejected():
    workspace_id = _create_workspace_as(USER_A, "Auth Required List WS")
    response = client.get(f"/workspaces/{workspace_id}/documents")
    assert response.status_code == 401
