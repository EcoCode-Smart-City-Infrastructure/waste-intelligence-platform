"""Minimal Postgres helper for the hub-layer repositories.

Reads the connection string from DATABASE_URL and exposes two helpers:
``fetch_all`` for SELECTs and ``execute_sql`` for writes. Keeps the
repository layer importable and gives it a real connection to target.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional

import psycopg2
import psycopg2.extras


def _connect():
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/waste")
    return psycopg2.connect(dsn)


def fetch_all(query: str, params: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """Run a SELECT and return rows as a list of dicts."""
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def execute_sql(query: str, params: Optional[Mapping[str, Any]] = None) -> int:
    """Run an INSERT/UPDATE/DELETE; returns the number of affected rows."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount
