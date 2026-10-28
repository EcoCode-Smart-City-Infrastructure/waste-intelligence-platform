-- Waste Intelligence Network Operating System (WIN OS)
-- PostgreSQL Database Schema - Part 3: Operations Tables
-- Version: 1.0.0

-- ============================================================================
-- OPERATIONS TABLES
-- ============================================================================

-- Routes
CREATE TABLE IF NOT EXISTS routes (
    id BIGSERIAL PRIMARY KEY,
    route_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    route_code VARCHAR(64),
    status route_status_enum NOT NULL DEFAULT 'planned',
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    vehicle_id UUID REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,
    driver_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    total_distance_km DOUBLE PRECISION DEFAULT 0,
    total_duration_minutes INTEGER DEFAULT 0,
    total_waste_kg DOUBLE PRECISION DEFAULT 0,
    total_stops INTEGER DEFAULT 0,
    completed_stops INTEGER DEFAULT 0,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Route Stops
CREATE TABLE IF NOT EXISTS route_stops (
    id BIGSERIAL PRIMARY KEY,
    route_stop_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    route_id UUID NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    bin_id UUID REFERENCES bins(bin_id) ON DELETE SET NULL,
    asset_id UUID REFERENCES assets(asset_id) ON DELETE SET NULL,
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE SET NULL,
    location_geom GEOMETRY(POINT, 4326),
    address TEXT,
    scheduled_arrival TIMESTAMPTZ,
    scheduled_departure TIMESTAMPTZ,
    actual_arrival TIMESTAMPTZ,
    actual_departure TIMESTAMPTZ,
    status route_stop_status_enum NOT NULL DEFAULT 'pending',
    distance_from_previous_km DOUBLE PRECISION DEFAULT 0,
    duration_minutes INTEGER DEFAULT 0,
    waste_collected_kg DOUBLE PRECISION DEFAULT 0,
    notes TEXT,
    exception_reason TEXT,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(route_id, sequence)
);

-- Collection Events
CREATE TABLE IF NOT EXISTS collection_events (
    id BIGSERIAL PRIMARY KEY,
    collection_event_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    route_stop_id UUID REFERENCES route_stops(route_stop_id) ON DELETE SET NULL,
    route_id UUID REFERENCES routes(route_id) ON DELETE SET NULL,
    bin_id UUID REFERENCES bins(bin_id) ON DELETE SET NULL,
    vehicle_id UUID REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    status collection_event_status_enum NOT NULL DEFAULT 'scheduled',
    scheduled_at TIMESTAMPTZ,
    dispatched_at TIMESTAMPTZ,
    arrived_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    waste_mass_kg DOUBLE PRECISION,
    fill_level_before_percent DOUBLE PRECISION,
    fill_level_after_percent DOUBLE PRECISION,
    contamination_flag BOOLEAN DEFAULT FALSE,
    contamination_severity contamination_severity_enum,
    contamination_types contamination_type_enum[],
    driver_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    crew_members UUID[],
    duration_minutes INTEGER,
    notes TEXT,
    exception_reason TEXT,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Collection Schedules
CREATE TABLE IF NOT EXISTS collection_schedules (
    id BIGSERIAL PRIMARY KEY,
    schedule_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    bin_id UUID NOT NULL REFERENCES bins(bin_id) ON DELETE CASCADE,
    route_id UUID REFERENCES routes(route_id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    frequency VARCHAR(32) NOT NULL,
    day_of_week INTEGER[],
    day_of_month INTEGER[],
    time_window_start TIME,
    time_window_end TIME,
    priority INTEGER DEFAULT 1,
    last_collection_at TIMESTAMPTZ,
    next_collection_at TIMESTAMPTZ,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- WASTE MANAGEMENT TABLES
-- ============================================================================

-- Waste Types
CREATE TABLE IF NOT EXISTS waste_types (
    id BIGSERIAL PRIMARY KEY,
    waste_type_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    category waste_category_enum NOT NULL DEFAULT 'organic',
    composition JSONB DEFAULT '{}',
    moisture_content_percent DOUBLE PRECISION,
    organic_content_percent DOUBLE PRECISION,
    density_kg_per_m3 DOUBLE PRECISION,
    energy_content_kwh_per_kg DOUBLE PRECISION,
    carbon_content_kg_co2_per_kg DOUBLE PRECISION,
    is_hazardous BOOLEAN DEFAULT FALSE,
    is_recyclable BOOLEAN DEFAULT FALSE,
    is_compostable BOOLEAN DEFAULT FALSE,
    is_reusable BOOLEAN DEFAULT FALSE,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Waste Streams
CREATE TABLE IF NOT EXISTS waste_streams (
    id BIGSERIAL PRIMARY KEY,
    waste_stream_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_location_geom GEOMETRY(POINT, 4326),
    source_location_description TEXT,
    source_type VARCHAR(64),
    dominant_waste_type_id UUID REFERENCES waste_types(waste_type_id) ON DELETE SET NULL,
    waste_type_distribution JSONB DEFAULT '{}',
    volume_tonnes_per_year DOUBLE PRECISION,
    volume_kg_per_day DOUBLE PRECISION,
    collection_frequency VARCHAR(64),
    collection_method VARCHAR(64),
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'derived',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Material Classifications
CREATE TABLE IF NOT EXISTS material_classifications (
    id BIGSERIAL PRIMARY KEY,
    classification_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    category VARCHAR(64) NOT NULL,
    is_recyclable BOOLEAN DEFAULT FALSE,
    is_compostable BOOLEAN DEFAULT FALSE,
    is_hazardous BOOLEAN DEFAULT FALSE,
    is_reusable BOOLEAN DEFAULT FALSE,
    average_value_per_kg DOUBLE PRECISION,
    market_demand VARCHAR(64),
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Contamination Observations
CREATE TABLE IF NOT EXISTS contamination_observations (
    id BIGSERIAL PRIMARY KEY,
    observation_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    collection_event_id UUID REFERENCES collection_events(collection_event_id) ON DELETE CASCADE,
    bin_id UUID REFERENCES bins(bin_id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    observation_type VARCHAR(64) NOT NULL,
    severity contamination_severity_enum NOT NULL,
    types contamination_type_enum[] NOT NULL,
    estimated_contamination_percent DOUBLE PRECISION,
    contaminated_mass_kg DOUBLE PRECISION,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detected_by VARCHAR(64),
    detector_id VARCHAR(128),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    resolution_notes TEXT,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Material Destinations
CREATE TABLE IF NOT EXISTS material_destinations (
    id BIGSERIAL PRIMARY KEY,
    destination_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    destination_type destination_type_enum NOT NULL,
    location_geom GEOMETRY(POINT, 4326),
    address TEXT,
    city VARCHAR(128),
    state VARCHAR(64),
    postal_code VARCHAR(32),
    country VARCHAR(64),
    is_active BOOLEAN DEFAULT TRUE,
    accepts_materials JSONB DEFAULT '{}',
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Recovery Pathways
CREATE TABLE IF NOT EXISTS recovery_pathways (
    id BIGSERIAL PRIMARY KEY,
    pathway_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    input_waste_type_id UUID REFERENCES waste_types(waste_type_id) ON DELETE CASCADE,
    process_name VARCHAR(255) NOT NULL,
    process_description TEXT,
    output_resource_name VARCHAR(255) NOT NULL,
    output_resource_description TEXT,
    efficiency_percent DOUBLE PRECISION,
    carbon_footprint_kg_co2_per_tonne DOUBLE PRECISION,
    energy_requirement_kwh_per_tonne DOUBLE PRECISION,
    water_requirement_m3_per_tonne DOUBLE PRECISION,
    economic_value_per_tonne DOUBLE PRECISION,
    operational_cost_per_tonne DOUBLE PRECISION,
    supporting_facility_ids UUID[],
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR OPERATIONS AND WASTE TABLES
-- ============================================================================

-- Routes
CREATE INDEX IF NOT EXISTS idx_routes_tenant ON routes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_routes_vehicle ON routes(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_routes_status ON routes(status);
CREATE INDEX IF NOT EXISTS idx_routes_scheduled_start ON routes(scheduled_start);

-- Route Stops
CREATE INDEX IF NOT EXISTS idx_route_stops_route ON route_stops(route_id);
CREATE INDEX IF NOT EXISTS idx_route_stops_bin ON route_stops(bin_id);
CREATE INDEX IF NOT EXISTS idx_route_stops_sequence ON route_stops(route_id, sequence);

-- Collection Events
CREATE INDEX IF NOT EXISTS idx_collection_events_route_stop ON collection_events(route_stop_id);
CREATE INDEX IF NOT EXISTS idx_collection_events_bin ON collection_events(bin_id);
CREATE INDEX IF NOT EXISTS idx_collection_events_vehicle ON collection_events(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_collection_events_status ON collection_events(status);

-- Waste Types
CREATE INDEX IF NOT EXISTS idx_waste_types_tenant ON waste_types(tenant_id);
CREATE INDEX IF NOT EXISTS idx_waste_types_name ON waste_types(name);
CREATE INDEX IF NOT EXISTS idx_waste_types_category ON waste_types(category);

-- Waste Streams
CREATE INDEX IF NOT EXISTS idx_waste_streams_tenant ON waste_streams(tenant_id);
CREATE INDEX IF NOT EXISTS idx_waste_streams_dominant_type ON waste_streams(dominant_waste_type_id);

-- Contamination Observations
CREATE INDEX IF NOT EXISTS idx_contamination_tenant ON contamination_observations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_contamination_bin ON contamination_observations(bin_id);
CREATE INDEX IF NOT EXISTS idx_contamination_detected ON contamination_observations(detected_at);

-- Material Destinations
CREATE INDEX IF NOT EXISTS idx_destinations_tenant ON material_destinations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_destinations_type ON material_destinations(destination_type);

-- Recovery Pathways
CREATE INDEX IF NOT EXISTS idx_pathways_tenant ON recovery_pathways(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pathways_waste_type ON recovery_pathways(input_waste_type_id);
