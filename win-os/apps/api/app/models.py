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
