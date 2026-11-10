# WIN OS migrations

Alembic owns the WIN OS schema on PostgreSQL/PostGIS deployments.

```bash
export WIN_DATABASE_URL=postgresql+psycopg://winos:<password>@localhost:5433/winos
cd win-os/data-platform/migrations
alembic upgrade head
```

SQLite development runs create tables from the SQLAlchemy models instead;
SQLite is never a production database (the API refuses it when
WIN_ENVIRONMENT=production). Geometry: EPSG:4326 throughout; `geom` columns
are GiST-indexed and populated from lat/lon by the ingestion layer.

## PostGIS extension privilege (verified 2026-11-10)

`CREATE EXTENSION postgis` requires superuser. In the Compose deployment the
database user is the cluster superuser, so migration 0001 creates it. On a
managed/shared PostgreSQL, an administrator must run
`CREATE EXTENSION IF NOT EXISTS postgis;` once before `alembic upgrade head`,
otherwise the migration stops with "permission denied to create extension" -
that is expected behaviour, not a migration defect.
