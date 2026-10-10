"""Configuration for Waste Intelligence Platform API."""

from __future__ import annotations

import os
from typing import Any


class Config:
    """Configuration settings for Waste Intelligence Platform API."""
    
    # Application settings
    CITY = "New York City"
    APP_NAME = "Waste Intelligence Platform API"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "NYC Waste Intelligence API for MCP + Smart City Testbed"
    
    # Database settings
    DB_URL = os.environ.get("DB_URL", "postgresql://timescale:password@localhost/wasteintel")
    
    # ML Service settings
    ML_URL = os.environ.get("ML_URL", "http://ml-service:8001")
    ML_TIMEOUT = float(os.environ.get("ML_TIMEOUT", "30.0"))
    
    # Knowledge Graph settings
    KG_URL = os.environ.get("KG_URL", "http://kg-service:8002")
    KG_TIMEOUT = float(os.environ.get("KG_TIMEOUT", "30.0"))
    
    # Waste Intelligence settings
    WASTE_INTEL_URL = os.environ.get("WASTE_INTEL_URL", "http://waste-intel-service:8003")
    
    # API settings
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "8000"))
    
    # Authentication settings
    API_KEY = os.environ.get("API_KEY")
    REQUIRE_API_KEY = os.environ.get("REQUIRE_API_KEY", "false").lower() == "true"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_SECONDS = int(os.environ.get("RATE_LIMIT_SECONDS", "60"))
    
    # CORS settings
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS = ["*"]
    
    # Logging settings
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Cache settings
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))  # 5 minutes
    
    # NYC-specific settings
    NYC_BOROUGHS = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
    
    # Facility metadata
    FACILITY_METADATA = {
        "FAC-001": {
            "name": "North River Transfer Station",
            "borough": "Manhattan",
            "type": "Transfer Station",
            "capacity_tons_per_day": 5000,
        },
        "FAC-002": {
            "name": "Hunts Point Transfer Station",
            "borough": "Bronx",
            "type": "Transfer Station",
            "capacity_tons_per_day": 4000,
        },
        "FAC-003": {
            "name": "26th Ward Transfer Station",
            "borough": "Brooklyn",
            "type": "Transfer Station",
            "capacity_tons_per_day": 3000,
        },
        "FAC-004": {
            "name": "Springfield Gardens Composting",
            "borough": "Queens",
            "type": "Composting Facility",
            "capacity_tons_per_day": 500,
        },
        "FAC-005": {
            "name": "Wards Island WPCP",
            "borough": "Manhattan",
            "type": "Wastewater Treatment",
            "capacity_tons_per_day": 10000,
        },
    }
    
    # Routing information
    ROUTING = {
        "Manhattan": {
            "districts": ["MN-01", "MN-02", "MN-03", "MN-04", "MN-05"],
            "collection_frequency": "daily",
        },
        "Bronx": {
            "districts": ["BX-01", "BX-02", "BX-03", "BX-04", "BX-05"],
            "collection_frequency": "daily",
        },
        "Brooklyn": {
            "districts": ["BK-01", "BK-02", "BK-03", "BK-04", "BK-05"],
            "collection_frequency": "daily",
        },
        "Queens": {
            "districts": ["QN-01", "QN-02", "QN-03", "QN-04", "QN-05"],
            "collection_frequency": "daily",
        },
        "Staten Island": {
            "districts": ["SI-01", "SI-02"],
            "collection_frequency": "daily",
        },
    }
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return getattr(cls, key, default)
    
    @classmethod
    def to_dict(cls) -> dict:
        """Convert configuration to dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }
