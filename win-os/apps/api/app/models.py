"""WIN OS core domain model (modular monolith).

Every operational record carries provenance (source system, source record id,
observation/ingestion timestamps) and an explicit data_status from the
vocabulary: observed | reported | derived | forecast | simulated | unavailable.
Missing measurements stay NULL - never zero. Geometry is stored as lat/lon
plus, on PostgreSQL, a PostGIS geometry column added by the Alembic migration
(win-os/data-platform/migrations); lat/lon is the portable source of truth.
"""
from __future__ import annotations
import enum
from datetime import datetime, timezone
from sqlalchemy import (DateTime, Enum, Float, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow():
    return datetime.now(timezone.utc)

class DataStatus(str, enum.Enum):
    observed = "observed"
    reported = "reported"
    derived = "derived"
    forecast = "forecast"
    simulated = "simulated"
    unavailable = "unavailable"

class Base(DeclarativeBase):
    pass

class ProvenanceMixin:
    data_status: Mapped[DataStatus] = mapped_column(
        Enum(DataStatus), default=DataStatus.reported, nullable=False)
    source_system: Mapped[str] = mapped_column(String(120), default="win-os-api")
    source_record_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(40), default="unknown")

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Asset(Base, ProvenanceMixin):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("org_id", "source_record_id",
                                       name="uq_asset_org_source"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(60), default="bin")
    status: Mapped[str] = mapped_column(String(60), default="active")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_liters: Mapped[float | None] = mapped_column(Float, nullable=True)
    service_area: Mapped[str | None] = mapped_column(String(120), nullable=True)

class Facility(Base, ProvenanceMixin):
    __tablename__ = "facilities"
    __table_args__ = (UniqueConstraint("org_id", "source_record_id",
                                       name="uq_facility_org_source"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(60), default="transfer_station")
    operational_status: Mapped[str] = mapped_column(String(60), default="unknown")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    accepted_materials: Mapped[str | None] = mapped_column(Text, nullable=True)
    # NULL means actual capacity is unknown; it is never displayed as 0.
    capacity_tons_per_day: Mapped[float | None] = mapped_column(Float, nullable=True)

class CollectionEvent(Base, ProvenanceMixin):
    __tablename__ = "collection_events"
    __table_args__ = (UniqueConstraint("org_id", "idempotency_key",
                                       name="uq_collection_org_idem"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    # scheduled | dispatched | reported | completed | missed | verified
    status: Mapped[str] = mapped_column(String(40), default="scheduled")
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quantity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)

class RoutePlan(Base):
    """A plan, never an executed route. execution stays 'planned' until a
    separate verified collection record exists."""
    __tablename__ = "route_plans"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(40), default="planned")
    data_status: Mapped[DataStatus] = mapped_column(Enum(DataStatus), default=DataStatus.derived)
    stops_json: Mapped[str] = mapped_column(Text, default="[]")
    total_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    method: Mapped[str] = mapped_column(String(80), default="nearest-neighbour")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="completed")
    records_ok: Mapped[int] = mapped_column(Integer, default=0)
    records_quarantined: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(120), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), default="baseline-linear-trend")
    model_version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    training_window: Mapped[str | None] = mapped_column(String(200), nullable=True)
    predictions_json: Mapped[str] = mapped_column(Text, default="[]")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_status: Mapped[DataStatus] = mapped_column(Enum(DataStatus), default=DataStatus.forecast)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_key_id: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Vehicle(Base, ProvenanceMixin):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("org_id", "source_record_id",
                                       name="uq_vehicle_org_source"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(60), default="collection_truck")
    # available | in_route | in_maintenance | out_of_service | offline | retired
    status: Mapped[str] = mapped_column(String(40), default="available")
    capacity_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fleet_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

class WasteStream(Base, ProvenanceMixin):
    __tablename__ = "waste_streams"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="mixed")
    material: Mapped[str | None] = mapped_column(String(120), nullable=True)

class RecoveryPathway(Base, ProvenanceMixin):
    __tablename__ = "recovery_pathways"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    waste_stream_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    # reuse | recycling | composting | anaerobic_digestion | energy_recovery | landfill
    pathway_type: Mapped[str] = mapped_column(String(60), default="recycling")
    # NULL = actual recovery performance is unknown; never displayed as a rate.
    diversion_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

class EnvironmentalRecord(Base):
    """A calculated estimate, always stored with its formula and method.
    data_status is 'derived' for calculations and 'simulated' for scenarios;
    measured inputs stay on their source records."""
    __tablename__ = "environmental_records"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    material: Mapped[str] = mapped_column(String(80), nullable=False)
    pathway_type: Mapped[str] = mapped_column(String(60), nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    co2e_kg: Mapped[float] = mapped_column(Float, nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(40), default="WIN-ENV-ACCT-1.0")
    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_status: Mapped[DataStatus] = mapped_column(Enum(DataStatus), default=DataStatus.derived)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("org_id", "device_id", name="uq_device_org"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TelemetryEvent(Base):
    """Edge telemetry. client_event_id makes offline store-and-forward
    replays idempotent. A device that has never reported has no events and
    its readings are 'unavailable' - never zero."""
    __tablename__ = "telemetry_events"
    __table_args__ = (UniqueConstraint("org_id", "device_id", "client_event_id",
                                       name="uq_telemetry_idem"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    client_event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    buffered_offline: Mapped[bool] = mapped_column(default=False)
    fill_level_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_status: Mapped[DataStatus] = mapped_column(Enum(DataStatus), default=DataStatus.observed)

class Scenario(Base):
    """Digital-twin / simulation run. Outputs are data_status=simulated and
    are never merged into observed or derived totals."""
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    results_json: Mapped[str] = mapped_column(Text, default="{}")
    data_status: Mapped[DataStatus] = mapped_column(Enum(DataStatus), default=DataStatus.simulated)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
