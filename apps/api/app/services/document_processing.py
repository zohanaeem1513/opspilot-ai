from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import DocumentStorage
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.services.chunking import chunk_text
from app.services.embeddings import generate_embeddings
from app.services.text_extraction import TextExtractionError, extract_text

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Raised when a document cannot be processed successfully."""


async def process_document(
    document: Document,
    db: AsyncSession,
    storage: DocumentStorage,
) -> None:
    document.status = "processing"
    document.processing_error = None
    await db.commit()

    try:
        content = await storage.download(document.storage_path)

        text = extract_text(
            content,
            document.content_type,
        )

        chunks = chunk_text(text)

        if not chunks:
            raise DocumentProcessingError("document produced no chunks")

        embeddings = generate_embeddings(chunks)

        await db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )

        for chunk_index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings, strict=True)
        ):
            db.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    workspace_id=document.workspace_id,
                    chunk_index=chunk_index,
                    content=chunk,
                    embedding=embedding,
                )
            )

        document.status = "processed"
        document.processing_error = None

        await db.commit()

    except TextExtractionError as exc:
        await _mark_failed(document, db, str(exc))
        raise DocumentProcessingError(str(exc)) from exc

    except Exception as exc:
        logger.exception(
            "Document processing failed for document %s",
            document.id,
        )

        await _mark_failed(
            document,
            db,
            "document processing failed",
        )

        raise DocumentProcessingError(
            "document processing failed"
        ) from exc


async def _mark_failed(
    document: Document,
    db: AsyncSession,
    message: str,
) -> None:
    await db.rollback()

    document.status = "failed"
    document.processing_error = message

    await db.commit()