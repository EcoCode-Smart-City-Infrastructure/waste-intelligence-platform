"""Repository patterns for facility persistence and retrieval."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hub_layer.db import execute_sql, fetch_all


class FacilityRepository:
    def __init__(self) -> None:
        self._table = "facilities"

    def list_facilities(self) -> List[Dict[str, Any]]:
        return fetch_all(f"SELECT * FROM {self._table} ORDER BY created_at DESC LIMIT 100;")

    def get_facility(self, facility_id: str) -> Optional[Dict[str, Any]]:
        # Parameterized: the old f-string interpolation was SQL injection.
        rows = fetch_all(f"SELECT * FROM {self._table} WHERE facility_id = %s LIMIT 1;", (facility_id,))
        return rows[0] if rows else None

    def create_facility(self, data: Dict[str, Any]) -> None:
        execute_sql(
            "INSERT INTO facilities (facility_id, name, facility_type, latitude, longitude, capacity_kg, current_load_kg, status) VALUES (:facility_id, :name, :facility_type, :latitude, :longitude, :capacity_kg, :current_load_kg, :status)",
            {
                "facility_id": data["facility_id"],
                "name": data.get("name", data["facility_id"]),
                "facility_type": data.get("facility_type", "transfer"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "capacity_kg": data.get("capacity_kg", 0.0),
                "current_load_kg": data.get("current_load_kg", 0.0),
                "status": data.get("status", "operational"),
            },
        )
