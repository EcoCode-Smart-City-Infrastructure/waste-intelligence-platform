# Database Schema - WIN OS

## Overview

This directory contains the PostgreSQL database schema for the Waste Intelligence Network Operating System (WIN OS). The schema is organized into multiple SQL files for better maintainability.

## Schema Files

### 01_extensions_and_types.sql
- Enables required PostgreSQL extensions (PostGIS, TimescaleDB, pg_cron, uuid-ossp)
- Defines all custom ENUM types used throughout the schema
- **Must be run first**

### 02_core_tables.sql
- Organizations, jurisdictions, service areas, tenants
- Users, permissions, roles, sessions, refresh tokens, audit logs
- Assets, bins, facilities, vehicles, fleets
- All indexes for core tables

### 03_operations_tables.sql
- Routes, route stops, collection events, collection schedules
- Waste types, waste streams, material classifications
- Contamination observations, material destinations, recovery pathways
- All indexes for operations tables

### 04_environmental_tables.sql
- Environmental metrics and records (time-series)
- Carbon accounting (time-series)
- Data sources, ingestion jobs, data quality assessments, provenance records
- Knowledge Graph tables (nodes, edges, pathways)
- All indexes for environmental and KG tables

### 05_intelligence_tables.sql
- Forecast models and runs
- Anomaly detections
- Optimization runs
- Simulations
- Telemetry (time-series)
- Weighing events (time-series)
- System health, backups
- Schema version tracking
- Functions, triggers, and comments
- Finalizes TimescaleDB setup

## Quick Start

### Initialize Database

```bash
# Connect to PostgreSQL
psql -U timescale -d wasteintel

# Run all schema files in order
\i hub_layer/database/01_extensions_and_types.sql
\i hub_layer/database/02_core_tables.sql
\i hub_layer/database/03_operations_tables.sql
\i hub_layer/database/04_environmental_tables.sql
\i hub_layer/database/05_intelligence_tables.sql
```

### Or use Docker

```bash
# Copy schema files to docker-entrypoint-initdb.d
cp hub_layer/database/0*.sql /docker-entrypoint-initdb.d/

# Start PostgreSQL with TimescaleDB
docker run -d --name timescaledb \
  -e POSTGRES_USER=timescale \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=wasteintel \
  -v $(pwd)/docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d \
  timescale/timescaledb:latest-pg15
```

## Schema Version

The current schema version is tracked in the `schema_versions` table. Version 1.0.0 includes the complete domain model for WIN OS.

## Key Features

### 1. Data Status Classification
All data records include a `data_status` field with the following vocabulary:
- `observed` - Direct measurement from sensors or verified reports
- `reported` - Human-reported data, not directly measured
- `derived` - Calculated or transformed from other data
- `forecast` - Predicted future values
- `simulated` - Generated from simulation models
- `unavailable` - Data not available or not applicable

### 2. Data Provenance
Every record includes provenance metadata:
- `source_system` - Origin system identifier
- `source_record_id` - Original record identifier in source system
- `ingestion_timestamp` - When the data was ingested (in provenance_records)
- `processing_timestamp` - When the data was processed/transformed
- `transformation_version` - Version of the transformation logic
- `ingestion_job_id` - ID of the ingestion job that processed this data

### 3. Geospatial Support
- PostGIS extension for spatial data types
- Geometry columns for locations (POINT, POLYGON)
- Spatial indexes for efficient querying
- EPSG:4326 (WGS84) coordinate reference system

### 4. Time-Series Support
- TimescaleDB extension for time-series data
- Hypertable conversion for telemetry, environmental records, etc.
- Efficient time-based queries and aggregations

### 5. Multi-Tenancy
- Tenant isolation through tenant_id columns
- Row-Level Security (RLS) ready (policies to be added)
- Organization and jurisdiction hierarchy

### 6. Knowledge Graph
- Dedicated tables for KG nodes and edges
- Type-specific properties stored as JSONB
- Pathway materialization for common queries

## Database Extensions

| Extension | Purpose | Version |
|-----------|---------|---------|
| postgis | Geospatial support | Latest |
| postgis_topology | Topology support | Latest |
| fuzzystrmatch | Fuzzy string matching | Latest |
| postgis_tiger_geocoder | Geocoding | Latest |
| timescaledb | Time-series database | Latest |
| pg_cron | Job scheduling | Latest |
| uuid-ossp | UUID generation | Latest |

## Domain Model

### Organizations & Tenancy
- **organizations** - Organizations using the platform
- **jurisdictions** - Geographic areas (cities, counties, districts)
- **service_areas** - Service areas within jurisdictions
- **tenants** - Multi-tenancy tenants

### Users & Authentication
- **users** - Platform users
- **permissions** - System permissions (RBAC)
- **roles** - User roles
- **role_permissions** - Role to permission mapping
- **user_roles** - User to role mapping
- **sessions** - Authentication sessions
- **refresh_tokens** - Long-lived authentication tokens
- **audit_logs** - Audit trail of user actions

### Assets & Infrastructure
- **assets** - Physical assets (bins, vehicles, equipment)
- **bins** - Waste bins/containers
- **facilities** - Waste processing facilities
- **vehicles** - Collection vehicles
- **fleets** - Vehicle fleets

### Operations
- **routes** - Collection routes
- **route_stops** - Stops along routes
- **collection_events** - Individual collection events
- **collection_schedules** - Scheduled collection times

### Waste Management
- **waste_types** - Types of waste materials
- **waste_streams** - Streams of waste from sources
- **material_classifications** - Material classification
- **contamination_observations** - Contamination observations
- **material_destinations** - Where materials are sent
- **recovery_pathways** - Paths from waste to resources

### Environmental Accounting
- **environmental_metrics** - Metric definitions
- **environmental_records** - Metric values (time-series)
- **carbon_accounting** - Carbon emissions tracking (time-series)

### Data Platform
- **data_sources** - External data source configurations
- **ingestion_jobs** - Data ingestion job tracking
- **data_quality_assessments** - Data quality results
- **provenance_records** - Data lineage tracking

### Knowledge Graph
- **kg_nodes** - Knowledge Graph nodes
- **kg_edges** - Knowledge Graph edges
- **kg_pathways** - Materialized pathways

### Intelligence
- **forecast_models** - Forecasting model definitions
- **forecast_runs** - Forecasting run results
- **anomaly_detections** - Anomaly detection results
- **optimization_runs** - Route optimization results
- **simulations** - Simulation results

### Telemetry
- **telemetry** - Sensor telemetry (time-series)
- **weighing_events** - Weighing events (time-series)

### System
- **system_health** - Service health checks
- **backups** - Backup job tracking
- **schema_versions** - Schema version history

## Migrations

For production use, we recommend using a migration tool like Alembic. The `migrations/` directory will contain version-controlled migration scripts.

## Backup & Restore

### Backup

```bash
# Full database backup
pg_dump -U timescale -d wasteintel -F c -f backup.dump

# Schema only
pg_dump -U timescale -d wasteintel -F c -s -f schema.dump

# Data only
pg_dump -U timescale -d wasteintel -F c -a -f data.dump
```

### Restore

```bash
# Restore full database
pg_restore -U timescale -d wasteintel -c backup.dump
```

## Performance Considerations

### Indexes
- All tables have appropriate indexes for common query patterns
- Spatial indexes on geometry columns
- Time-series tables use hypertables for efficient time-based queries

### Partitioning
- TimescaleDB automatically partitions time-series data by time
- Hypertable chunk size can be configured based on data volume

### Query Optimization
- Use spatial indexes for geospatial queries
- Use time-based indexes for time-series queries
- Consider materialized views for common aggregations

## Security

### Row-Level Security (RLS)
The schema is designed for RLS implementation. Add policies like:

```sql
-- Enable RLS on a table
ALTER TABLE bins ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
CREATE POLICY tenant_isolation_bins ON bins
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

### SSL
Always use SSL for database connections in production:

```sql
-- Force SSL for all connections
ALTER SYSTEM SET ssl = on;
```

## Monitoring

### Key Metrics to Monitor
- Database size and growth
- Query performance (slow query log)
- Connection count
- Cache hit ratio
- Lock contention
- Replication lag (if using replication)

### TimescaleDB Metrics
- Hypertable size
- Chunk count
- Compression ratio
- Query performance on time-series data

## Maintenance

### Regular Tasks
1. **Vacuum** - Reclaim space from deleted rows
2. **Analyze** - Update statistics for query planner
3. **Reindex** - Rebuild indexes periodically
4. **Backup** - Regular backups (daily recommended)
5. **Monitor** - Monitor database health and performance

### TimescaleDB Maintenance
1. **Compression** - Enable compression for hypertables
2. **Retention** - Set retention policies for time-series data
3. **Chunk Management** - Monitor and manage chunks

## Troubleshooting

### Common Issues

1. **Extension Errors**
   - Ensure all required extensions are installed
   - Check PostgreSQL version compatibility
   - Verify extension dependencies

2. **Type Errors**
   - Verify all ENUM types are created before tables
   - Check for typos in type definitions

3. **Reference Errors**
   - Verify table creation order (tables before references)
   - Check for circular references

4. **Permission Errors**
   - Ensure user has CREATE privileges
   - Check for schema restrictions

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Current | Initial complete schema |
