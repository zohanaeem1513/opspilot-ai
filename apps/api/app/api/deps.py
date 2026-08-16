from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenVerificationError, verify_access_token
from app.db.models.profile import Profile
from app.db.models.workspace import Workspace
from app.db.models.workspace_member import WorkspaceMember
from app.db.session import get_db


class AuthenticatedUser(BaseModel):
    id: uuid.UUID
    email: str | None = None


def _extract_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(
    token: Annotated[str, Depends(_extract_bearer_token)],
) -> AuthenticatedUser:
    """FastAPI dependency seam — tests override this to inject a fake
    authenticated user without a real Supabase token."""
    try:
        claims = verify_access_token(token)
    except TokenVerificationError as exc:
        raise HTTPException(status_code=401, detail="not authenticated") from exc

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="not authenticated")

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="not authenticated") from exc

    return AuthenticatedUser(id=user_id, email=claims.get("email"))


async def get_current_profile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profile:
    """Returns the caller's profile row, creating it the first time a newly
    authenticated Supabase user (id taken from the verified token) is seen."""
    profile = await db.get(Profile, user.id)
    if profile is not None:
        return profile

    profile = Profile(id=user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@dataclass
class WorkspaceAccess:
    """A workspace the caller is confirmed to be a member of, plus their
    role in it. Returned by get_workspace_access so route handlers never
    need to re-check membership themselves."""

    workspace: Workspace
    role: str


async def get_workspace_access(
    workspace_id: uuid.UUID,
    profile: Annotated[Profile, Depends(get_current_profile)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceAccess:
    """Loads a workspace only if the caller belongs to it. A single query
    covers both "workspace doesn't exist" and "not a member" so a 404
    never reveals which case applies — a caller can't use this to probe
    for other users' workspace UUIDs."""
    result = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.profile_id == profile.id,
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="workspace not found")

    workspace, role = row
    return WorkspaceAccess(workspace=workspace, role=role)
