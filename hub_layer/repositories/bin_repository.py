"""Repository patterns for bin persistence and retrieval."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hub_layer.db import execute_sql, fetch_all


class BinRepository:
    def __init__(self) -> None:
        self._table = "bins"

    def list_bins(self) -> List[Dict[str, Any]]:
        # Schema has created_at, not updated_at (that column does not
        # exist, so the old ORDER BY failed on Postgres).
        # Join the latest telemetry row per bin so callers that need a
        # fill level (e.g. the web app's twin live-feed parser, which
        # requires fill) get one instead of dropping every hub row.
        # Bins with no telemetry get latest_fill_percent = NULL.
        return fetch_all(
            f"SELECT b.*, t.fill_level_percent AS latest_fill_percent "
            f"FROM {self._table} b "
            f"LEFT JOIN LATERAL ("
            f"SELECT fill_level_percent FROM telemetry "
            f"WHERE telemetry.bin_id = b.bin_id "
            f"ORDER BY reported_at DESC LIMIT 1) t ON TRUE "
            f"ORDER BY b.created_at DESC LIMIT 100;"
        )

    def get_bin(self, bin_id: str) -> Optional[Dict[str, Any]]:
        # Parameterized: the old f-string interpolation was SQL injection.
        rows = fetch_all(f"SELECT * FROM {self._table} WHERE bin_id = %s LIMIT 1;", (bin_id,))
        return rows[0] if rows else None

    def create_bin(self, data: Dict[str, Any]) -> None:
        execute_sql(
            "INSERT INTO bins (bin_id, cluster_id, facility_id, latitude, longitude, status) VALUES (:bin_id, :cluster_id, :facility_id, :latitude, :longitude, :status)",
            {
                "bin_id": data["bin_id"],
                "cluster_id": data.get("cluster_id", "unknown"),
                "facility_id": data.get("facility_id", "unknown"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "status": data.get("status", "active"),
            },
        )
