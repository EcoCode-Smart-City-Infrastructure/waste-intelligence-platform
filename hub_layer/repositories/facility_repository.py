"""Repository patterns for facility persistence and retrieval."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hub_layer.db import execute_sql, fetch_all


class FacilityRepository:
    def __init__(self) -> None:
        self._table = "facilities"

    def list_facilities(self, tenant_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self._table}"
        params = {}
        
        if tenant_id:
            query += " WHERE tenant_id = %(tenant_id)s"
            params["tenant_id"] = tenant_id
        
        query += " ORDER BY created_at DESC LIMIT %(limit)s"
        params["limit"] = limit
        
        return fetch_all(query, params)

    def get_facility(self, facility_id: str) -> Optional[Dict[str, Any]]:
        rows = fetch_all(
            "SELECT * FROM facilities WHERE facility_id = %s LIMIT 1",
            {"facility_id": facility_id}
        )
        return rows[0] if rows else None

    def get_facility_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        rows = fetch_all(
            "SELECT * FROM facilities WHERE name = %s LIMIT 1",
            {"name": name}
        )
        return rows[0] if rows else None

    def create_facility(self, data: Dict[str, Any]) -> None:
        execute_sql(
            """INSERT INTO facilities 
               (facility_id, tenant_id, organization_id, name, description, facility_type, 
                operational_status, location_geom, address, city, state, postal_code, country, 
                contact_name, contact_email, contact_phone, website, capacity_kg, 
                capacity_tonnes_per_year, current_load_kg, operating_hours, days_of_operation, 
                accepts_public, accepted_waste_types, supported_process_ids, 
                source_system, data_status) 
               VALUES (:facility_id, :tenant_id, :organization_id, :name, :description, :facility_type, 
                      :operational_status, ST_GeomFromText(:location_geom, 4326), :address, :city, 
                      :state, :postal_code, :country, :contact_name, :contact_email, :contact_phone, 
                      :website, :capacity_kg, :capacity_tonnes_per_year, :current_load_kg, 
                      :operating_hours, :days_of_operation, :accepts_public, :accepted_waste_types, 
                      :supported_process_ids, :source_system, :data_status)""",
            {
                "facility_id": data.get("facility_id"),
                "tenant_id": data.get("tenant_id"),
                "organization_id": data.get("organization_id"),
                "name": data.get("name", data.get("facility_id", "")),
                "description": data.get("description", ""),
                "facility_type": data.get("facility_type", "transfer_station"),
                "operational_status": data.get("operational_status", "operational"),
                "location_geom": data.get("location_geom", "POINT(0 0)"),
                "address": data.get("address", ""),
                "city": data.get("city", "New York"),
                "state": data.get("state", "NY"),
                "postal_code": data.get("postal_code", "10001"),
                "country": data.get("country", "USA"),
                "contact_name": data.get("contact_name"),
                "contact_email": data.get("contact_email"),
                "contact_phone": data.get("contact_phone"),
                "website": data.get("website"),
                "capacity_kg": data.get("capacity_kg", 0.0),
                "capacity_tonnes_per_year": data.get("capacity_tonnes_per_year", 0.0),
                "current_load_kg": data.get("current_load_kg", 0.0),
                "operating_hours": data.get("operating_hours", "09:00-17:00"),
                "days_of_operation": data.get("days_of_operation", "Monday-Friday"),
                "accepts_public": data.get("accepts_public", False),
                "accepted_waste_types": data.get("accepted_waste_types", []),
                "supported_process_ids": data.get("supported_process_ids", []),
                "source_system": data.get("source_system", "win_os"),
                "data_status": data.get("data_status", "reported"),
            },
        )

    def update_facility(self, facility_id: str, data: Dict[str, Any]) -> int:
        set_clause = ", ".join([f"{k} = %({k})s" for k in data.keys()])
        query = f"UPDATE facilities SET {set_clause} WHERE facility_id = %(facility_id)s"
        data["facility_id"] = facility_id
        return execute_sql(query, data)

    def delete_facility(self, facility_id: str) -> int:
        return execute_sql("DELETE FROM facilities WHERE facility_id = %s", {"facility_id": facility_id})
