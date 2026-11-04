import uuid
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient

from app.api.deps import WorkspaceAccess, get_workspace_access
from app.api.routes import questions
from app.api.routes.questions import get_question_provider
from app.db.models.workspace import Workspace
from app.db.session import get_db
from app.main import app
from app.services.rag import RAGAnswer, RAGCitation, RAGNoContextError


class FakeAIProvider:
    async def generate(self, prompt: str) -> str:
        return "fake answer"


async def _override_get_db() -> AsyncGenerator[object, None]:
    yield object()


async def _override_workspace_access(
    workspace_id: uuid.UUID,
) -> WorkspaceAccess:
    return WorkspaceAccess(
        workspace=Workspace(
            id=workspace_id,
            name="Test Workspace",
        ),
        role="owner",
    )


def _override_provider() -> FakeAIProvider:
    return FakeAIProvider()


client = TestClient(app)


def _set_overrides() -> None:
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_workspace_access] = (
        _override_workspace_access
    )
    app.dependency_overrides[get_question_provider] = (
        _override_provider
    )


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_workspace_access, None)
    app.dependency_overrides.pop(get_question_provider, None)


def test_ask_question_returns_answer_and_citations(
    monkeypatch,
) -> None:
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    async def fake_answer_question(
        question,
        workspace_id,
        db,
        provider,
    ):
        return RAGAnswer(
            answer="Users can upload and organize documents [S1].",
            citations=[
                RAGCitation(
                    label="S1",
                    document_id=document_id,
                    filename="smallpdf.pdf",
                    chunk_index=0,
                    content_preview=(
                        "Users can upload, organize, and share documents."
                    ),
                )
            ],
        )

    monkeypatch.setattr(
        questions,
        "answer_question",
        fake_answer_question,
    )

    _set_overrides()

    try:
        response = client.post(
            f"/workspaces/{workspace_id}/questions",
            json={
                "question": "What can users do with documents?",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["answer"] == (
            "Users can upload and organize documents [S1]."
        )
        assert len(body["citations"]) == 1
        assert body["citations"][0]["label"] == "S1"
        assert body["citations"][0]["document_id"] == str(
            document_id
        )
        assert body["citations"][0]["filename"] == "smallpdf.pdf"
        assert body["citations"][0]["chunk_index"] == 0

    finally:
        _clear_overrides()


def test_ask_question_rejects_empty_question() -> None:
    workspace_id = uuid.uuid4()

    _set_overrides()

    try:
        response = client.post(
            f"/workspaces/{workspace_id}/questions",
            json={
                "question": "   ",
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"] == (
            "question cannot be empty"
        )

    finally:
        _clear_overrides()


def test_ask_question_handles_no_context(
    monkeypatch,
) -> None:
    workspace_id = uuid.uuid4()

    async def fake_answer_question(
        question,
        workspace_id,
        db,
        provider,
    ):
        raise RAGNoContextError(
            "no relevant document context is available"
        )

    monkeypatch.setattr(
        questions,
        "answer_question",
        fake_answer_question,
    )

    _set_overrides()

    try:
        response = client.post(
            f"/workspaces/{workspace_id}/questions",
            json={
                "question": "What is the refund policy?",
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"] == (
            "no relevant document context is available"
        )

    finally:
        _clear_overrides()


def test_ask_question_handles_provider_failure(
    monkeypatch,
) -> None:
    workspace_id = uuid.uuid4()

    async def fake_answer_question(
        question,
        workspace_id,
        db,
        provider,
    ):
        from app.ai.base import AIProviderError

        raise AIProviderError(
            "provider failed"
        )

    monkeypatch.setattr(
        questions,
        "answer_question",
        fake_answer_question,
    )

    _set_overrides()

    try:
        response = client.post(
            f"/workspaces/{workspace_id}/questions",
            json={
                "question": "What can users do?",
            },
        )

        assert response.status_code == 502
        assert response.json()["detail"] == (
            "AI provider request failed"
        )

    finally:
        _clear_overrides()  


def test_ask_question_requires_workspace_access() -> None:
    workspace_id = uuid.uuid4()

    async def deny_workspace_access():
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="workspace not found",
        )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_workspace_access] = (
        deny_workspace_access
    )
    app.dependency_overrides[get_question_provider] = (
        _override_provider
    )

    try:
        response = client.post(
            f"/workspaces/{workspace_id}/questions",
            json={
                "question": "What is in this workspace?",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "workspace not found"
        )

    finally:
        _clear_overrides()        