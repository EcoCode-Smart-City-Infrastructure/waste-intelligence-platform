"""Tests for NYC Open Data realtime tools."""

from __future__ import annotations

import pytest

from src.nyc_opendata_mcp.tools.realtime import (
    nyc_air_quality,
    nyc_mta_ridership,
    nyc_parking_live,
    nyc_pedestrian_traffic,
    nyc_water_quality,
    nyc_weather_live,
)


class TestWeatherLive:
    """Test weather live data functionality."""

    @pytest.mark.asyncio
    async def test_weather_all_stations(self):
        """Test getting weather for all stations."""
        from src.nyc_opendata_mcp.models import WeatherLiveInput
        
        input_data = WeatherLiveInput()
        result = await nyc_weather_live(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_weather_single_station(self):
        """Test getting weather for a single station."""
        from src.nyc_opendata_mcp.models import WeatherLiveInput
        
        input_data = WeatherLiveInput(station="KNYC")
        result = await nyc_weather_live(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_weather_json_format(self):
        """Test getting weather in JSON format."""
        from src.nyc_opendata_mcp.models import WeatherLiveInput
        
        input_data = WeatherLiveInput(format="json")
        result = await nyc_weather_live(input_data)
        
        assert result is not None
        assert "status" in result
        assert "data" in result or "markdown" in result


class TestAirQuality:
    """Test air quality data functionality."""

    @pytest.mark.asyncio
    async def test_air_quality_all_stations(self):
        """Test getting air quality for all stations."""
        from src.nyc_opendata_mcp.models import AirQualityInput
        
        input_data = AirQualityInput()
        result = await nyc_air_quality(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_air_quality_json_format(self):
        """Test getting air quality in JSON format."""
        from src.nyc_opendata_mcp.models import AirQualityInput
        
        input_data = AirQualityInput(format="json")
        result = await nyc_air_quality(input_data)
        
        assert result is not None
        assert "status" in result


class TestWaterQuality:
    """Test water quality data functionality."""

    @pytest.mark.asyncio
    async def test_water_quality_all_stations(self):
        """Test getting water quality for all stations."""
        from src.nyc_opendata_mcp.models import WaterQualityInput
        
        input_data = WaterQualityInput()
        result = await nyc_water_quality(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_water_quality_json_format(self):
        """Test getting water quality in JSON format."""
        from src.nyc_opendata_mcp.models import WaterQualityInput
        
        input_data = WaterQualityInput(format="json")
        result = await nyc_water_quality(input_data)
        
        assert result is not None
        assert "status" in result


class TestPedestrianTraffic:
    """Test pedestrian traffic data functionality."""

    @pytest.mark.asyncio
    async def test_pedestrian_traffic_all_locations(self):
        """Test getting pedestrian traffic for all locations."""
        from src.nyc_opendata_mcp.models import PedestrianInput
        
        input_data = PedestrianInput()
        result = await nyc_pedestrian_traffic(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_pedestrian_traffic_json_format(self):
        """Test getting pedestrian traffic in JSON format."""
        from src.nyc_opendata_mcp.models import PedestrianInput
        
        input_data = PedestrianInput(format="json")
        result = await nyc_pedestrian_traffic(input_data)
        
        assert result is not None
        assert "status" in result


class TestMTARidership:
    """Test MTA ridership data functionality."""

    @pytest.mark.asyncio
    async def test_mta_ridership_all_lines(self):
        """Test getting MTA ridership for all lines."""
        from src.nyc_opendata_mcp.models import MTARidershipInput
        
        input_data = MTARidershipInput()
        result = await nyc_mta_ridership(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_mta_ridership_single_line(self):
        """Test getting MTA ridership for a single line."""
        from src.nyc_opendata_mcp.models import MTARidershipInput
        
        input_data = MTARidershipInput(line="1")
        result = await nyc_mta_ridership(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_mta_ridership_json_format(self):
        """Test getting MTA ridership in JSON format."""
        from src.nyc_opendata_mcp.models import MTARidershipInput
        
        input_data = MTARidershipInput(format="json")
        result = await nyc_mta_ridership(input_data)
        
        assert result is not None
        assert "status" in result


class TestParkingLive:
    """Test parking live data functionality."""

    @pytest.mark.asyncio
    async def test_parking_all_lots(self):
        """Test getting parking for all lots."""
        from src.nyc_opendata_mcp.models import ParkingLiveInput
        
        input_data = ParkingLiveInput()
        result = await nyc_parking_live(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_parking_json_format(self):
        """Test getting parking in JSON format."""
        from src.nyc_opendata_mcp.models import ParkingLiveInput
        
        input_data = ParkingLiveInput(format="json")
        result = await nyc_parking_live(input_data)
        
        assert result is not None
        assert "status" in result
