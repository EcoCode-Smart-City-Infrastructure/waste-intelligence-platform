#!/usr/bin/env python3
"""Seed the hub database with the demo bins and facilities.

Reads :data:`scripts.seed_data.BIN_SEED` / ``FACILITY_SEED`` and inserts them
into the ``bins`` / ``facilities`` tables from ``hub_layer/database/schema.sql``.
Idempotent: re-runs are safe (``ON CONFLICT DO NOTHING``).

Usage (from the repository root)::

    DATABASE_URL=postgresql://timescale:password@localhost:5432/wasteintel \\
        python scripts/seed_db.py

The seed dictionaries may carry fields the schema does not have (e.g.
``facility_type``, ``current_load_kg``); only columns present in the schema
are inserted.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Allow running as ``python scripts/seed_db.py`` from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from hub_layer.db import execute_sql  # noqa: E402
from scripts.seed_data import BIN_SEED, FACILITY_SEED  # noqa: E402

logger = logging.getLogger("seed_db")

SCHEMA_PATH = REPO_ROOT / "hub_layer" / "database" / "schema.sql"


def ensure_schema() -> None:
    """Apply the hub-layer schema (idempotent ``CREATE TABLE IF NOT EXISTS``)."""
    if not SCHEMA_PATH.exists():
        logger.warning("schema file not found at %s - skipping", SCHEMA_PATH)
        return
    statements = [s.strip() for s in SCHEMA_PATH.read_text(encoding="utf-8").split(";") if s.strip()]
    for stmt in statements:
        execute_sql(stmt)
    logger.info("schema ensured (%d statements)", len(statements))


def seed_bins() -> int:
    inserted = 0
    for b in BIN_SEED:
        inserted += execute_sql(
            "INSERT INTO bins (bin_id, cluster_id, facility_id, latitude, longitude, status) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (bin_id) DO NOTHING",
            (b["bin_id"], b.get("cluster_id"), b.get("facility_id"),
             b["latitude"], b["longitude"], b.get("status", "active")),
        )
    return inserted


def seed_facilities() -> int:
    inserted = 0
    for f in FACILITY_SEED:
        inserted += execute_sql(
            "INSERT INTO facilities (facility_id, name, latitude, longitude, capacity_kg) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (facility_id) DO NOTHING",
            (f["facility_id"], f["name"], f["latitude"], f["longitude"], f["capacity_kg"]),
        )
    return inserted


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("SEED_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    ensure_schema()
    bins = seed_bins()
    facilities = seed_facilities()
    print(f"seeded: {bins} new bins, {facilities} new facilities "
          f"(source: {len(BIN_SEED)} bins, {len(FACILITY_SEED)} facilities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
