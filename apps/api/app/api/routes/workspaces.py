import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceAccess, get_current_profile, get_workspace_access
from app.db.models.profile import Profile
from app.db.models.workspace import Workspace
from app.db.models.workspace_member import WorkspaceMember
from app.db.session import get_db

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class _WorkspaceNameField(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def _strip_and_require_non_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class WorkspaceCreateRequest(_WorkspaceNameField):
    pass


class WorkspaceUpdateRequest(_WorkspaceNameField):
    pass


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    created_at: datetime
    updated_at: datetime


def _to_response(workspace: Workspace, role: str) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        role=role,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    profile: Annotated[Profile, Depends(get_current_profile)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    """Creates a workspace and makes the caller its owner in one commit."""
    workspace = Workspace(id=uuid.uuid4(), name=payload.name)
    db.add(workspace)
    db.add(WorkspaceMember(workspace_id=workspace.id, profile_id=profile.id, role="owner"))
    await db.commit()
    await db.refresh(workspace)
    return _to_response(workspace, "owner")


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    profile: Annotated[Profile, Depends(get_current_profile)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkspaceResponse]:
    result = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.profile_id == profile.id)
        .order_by(Workspace.created_at.desc())
    )
    return [_to_response(workspace, role) for workspace, role in result.all()]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
) -> WorkspaceResponse:
    return _to_response(access.workspace, access.role)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    payload: WorkspaceUpdateRequest,
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    access.workspace.name = payload.name
    await db.commit()
    await db.refresh(access.workspace)
    return _to_response(access.workspace, access.role)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    access: Annotated[WorkspaceAccess, Depends(get_workspace_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    # A plain DELETE (not session.delete()) lets the database's own ON
    # DELETE CASCADE (migration 0001) remove the workspace_members rows.
    # session.delete() would instead try to null out workspace_members.
    # workspace_id via the ORM relationship, which fails — that column is
    # part of a composite primary key and can't be nulled.
    await db.execute(delete(Workspace).where(Workspace.id == access.workspace.id))
    await db.commit()
