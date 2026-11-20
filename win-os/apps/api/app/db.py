"""Database session handling. PostgreSQL/PostGIS in deployment; SQLite is a
development/test fallback only and is rejected in production (config.py).

`get_db` is the single FastAPI dependency used by every router. `init_db`
is called once by the application factory (and by tests) to bind the engine.
"""
from __future__ import annotations
import logging, os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

_engine = None
_sessions = None
log = logging.getLogger("win-os-api.db")

def init_db(database_url: str):
    global _engine, _sessions
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    _sessions = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine

def create_tables() -> None:
    """Create the schema ONLY where Alembic does not own it.

    Production schema is owned by Alembic migrations
    (win-os/data-platform/migrations); see docs/deployment/ubuntu-24.04.md.
    Creating tables on boot against Postgres caused a real failure in
    deploy-verify run #2 (2026-11-20): the API created the tables, Alembic
    then found no version row and tried to CREATE TABLE organizations again
    (DuplicateTable). So create_all runs only for SQLite (dev/test) or when
    WIN_DB_AUTO_CREATE=1 is set explicitly; against Postgres it is skipped
    and the operator must run `alembic upgrade head` first."""
    url = str(_engine.url)
    if url.startswith("sqlite") or os.environ.get("WIN_DB_AUTO_CREATE") == "1":
        Base.metadata.create_all(_engine)
    else:
        log.info("skipping create_all on %s: schema is owned by Alembic migrations",
                 url.split("@")[-1] if "@" in url else url)

def get_db():
    if _sessions is None:
        raise RuntimeError("Database not initialised; call init_db first.")
    db = _sessions()
    try:
        yield db
    finally:
        db.close()

def engine():
    return _engine
