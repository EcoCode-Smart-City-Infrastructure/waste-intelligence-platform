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
