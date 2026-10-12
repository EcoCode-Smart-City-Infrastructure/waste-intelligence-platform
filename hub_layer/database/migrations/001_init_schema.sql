-- Initial database schema for waste-intelligence hub layer

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Bins table
CREATE TABLE IF NOT EXISTS bins (
    id BIGSERIAL PRIMARY KEY,
    bin_id VARCHAR(64) UNIQUE NOT NULL,
    cluster_id VARCHAR(64),
    facility_id VARCHAR(64),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'active',
    battery_percent INT DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_bins_cluster ON bins(cluster_id);
CREATE INDEX idx_bins_facility ON bins(facility_id);

-- Facilities table
CREATE TABLE IF NOT EXISTS facilities (
    id BIGSERIAL PRIMARY KEY,
    facility_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    facility_type VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    capacity_kg DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'operational',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_facilities_type ON facilities(facility_type);

-- Telemetry table (time-series)
CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL,
    bin_id VARCHAR(64) NOT NULL,
    fill_level_percent DOUBLE PRECISION,
    mass_kg DOUBLE PRECISION,
    battery_percent INT,
    contamination_flag BOOLEAN DEFAULT FALSE,
    reported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (reported_at, id)
);

SELECT create_hypertable('telemetry', 'reported_at', if_not_exists => TRUE);
CREATE INDEX idx_telemetry_bin ON telemetry(bin_id, reported_at DESC);

-- Waste events table
CREATE TABLE IF NOT EXISTS waste_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    bin_id VARCHAR(64) NOT NULL,
    facility_id VARCHAR(64),
    waste_type VARCHAR(32),
    mass_kg DOUBLE PRECISION,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_waste_events_bin ON waste_events(bin_id, occurred_at DESC);
CREATE INDEX idx_waste_events_facility ON waste_events(facility_id, occurred_at DESC);
