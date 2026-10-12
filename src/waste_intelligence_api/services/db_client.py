"""Database client for TimescaleDB.

Provides access to bin, cluster, and facility telemetry from the hub
schema (``hub_layer/database/schema.sql``):

- ``bins``       - registered bins with cluster/facility assignment and location
- ``facilities`` - waste facilities with capacity
- ``telemetry``  - bin sensor readings written by the MQTT bridge

Packets are shaped for the validators in ``packet_builder``:
``{"bin_id", "timestamp", "sensors", "location"}`` for bins,
``{"cluster_id", "timestamp", "aggregated"}`` for clusters, and
``{"facility_id", "facility_name", "timestamp", "load", "forecast"}``
for facilities.

Borough/district filters are accepted for API compatibility but are
not applied: the hub schema does not model boroughs or districts.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

from ..config import Config

logger = logging.getLogger(__name__)

# Connection pool
_connection_pool: list = []
_max_connections = int(os.environ.get("DB_POOL_SIZE", "5"))


def get_conn():
    """Get a database connection from the pool or create a new one."""
    global _connection_pool

    if _connection_pool:
        return _connection_pool.pop()

    try:
        # NOTE: isolation_level is not a valid libpq DSN option; it must be
        # set on the connection object after connecting.
        conn = psycopg2.connect(Config.DB_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def return_conn(conn):
    """Return a connection to the pool."""
    global _connection_pool

    if len(_connection_pool) < _max_connections:
        _connection_pool.append(conn)
    else:
        try:
            conn.close()
        except Exception:
            pass


def close_all_connections():
    """Close all connections in the pool."""
    global _connection_pool

    for conn in _connection_pool:
        try:
            conn.close()
        except Exception:
            pass
    _connection_pool = []


# Latest telemetry row per bin, reused by the bin/cluster/facility queries.
_LATEST_TELEMETRY = """
    SELECT DISTINCT ON (t.bin_id)
        t.bin_id, t.fill_level_percent, t.mass_kg, t.reported_at
    FROM telemetry t
    ORDER BY t.bin_id, t.reported_at DESC
"""


def _bin_packet(row) -> dict:
    """Shape a (bin_id, fill, mass, reported_at, lat, lon) row as a packet."""
    bin_id, fill, mass, reported_at, lat, lon = row
    return {
        "bin_id": bin_id,
        "timestamp": str(reported_at),
        "sensors": {
            "fill_level_percent": float(fill) if fill is not None else None,
            "mass_kg": float(mass) if mass is not None else None,
        },
        "location": {"latitude": lat, "longitude": lon},
    }


async def get_bin_packet(
    bin_id: str | None = None,
    limit: int = 1,
    offset: int = 0,
    history: bool = False,
    borough: str | None = None,  # noqa: ARG001 - accepted for API compatibility
    district: str | None = None,  # noqa: ARG001 - accepted for API compatibility
    list_all: bool = False,
) -> Any:
    """Get bin telemetry packet(s) from the ``telemetry`` table."""
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        if list_all:
            cur.execute(
                f"""
                SELECT l.bin_id, l.fill_level_percent, l.mass_kg, l.reported_at,
                       b.latitude, b.longitude
                FROM ({_LATEST_TELEMETRY}) l
                JOIN bins b ON b.bin_id = l.bin_id
                ORDER BY l.bin_id LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            return [_bin_packet(row) for row in cur.fetchall()]

        if history:
            cur.execute(
                """
                SELECT t.bin_id, t.fill_level_percent, t.mass_kg, t.reported_at,
                       b.latitude, b.longitude
                FROM telemetry t
                LEFT JOIN bins b ON b.bin_id = t.bin_id
                WHERE t.bin_id = %s
                ORDER BY t.reported_at DESC
                LIMIT %s OFFSET %s
                """,
                (bin_id, limit, offset),
            )
            return [_bin_packet(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT t.bin_id, t.fill_level_percent, t.mass_kg, t.reported_at,
                   b.latitude, b.longitude
            FROM telemetry t
            LEFT JOIN bins b ON b.bin_id = t.bin_id
            WHERE t.bin_id = %s
            ORDER BY t.reported_at DESC
            LIMIT %s
            """,
            (bin_id, limit),
        )
        row = cur.fetchone()
        return _bin_packet(row) if row else None

    except Exception as e:
        logger.error(f"Database error in get_bin_packet: {e}")
        raise
    finally:
        if conn:
            return_conn(conn)


async def get_cluster_packet(
    cluster_id: str | None = None,
    limit: int = 1,
    offset: int = 0,
    history: bool = False,
    borough: str | None = None,  # noqa: ARG001 - accepted for API compatibility
    district: str | None = None,  # noqa: ARG001 - accepted for API compatibility
    list_all: bool = False,
) -> Any:
    """Aggregate the latest bin telemetry per cluster.

    There is no cluster telemetry table; aggregates are computed live from
    the latest ``telemetry`` row of each bin in the cluster. History is not
    available and returns an empty list.
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        base = f"""
            SELECT b.cluster_id,
                   COUNT(*) AS bin_count,
                   AVG(l.fill_level_percent) AS avg_fill,
                   SUM(l.mass_kg) AS total_mass,
                   MAX(l.reported_at) AS latest
            FROM ({_LATEST_TELEMETRY}) l
            JOIN bins b ON b.bin_id = l.bin_id
        """

        def _cluster_packet(row) -> dict:
            cid, count, avg_fill, total_mass, latest = row
            return {
                "cluster_id": cid,
                "timestamp": str(latest),
                "aggregated": {
                    "bin_count": count,
                    "avg_fill_percent": float(avg_fill) if avg_fill is not None else None,
                    "total_mass_kg": float(total_mass) if total_mass is not None else None,
                },
            }

        if list_all:
            cur.execute(
                base + " GROUP BY b.cluster_id ORDER BY b.cluster_id LIMIT %s OFFSET %s",
                (limit, offset),
            )
            return [_cluster_packet(row) for row in cur.fetchall()]

        if history:
            return []

        cur.execute(base + " WHERE b.cluster_id = %s GROUP BY b.cluster_id", (cluster_id,))
        row = cur.fetchone()
        return _cluster_packet(row) if row else None

    except Exception as e:
        logger.error(f"Database error in get_cluster_packet: {e}")
        raise
    finally:
        if conn:
            return_conn(conn)


async def get_facility_packet(
    facility_id: str | None = None,
    limit: int = 1,
    offset: int = 0,
    history: bool = False,
    facility_type: str | None = None,  # noqa: ARG001 - not in the hub schema
    borough: str | None = None,  # noqa: ARG001 - accepted for API compatibility
    list_all: bool = False,
) -> Any:
    """Facility info plus live load aggregated from its bins' telemetry.

    Load is the sum of the latest ``telemetry`` readings of the bins
    assigned to the facility. History is not available and returns an
    empty list.
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        base = f"""
            SELECT f.facility_id, f.name, f.capacity_kg,
                   COUNT(b.bin_id) AS bin_count,
                   COALESCE(SUM(l.mass_kg), 0) AS total_mass,
                   MAX(l.reported_at) AS latest
            FROM facilities f
            LEFT JOIN bins b ON b.facility_id = f.facility_id
            LEFT JOIN ({_LATEST_TELEMETRY}) l ON l.bin_id = b.bin_id
        """

        def _facility_packet(row) -> dict:
            fid, name, capacity, count, total_mass, latest = row
            total_mass = float(total_mass)
            utilization = (total_mass / capacity * 100) if capacity else None
            return {
                "facility_id": fid,
                "facility_name": name,
                "timestamp": str(latest) if latest else "",
                "load": {
                    "bin_count": count,
                    "current_load_kg": total_mass,
                    "capacity_kg": float(capacity) if capacity is not None else None,
                    "utilization_percent": utilization,
                },
                "forecast": {},
            }

        if list_all:
            cur.execute(
                base + " GROUP BY f.facility_id, f.name, f.capacity_kg"
                       " ORDER BY f.facility_id LIMIT %s OFFSET %s",
                (limit, offset),
            )
            return [_facility_packet(row) for row in cur.fetchall()]

        if history:
            return []

        cur.execute(
            base + " WHERE f.facility_id = %s"
                   " GROUP BY f.facility_id, f.name, f.capacity_kg",
            (facility_id,),
        )
        row = cur.fetchone()
        return _facility_packet(row) if row else None

    except Exception as e:
        logger.error(f"Database error in get_facility_packet: {e}")
        raise
    finally:
        if conn:
            return_conn(conn)
