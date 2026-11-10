"""WIN OS v0.2: operations, accounting, edge and simulation tables.

Revision ID: 0002_operations_edge
Revises: 0001_win_os_core
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_operations_edge"
down_revision = "0001_win_os_core"
branch_labels = None
depends_on = None

DATA_STATUS = sa.Enum("observed", "reported", "derived", "forecast",
                      "simulated", "unavailable", name="win_data_status",
                      create_type=False)

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
    op.create_table("vehicles",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("vehicle_type", sa.String(60), server_default="collection_truck"),
        sa.Column("status", sa.String(40), server_default="available"),
        sa.Column("capacity_kg", sa.Float), sa.Column("fuel_type", sa.String(40)),
        sa.Column("fleet_name", sa.String(120)),
        *provenance(),
        sa.UniqueConstraint("org_id", "source_record_id", name="uq_vehicle_org_source"))
    op.create_table("waste_streams",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(60), server_default="mixed"),
        sa.Column("material", sa.String(120)),
        *provenance())
    op.create_table("recovery_pathways",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("waste_stream_id", sa.String(80), nullable=False, index=True),
        sa.Column("facility_id", sa.String(80), nullable=False, index=True),
        sa.Column("pathway_type", sa.String(60), server_default="recycling"),
        sa.Column("diversion_rate_pct", sa.Float),
        *provenance())
    op.create_table("environmental_records",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("material", sa.String(80), nullable=False),
        sa.Column("pathway_type", sa.String(60), nullable=False),
        sa.Column("quantity_kg", sa.Float, nullable=False),
        sa.Column("co2e_kg", sa.Float, nullable=False),
        sa.Column("formula", sa.Text, nullable=False),
        sa.Column("methodology_version", sa.String(40), server_default="WIN-ENV-ACCT-1.0"),
        sa.Column("assumptions", sa.Text),
        sa.Column("data_status", DATA_STATUS, server_default="derived"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_table("devices",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("device_id", sa.String(120), nullable=False),
        sa.Column("asset_id", sa.String(80)),
        sa.Column("firmware_version", sa.String(60)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "device_id", name="uq_device_org"))
    op.create_table("telemetry_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("device_id", sa.String(120), nullable=False, index=True),
        sa.Column("client_event_id", sa.String(120), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("buffered_offline", sa.Boolean, server_default=sa.text("false")),
        sa.Column("fill_level_percent", sa.Float),
        sa.Column("weight_kg", sa.Float),
        sa.Column("data_status", DATA_STATUS, server_default="observed"),
        sa.UniqueConstraint("org_id", "device_id", "client_event_id",
                            name="uq_telemetry_idem"))
    op.execute("CREATE INDEX ix_telemetry_observed ON telemetry_events (observed_at DESC)")
    op.create_table("scenarios",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("org_id", sa.String(80), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("params_json", sa.Text, server_default="{}"),
        sa.Column("results_json", sa.Text, server_default="{}"),
        sa.Column("data_status", DATA_STATUS, server_default="simulated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))

def downgrade():
    for table in ("scenarios", "telemetry_events", "devices", "environmental_records",
                  "recovery_pathways", "waste_streams", "vehicles"):
        op.drop_table(table)
