-- Waste Intelligence Network Operating System (WIN OS)
-- PostgreSQL Database Schema - Part 2: Core Tables (Organizations, Users, Assets)
-- Version: 1.0.0

-- ============================================================================
-- CORE TABLES: ORGANIZATIONS AND TENANCY
-- ============================================================================

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id BIGSERIAL PRIMARY KEY,
    organization_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    website VARCHAR(512),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(64),
    address TEXT,
    city VARCHAR(128),
    state VARCHAR(64),
    postal_code VARCHAR(32),
    country VARCHAR(64) DEFAULT 'United States',
    timezone VARCHAR(64) DEFAULT 'America/New_York',
    logo_url VARCHAR(512),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_email CHECK (contact_email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$' OR contact_email IS NULL)
);

-- Jurisdictions
CREATE TABLE IF NOT EXISTS jurisdictions (
    id BIGSERIAL PRIMARY KEY,
    jurisdiction_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    boundary_geom GEOMETRY(POLYGON, 4326),
    boundary_centroid GEOMETRY(POINT, 4326),
    population INTEGER,
    area_sq_km DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create spatial index on jurisdictions
CREATE INDEX IF NOT EXISTS idx_jurisdictions_boundary ON jurisdictions USING GIST(boundary_geom);

-- Service Areas
CREATE TABLE IF NOT EXISTS service_areas (
    id BIGSERIAL PRIMARY KEY,
    service_area_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    jurisdiction_id UUID NOT NULL REFERENCES jurisdictions(jurisdiction_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    boundary_geom GEOMETRY(POLYGON, 4326),
    boundary_centroid GEOMETRY(POINT, 4326),
    service_type VARCHAR(128),
    service_frequency VARCHAR(64),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create spatial index on service areas
CREATE INDEX IF NOT EXISTS idx_service_areas_boundary ON service_areas USING GIST(boundary_geom);

-- Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    configuration JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- CORE TABLES: USERS AND AUTHENTICATION
-- ============================================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(512),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(64),
    job_title VARCHAR(128),
    department VARCHAR(128),
    avatar_url VARCHAR(512),
    timezone VARCHAR(64) DEFAULT 'America/New_York',
    locale VARCHAR(16) DEFAULT 'en-US',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$')
);

-- Permissions
CREATE TABLE IF NOT EXISTS permissions (
    id BIGSERIAL PRIMARY KEY,
    permission_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    resource_type VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id BIGSERIAL PRIMARY KEY,
    role_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Role Permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    id BIGSERIAL PRIMARY KEY,
    role_id UUID NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(permission_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(role_id, permission_id)
);

-- User Roles
CREATE TABLE IF NOT EXISTS user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(512) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_expiry CHECK (expires_at > NOW())
);

-- Refresh Tokens
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    token_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(512) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,
    CONSTRAINT valid_expiry CHECK (expires_at > NOW())
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    audit_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(128) NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    session_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- ============================================================================
-- CORE TABLES: ASSETS AND INFRASTRUCTURE
-- ============================================================================

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id BIGSERIAL PRIMARY KEY,
    asset_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    service_area_id UUID REFERENCES service_areas(service_area_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    asset_type asset_type_enum NOT NULL DEFAULT 'bin',
    status asset_status_enum NOT NULL DEFAULT 'active',
    location_geom GEOMETRY(POINT, 4326),
    address TEXT,
    manufacturer VARCHAR(128),
    model VARCHAR(128),
    serial_number VARCHAR(128),
    year_manufactured INTEGER,
    year_installed INTEGER,
    capacity_kg DOUBLE PRECISION,
    capacity_volume_m3 DOUBLE PRECISION,
    is_smart BOOLEAN DEFAULT FALSE,
    is_connected BOOLEAN DEFAULT FALSE,
    installed_at TIMESTAMPTZ,
    last_maintenance_at TIMESTAMPTZ,
    next_maintenance_at TIMESTAMPTZ,
    decommissioned_at TIMESTAMPTZ,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create spatial index on assets
CREATE INDEX IF NOT EXISTS idx_assets_location ON assets USING GIST(location_geom);

-- Bins
CREATE TABLE IF NOT EXISTS bins (
    id BIGSERIAL PRIMARY KEY,
    bin_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    asset_id UUID UNIQUE REFERENCES assets(asset_id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    cluster_id UUID,
    facility_id UUID REFERENCES facilities(facility_id) ON DELETE SET NULL,
    route_id UUID REFERENCES routes(route_id) ON DELETE SET NULL,
    bin_type VARCHAR(64),
    waste_type_id UUID REFERENCES waste_types(waste_type_id) ON DELETE SET NULL,
    bin_status bin_status_enum NOT NULL DEFAULT 'unknown',
    last_collection_at TIMESTAMPTZ,
    next_collection_at TIMESTAMPTZ,
    capacity_kg DOUBLE PRECISION,
    current_fill_level_percent DOUBLE PRECISION DEFAULT 0,
    current_mass_kg DOUBLE PRECISION DEFAULT 0,
    has_sensor BOOLEAN DEFAULT FALSE,
    sensor_id VARCHAR(128),
    sensor_type VARCHAR(64),
    color VARCHAR(32),
    brand VARCHAR(64),
    model VARCHAR(64),
    serial_number VARCHAR(128),
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'observed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Facilities
CREATE TABLE IF NOT EXISTS facilities (
    id BIGSERIAL PRIMARY KEY,
    facility_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    jurisdiction_id UUID REFERENCES jurisdictions(jurisdiction_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    facility_type facility_type_enum NOT NULL DEFAULT 'composting',
    operational_status facility_operational_status_enum NOT NULL DEFAULT 'operational',
    location_geom GEOMETRY(POINT, 4326),
    address TEXT NOT NULL,
    city VARCHAR(128) NOT NULL,
    state VARCHAR(64) NOT NULL,
    postal_code VARCHAR(32),
    country VARCHAR(64) DEFAULT 'United States',
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(64),
    website VARCHAR(512),
    capacity_kg DOUBLE PRECISION,
    capacity_tonnes_per_year DOUBLE PRECISION,
    current_load_kg DOUBLE PRECISION DEFAULT 0,
    operating_hours TEXT,
    days_of_operation TEXT,
    accepts_public BOOLEAN DEFAULT FALSE,
    accepted_waste_types UUID[],
    supported_process_ids UUID[],
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create spatial index on facilities
CREATE INDEX IF NOT EXISTS idx_facilities_location ON facilities USING GIST(location_geom);

-- Vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    id BIGSERIAL PRIMARY KEY,
    vehicle_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    fleet_id UUID REFERENCES fleets(fleet_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vehicle_type vehicle_type_enum NOT NULL DEFAULT 'collection_truck',
    status vehicle_status_enum NOT NULL DEFAULT 'available',
    license_plate VARCHAR(32),
    vin VARCHAR(64),
    manufacturer VARCHAR(128),
    model VARCHAR(128),
    year INTEGER,
    fuel_type VARCHAR(32),
    capacity_kg DOUBLE PRECISION,
    capacity_volume_m3 DOUBLE PRECISION,
    current_location GEOMETRY(POINT, 4326),
    current_route_id UUID REFERENCES routes(route_id) ON DELETE SET NULL,
    odometer_km DOUBLE PRECISION DEFAULT 0,
    fuel_level_percent DOUBLE PRECISION DEFAULT 100,
    has_gps BOOLEAN DEFAULT FALSE,
    has_telematics BOOLEAN DEFAULT FALSE,
    device_id VARCHAR(128),
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fleets
CREATE TABLE IF NOT EXISTS fleets (
    id BIGSERIAL PRIMARY KEY,
    fleet_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(organization_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_location_geom GEOMETRY(POINT, 4326),
    base_address TEXT,
    operating_region VARCHAR(255),
    average_daily_km DOUBLE PRECISION,
    source_system VARCHAR(128),
    source_record_id VARCHAR(255),
    data_status data_status_enum NOT NULL DEFAULT 'reported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR CORE TABLES
-- ============================================================================

-- Organizations
CREATE INDEX IF NOT EXISTS idx_organizations_organization_id ON organizations(organization_id);
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);

-- Jurisdictions
CREATE INDEX IF NOT EXISTS idx_jurisdictions_organization ON jurisdictions(organization_id);
CREATE INDEX IF NOT EXISTS idx_jurisdictions_name ON jurisdictions(name);

-- Service Areas
CREATE INDEX IF NOT EXISTS idx_service_areas_jurisdiction ON service_areas(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_service_areas_name ON service_areas(name);

-- Tenants
CREATE INDEX IF NOT EXISTS idx_tenants_organization ON tenants(organization_id);
CREATE INDEX IF NOT EXISTS idx_tenants_name ON tenants(name);

-- Users
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Assets
CREATE INDEX IF NOT EXISTS idx_assets_tenant ON assets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_assets_organization ON assets(organization_id);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);

-- Bins
CREATE INDEX IF NOT EXISTS idx_bins_tenant ON bins(tenant_id);
CREATE INDEX IF NOT EXISTS idx_bins_asset ON bins(asset_id);
CREATE INDEX IF NOT EXISTS idx_bins_facility ON bins(facility_id);
CREATE INDEX IF NOT EXISTS idx_bins_route ON bins(route_id);
CREATE INDEX IF NOT EXISTS idx_bins_status ON bins(bin_status);

-- Facilities
CREATE INDEX IF NOT EXISTS idx_facilities_tenant ON facilities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_facilities_organization ON facilities(organization_id);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON facilities(facility_type);
CREATE INDEX IF NOT EXISTS idx_facilities_status ON facilities(operational_status);

-- Vehicles
CREATE INDEX IF NOT EXISTS idx_vehicles_tenant ON vehicles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_fleet ON vehicles(fleet_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);
