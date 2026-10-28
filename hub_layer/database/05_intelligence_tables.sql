-- Waste Intelligence Network Operating System (WIN OS)
-- PostgreSQL Database Schema - Part 5: Intelligence Tables
-- Version: 1.0.0

-- ============================================================================
-- INTELLIGENCE TABLES
-- ============================================================================

-- Forecast Models
CREATE TABLE IF NOT EXISTS forecast_models (
    id BIGSERIAL PRIMARY KEY,
    model_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_type forecast_model_type_enum NOT NULL,
    version VARCHAR(64) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    training_data_window_start TIMESTAMPTZ,
    training_data_window_end TIMESTAMPTZ,
    training_duration_seconds INTEGER,
    trained_at TIMESTAMPTZ,
    feature_definitions JSONB DEFAULT '{}',
    target_variables JSONB DEFAULT '[]',
    evaluation_metrics JSONB DEFAULT '{}',
    status forecast_model_status_enum NOT NULL DEFAULT 'draft',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Forecast Runs
CREATE TABLE IF NOT EXISTS forecast_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES forecast_models(model_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    run_type VARCHAR(128) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'pending',
    predictions JSONB NOT NULL DEFAULT '{}',
    prediction_timestamp TIMESTAMPTZ NOT NULL,
    run_started_at TIMESTAMPTZ,
    run_completed_at TIMESTAMPTZ,
    metrics JSONB DEFAULT '{}',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'forecast',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Anomaly Detections
CREATE TABLE IF NOT EXISTS anomaly_detections (
    id BIGSERIAL PRIMARY KEY,
    detection_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    detection_type anomaly_detection_type_enum NOT NULL,
    severity VARCHAR(32) NOT NULL,
    description TEXT NOT NULL,
    entity_type VARCHAR(128) NOT NULL,
    entity_id UUID NOT NULL,
    context_json JSONB DEFAULT '{}',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    status anomaly_status_enum NOT NULL DEFAULT 'detected',
    resolved_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    resolution_notes TEXT,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optimization Runs
CREATE TABLE IF NOT EXISTS optimization_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    scenario_id UUID,
    objective optimization_objective_enum NOT NULL,
    constraints JSONB DEFAULT '{}',
    result JSONB NOT NULL DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    run_started_at TIMESTAMPTZ,
    run_completed_at TIMESTAMPTZ,
    status VARCHAR(64) NOT NULL DEFAULT 'pending',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'simulated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Simulations
CREATE TABLE IF NOT EXISTS simulations (
    id BIGSERIAL PRIMARY KEY,
    simulation_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    simulation_type simulation_type_enum NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    results JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    status simulation_status_enum NOT NULL DEFAULT 'created',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'simulated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TELEMETRY TABLES (Time-series)
-- ============================================================================

-- Telemetry (enhanced)
CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL PRIMARY KEY,
    telemetry_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    bin_id UUID REFERENCES bins(bin_id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(asset_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    sensor_id VARCHAR(128),
    sensor_type VARCHAR(64),
    device_id VARCHAR(128),
    fill_level_percent DOUBLE PRECISION,
    mass_kg DOUBLE PRECISION,
    volume_m3 DOUBLE PRECISION,
    temperature_celsius DOUBLE PRECISION,
    humidity_percent DOUBLE PRECISION,
    contamination_flag BOOLEAN DEFAULT FALSE,
    contamination_types contamination_type_enum[],
    overflow_flag BOOLEAN DEFAULT FALSE,
    tamper_flag BOOLEAN DEFAULT FALSE,
    location_geom GEOMETRY(POINT, 4326),
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal_strength_dbm DOUBLE PRECISION,
    battery_percent DOUBLE PRECISION,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    data_quality_status data_quality_status_enum DEFAULT 'unknown',
    confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable for time-series data
SELECT create_hypertable('telemetry', 'reported_at');

-- Weighing Events
CREATE TABLE IF NOT EXISTS weighing_events (
    id BIGSERIAL PRIMARY KEY,
    weighing_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    bin_id UUID REFERENCES bins(bin_id) ON DELETE SET NULL,
    collection_event_id UUID REFERENCES collection_events(collection_event_id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    mass_kg DOUBLE PRECISION NOT NULL,
    previous_mass_kg DOUBLE PRECISION,
    net_mass_kg DOUBLE PRECISION,
    weighed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable for time-series data
SELECT create_hypertable('weighing_events', 'weighed_at');

-- ============================================================================
-- SYSTEM TABLES
-- ============================================================================

-- System Health
CREATE TABLE IF NOT EXISTS system_health (
    id BIGSERIAL PRIMARY KEY,
    health_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    service_name VARCHAR(128) NOT NULL,
    service_version VARCHAR(64),
    status VARCHAR(64) NOT NULL,
    metrics JSONB DEFAULT '{}',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Backups
CREATE TABLE IF NOT EXISTS backups (
    id BIGSERIAL PRIMARY KEY,
    backup_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    backup_type backup_type_enum NOT NULL,
    backup_name VARCHAR(255) NOT NULL,
    description TEXT,
    storage_location VARCHAR(512) NOT NULL,
    storage_size_bytes BIGINT,
    status backup_status_enum NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    verified_at TIMESTAMPTZ,
    verification_status VARCHAR(64),
    retention_policy VARCHAR(64),
    expires_at TIMESTAMPTZ,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================

-- Schema metadata
CREATE TABLE IF NOT EXISTS schema_versions (
    id BIGSERIAL PRIMARY KEY,
    version VARCHAR(64) NOT NULL,
    description TEXT,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by VARCHAR(255)
);

-- Record this schema version
INSERT INTO schema_versions (version, description, applied_by) 
VALUES ('1.0.0', 'Initial WIN OS schema with full domain model', 'schema.sql')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE organizations IS 'Organizations that use the WIN OS platform';
COMMENT ON TABLE jurisdictions IS 'Geographic jurisdictions (cities, counties, districts)';
COMMENT ON TABLE service_areas IS 'Service areas within jurisdictions';
COMMENT ON TABLE tenants IS 'Multi-tenancy tenants';
COMMENT ON TABLE users IS 'Platform users';
COMMENT ON TABLE permissions IS 'System permissions';
COMMENT ON TABLE roles IS 'User roles';
COMMENT ON TABLE role_permissions IS 'Many-to-many: roles to permissions';
COMMENT ON TABLE user_roles IS 'Many-to-many: users to roles';
COMMENT ON TABLE sessions IS 'User authentication sessions';
COMMENT ON TABLE refresh_tokens IS 'Refresh tokens for long-lived authentication';
COMMENT ON TABLE audit_logs IS 'Audit log of all user actions';
COMMENT ON TABLE assets IS 'Physical assets (bins, vehicles, equipment)';
COMMENT ON TABLE bins IS 'Waste bins/containers';
COMMENT ON TABLE facilities IS 'Waste processing facilities';
COMMENT ON TABLE vehicles IS 'Collection vehicles';
COMMENT ON TABLE fleets IS 'Vehicle fleets';
COMMENT ON TABLE routes IS 'Collection routes';
COMMENT ON TABLE route_stops IS 'Stops along collection routes';
COMMENT ON TABLE collection_events IS 'Individual collection events';
COMMENT ON TABLE collection_schedules IS 'Scheduled collection times';
COMMENT ON TABLE waste_types IS 'Types of waste materials';
COMMENT ON TABLE waste_streams IS 'Streams of waste from sources';
COMMENT ON TABLE material_classifications IS 'Classification of materials';
COMMENT ON TABLE contamination_observations IS 'Observations of contamination';
COMMENT ON TABLE material_destinations IS 'Where materials are sent';
COMMENT ON TABLE recovery_pathways IS 'Paths from waste to resources';
COMMENT ON TABLE environmental_metrics IS 'Environmental metric definitions';
COMMENT ON TABLE environmental_records IS 'Environmental metric values (time-series)';
COMMENT ON TABLE carbon_accounting IS 'Carbon emissions accounting (time-series)';
COMMENT ON TABLE data_sources IS 'External data source configurations';
COMMENT ON TABLE ingestion_jobs IS 'Data ingestion job tracking';
COMMENT ON TABLE data_quality_assessments IS 'Data quality assessment results';
COMMENT ON TABLE provenance_records IS 'Data provenance tracking';
COMMENT ON TABLE kg_nodes IS 'Knowledge Graph nodes';
COMMENT ON TABLE kg_edges IS 'Knowledge Graph edges';
COMMENT ON TABLE kg_pathways IS 'Knowledge Graph materialized pathways';
COMMENT ON TABLE forecast_models IS 'Forecasting model definitions';
COMMENT ON TABLE forecast_runs IS 'Forecasting run results';
COMMENT ON TABLE anomaly_detections IS 'Anomaly detection results';
COMMENT ON TABLE optimization_runs IS 'Route optimization results';
COMMENT ON TABLE simulations IS 'Simulation results';
COMMENT ON TABLE telemetry IS 'Sensor telemetry data (time-series)';
COMMENT ON TABLE weighing_events IS 'Weighing event data (time-series)';
COMMENT ON TABLE system_health IS 'System health check results';
COMMENT ON TABLE backups IS 'Backup job tracking';

-- ============================================================================
-- FINALIZE TIMESCALEDB
-- ============================================================================

-- Finalize timescaledb setup
SELECT timescaledb_post_restore();

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
