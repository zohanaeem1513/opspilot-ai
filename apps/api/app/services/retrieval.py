from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.services.embeddings import generate_embeddings

DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    content: str
    similarity: float


async def retrieve_relevant_chunks(
    question: str,
    workspace_id: uuid.UUID,
    db: AsyncSession,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Return the document chunks most relevant to a workspace question."""

    question = question.strip()

    if not question:
        return []

    question_embedding = generate_embeddings([question])[0]

    distance = DocumentChunk.embedding.cosine_distance(
        question_embedding
    ).label("distance")

    result = await db.execute(
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id,
            Document.filename,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            distance,
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            DocumentChunk.workspace_id == workspace_id,
            Document.workspace_id == workspace_id,
            Document.status == "processed",
        )
        .order_by(distance)
        .limit(top_k)
    )

    chunks: list[RetrievedChunk] = []

    for row in result.all():
        similarity = 1.0 - float(row.distance)

        if similarity <= 0:
            continue

        chunks.append(
            RetrievedChunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                filename=row.filename,
                chunk_index=row.chunk_index,
                content=row.content,
                similarity=similarity,
            )
        )

    return chunks