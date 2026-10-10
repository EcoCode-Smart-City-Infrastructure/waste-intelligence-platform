"""Endpoints, layer maps and other static configuration for NYC Open Data MCP Server."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Literal

# NYC Open Data (Socrata) API
SOCRATA_BASE_URL = "https://data.cityofnewyork.us"
SOCRATA_API_URL = f"{SOCRATA_BASE_URL}/resource"
SOCRATA_DATASET_URL = f"{SOCRATA_BASE_URL}/api/views"

# Environmental APIs
NOAA_BASE_URL = "https://api.weather.gov"
NOAA_STATIONS_URL = f"{NOAA_BASE_URL}/stations"
AIRNOW_API_URL = "https://www.airnowapi.org/aq/observation"
NYC_DEP_WATER_URL = "https://data.cityofnewyork.us/resource/7c3d-6b2j"

# Mobility APIs
MTA_GTFS_REALTIME_URL = "https://api.mta.info/gtfs/realtime"
NYC_DOT_PEDESTRIAN_URL = "https://data.cityofnewyork.us/resource/tv4k-3ndv"
NYC_DOT_PARKING_URL = "https://data.cityofnewyork.us/resource/2v8k-7z7z"

# Geodata APIs
NYC_GEOHUB_URL = "https://geodata.cityofnewyork.us"
NYC_PLUTO_URL = "https://pluto.cityofnewyork.us"

# Government APIs
NYC_COUNCIL_API_URL = "https://legistar.council.nyc.gov/api"
NYC_LEGISTAR_URL = "https://legistar.council.nyc.gov"

# Waste Intelligence Platform APIs
WASTE_INTEL_API_URL = "https://waste-intel-api.cityofnewyork.us"
WASTE_INTEL_MQTT_URL = "mqtt://waste-intel-mqtt.cityofnewyork.us"
WASTE_INTEL_LORAWAN_URL = "https://waste-intel-lorawan.cityofnewyork.us"

REQUEST_TIMEOUT = 30.0

try:
    PACKAGE_VERSION = version("nyc-opendata-mcp")
except PackageNotFoundError:  # pragma: no cover - only when running from a non-installed tree
    PACKAGE_VERSION = "0.0.0+local"

# Public identity for User-Agent and server info
REPO_URL = "https://github.com/EcoCode-Smart-City-Infrastructure/waste-intelligence-platform"

USER_AGENT = f"NYCOpenDataMCP/{PACKAGE_VERSION} (+{REPO_URL})"

# NYC Open Data categories (Socrata groups)
NYC_CATEGORIES = [
    "business",
    "city-government",
    "education",
    "environment",
    "health",
    "housing-development",
    "public-safety",
    "social-services",
    "transportation",
    "waste-management",
]

# NYC Boroughs
NYC_BOROUGHS = [
    "manhattan",
    "bronx",
    "brooklyn",
    "queens",
    "staten-island",
]

# NYC Environmental Stations
NYC_WEATHER_STATIONS = [
    "KNYC",  # Central Park
    "KNYN",  # LaGuardia Airport
    "KJFK",  # JFK Airport
    "KEWR",  # Newark Airport
]

NYC_AIR_QUALITY_STATIONS = [
    "101",  # Manhattan
    "102",  # Bronx
    "103",  # Brooklyn
    "104",  # Queens
    "105",  # Staten Island
]

# NYC Water Quality Monitoring Stations
NYC_WATER_STATIONS = [
    "East River",
    "Hudson River",
    "Harbor",
    "Newtown Creek",
    "Gowanus Canal",
]

# MTA Subway Lines
MTA_SUBWAY_LINES = [
    "1", "2", "3", "4", "5", "6", "7", "A", "B", "C", "D", "E", "F", "G",
    "J", "L", "M", "N", "Q", "R", "S", "W", "Z"
]

# Geodata layers for NYC GeoHub
GEOHUB_LAYERS: dict[str, tuple[str, str, str]] = {
    "boroughs": (
        "boroughs",
        "borough_boundaries",
        "Borough Boundaries (Polygons)",
    ),
    "neighborhoods": (
        "neighborhoods",
        "neighborhood_tabulation_areas",
        "Neighborhood Tabulation Areas (Polygons)",
    ),
    "council_districts": (
        "council_districts",
        "council_districts",
        "City Council Districts (Polygons)",
    ),
    "community_districts": (
        "community_districts",
        "community_districts",
        "Community Districts (Polygons)",
    ),
    "zip_codes": (
        "zip_codes",
        "zip_code_boundaries",
        "ZIP Code Boundaries (Polygons)",
    ),
    "schools": (
        "schools",
        "school_locations",
        "Public School Locations (Points)",
    ),
    "parks": (
        "parks",
        "parks",
        "Parks and Recreation Facilities (Polygons)",
    ),
    "hospitals": (
        "hospitals",
        "hospital_locations",
        "Hospital Locations (Points)",
    ),
    "subway_stations": (
        "subway_stations",
        "subway_stations",
        "Subway Station Entrances (Points)",
    ),
    "waste_facilities": (
        "waste_facilities",
        "dsny_facilities",
        "DSNY Waste Management Facilities (Points)",
    ),
    "recycling_centers": (
        "recycling_centers",
        "recycling_centers",
        "Recycling Centers (Points)",
    ),
}

# NYC Waste Management Dataset IDs (Socrata)
WASTE_DATASETS = {
    "dsny_tonnage": "7c3d-6b2j",  # DSNY Monthly Tonnage Reports
    "organics_collection": "q48t-q583",  # NYC Organics Collection Pilot
    "commercial_waste": "2v8k-7z7z",  # Commercial Waste Zones
    "facility_locations": "4v9k-7z7z",  # Facility Locations
    "recycling_contamination": "3v9k-8z8z",  # Recycling Contamination
    "zero_waste": "1v9k-9z9z",  # Zero Waste NYC
}

# NYC Mobility Dataset IDs (Socrata)
MOBILITY_DATASETS = {
    "pedestrian_counts": "tv4k-3ndv",  # NYC DOT Pedestrian Counts
    "parking_sensors": "2v8k-7z7z",  # NYC DOT Parking Sensors
    "taxi_trips": "2v8k-7z7z",  # NYC TLC Taxi Trips
}

# NYC Environmental Dataset IDs (Socrata)
ENVIRONMENTAL_DATASETS = {
    "air_quality": "q68m-8z8z",  # NYC DEP Air Quality
    "water_quality": "7c3d-6b2j",  # NYC DEP Harbor Water Quality
    "noise_complaints": "3v9k-8z8z",  # NYC 311 Noise Complaints
}

# NYC Government Dataset IDs (Socrata)
GOVERNMENT_DATASETS = {
    "council_members": "1v9k-9z9z",  # NYC Council Members
    "legislation": "2v8k-7z7z",  # NYC Council Legislation
    "budget": "3v9k-8z8z",  # NYC Budget
}

# Literal aliases for Pydantic input models
NYCCategory = Literal[
    "business",
    "city-government",
    "education",
    "environment",
    "health",
    "housing-development",
    "public-safety",
    "social-services",
    "transportation",
    "waste-management",
]

GeoLayerId = Literal[
    "boroughs",
    "neighborhoods",
    "council_districts",
    "community_districts",
    "zip_codes",
    "schools",
    "parks",
    "hospitals",
    "subway_stations",
    "waste_facilities",
    "recycling_centers",
]

NYCBorough = Literal[
    "manhattan",
    "bronx",
    "brooklyn",
    "queens",
    "staten-island",
]

NYCWeatherStation = Literal[
    "KNYC",
    "KNYN",
    "KJFK",
    "KEWR",
]

NYCAirQualityStation = Literal[
    "101",
    "102",
    "103",
    "104",
    "105",
]

NYCWaterStation = Literal[
    "East River",
    "Hudson River",
    "Harbor",
    "Newtown Creek",
    "Gowanus Canal",
]

MTALine = Literal[
    "1", "2", "3", "4", "5", "6", "7", "A", "B", "C", "D", "E", "F", "G",
    "J", "L", "M", "N", "Q", "R", "S", "W", "Z"
]

OutputFormat = Literal["markdown", "json"]
