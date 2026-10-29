"""Repository patterns for bin persistence and retrieval."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hub_layer.db import execute_sql, fetch_all


class BinRepository:
    def __init__(self) -> None:
        self._table = "bins"

    def list_bins(self, tenant_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self._table}"
        params = {}
        
        if tenant_id:
            query += " WHERE tenant_id = %(tenant_id)s"
            params["tenant_id"] = tenant_id
        
        query += " ORDER BY updated_at DESC LIMIT %(limit)s"
        params["limit"] = limit
        
        return fetch_all(query, params)

    def get_bin(self, bin_id: str) -> Optional[Dict[str, Any]]:
        rows = fetch_all(
            "SELECT * FROM bins WHERE bin_id = %s LIMIT 1",
            {"bin_id": bin_id}
        )
        return rows[0] if rows else None

    def get_bin_by_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        rows = fetch_all(
            "SELECT * FROM bins WHERE asset_id = %s LIMIT 1",
            {"asset_id": asset_id}
        )
        return rows[0] if rows else None

    def create_bin(self, data: Dict[str, Any]) -> None:
        execute_sql(
            """INSERT INTO bins 
               (bin_id, asset_id, tenant_id, cluster_id, facility_id, bin_type, bin_status, 
                last_collection_at, next_collection_at, capacity_kg, current_fill_level_percent, 
                current_mass_kg, has_sensor, sensor_id, sensor_type, color, brand, model, 
                source_system, data_status) 
               VALUES (:bin_id, :asset_id, :tenant_id, :cluster_id, :facility_id, :bin_type, 
                      :bin_status, :last_collection_at, :next_collection_at, :capacity_kg, 
                      :current_fill_level_percent, :current_mass_kg, :has_sensor, :sensor_id, 
                      :sensor_type, :color, :brand, :model, :source_system, :data_status)""",
            {
                "bin_id": data.get("bin_id"),
                "asset_id": data.get("asset_id"),
                "tenant_id": data.get("tenant_id"),
                "cluster_id": data.get("cluster_id", "unknown"),
                "facility_id": data.get("facility_id"),
                "bin_type": data.get("bin_type", "standard"),
                "bin_status": data.get("bin_status", "active"),
                "last_collection_at": data.get("last_collection_at"),
                "next_collection_at": data.get("next_collection_at"),
                "capacity_kg": data.get("capacity_kg", 500.0),
                "current_fill_level_percent": data.get("current_fill_level_percent", 0.0),
                "current_mass_kg": data.get("current_mass_kg", 0.0),
                "has_sensor": data.get("has_sensor", False),
                "sensor_id": data.get("sensor_id"),
                "sensor_type": data.get("sensor_type"),
                "color": data.get("color", "green"),
                "brand": data.get("brand"),
                "model": data.get("model"),
                "source_system": data.get("source_system", "win_os"),
                "data_status": data.get("data_status", "observed"),
            },
        )

    def update_bin(self, bin_id: str, data: Dict[str, Any]) -> int:
        set_clause = ", ".join([f"{k} = %({k})s" for k in data.keys()])
        query = f"UPDATE bins SET {set_clause} WHERE bin_id = %(bin_id)s"
        data["bin_id"] = bin_id
        return execute_sql(query, data)

    def delete_bin(self, bin_id: str) -> int:
        return execute_sql("DELETE FROM bins WHERE bin_id = %s", {"bin_id": bin_id})
