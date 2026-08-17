import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceAccess, get_current_profile, get_storage, get_workspace_access
from app.core.storage import DocumentStorage, StorageError
from app.db.models.document import Document
from app.db.models.profile import Profile
from app.db.session import get_db

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
    )


def _safe_filename(filename: str | None) -> str:
    name = (filename or "untitled").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name or "untitled"


async def _get_document_or_404(
    document_id: uuid.UUID, workspace_id: uuid.UUID, db: AsyncSession
) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="document not found")
    return document


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[DocumentStorage, Depends(get_storage)],
    file: UploadFile,
) -> DocumentResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="unsupported file type")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="file is empty")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="file too large")

    document_id = uuid.uuid4()
    filename = _safe_filename(file.filename)
    storage_path = f"{access.workspace.id}/{document_id}/{filename}"

    try:
        await storage.upload(storage_path, content, file.content_type)
    except StorageError as exc:
        raise HTTPException(status_code=502, detail="failed to store file") from exc

    document = Document(
        id=document_id,
        workspace_id=access.workspace.id,
        uploaded_by=profile.id,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(content),
        storage_path=storage_path,
    )
    db.add(document)
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        try:
            await storage.delete(storage_path)
        except StorageError:
            pass
        raise HTTPException(status_code=500, detail="failed to save document") from exc

    await db.refresh(document)
    return _to_response(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentResponse]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == access.workspace.id)
        .order_by(Document.created_at.desc())
    )
    return [_to_response(document) for document in result.scalars().all()]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    document = await _get_document_or_404(document_id, access.workspace.id, db)
    return _to_response(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[DocumentStorage, Depends(get_storage)],
) -> None:
    document = await _get_document_or_404(document_id, access.workspace.id, db)
    try:
        await storage.delete(document.storage_path)
    except StorageError as exc:
        raise HTTPException(status_code=502, detail="failed to delete file") from exc

    await db.execute(delete(Document).where(Document.id == document.id))
    await db.commit()
