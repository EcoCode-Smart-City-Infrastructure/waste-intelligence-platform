-- Waste Intelligence Network Operating System (WIN OS)
-- PostgreSQL Database Schema - Part 4: Environmental Accounting Tables
-- Version: 1.0.0

-- ============================================================================
-- ENVIRONMENTAL ACCOUNTING TABLES
-- ============================================================================

-- Environmental Metrics
CREATE TABLE IF NOT EXISTS environmental_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category metric_category_enum NOT NULL,
    unit metric_unit_enum NOT NULL,
    calculation_formula TEXT,
    calculation_methodology VARCHAR(255),
    methodology_version VARCHAR(64),
    assumptions TEXT,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Environmental Records (time-series)
CREATE TABLE IF NOT EXISTS environmental_records (
    id BIGSERIAL PRIMARY KEY,
    record_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    metric_id UUID NOT NULL REFERENCES environmental_metrics(metric_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    value DOUBLE PRECISION NOT NULL,
    unit metric_unit_enum NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    context_json JSONB DEFAULT '{}',
    source_system VARCHAR(128) NOT NULL,
    source_record_id VARCHAR(255),
    calculation_version VARCHAR(64),
    data_source VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable for time-series data
SELECT create_hypertable('environmental_records', 'timestamp');

-- Carbon Accounting (time-series)
CREATE TABLE IF NOT EXISTS carbon_accounting (
    id BIGSERIAL PRIMARY KEY,
    accounting_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    activity_type VARCHAR(128) NOT NULL,
    activity_description TEXT,
    emissions_kg_co2 DOUBLE PRECISION NOT NULL,
    emissions_kg_co2e DOUBLE PRECISION,
    scope VARCHAR(32),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system VARCHAR(128) NOT NULL,
    source_record_id VARCHAR(255),
    methodology VARCHAR(255) NOT NULL,
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    confidence DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable for time-series data
SELECT create_hypertable('carbon_accounting', 'timestamp');

-- ============================================================================
-- DATA PLATFORM TABLES
-- ============================================================================

-- Data Sources
CREATE TABLE IF NOT EXISTS data_sources (
    id BIGSERIAL PRIMARY KEY,
    source_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type data_source_type_enum NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    auth_type VARCHAR(64),
    auth_configuration JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    last_sync_status VARCHAR(64),
    last_sync_error TEXT,
    sync_frequency_minutes INTEGER DEFAULT 60,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Ingestion Jobs
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES data_sources(source_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    job_type VARCHAR(128) NOT NULL,
    status ingestion_job_status_enum NOT NULL DEFAULT 'pending',
    records_processed INTEGER DEFAULT 0,
    records_successful INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    errors TEXT[],
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Data Quality Assessments
CREATE TABLE IF NOT EXISTS data_quality_assessments (
    id BIGSERIAL PRIMARY KEY,
    assessment_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES ingestion_jobs(job_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    metric_description TEXT,
    value DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    status data_quality_status_enum NOT NULL DEFAULT 'unknown',
    context_json JSONB DEFAULT '{}',
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Provenance Records
CREATE TABLE IF NOT EXISTS provenance_records (
    id BIGSERIAL PRIMARY KEY,
    provenance_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    record_type VARCHAR(128) NOT NULL,
    record_id UUID NOT NULL,
    source_system VARCHAR(128) NOT NULL,
    source_record_id VARCHAR(255),
    source_publication_timestamp TIMESTAMPTZ,
    transformation_version VARCHAR(64),
    transformation_description TEXT,
    observation_timestamp TIMESTAMPTZ,
    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_timestamp TIMESTAMPTZ,
    data_quality_status data_quality_status_enum DEFAULT 'unknown',
    confidence DOUBLE PRECISION,
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    ingestion_job_id UUID REFERENCES ingestion_jobs(job_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- KNOWLEDGE GRAPH TABLES
-- ============================================================================

-- KG Nodes
CREATE TABLE IF NOT EXISTS kg_nodes (
    id BIGSERIAL PRIMARY KEY,
    node_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    node_type kg_node_type_enum NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    properties JSONB DEFAULT '{}',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, node_id)
);

-- KG Edges
CREATE TABLE IF NOT EXISTS kg_edges (
    id BIGSERIAL PRIMARY KEY,
    edge_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    edge_type kg_edge_type_enum NOT NULL,
    source_id UUID NOT NULL REFERENCES kg_nodes(node_id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES kg_nodes(node_id) ON DELETE CASCADE,
    properties JSONB DEFAULT '{}',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, edge_id),
    UNIQUE(tenant_id, source_id, edge_type, target_id)
);

-- KG Pathways (materialized view for common queries)
CREATE TABLE IF NOT EXISTS kg_pathways (
    id BIGSERIAL PRIMARY KEY,
    pathway_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    waste_type_id UUID NOT NULL REFERENCES kg_nodes(node_id) ON DELETE CASCADE,
    process_id UUID NOT NULL REFERENCES kg_nodes(node_id) ON DELETE CASCADE,
    resource_id UUID NOT NULL REFERENCES kg_nodes(node_id) ON DELETE CASCADE,
    efficiency DOUBLE PRECISION,
    carbon_footprint_kg_co2_per_tonne DOUBLE PRECISION,
    economic_value_per_tonne DOUBLE PRECISION,
    facility_ids UUID[],
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, waste_type_id, process_id, resource_id)
);

-- ============================================================================
-- INDEXES FOR ENVIRONMENTAL AND KG TABLES
-- ============================================================================

-- Environmental Metrics
CREATE INDEX IF NOT EXISTS idx_env_metrics_tenant ON environmental_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_env_metrics_name ON environmental_metrics(name);
CREATE INDEX IF NOT EXISTS idx_env_metrics_category ON environmental_metrics(category);

-- Environmental Records
CREATE INDEX IF NOT EXISTS idx_env_records_metric ON environmental_records(metric_id);
CREATE INDEX IF NOT EXISTS idx_env_records_tenant ON environmental_records(tenant_id);
CREATE INDEX IF NOT EXISTS idx_env_records_timestamp ON environmental_records(timestamp);

-- Carbon Accounting
CREATE INDEX IF NOT EXISTS idx_carbon_tenant ON carbon_accounting(tenant_id);
CREATE INDEX IF NOT EXISTS idx_carbon_timestamp ON carbon_accounting(timestamp);

-- Data Sources
CREATE INDEX IF NOT EXISTS idx_data_sources_tenant ON data_sources(tenant_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_name ON data_sources(name);
CREATE INDEX IF NOT EXISTS idx_data_sources_type ON data_sources(source_type);

-- Ingestion Jobs
CREATE INDEX IF NOT EXISTS idx_ingestion_source ON ingestion_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_tenant ON ingestion_jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_status ON ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_started ON ingestion_jobs(started_at);

-- Data Quality Assessments
CREATE INDEX IF NOT EXISTS idx_quality_job ON data_quality_assessments(job_id);
CREATE INDEX IF NOT EXISTS idx_quality_tenant ON data_quality_assessments(tenant_id);

-- Provenance Records
CREATE INDEX IF NOT EXISTS idx_provenance_tenant ON provenance_records(tenant_id);
CREATE INDEX IF NOT EXISTS idx_provenance_record ON provenance_records(record_type, record_id);

-- KG Nodes
CREATE INDEX IF NOT EXISTS idx_kg_nodes_tenant ON kg_nodes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_kgnodes_type ON kg_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_kgnodes_name ON kg_nodes(name);

-- KG Edges
CREATE INDEX IF NOT EXISTS idx_kgedges_tenant ON kg_edges(tenant_id);
CREATE INDEX IF NOT EXISTS idx_kgedges_type ON kg_edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_kgedges_source ON kg_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_kgedges_target ON kg_edges(target_id);

-- KG Pathways
CREATE INDEX IF NOT EXISTS idx_kgpathways_tenant ON kg_pathways(tenant_id);
CREATE INDEX IF NOT EXISTS idx_kgpathways_waste_type ON kg_pathways(waste_type_id);
