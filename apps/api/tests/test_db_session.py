import pytest

import app.db.session as db_session
from app.db.session import DatabaseNotConfiguredError, get_engine


def test_get_engine_raises_when_database_url_unset(monkeypatch):
    monkeypatch.setattr(db_session.settings, "database_url", None)
    monkeypatch.setattr(db_session, "_engine", None)

    try:
        with pytest.raises(DatabaseNotConfiguredError):
            get_engine()
    finally:
        monkeypatch.setattr(db_session, "_engine", None)
