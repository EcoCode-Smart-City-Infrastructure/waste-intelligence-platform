"""Tests for NYC Open Data MCP Server."""

from __future__ import annotations

import pytest

from src.nyc_opendata_mcp.app import mcp
from src.nyc_opendata_mcp.config import (
    NYC_AIR_QUALITY_STATIONS,
    NYC_BOROUGHS,
    NYC_WEATHER_STATIONS,
    NYC_WATER_STATIONS,
)


@pytest.fixture
def test_app():
    """Test fixture for MCP server."""
    return mcp


class TestServerConfiguration:
    """Test server configuration."""

    def test_mcp_server_created(self, test_app):
        """Test that MCP server is created."""
        assert test_app is not None
        assert test_app.name == "nyc_opendata_mcp"

    def test_server_metadata(self, test_app):
        """Test server metadata."""
        assert test_app.title == "New York City Open Data"
        assert "NYC" in test_app.description
        assert test_app.version is not None

    def test_server_instructions(self, test_app):
        """Test server instructions."""
        assert test_app.instructions is not None
        assert len(test_app.instructions) > 0


class TestConfiguration:
    """Test configuration values."""

    def test_nyc_boroughs(self):
        """Test NYC boroughs list."""
        assert len(NYC_BOROUGHS) == 5
        assert "manhattan" in NYC_BOROUGHS
        assert "bronx" in NYC_BOROUGHS
        assert "brooklyn" in NYC_BOROUGHS
        assert "queens" in NYC_BOROUGHS
        assert "staten-island" in NYC_BOROUGHS

    def test_weather_stations(self):
        """Test weather station list."""
        assert len(NYC_WEATHER_STATIONS) >= 4
        assert "KNYC" in NYC_WEATHER_STATIONS  # Central Park
        assert "KNYN" in NYC_WEATHER_STATIONS  # LaGuardia
        assert "KJFK" in NYC_WEATHER_STATIONS  # JFK
        assert "KEWR" in NYC_WEATHER_STATIONS  # Newark

    def test_air_quality_stations(self):
        """Test air quality station list."""
        assert len(NYC_AIR_QUALITY_STATIONS) >= 5
        assert all(s.isdigit() for s in NYC_AIR_QUALITY_STATIONS)

    def test_water_stations(self):
        """Test water quality station list."""
        assert len(NYC_WATER_STATIONS) >= 5
        assert "East River" in NYC_WATER_STATIONS
        assert "Hudson River" in NYC_WATER_STATIONS


class TestToolRegistration:
    """Test tool registration."""

    def test_tools_registered(self, test_app):
        """Test that tools are registered."""
        # Import tool modules to register them
        from src.nyc_opendata_mcp.tools import (
            catalog,
            datastore,
            geo,
            government,
            mobility,
            realtime,
            waste_intel,
            waste_datasets,
        )
        
        # Check that tools are registered
        tool_count = len(test_app._tool_manager._tools)
        assert tool_count > 0

    def test_catalog_tools_registered(self, test_app):
        """Test that catalog tools are registered."""
        from src.nyc_opendata_mcp.tools import catalog
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_search_datasets" in tool_names
        assert "nyc_get_dataset" in tool_names
        assert "nyc_list_categories" in tool_names
        assert "nyc_list_tags" in tool_names

    def test_realtime_tools_registered(self, test_app):
        """Test that realtime tools are registered."""
        from src.nyc_opendata_mcp.tools import realtime
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_weather_live" in tool_names
        assert "nyc_air_quality" in tool_names
        assert "nyc_water_quality" in tool_names
        assert "nyc_pedestrian_traffic" in tool_names
        assert "nyc_mta_ridership" in tool_names
        assert "nyc_parking_live" in tool_names

    def test_geo_tools_registered(self, test_app):
        """Test that geo tools are registered."""
        from src.nyc_opendata_mcp.tools import geo
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_geo_layers" in tool_names
        assert "nyc_geo_features" in tool_names
        assert "nyc_geo_spatial_query" in tool_names

    def test_waste_intel_tools_registered(self, test_app):
        """Test that waste intelligence tools are registered."""
        from src.nyc_opendata_mcp.tools import waste_intel
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_wastebin_live" in tool_names
        assert "nyc_wastecluster_live" in tool_names
        assert "nyc_wastefacility_load" in tool_names
        assert "nyc_waste_forecast" in tool_names
        assert "nyc_waste_anomaly" in tool_names
        assert "nyc_waste_contamination" in tool_names
        assert "nyc_waste_kg_query" in tool_names

    def test_waste_dataset_tools_registered(self, test_app):
        """Test that waste dataset tools are registered."""
        from src.nyc_opendata_mcp.tools import waste_datasets
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_waste_datasets" in tool_names
        assert "nyc_waste_tonnage" in tool_names
        assert "nyc_waste_facilities" in tool_names
        assert "nyc_organics_collection" in tool_names
        assert "nyc_recycling_contamination" in tool_names

    def test_government_tools_registered(self, test_app):
        """Test that government tools are registered."""
        from src.nyc_opendata_mcp.tools import government
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_council_members" in tool_names
        assert "nyc_council_search" in tool_names
        assert "nyc_legislation" in tool_names
        assert "nyc_legislation_detail" in tool_names
        assert "nyc_mayoral_orders" in tool_names

    def test_mobility_tools_registered(self, test_app):
        """Test that mobility tools are registered."""
        from src.nyc_opendata_mcp.tools import mobility
        
        tool_names = [t.name for t in test_app._tool_manager._tools.values()]
        
        assert "nyc_mta_status" in tool_names
        assert "nyc_mta_station_status" in tool_names
        assert "nyc_traffic_incidents" in tool_names
        assert "nyc_bike_share" in tool_names
