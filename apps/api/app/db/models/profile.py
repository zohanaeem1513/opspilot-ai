import uuid

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Profile(Base):
    """Minimal Phase 3A profile. Phase 3B adds
    FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
    and creates rows from the authenticated Supabase user's id.
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
