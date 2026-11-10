"""Keep PostGIS geom in sync with lat/lon automatically (assets, facilities).

Found during the 2026-11-10 field verification: the API writes lat/lon, and
geom stayed NULL until a manual UPDATE. This trigger makes geom a pure
function of lat/lon for every writer, present and future.

Revision ID: 0003_geom_sync
Revises: 0002_operations_edge
"""
from alembic import op

revision = "0003_geom_sync"
down_revision = "0002_operations_edge"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE OR REPLACE FUNCTION win_sync_geom() RETURNS trigger AS $$
    BEGIN
        IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
            NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
        ELSE
            NEW.geom := NULL;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    for table in ("assets", "facilities"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_geom ON {table}")
        op.execute(f"""
        CREATE TRIGGER trg_{table}_geom BEFORE INSERT OR UPDATE
        OF latitude, longitude ON {table}
        FOR EACH ROW EXECUTE FUNCTION win_sync_geom();
        """)
        op.execute(f"""
        UPDATE {table} SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
        """)

def downgrade():
    for table in ("assets", "facilities"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_geom ON {table}")
    op.execute("DROP FUNCTION IF EXISTS win_sync_geom()")
