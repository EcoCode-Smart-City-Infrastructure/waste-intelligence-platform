"""WIN OS core schema (PostgreSQL/PostGIS).

Creates the canonical WIN OS tables that mirror win-os/apps/api/app/models.py,
plus a PostGIS geometry column on assets/facilities kept in sync from lat/lon.
The fuller platform DDL in hub_layer/database/01-05*.sql remains the reference
schema for the legacy stack; this migration is the WIN OS source of truth and
the two are reconciled in docs/architecture/adr-011-win-os-foundation.md.

Revision ID: 0001_win_os_core
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_win_os_core"
down_revision = None
branch_labels = None
depends_on = None

DATA_STATUS = sa.Enum("observed", "reported", "derived", "forecast",
                      "simulated", "unavailable", name="win_data_status")

def provenance():
    return [
        sa.Column("data_status", DATA_STATUS, nullable=False, server_default="reported"),
        sa.Column("source_system", sa.String(120), server_default="win-os-api"),
        sa.Column("source_record_id", sa.String(200)),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("quality_status", sa.String(40), server_default="unknown"),
    ]

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table("organizations",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_table("assets",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("asset_type", sa.String(60), server_default="bin"),
        sa.Column("status", sa.String(60), server_default="active"),
        sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float),
        sa.Column("capacity_liters", sa.Float),
        sa.Column("service_area", sa.String(120)),
        *provenance(),
        sa.UniqueConstraint("org_id", "source_record_id", name="uq_asset_org_source"))
    op.execute("ALTER TABLE assets ADD COLUMN geom geometry(Point, 4326)")
    op.execute("CREATE INDEX ix_assets_geom ON assets USING GIST (geom)")
    op.execute("CREATE INDEX ix_assets_org ON assets (org_id)")
    op.create_table("facilities",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("facility_type", sa.String(60), server_default="transfer_station"),
        sa.Column("operational_status", sa.String(60), server_default="unknown"),
        sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float),
        sa.Column("accepted_materials", sa.Text),
        sa.Column("capacity_tons_per_day", sa.Float),
        *provenance(),
        sa.UniqueConstraint("org_id", "source_record_id", name="uq_facility_org_source"))
    op.execute("ALTER TABLE facilities ADD COLUMN geom geometry(Point, 4326)")
    op.execute("CREATE INDEX ix_facilities_geom ON facilities USING GIST (geom)")
    op.create_table("collection_events",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("asset_id", sa.String(80), nullable=False, index=True),
        sa.Column("status", sa.String(40), server_default="scheduled"),
        sa.Column("planned_at", sa.DateTime(timezone=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("quantity_kg", sa.Float),
        sa.Column("idempotency_key", sa.String(200)),
        *provenance(),
        sa.UniqueConstraint("org_id", "idempotency_key", name="uq_collection_org_idem"))
    op.create_table("route_plans",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("execution_status", sa.String(40), server_default="planned"),
        sa.Column("data_status", DATA_STATUS, server_default="derived"),
        sa.Column("stops_json", sa.Text, server_default="[]"),
        sa.Column("total_distance_km", sa.Float),
        sa.Column("method", sa.String(80), server_default="nearest-neighbour"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_table("ingestion_jobs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("status", sa.String(40), server_default="completed"),
        sa.Column("records_ok", sa.Integer, server_default="0"),
        sa.Column("records_quarantined", sa.Integer, server_default="0"),
        sa.Column("detail", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_table("forecast_runs",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("target", sa.String(120), nullable=False),
        sa.Column("model_id", sa.String(120), server_default="baseline-linear-trend"),
        sa.Column("model_version", sa.String(40), server_default="1.0.0"),
        sa.Column("training_window", sa.String(200)),
        sa.Column("predictions_json", sa.Text, server_default="[]"),
        sa.Column("metrics_json", sa.Text, server_default="{}"),
        sa.Column("limitations", sa.Text),
        sa.Column("data_status", DATA_STATUS, server_default="forecast"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_table("audit_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("actor_key_id", sa.String(80), nullable=False),
        sa.Column("actor_role", sa.String(60), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))

def downgrade():
    for table in ("audit_events", "forecast_runs", "ingestion_jobs", "route_plans",
                  "collection_events", "facilities", "assets", "organizations"):
        op.drop_table(table)
    op.execute("DROP TYPE IF EXISTS win_data_status")
