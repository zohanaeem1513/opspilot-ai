from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider, AIProviderError
from app.ai.factory import get_ai_provider
from app.api.deps import WorkspaceAccess, get_workspace_access
from app.db.session import get_db
from app.services.rag import RAGNoContextError, answer_question

router = APIRouter(
    prefix="/workspaces/{workspace_id}/questions",
    tags=["questions"],
)


class QuestionRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    label: str
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    content_preview: str


class QuestionResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


def get_question_provider() -> AIProvider:
    """Return the configured AI provider for question answering."""

    try:
        return get_ai_provider()
    except AIProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI provider is not configured",
        ) from exc


@router.post("", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider: Annotated[AIProvider, Depends(get_question_provider)],
) -> QuestionResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="question cannot be empty",
        )

    try:
        result = await answer_question(
            question=question,
            workspace_id=access.workspace.id,
            db=db,
            provider=provider,
        )

    except RAGNoContextError as exc:
        raise HTTPException(
            status_code=422,
            detail="no relevant document context is available",
        ) from exc

    except AIProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI provider request failed",
        ) from exc

    return QuestionResponse(
        answer=result.answer,
        citations=[
            CitationResponse(
                label=citation.label,
                document_id=citation.document_id,
                filename=citation.filename,
                chunk_index=citation.chunk_index,
                content_preview=citation.content_preview,
            )
            for citation in result.citations
        ],
    )