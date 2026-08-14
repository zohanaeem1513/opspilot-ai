"""profiles.id references auth.users.id

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-14

Hand-written, like 0001 — no live database connection made while writing or
verifying this migration (verified with `alembic upgrade head --sql`).

Phase 3B: profiles.id becomes a foreign key into Supabase's own auth.users
table, which this project does not own or migrate. profiles.id values now
come from the authenticated Supabase user's id (see app/api/deps.py).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "profiles_id_fkey",
        source_table="profiles",
        referent_table="users",
        local_cols=["id"],
        remote_cols=["id"],
        referent_schema="auth",
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("profiles_id_fkey", "profiles", type_="foreignkey")
