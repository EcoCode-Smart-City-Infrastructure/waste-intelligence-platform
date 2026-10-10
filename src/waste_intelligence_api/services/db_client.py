"""Database client for TimescaleDB.

Provides access to bin, cluster, and facility packet data from TimescaleDB.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import psycopg2
from psycopg2 import sql
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
        conn = psycopg2.connect(
            Config.DB_URL,
            isolation_level=ISOLATION_LEVEL_READ_COMMITTED,
        )
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


async def get_bin_packet(
    bin_id: str | None = None,
    limit: int = 1,
    offset: int = 0,
    history: bool = False,
    borough: str | None = None,
    district: str | None = None,
    list_all: bool = False,
) -> Any:
    """Get bin telemetry packet(s) from database.
    
    Args:
        bin_id: Bin identifier (optional for list_all)
        limit: Maximum number of packets
        offset: Pagination offset
        history: Whether to get historical data
        borough: Filter by borough
        district: Filter by district
        list_all: Whether to list all bins
        
    Returns:
        Bin packet(s) from database
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if list_all:
            # Get list of all bins with latest data
            query = """
                SELECT b.bin_id, b.timestamp, b.packet->'sensors' as sensors, 
                       b.packet->'location' as location
                FROM bin_packets b
                INNER JOIN (
                    SELECT bin_id, MAX(timestamp) as max_timestamp
                    FROM bin_packets
                    GROUP BY bin_id
                ) latest ON b.bin_id = latest.bin_id AND b.timestamp = latest.max_timestamp
            """
            params = []
            
            where_clauses = []
            if borough:
                where_clauses.append("b.packet->'location'->>'borough_id' = %s")
                params.append(borough)
            if district:
                where_clauses.append("b.packet->'location'->>'block_id' LIKE %s")
                params.append(f"{district}%")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY b.bin_id LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                packet = {
                    "bin_id": row[0],
                    "timestamp": row[1],
                    "sensors": row[2],
                    "location": row[3],
                }
                result.append(packet)
            
            return result
        
        elif history:
            # Get historical data for a specific bin
            query = """
                SELECT timestamp, packet
                FROM bin_packets
                WHERE bin_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (bin_id, limit, offset))
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                packet = row[1]
                if isinstance(packet, str):
                    import json
                    packet = json.loads(packet)
                packet["timestamp"] = str(row[0])
                result.append(packet)
            
            return result
        
        else:
            # Get latest packet for a specific bin
            query = """
                SELECT packet
                FROM bin_packets
                WHERE bin_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cur.execute(query, (bin_id, limit))
            row = cur.fetchone()
            
            if row:
                packet = row[0]
                if isinstance(packet, str):
                    import json
                    packet = json.loads(packet)
                return packet
            
            return None
            
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
    borough: str | None = None,
    district: str | None = None,
    list_all: bool = False,
) -> Any:
    """Get cluster telemetry packet(s) from database.
    
    Args:
        cluster_id: Cluster identifier (optional for list_all)
        limit: Maximum number of packets
        offset: Pagination offset
        history: Whether to get historical data
        borough: Filter by borough
        district: Filter by district
        list_all: Whether to list all clusters
        
    Returns:
        Cluster packet(s) from database
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if list_all:
            # Get list of all clusters with latest data
            query = """
                SELECT c.cluster_id, c.timestamp, c.packet->'aggregated' as aggregated
                FROM cluster_packets c
                INNER JOIN (
                    SELECT cluster_id, MAX(timestamp) as max_timestamp
                    FROM cluster_packets
                    GROUP BY cluster_id
                ) latest ON c.cluster_id = latest.cluster_id AND c.timestamp = latest.max_timestamp
            """
            params = []
            
            where_clauses = []
            if borough:
                where_clauses.append("c.packet->'location'->>'borough_id' = %s")
                params.append(borough)
            if district:
                where_clauses.append("c.packet->'location'->>'district_id' = %s")
                params.append(district)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY c.cluster_id LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                packet = {
                    "cluster_id": row[0],
                    "timestamp": row[1],
                    "aggregated": row[2],
                }
                result.append(packet)
            
            return result
        
        elif history:
            # Get historical data for a specific cluster
            query = """
                SELECT timestamp, packet
                FROM cluster_packets
                WHERE cluster_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (cluster_id, limit, offset))
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                packet = row[1]
                if isinstance(packet, str):
                    import json
                    packet = json.loads(packet)
                packet["timestamp"] = str(row[0])
                result.append(packet)
            
            return result
        
        else:
            # Get latest packet for a specific cluster
            query = """
                SELECT packet
                FROM cluster_packets
                WHERE cluster_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cur.execute(query, (cluster_id, limit))
            row = cur.fetchone()
            
            if row:
                packet = row[0]
                if isinstance(packet, str):
                    import json
                    packet = json.loads(packet)
                return packet
            
            return None
            
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
    facility_type: str | None = None,
    borough: str | None = None,
    list_all: bool = False,
) -> Any:
    """Get facility telemetry packet(s) from database.
    
    Args:
        facility_id: Facility identifier (optional for list_all)
        limit: Maximum number of packets
        offset: Pagination offset
        history: Whether to get historical data
        facility_type: Filter by facility type
        borough: Filter by borough
        list_all: Whether to list all facilities
        
    Returns:
        Facility packet(s) from database
    """
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        if list_all:
            # Get list of all facilities with latest data
            query = """
                SELECT f.facility_id, f.facility_name, f.timestamp, 
                       f.packet->'load' as load, 
                       f.packet->'forecast' as forecast
                FROM facility_packets f
                INNER JOIN (
                    SELECT facility_id, MAX(timestamp) as max_timestamp
                    FROM facility_packets
                    GROUP BY facility_id
                ) latest ON f.facility_id = latest.facility_id AND f.timestamp = latest.max_timestamp
            """
            params = []
            
            where_clauses = []
            if facility_type:
                where_clauses.append("f.packet->>'facility_type' = %s")
                params.append(facility_type)
            if borough:
                where_clauses.append("f.packet->'location'->>'borough' = %s")
                params.append(borough)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY f.facility_id LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                packet = {
                    "facility_id": row[0],
                    "facility_name": row[1],
                    "timestamp": row[2],
                    "load": row[3],
                    "forecast": row[4],
                }
                result.append(packet)
            
            return result
        
        elif history:
            # Get historical data for a specific facility
            query = """
                SELECT timestamp, packet
                FROM facility_packets
                WHERE facility_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(query, (facility_id, limit, offset))
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                packet = row[1]
                if isinstance(packet, str):
                    import json
                    packet = json.loads(packet)
                packet["timestamp"] = str(row[0])
                result.append(packet)
            
            return result
        
        else:
            # Get latest packet for a specific facility
            query = """
                SELECT facility_name, packet
                FROM facility_packets
                WHERE facility_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            cur.execute(query, (facility_id, limit))
            row = cur.fetchone()
            
            if row:
                packet = row[1]
                if isinstance(packet, str):
                    import json
                    packet = json.loads(packet)
                packet["facility_name"] = row[0]
                return packet
            
            return None
            
    except Exception as e:
        logger.error(f"Database error in get_facility_packet: {e}")
        raise
    finally:
        if conn:
            return_conn(conn)
