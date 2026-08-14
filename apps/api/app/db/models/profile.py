import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Profile(Base):
    """Phase 3B profile: id is the authenticated Supabase user's id
    (auth.users.id), and rows are created on first sight of a newly
    authenticated user — see app/api/deps.py get_current_profile.
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True
    )
