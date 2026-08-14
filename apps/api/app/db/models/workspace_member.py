from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.workspace import Workspace


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(nullable=False, default="member", server_default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="members")
