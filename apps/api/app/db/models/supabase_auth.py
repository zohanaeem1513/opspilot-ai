"""A minimal, unmanaged stand-in for Supabase's own `auth.users` table.

This project does not own or migrate `auth.users` — Supabase does. But
`profiles.id` has a real `FOREIGN KEY REFERENCES auth.users(id)` (migration
`0002`, already applied to the real database). SQLAlchemy's ORM needs *some*
`Table` object registered in `Base.metadata` to resolve that string FK
reference — and it resolves it during mapper configuration, which runs
globally for the whole registry on the *first* ORM query of any kind, not
just queries that touch `profiles`. Without this stub, every ORM query
(including ones that never touch `profiles`, e.g. `GET /workspaces`) raises
`sqlalchemy.exc.NoReferencedTableError` against a real database.

Only the "id" column is declared — enough for the FK to resolve. This is
never created via `Base.metadata.create_all()` against the real database
(the app never calls that; Alembic owns real DDL, and Supabase already owns
this table), and Alembic's autogenerate is explicitly told to ignore
anything in the "auth" schema (see `include_object` in `alembic/env.py`) so
it never tries to alter or drop the real table based on this one-column
stand-in.
"""

import sqlalchemy as sa

from app.db.base import Base

auth_users_table = sa.Table(
    "users",
    Base.metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    schema="auth",
)
