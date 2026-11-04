from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.services.retrieval import RetrievedChunk, retrieve_relevant_chunks


class RAGNoContextError(Exception):
    """Raised when no relevant document context is available."""


@dataclass(frozen=True)
class RAGCitation:
    label: str
    document_id: uuid.UUID
    filename: str
    chunk_index: int
    content_preview: str


@dataclass(frozen=True)
class RAGAnswer:
    answer: str
    citations: list[RAGCitation]


async def answer_question(
    question: str,
    workspace_id: uuid.UUID,
    db: AsyncSession,
    provider: AIProvider,
) -> RAGAnswer:
    """Answer a question using retrieved workspace document chunks."""

    question = question.strip()

    if not question:
        raise ValueError("question cannot be empty")

    chunks = await retrieve_relevant_chunks(
        question=question,
        workspace_id=workspace_id,
        db=db,
    )

    if not chunks:
        raise RAGNoContextError(
            "no relevant document context is available"
        )

    prompt = _build_prompt(
        question=question,
        chunks=chunks,
    )

    answer = await provider.generate(prompt)

    citations = [
        RAGCitation(
            label=f"S{index}",
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            content_preview=chunk.content[:300],
        )
        for index, chunk in enumerate(chunks, start=1)
    ]

    return RAGAnswer(
        answer=answer,
        citations=citations,
    )


def _build_prompt(
    question: str,
    chunks: list[RetrievedChunk],
) -> str:
    sources = []

    for index, chunk in enumerate(chunks, start=1):
        label = f"S{index}"

        sources.append(
            "\n".join(
                [
                    f"[{label}]",
                    f"Source: {chunk.filename}",
                    f"Chunk: {chunk.chunk_index}",
                    chunk.content,
                ]
            )
        )

    context = "\n\n".join(sources)

    return f"""You are answering questions using workspace documents.

Use only the sources provided below.
Do not use outside knowledge.
If the sources do not contain enough information to answer the question,
say that the available documents do not contain enough information.

Cite factual statements using the source labels exactly as provided,
for example [S1] or [S2].
Do not invent source labels.

Sources:
{context}

Question:
{question}

Answer:
"""