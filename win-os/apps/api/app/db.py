"""Database session handling. PostgreSQL/PostGIS in deployment; SQLite is a
development/test fallback only and is rejected in production (config.py).

`get_db` is the single FastAPI dependency used by every router. `init_db`
is called once by the application factory (and by tests) to bind the engine.
"""
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

_engine = None
_sessions = None

def init_db(database_url: str):
    global _engine, _sessions
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    _sessions = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine

def create_tables() -> None:
    """Dev/test convenience. Production schema is owned by Alembic migrations
    (win-os/data-platform/migrations); see docs/deployment/ubuntu-24.04.md."""
    Base.metadata.create_all(_engine)

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
