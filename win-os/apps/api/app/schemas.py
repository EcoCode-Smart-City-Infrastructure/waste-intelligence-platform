"""Validated request/response schemas for the WIN OS API (/api/v1)."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from .models import DataStatus

class AssetIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    asset_type: str = "bin"
    status: str = "active"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    capacity_liters: float | None = Field(default=None, ge=0)
    service_area: str | None = None
    data_status: DataStatus = DataStatus.reported
    source_system: str = "win-os-api"
    source_record_id: str | None = None
    observed_at: datetime | None = None

class AssetOut(AssetIn):
    id: str
    org_id: str
    ingested_at: datetime
    quality_status: str = "unknown"

class FacilityIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    facility_type: str = "transfer_station"
    operational_status: str = "unknown"
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accepted_materials: str | None = None
    capacity_tons_per_day: float | None = Field(default=None, ge=0)
    data_status: DataStatus = DataStatus.reported
    source_system: str = "win-os-api"
    source_record_id: str | None = None
    observed_at: datetime | None = None

class FacilityOut(FacilityIn):
    id: str
    org_id: str
    ingested_at: datetime
    quality_status: str = "unknown"

class CollectionIn(BaseModel):
    asset_id: str
    status: str = "scheduled"
    planned_at: datetime | None = None
    occurred_at: datetime | None = None
    quantity_kg: float | None = Field(default=None, ge=0)
    data_status: DataStatus = DataStatus.reported
    source_system: str = "win-os-api"

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        allowed = {"scheduled", "dispatched", "reported", "completed", "missed", "verified"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v

class ForecastIn(BaseModel):
    target: str = "waste_generation_kg"
    series: list[float] = Field(min_length=3)
    horizon: int = Field(default=3, ge=1, le=30)

class AnomalyIn(BaseModel):
    values: list[float] = Field(min_length=5)
    z_threshold: float = Field(default=3.0, ge=1.0, le=10.0)

class RoutePlanIn(BaseModel):
    name: str = "Planned route"
    depot_latitude: float = Field(ge=-90, le=90)
    depot_longitude: float = Field(ge=-180, le=180)
    asset_ids: list[str] = Field(min_length=1, max_length=200)

class CsvIngestIn(BaseModel):
    source: str = "csv-upload"
    records: list[dict]
