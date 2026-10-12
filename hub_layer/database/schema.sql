-- Hub schema

CREATE TABLE IF NOT EXISTS bins (
    id SERIAL PRIMARY KEY,
    bin_id VARCHAR(64) UNIQUE NOT NULL,
    cluster_id VARCHAR(64),
    facility_id VARCHAR(64),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facilities (
    id SERIAL PRIMARY KEY,
    facility_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    capacity_kg DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    bin_id VARCHAR(64) NOT NULL,
    fill_level_percent DOUBLE PRECISION,
    mass_kg DOUBLE PRECISION,
    contamination_flag BOOLEAN DEFAULT FALSE,
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
