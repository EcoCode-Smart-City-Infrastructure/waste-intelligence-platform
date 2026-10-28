-- Waste Intelligence Network Operating System (WIN OS)
-- PostgreSQL Database Schema - Part 1: Extensions and Types
-- Version: 1.0.0

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable timescaledb for hypertable support
SELECT timescaledb_pre_restore();

-- ============================================================================
-- ENUMS AND TYPES
-- ============================================================================

-- Data status classification
CREATE TYPE data_status_enum AS ENUM (
    'observed',      -- Direct measurement from sensors or verified reports
    'reported',      -- Human-reported data, not directly measured
    'derived',       -- Calculated or transformed from other data
    'forecast',      -- Predicted future values
    'simulated',     -- Generated from simulation models
    'unavailable'    -- Data not available or not applicable
);

-- Data quality status
CREATE TYPE data_quality_status_enum AS ENUM (
    'excellent', 'good', 'fair', 'poor', 'invalid', 'unknown'
);

-- Node types for Knowledge Graph
CREATE TYPE kg_node_type_enum AS ENUM (
    'Waste_Type', 'Waste_Stream', 'Process', 'Resource', 'Facility', 'Constraint', 'Actor'
);

-- Edge types for Knowledge Graph
CREATE TYPE kg_edge_type_enum AS ENUM (
    'WASTECANBEPROCESSEDBY', 'PROCESSPRODUCESRESOURCE', 'FACILITYSUPPORTSPROCESS',
    'FACILITYACCEPTSWASTE', 'RESOURCEDEMANDEDBY_ACTOR', 'CONSTRAINTAPPLIESTO',
    'WASTESTREAMHASWASTETYPE', 'FACILITYLOCATEDIN', 'ACTOROPERATESFACILITY'
);

-- Asset types
CREATE TYPE asset_type_enum AS ENUM (
    'bin', 'compactor', 'container', 'sensor', 'gateway', 'vehicle', 'facility_equipment', 'other'
);

-- Asset status
CREATE TYPE asset_status_enum AS ENUM (
    'active', 'inactive', 'maintenance', 'retired', 'lost', 'stolen'
);

-- Bin status
CREATE TYPE bin_status_enum AS ENUM (
    'empty', 'partial', 'full', 'overflowing', 'in_collection', 'maintenance', 'offline', 'unknown'
);

-- Facility types
CREATE TYPE facility_type_enum AS ENUM (
    'composting', 'anaerobic_digestion', 'recycling', 'transfer_station',
    'landfill', 'waste_to_energy', 'material_recovery', 'collection_depot', 'other'
);

-- Facility operational status
CREATE TYPE facility_operational_status_enum AS ENUM (
    'operational', 'maintenance', 'shutdown', 'seasonal', 'temporary_closure',
    'permanent_closure', 'unknown'
);

-- Vehicle types
CREATE TYPE vehicle_type_enum AS ENUM (
    'collection_truck', 'compaction_truck', 'hook_lift_truck', 'roll_off_truck',
    'van', 'trailer', 'other'
);

-- Vehicle status
CREATE TYPE vehicle_status_enum AS ENUM (
    'available', 'in_route', 'in_maintenance', 'out_of_service', 'offline', 'retired'
);

-- Route status
CREATE TYPE route_status_enum AS ENUM (
    'planned', 'dispatched', 'in_progress', 'completed', 'cancelled', 'delayed', 'on_hold'
);

-- Route stop status
CREATE TYPE route_stop_status_enum AS ENUM (
    'pending', 'in_progress', 'completed', 'skipped', 'failed', 'missed'
);

-- Collection event status
CREATE TYPE collection_event_status_enum AS ENUM (
    'scheduled', 'dispatched', 'arrived', 'collecting', 'completed', 'failed',
    'cancelled', 'verified'
);

-- Waste type categories
CREATE TYPE waste_category_enum AS ENUM (
    'organic', 'recyclable', 'hazardous', 'electronic', 'construction',
    'medical', 'mixed', 'other'
);

-- Contamination types
CREATE TYPE contamination_type_enum AS ENUM (
    'non_recyclable', 'hazardous', 'electronic', 'medical',
    'construction', 'liquid', 'other', 'unknown'
);

-- Contamination severity
CREATE TYPE contamination_severity_enum AS ENUM (
    'trace', 'minor', 'moderate', 'major', 'severe'
);

-- Material destination types
CREATE TYPE destination_type_enum AS ENUM (
    'composting_facility', 'anaerobic_digestion', 'recycling_facility',
    'landfill', 'waste_to_energy', 'material_recovery_facility',
    'transfer_station', 'export', 'other'
);

-- Environmental metric categories
CREATE TYPE metric_category_enum AS ENUM (
    'waste_generation', 'waste_diversion', 'waste_recovery', 'emissions',
    'energy', 'water', 'carbon', 'economic', 'operational', 'other'
);

-- Environmental metric units
CREATE TYPE metric_unit_enum AS ENUM (
    'kg', 'tonnes', 'm3', 'liters', 'kwh', 'mj',
    'kg_co2e', 'tonnes_co2e', 'usd', 'eur', 'percentage',
    'count', 'km', 'miles', 'hours', 'days', 'other'
);

-- Constraint types
CREATE TYPE constraint_type_enum AS ENUM (
    'regulatory', 'environmental', 'safety', 'economic',
    'operational', 'technical', 'legal', 'other'
);

-- Constraint severity
CREATE TYPE constraint_severity_enum AS ENUM (
    'info', 'warning', 'critical', 'mandatory'
);

-- Actor types
CREATE TYPE actor_type_enum AS ENUM (
    'municipality', 'private_hauler', 'waste_processor', 'urban_farm',
    'community_organization', 'business', 'residential', 'government', 'other'
);

-- Actor scale
CREATE TYPE actor_scale_enum AS ENUM (
    'individual', 'small', 'medium', 'large', 'enterprise', 'government'
);

-- Ingestion job status
CREATE TYPE ingestion_job_status_enum AS ENUM (
    'pending', 'running', 'completed', 'failed', 'cancelled', 'paused'
);

-- Data source types
CREATE TYPE data_source_type_enum AS ENUM (
    'api', 'csv_upload', 'database', 'mqtt', 'lorawan',
    'manual_entry', 'sensor', 'webhook', 'other'
);

-- Forecast model types
CREATE TYPE forecast_model_type_enum AS ENUM (
    'statistical', 'machine_learning', 'time_series', 'ensemble', 'other'
);

-- Forecast model status
CREATE TYPE forecast_model_status_enum AS ENUM (
    'draft', 'training', 'trained', 'deployed', 'retired', 'failed'
);

-- Anomaly detection types
CREATE TYPE anomaly_detection_type_enum AS ENUM (
    'statistical', 'machine_learning', 'threshold', 'rule_based', 'other'
);

-- Anomaly status
CREATE TYPE anomaly_status_enum AS ENUM (
    'detected', 'investigating', 'confirmed', 'false_positive', 'resolved', 'escalated'
);

-- Optimization objective types
CREATE TYPE optimization_objective_enum AS ENUM (
    'minimize_distance', 'minimize_time', 'minimize_cost', 'minimize_fuel',
    'minimize_emissions', 'maximize_capacity_utilization',
    'balance_workload', 'meet_deadlines', 'other'
);

-- Simulation types
CREATE TYPE simulation_type_enum AS ENUM (
    'collection_route', 'facility_capacity', 'waste_flow',
    'resource_allocation', 'environmental_impact', 'cost_analysis', 'other'
);

-- Simulation status
CREATE TYPE simulation_status_enum AS ENUM (
    'created', 'queued', 'running', 'completed', 'failed', 'cancelled'
);

-- Backup status
CREATE TYPE backup_status_enum AS ENUM (
    'pending', 'running', 'completed', 'failed', 'cancelled', 'verifying', 'verified'
);

-- Backup type
CREATE TYPE backup_type_enum AS ENUM (
    'full', 'incremental', 'differential', 'logical', 'physical'
);
