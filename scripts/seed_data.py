"""Comprehensive seed data generator for WIN OS with real database connections.

This script populates the PostgreSQL database with realistic sample data
for the Waste Intelligence Network Operating System.

Usage:
    python scripts/seed_data.py [--clear] [--tenant TENANT_NAME] [--count N]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras


DEFAULT_TENANT = "demo-tenant"
DEFAULT_ORG = "NYC Waste Management"
DEFAULT_COUNT = 10

NYC_BBOX = (
    (-74.25909, 40.477399),
    (-73.700181, 40.917556),
)


class Database:
    """Database connection manager."""

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or "postgresql://postgres:postgres@localhost:5432/waste"
        self.connection: Optional[psycopg2.extensions.connection] = None

    def connect(self):
        if self.connection is None or self.connection.closed:
            self.connection = psycopg2.connect(self.dsn)
        return self.connection

    def execute(self, query: str, params: Optional[tuple] = None):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    def execute_many(self, query: str, params_list: List[tuple]):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
                return cur.rowcount

    def fetch_one(self, query: str, params: Optional[tuple] = None):
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def fetch_all(self, query: str, params: Optional[tuple] = None):
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def get_tenant_id(self, tenant_name: str) -> Optional[uuid.UUID]:
        result = self.fetch_one("SELECT tenant_id FROM tenants WHERE name = %s", (tenant_name,))
        if result:
            return result["tenant_id"]
        return None

    def get_organization_id(self, org_name: str) -> Optional[uuid.UUID]:
        result = self.fetch_one("SELECT organization_id FROM organizations WHERE name = %s", (org_name,))
        if result:
            return result["organization_id"]
        return None


class DataGenerator:
    WASTE_TYPES = [
        {"name": "Food Scraps", "category": "organic", "is_compostable": True, "is_recyclable": False},
        {"name": "Yard Waste", "category": "organic", "is_compostable": True, "is_recyclable": False},
        {"name": "Coffee Grounds", "category": "organic", "is_compostable": True, "is_recyclable": False},
        {"name": "Spent Grain", "category": "organic", "is_compostable": True, "is_recyclable": False},
        {"name": "Fats, Oils, Grease", "category": "organic", "is_compostable": False, "is_recyclable": True},
        {"name": "Paper", "category": "recyclable", "is_compostable": True, "is_recyclable": True},
        {"name": "Cardboard", "category": "recyclable", "is_compostable": True, "is_recyclable": True},
        {"name": "Plastic", "category": "recyclable", "is_compostable": False, "is_recyclable": True},
        {"name": "Glass", "category": "recyclable", "is_compostable": False, "is_recyclable": True},
        {"name": "Metal", "category": "recyclable", "is_compostable": False, "is_recyclable": True},
        {"name": "Electronic Waste", "category": "electronic", "is_compostable": False, "is_recyclable": True},
        {"name": "Construction Debris", "category": "construction", "is_compostable": False, "is_recyclable": False},
        {"name": "Hazardous Waste", "category": "hazardous", "is_compostable": False, "is_recyclable": False},
        {"name": "Medical Waste", "category": "medical", "is_compostable": False, "is_recyclable": False},
        {"name": "Mixed Waste", "category": "mixed", "is_compostable": False, "is_recyclable": False},
    ]

    FACILITY_TYPES = [
        {"name": "Composting Facility", "type": "composting", "accepted_waste": ["Food Scraps", "Yard Waste", "Coffee Grounds", "Spent Grain"], "capacity_tonnes": 5000},
        {"name": "Anaerobic Digestion Plant", "type": "anaerobic_digestion", "accepted_waste": ["Food Scraps", "Fats, Oils, Grease"], "capacity_tonnes": 10000},
        {"name": "Material Recovery Facility", "type": "material_recovery", "accepted_waste": ["Paper", "Cardboard", "Plastic", "Glass", "Metal"], "capacity_tonnes": 8000},
        {"name": "Transfer Station", "type": "transfer_station", "accepted_waste": ["Mixed Waste", "Construction Debris", "Hazardous Waste", "Medical Waste"], "capacity_tonnes": 15000},
        {"name": "Waste-to-Energy Plant", "type": "waste_to_energy", "accepted_waste": ["Mixed Waste", "Non-Recyclable"], "capacity_tonnes": 20000},
        {"name": "Recycling Center", "type": "recycling", "accepted_waste": ["Paper", "Cardboard", "Plastic", "Glass", "Metal", "Electronic Waste"], "capacity_tonnes": 6000},
    ]

    PROCESS_TYPES = [
        {"name": "Aerobic Composting", "description": "Decomposition of organic waste in oxygen", "input_waste": ["Food Scraps", "Yard Waste"], "output_resources": ["Compost", "CO2"], "efficiency": 0.85, "carbon_footprint": -0.2},
        {"name": "Anaerobic Digestion", "description": "Decomposition without oxygen, producing biogas", "input_waste": ["Food Scraps", "Fats, Oils, Grease"], "output_resources": ["Biogas", "Digestate"], "efficiency": 0.90, "carbon_footprint": 0.1},
        {"name": "Black Soldier Fly Larvae", "description": "Insect-based organic waste processing", "input_waste": ["Food Scraps"], "output_resources": ["Animal Feed", "Fertilizer"], "efficiency": 0.75, "carbon_footprint": -0.15},
        {"name": "Biochar Production", "description": "Pyrolysis of organic waste to produce biochar", "input_waste": ["Yard Waste", "Wood Waste"], "output_resources": ["Biochar", "Syngas"], "efficiency": 0.70, "carbon_footprint": -0.5},
    ]

    RESOURCE_TYPES = [
        {"name": "Compost", "description": "Organic fertilizer from composting", "value_per_tonne": 50.0},
        {"name": "Biogas", "description": "Methane-rich gas for energy", "value_per_tonne": 200.0},
        {"name": "Digestate", "description": "Nutrient-rich byproduct of anaerobic digestion", "value_per_tonne": 30.0},
        {"name": "Animal Feed", "description": "Protein-rich feed from insect processing", "value_per_tonne": 150.0},
        {"name": "Fertilizer", "description": "Nutrient-rich soil amendment", "value_per_tonne": 80.0},
        {"name": "Biochar", "description": "Carbon-rich charcoal for soil", "value_per_tonne": 300.0},
        {"name": "Recycled Paper", "description": "Processed paper for reuse", "value_per_tonne": 100.0},
        {"name": "Recycled Plastic", "description": "Processed plastic for reuse", "value_per_tonne": 500.0},
        {"name": "Recycled Glass", "description": "Processed glass for reuse", "value_per_tonne": 150.0},
        {"name": "Recycled Metal", "description": "Processed metal for reuse", "value_per_tonne": 800.0},
    ]

    ACTOR_TYPES = [
        {"name": "DSNY", "type": "municipality", "scale": "government"},
        {"name": "Private Hauler A", "type": "private_hauler", "scale": "large"},
        {"name": "Private Hauler B", "type": "private_hauler", "scale": "medium"},
        {"name": "Urban Farm Co-op", "type": "urban_farm", "scale": "small"},
        {"name": "Green Waste Processors", "type": "waste_processor", "scale": "medium"},
        {"name": "Community Garden Network", "type": "community_organization", "scale": "small"},
    ]

    VEHICLE_TYPES = [
        {"name": "Collection Truck", "type": "collection_truck", "capacity_kg": 10000, "fuel": "diesel"},
        {"name": "Compaction Truck", "type": "compaction_truck", "capacity_kg": 15000, "fuel": "diesel"},
        {"name": "Hook Lift Truck", "type": "hook_lift_truck", "capacity_kg": 20000, "fuel": "diesel"},
        {"name": "Electric Collection Truck", "type": "collection_truck", "capacity_kg": 8000, "fuel": "electric"},
    ]

    NYC_NEIGHBORHOODS = [
        "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island",
        "Upper East Side", "Upper West Side", "Midtown", "Lower Manhattan",
        "Williamsburg", "Greenpoint", "Bushwick", "Bedford-Stuyvesant",
        "Park Slope", "Sunset Park", "Astoria", "Long Island City",
        "Jackson Heights", "Flushing", "Jamaica", "Forest Hills",
    ]

    STREET_NAMES = [
        "Main St", "Broadway", "Park Ave", "5th Ave", "Madison Ave",
        "Lexington Ave", "3rd Ave", "1st Ave", "2nd Ave", "Fulton St",
        "Atlantic Ave", "Flatbush Ave", "Bedford Ave", "Grand St",
        "Delancey St", "Houston St", "Canal St", "Bleecker St",
    ]

    @classmethod
    def generate_coordinates(cls, bbox: Optional[Tuple] = None) -> Tuple[float, float]:
        bbox = bbox or NYC_BBOX
        min_lon, min_lat = bbox[0]
        max_lon, max_lat = bbox[1]
        lon = random.uniform(min_lon, max_lon)
        lat = random.uniform(min_lat, max_lat)
        return (lon, lat)

    @classmethod
    def generate_nyc_address(cls) -> Dict[str, str]:
        street = random.choice(cls.STREET_NAMES)
        number = random.randint(100, 9999)
        return {
            "address": f"{number} {street}",
            "city": "New York",
            "state": "NY",
            "postal_code": f"{random.randint(10001, 11299)}",
        }

    @classmethod
    def generate_timestamp(cls, days_ago: int = 0, days_range: int = 30) -> datetime:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days_ago + days_range)
        end = now - timedelta(days=days_ago)
        delta = random.randint(0, int((end - start).total_seconds()))
        return start + timedelta(seconds=delta)


class SeedDataGenerator:
    def __init__(self, db: Database, tenant_name: str = DEFAULT_TENANT, count: int = DEFAULT_COUNT):
        self.db = db
        self.tenant_name = tenant_name
        self.count = count
        self.tenant_id: Optional[uuid.UUID] = None
        self.organization_id: Optional[uuid.UUID] = None

    def initialize_tenant(self) -> None:
        org_id = self.db.get_organization_id(DEFAULT_ORG)
        if not org_id:
            org_id = uuid.uuid4()
            self.db.execute(
                "INSERT INTO organizations (organization_id, name, description, contact_email, city, state, country, timezone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (org_id, DEFAULT_ORG, "New York City Waste Management Authority", "info@nycwaste.gov", "New York", "NY", "USA", "America/New_York")
            )
            self.db.connection.commit()
        self.organization_id = org_id

        tenant_id = self.db.get_tenant_id(self.tenant_name)
        if not tenant_id:
            tenant_id = uuid.uuid4()
            self.db.execute(
                "INSERT INTO tenants (tenant_id, organization_id, name, description) VALUES (%s, %s, %s, %s)",
                (tenant_id, org_id, self.tenant_name, "Demo tenant for WIN OS")
            )
            self.db.connection.commit()
        self.tenant_id = tenant_id

        print(f"Tenant: {self.tenant_name} (ID: {tenant_id})")
        print(f"Organization: {DEFAULT_ORG} (ID: {org_id})")

    def seed_waste_types(self) -> List[uuid.UUID]:
        waste_type_ids = []
        for waste_type in DataGenerator.WASTE_TYPES:
            waste_type_id = uuid.uuid4()
            self.db.execute(
                """INSERT INTO waste_types (waste_type_id, tenant_id, name, description, category, is_compostable, is_recyclable, is_hazardous, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, name) DO NOTHING""",
                (waste_type_id, self.tenant_id, waste_type["name"], waste_type.get("description", ""), waste_type["category"], waste_type.get("is_compostable", False), waste_type.get("is_recyclable", False), waste_type.get("is_hazardous", False))
            )
            waste_type_ids.append(waste_type_id)
        self.db.connection.commit()
        print(f"Seeded {len(waste_type_ids)} waste types")
        return waste_type_ids

    def seed_facilities(self, waste_type_ids: List[uuid.UUID]) -> List[uuid.UUID]:
        facility_ids = []
        waste_type_map = {wt["name"]: wt_id for wt, wt_id in zip(DataGenerator.WASTE_TYPES, waste_type_ids)}

        for facility in DataGenerator.FACILITY_TYPES:
            facility_id = uuid.uuid4()
            lon, lat = DataGenerator.generate_coordinates()
            address = DataGenerator.generate_nyc_address()
            accepted_waste_ids = [waste_type_map[name] for name in facility["accepted_waste"] if name in waste_type_map]

            self.db.execute(
                """INSERT INTO facilities (facility_id, tenant_id, organization_id, name, description, facility_type, operational_status, location_geom, address, city, state, postal_code, country, contact_email, contact_phone, capacity_kg, capacity_tonnes_per_year, current_load_kg, accepts_public, accepted_waste_types, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (facility_id) DO NOTHING""",
                (facility_id, self.tenant_id, self.organization_id, facility["name"], facility.get("description", ""), facility["type"], "operational", f"POINT({lon} {lat})", address["address"], address["city"], address["state"], address["postal_code"], "USA", "contact@facility.com", "555-0123", facility["capacity_tonnes"] * 1000, facility["capacity_tonnes"], facility["capacity_tonnes"] * 1000 * 0.3, True, accepted_waste_ids)
            )
            facility_ids.append(facility_id)
        self.db.connection.commit()
        print(f"Seeded {len(facility_ids)} facilities")
        return facility_ids

    def seed_assets(self, facility_ids: List[uuid.UUID]) -> List[uuid.UUID]:
        asset_ids = []
        for i in range(self.count):
            bin_id = uuid.uuid4()
            asset_id = uuid.uuid4()
            facility_id = random.choice(facility_ids) if facility_ids else None
            lon, lat = DataGenerator.generate_coordinates()

            self.db.execute(
                """INSERT INTO assets (asset_id, tenant_id, organization_id, name, description, asset_type, status, location_geom, capacity_kg, capacity_volume_m3, is_smart, is_connected, source_system, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, 'observed') ON CONFLICT (asset_id) DO NOTHING""",
                (asset_id, self.tenant_id, self.organization_id, f"Smart Bin {i+1}", f"Smart waste bin with IoT sensor", "bin", "active", f"POINT({lon} {lat})", 500.0, 1.0, True, True, "win_os")
            )

            self.db.execute(
                """INSERT INTO bins (bin_id, asset_id, tenant_id, cluster_id, facility_id, bin_type, bin_status, last_collection_at, next_collection_at, capacity_kg, current_fill_level_percent, current_mass_kg, has_sensor, sensor_id, sensor_type, color, brand, model, source_system, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'observed') ON CONFLICT (bin_id) DO NOTHING""",
                (bin_id, asset_id, self.tenant_id, f"cluster-{random.randint(1, 5)}", facility_id, "smart_bin", random.choice(["empty", "partial", "full", "unknown"]), DataGenerator.generate_timestamp(days_ago=7, days_range=3), DataGenerator.generate_timestamp(days_ago=0, days_range=3), 500.0, random.uniform(0, 100), random.uniform(0, 500), True, f"sensor-{i+1}", "ultrasonic", "green", "Sensoneo", "SMART-2000", "win_os")
            )
            asset_ids.append(asset_id)

        for i in range(self.count // 2):
            vehicle_id = uuid.uuid4()
            vehicle_type = random.choice(DataGenerator.VEHICLE_TYPES)
            lon, lat = DataGenerator.generate_coordinates()
            self.db.execute(
                """INSERT INTO vehicles (vehicle_id, tenant_id, organization_id, name, description, vehicle_type, status, license_plate, vin, manufacturer, model, year, fuel_type, capacity_kg, capacity_volume_m3, current_location, odometer_km, fuel_level_percent, has_gps, has_telematics, device_id, source_system, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (vehicle_id) DO NOTHING""",
                (vehicle_id, self.tenant_id, self.organization_id, f"Truck {i+1}", f"Collection truck for route {i+1}", vehicle_type["type"], "available", f"NYC-{i+100:04d}", f"VIN-{i+1000:06d}", "Mack", "LR", 2020, vehicle_type["fuel"], vehicle_type["capacity_kg"], vehicle_type["capacity_kg"] / 1000, f"POINT({lon} {lat})", random.uniform(0, 50000), random.uniform(0, 100), True, True, f"gps-{i+1}", "win_os")
            )
            asset_ids.append(vehicle_id)

        self.db.connection.commit()
        print(f"Seeded {len(asset_ids)} assets ({self.count} bins, {self.count//2} vehicles)")
        return asset_ids

    def seed_routes(self, facility_ids: List[uuid.UUID], asset_ids: List[uuid.UUID]) -> List[uuid.UUID]:
        route_ids = []
        bins = self.db.fetch_all("SELECT bin_id FROM bins WHERE tenant_id = %s LIMIT %s", (self.tenant_id, self.count))
        bin_ids = [row["bin_id"] for row in bins]

        for i in range(self.count // 2):
            route_id = uuid.uuid4()
            vehicle_id = random.choice(asset_ids) if asset_ids else None
            start_time = DataGenerator.generate_timestamp(days_ago=0, days_range=1)
            end_time = start_time + timedelta(hours=8)

            self.db.execute(
                """INSERT INTO routes (route_id, tenant_id, organization_id, name, description, route_code, status, scheduled_start, scheduled_end, vehicle_id, total_distance_km, total_duration_minutes, total_waste_kg, total_stops, completed_stops, source_system, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned') ON CONFLICT (route_id) DO NOTHING""",
                (route_id, self.tenant_id, self.organization_id, f"Route {i+1}", f"Daily collection route", f"RT-{i+100:03d}", random.choice(["planned", "dispatched", "completed"]), start_time, end_time, vehicle_id, random.uniform(20, 100), random.randint(240, 480), random.uniform(5000, 20000), random.randint(10, 50), random.randint(0, 50), "win_os")
            )
            route_ids.append(route_id)

            num_stops = random.randint(5, 20)
            for j in range(num_stops):
                if bin_ids:
                    bin_id = random.choice(bin_ids)
                    stop_lon, stop_lat = DataGenerator.generate_coordinates()
                    self.db.execute(
                        """INSERT INTO route_stops (route_stop_id, route_id, tenant_id, sequence, bin_id, location_geom, address, scheduled_arrival, scheduled_departure, status, distance_from_previous_km, duration_minutes, waste_collected_kg, source_system, data_status) 
                           VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned') ON CONFLICT (route_id, sequence) DO NOTHING""",
                        (uuid.uuid4(), route_id, self.tenant_id, j, bin_id, f"POINT({stop_lon} {stop_lat})", f"{random.randint(100, 9999)} {random.choice(DataGenerator.STREET_NAMES)}", start_time + timedelta(hours=j * 0.5), start_time + timedelta(hours=j * 0.5 + 0.25), random.choice(["pending", "completed", "skipped"]), random.uniform(0.5, 5.0), random.randint(5, 30), random.uniform(100, 1000), "win_os")
                    )

        self.db.connection.commit()
        print(f"Seeded {len(route_ids)} routes with stops")
        return route_ids

    def seed_collection_events(self, route_ids: List[uuid.UUID], asset_ids: List[uuid.UUID]) -> None:
        route_stops = self.db.fetch_all("SELECT route_stop_id, route_id, bin_id FROM route_stops WHERE tenant_id = %s", (self.tenant_id,))
        for stop in route_stops:
            if random.random() > 0.3:
                event_id = uuid.uuid4()
                now = datetime.now(timezone.utc)
                event_time = now - timedelta(hours=random.randint(1, 24))
                self.db.execute(
                    """INSERT INTO collection_events (collection_event_id, route_stop_id, route_id, bin_id, tenant_id, event_type, status, scheduled_at, dispatched_at, arrived_at, started_at, completed_at, waste_mass_kg, fill_level_before_percent, fill_level_after_percent, contamination_flag, contamination_severity, contamination_types, driver_id, duration_minutes, source_system, data_status) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'observed') ON CONFLICT (collection_event_id) DO NOTHING""",
                    (event_id, stop["route_stop_id"], stop["route_id"], stop["bin_id"], self.tenant_id, "regular_collection", random.choice(["scheduled", "dispatched", "arrived", "collecting", "completed", "verified"]), event_time - timedelta(hours=2), event_time - timedelta(hours=1), event_time - timedelta(minutes=30), event_time - timedelta(minutes=15), event_time, random.uniform(100, 1000), random.uniform(50, 100), random.uniform(0, 20), random.random() > 0.8, random.choice(["trace", "minor", "moderate", "major", "severe"]) if random.random() > 0.8 else None, [random.choice(["non_recyclable", "hazardous", "electronic", "medical", "construction", "liquid"])] if random.random() > 0.8 else None, None, random.randint(5, 60), "win_os")
                )
        self.db.connection.commit()
        print("Seeded collection events")

    def seed_telemetry(self, asset_ids: List[uuid.UUID]) -> None:
        bins = self.db.fetch_all("SELECT bin_id, asset_id FROM bins WHERE tenant_id = %s", (self.tenant_id,))
        now = datetime.now(timezone.utc)
        for bin_row in bins[:self.count]:
            for i in range(24):
                timestamp = now - timedelta(hours=24 - i)
                self.db.execute(
                    """INSERT INTO telemetry (telemetry_id, bin_id, asset_id, tenant_id, sensor_id, sensor_type, fill_level_percent, mass_kg, volume_m3, temperature_celsius, humidity_percent, contamination_flag, contamination_types, overflow_flag, tamper_flag, location_geom, reported_at, received_at, signal_strength_dbm, battery_percent, source_system, data_status, data_quality_status, confidence) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s, 'observed', %s, %s, %s) ON CONFLICT (telemetry_id) DO NOTHING""",
                    (uuid.uuid4(), bin_row["bin_id"], bin_row["asset_id"], self.tenant_id, f"sensor-{bin_row['bin_id'][:8]}", "ultrasonic", random.uniform(0, 100), random.uniform(0, 500), random.uniform(0, 1.0), random.uniform(10, 40), random.uniform(30, 80), random.random() > 0.9, [random.choice(["non_recyclable", "hazardous"])] if random.random() > 0.9 else None, random.random() > 0.95, random.random() > 0.98, f"POINT({random.uniform(-74.25909, -73.700181)} {random.uniform(40.477399, 40.917556)})", timestamp, timestamp + timedelta(minutes=random.randint(0, 10)), random.uniform(-80, -40), random.uniform(0, 100), "win_os", random.choice(["excellent", "good", "fair", "poor"]), random.uniform(0.8, 1.0))
                )
        self.db.connection.commit()
        print(f"Seeded telemetry data for {len(bins[:self.count])} bins")

    def seed_users_and_roles(self) -> None:
        roles = [
            {"name": "Platform Admin", "description": "Full access to all features", "is_default": False},
            {"name": "Organization Admin", "description": "Admin access for organization", "is_default": False},
            {"name": "Operations Manager", "description": "Manage operations and collections", "is_default": False},
            {"name": "Analyst", "description": "View and analyze data", "is_default": False},
            {"name": "Operator", "description": "Perform daily operations", "is_default": False},
            {"name": "Viewer", "description": "Read-only access", "is_default": True},
        ]

        role_ids = []
        for role in roles:
            role_id = uuid.uuid4()
            self.db.execute("INSERT INTO roles (role_id, tenant_id, name, description, is_default) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (tenant_id, name) DO NOTHING", (role_id, self.tenant_id, role["name"], role["description"], role["is_default"]))
            role_ids.append(role_id)

        permissions = [
            {"name": "manage_users", "resource_type": "user", "action": "manage"},
            {"name": "view_dashboard", "resource_type": "dashboard", "action": "view"},
            {"name": "manage_assets", "resource_type": "asset", "action": "manage"},
            {"name": "manage_routes", "resource_type": "route", "action": "manage"},
            {"name": "view_reports", "resource_type": "report", "action": "view"},
            {"name": "manage_organization", "resource_type": "organization", "action": "manage"},
            {"name": "view_analytics", "resource_type": "analytics", "action": "view"},
            {"name": "manage_data_sources", "resource_type": "data_source", "action": "manage"},
        ]

        permission_ids = []
        for perm in permissions:
            perm_id = uuid.uuid4()
            self.db.execute("INSERT INTO permissions (permission_id, name, description, resource_type, action) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (name) DO NOTHING", (perm_id, perm["name"], perm["description"], perm["resource_type"], perm["action"]))
            permission_ids.append(perm_id)

        role_permission_map = {
            "Platform Admin": [0, 1, 2, 3, 4, 5, 6, 7],
            "Organization Admin": [0, 1, 2, 3, 4, 5, 6],
            "Operations Manager": [1, 2, 3, 4, 5, 6],
            "Analyst": [1, 4, 5, 6],
            "Operator": [1, 2, 3, 4],
            "Viewer": [1, 4, 5],
        }

        for role, perm_indices in role_permission_map.items():
            role_idx = roles.index(next(r for r in roles if r["name"] == role))
            for perm_idx in perm_indices:
                self.db.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (role_ids[role_idx], permission_ids[perm_idx]))

        users = [
            {"email": "admin@nycwaste.gov", "full_name": "System Administrator", "job_title": "Platform Admin", "role": "Platform Admin", "is_superuser": True},
            {"email": "manager@nycwaste.gov", "full_name": "Operations Manager", "job_title": "Operations Manager", "role": "Operations Manager", "is_superuser": False},
            {"email": "analyst@nycwaste.gov", "full_name": "Data Analyst", "job_title": "Waste Analyst", "role": "Analyst", "is_superuser": False},
            {"email": "operator@nycwaste.gov", "full_name": "Field Operator", "job_title": "Collection Operator", "role": "Operator", "is_superuser": False},
        ]

        for user in users:
            user_id = uuid.uuid4()
            role_idx = roles.index(next(r for r in roles if r["name"] == user["role"]))
            self.db.execute("""INSERT INTO users (user_id, tenant_id, organization_id, email, full_name, job_title, department, timezone, locale, is_active, is_verified, is_superuser, password_hash, source_system) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (email) DO NOTHING""",
                (user_id, self.tenant_id, self.organization_id, user["email"], user["full_name"], user["job_title"], "Operations", "America/New_York", "en-US", True, True, user["is_superuser"], "$2b$12$hashed_password_placeholder", "win_os"))
            self.db.execute("INSERT INTO user_roles (user_id, role_id, assigned_by, created_at) VALUES (%s, %s, %s, NOW()) ON CONFLICT (user_id, role_id) DO NOTHING", (user_id, role_ids[role_idx], user_id))

        self.db.connection.commit()
        print(f"Seeded {len(users)} users, {len(roles)} roles, {len(permissions)} permissions")

    def seed_data_sources(self) -> None:
        sources = [
            {"name": "NYC Open Data Portal", "type": "api", "description": "NYC municipal waste data API", "config": {"url": "https://data.cityofnewyork.us/api", "rate_limit": 100}},
            {"name": "DSNY Collection Data", "type": "database", "description": "DSNY collection event database", "config": {"connection_string": "postgresql://dsny:password@dsny-db:5432/dsny"}},
            {"name": "Smart Bin Telemetry", "type": "mqtt", "description": "IoT sensor data from smart bins", "config": {"broker": "mqtt://iot-broker:1883", "topic": "sensors/+/telemetry"}},
            {"name": "Weather Data", "type": "api", "description": "NOAA weather data for forecasting", "config": {"url": "https://api.weather.gov", "rate_limit": 50}},
        ]
        for source in sources:
            source_id = uuid.uuid4()
            self.db.execute("""INSERT INTO data_sources (source_id, tenant_id, name, description, source_type, configuration, auth_type, is_active, sync_frequency_minutes, source_system, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, name) DO NOTHING""",
                (source_id, self.tenant_id, source["name"], source["description"], source["type"], json.dumps(source["config"]), "none", True, 60, "win_os"))
        self.db.connection.commit()
        print(f"Seeded {len(sources)} data sources")

    def seed_kg_nodes(self) -> Tuple[List[uuid.UUID], List[uuid.UUID], List[uuid.UUID]]:
        actor_ids = []
        process_ids = []
        resource_ids = []

        for actor in DataGenerator.ACTOR_TYPES:
            actor_id = uuid.uuid4()
            self.db.execute("""INSERT INTO kg_nodes (node_id, tenant_id, node_type, name, description, properties, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, node_id) DO NOTHING""",
                (actor_id, self.tenant_id, "Actor", actor["name"], f"{actor['type'].replace('_', ' ').title()} - {actor['scale']}", json.dumps({"actor_type": actor["type"], "scale": actor["scale"]})))
            actor_ids.append(actor_id)

        for process in DataGenerator.PROCESS_TYPES:
            process_id = uuid.uuid4()
            self.db.execute("""INSERT INTO kg_nodes (node_id, tenant_id, node_type, name, description, properties, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, node_id) DO NOTHING""",
                (process_id, self.tenant_id, "Process", process["name"], process["description"], json.dumps({"efficiency": process["efficiency"], "carbon_footprint": process["carbon_footprint"], "input_waste": process["input_waste"], "output_resources": process["output_resources"]})))
            process_ids.append(process_id)

        for resource in DataGenerator.RESOURCE_TYPES:
            resource_id = uuid.uuid4()
            self.db.execute("""INSERT INTO kg_nodes (node_id, tenant_id, node_type, name, description, properties, data_status) 
                   VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, node_id) DO NOTHING""",
                (resource_id, self.tenant_id, "Resource", resource["name"], resource["description"], json.dumps({"value_per_tonne": resource["value_per_tonne"]})))
            resource_ids.append(resource_id)

        self.db.connection.commit()
        print(f"Seeded {len(actor_ids)} actors, {len(process_ids)} processes, {len(resource_ids)} resources")
        return actor_ids, process_ids, resource_ids

    def seed_kg_edges(self, waste_type_ids: List[uuid.UUID], process_ids: List[uuid.UUID], resource_ids: List[uuid.UUID], facility_ids: List[uuid.UUID], actor_ids: List[uuid.UUID]) -> None:
        waste_type_map = {wt["name"]: wt_id for wt, wt_id in zip(DataGenerator.WASTE_TYPES, waste_type_ids)}
        process_map = {p["name"]: p_id for p, p_id in zip(DataGenerator.PROCESS_TYPES, process_ids)}
        resource_map = {r["name"]: r_id for r, r_id in zip(DataGenerator.RESOURCE_TYPES, resource_ids)}
        facility_map = {f["name"]: f_id for f, f_id in zip(DataGenerator.FACILITY_TYPES, facility_ids)}

        for process in DataGenerator.PROCESS_TYPES:
            p_id = process_map[process["name"]]
            for input_waste in process["input_waste"]:
                if input_waste in waste_type_map:
                    self.db.execute("""INSERT INTO kg_edges (edge_id, tenant_id, edge_type, source_id, target_id, properties, data_status) 
                           VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, source_id, edge_type, target_id) DO NOTHING""",
                        (uuid.uuid4(), self.tenant_id, "WASTECANBEPROCESSEDBY", waste_type_map[input_waste], p_id, json.dumps({})))

            for output_resource in process["output_resources"]:
                if output_resource in resource_map:
                    self.db.execute("""INSERT INTO kg_edges (edge_id, tenant_id, edge_type, source_id, target_id, properties, data_status) 
                           VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, source_id, edge_type, target_id) DO NOTHING""",
                        (uuid.uuid4(), self.tenant_id, "PROCESSPRODUCESRESOURCE", p_id, resource_map[output_resource], json.dumps({})))

        facility_process_map = {
            "Composting Facility": ["Aerobic Composting"],
            "Anaerobic Digestion Plant": ["Anaerobic Digestion"],
        }
        for facility in DataGenerator.FACILITY_TYPES:
            if facility["name"] in facility_process_map:
                f_id = facility_map[facility["name"]]
                for p_name in facility_process_map[facility["name"]]:
                    if p_name in process_map:
                        self.db.execute("""INSERT INTO kg_edges (edge_id, tenant_id, edge_type, source_id, target_id, properties, data_status) 
                               VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, source_id, edge_type, target_id) DO NOTHING""",
                            (uuid.uuid4(), self.tenant_id, "FACILITYSUPPORTSPROCESS", f_id, process_map[p_name], json.dumps({})))

        actor_resource_demand = {
            "Urban Farm Co-op": ["Compost", "Fertilizer"],
            "Green Waste Processors": ["Biogas", "Digestate", "Compost"],
        }
        for actor in DataGenerator.ACTOR_TYPES:
            if actor["name"] in actor_resource_demand:
                a_id = actor_ids[[a["name"] for a in DataGenerator.ACTOR_TYPES].index(actor["name"])]
                for r_name in actor_resource_demand[actor["name"]]:
                    if r_name in resource_map:
                        self.db.execute("""INSERT INTO kg_edges (edge_id, tenant_id, edge_type, source_id, target_id, properties, data_status) 
                               VALUES (%s, %s, %s, %s, %s, %s, 'reported') ON CONFLICT (tenant_id, source_id, edge_type, target_id) DO NOTHING""",
                            (uuid.uuid4(), self.tenant_id, "RESOURCEDEMANDEDBY_ACTOR", resource_map[r_name], a_id, json.dumps({})))

        self.db.connection.commit()
        print("Seeded Knowledge Graph edges")

    def seed_all(self, clear: bool = False) -> None:
        print("=" * 60)
        print("WIN OS - Comprehensive Seed Data Generator")
        print("=" * 60)
        print()

        self.initialize_tenant()
        print()

        if clear:
            self.clear_data()

        print("Seeding data...")
        print()

        waste_type_ids = self.seed_waste_types()
        facility_ids = self.seed_facilities(waste_type_ids)
        actor_ids, process_ids, resource_ids = self.seed_kg_nodes()
        self.seed_kg_edges(waste_type_ids, process_ids, resource_ids, facility_ids, actor_ids)
        asset_ids = self.seed_assets(facility_ids)
        route_ids = self.seed_routes(facility_ids, asset_ids)
        self.seed_collection_events(route_ids, asset_ids)
        self.seed_telemetry(asset_ids)
        self.seed_users_and_roles()
        self.seed_data_sources()

        print()
        print("=" * 60)
        print("Seed data generation complete!")
        print("=" * 60)

    def clear_data(self) -> None:
        print("Clearing existing data...")
        self.db.execute("SET session_replication_role = 'replica'")
        tables = ["kg_edges", "kg_nodes", "telemetry", "collection_events", "route_stops", "routes", "bins", "assets", "vehicles", "facilities", "waste_types", "data_sources", "users", "roles", "permissions", "role_permissions", "user_roles"]
        for table in tables:
            self.db.execute(f"DELETE FROM {table} WHERE tenant_id = %s", (self.tenant_id,))
        self.db.execute("SET session_replication_role = 'DEFAULT'")
        self.db.connection.commit()
        print("Cleared existing data")


def main():
    parser = argparse.ArgumentParser(description="WIN OS Seed Data Generator")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    parser.add_argument("--tenant", default=DEFAULT_TENANT, help="Tenant name")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of records to create")
    parser.add_argument("--dsn", default=None, help="Database connection string")
    args = parser.parse_args()

    try:
        db = Database(args.dsn)
        generator = SeedDataGenerator(db, args.tenant, args.count)
        generator.seed_all(clear=args.clear)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
