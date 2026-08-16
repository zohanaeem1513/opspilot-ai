"""Regression test for a real-database bug that the SQLite-backed workspace
tests didn't catch: profiles.id has a foreign key to auth.users.id, a table
Supabase owns and this codebase never creates. SQLAlchemy resolves that FK
during ORM mapper configuration, which runs globally for the whole model
registry on the first ORM query of any kind — so without a stand-in table
registered in Base.metadata, even a query that never touches `profiles`
(e.g. GET /workspaces) raised sqlalchemy.exc.NoReferencedTableError against
the real Postgres/Supabase database.

This test needs no database at all — mapper configuration is a pure
metadata-resolution step — so it catches the regression directly, without
depending on the SQLite test harness in test_workspaces.py to happen to
provide its own stand-in (which is exactly how this bug slipped through:
the old stand-in lived only in that test file, not in production code).
"""

from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.db.models import Profile, Workspace, WorkspaceMember  # noqa: F401


def test_mapper_configuration_resolves_auth_users_fk():
    configure_mappers()


def test_auth_users_stub_is_registered_for_fk_resolution():
    assert "auth.users" in Base.metadata.tables
