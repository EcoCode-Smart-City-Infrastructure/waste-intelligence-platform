"""Tests for Waste Intelligence Platform tools."""

from __future__ import annotations

import pytest

from src.nyc_opendata_mcp.tools.waste_intel import (
    nyc_waste_anomaly,
    nyc_wastebin_live,
    nyc_wastecluster_live,
    nyc_waste_contamination,
    nyc_wastefacility_load,
    nyc_waste_forecast,
    nyc_waste_kg_query,
    nyc_waste_circular_economy,
)


class TestWasteBinLive:
    """Test waste bin live telemetry functionality."""

    @pytest.mark.asyncio
    async def test_bin_live(self):
        """Test getting live bin telemetry."""
        from src.nyc_opendata_mcp.tools.waste_intel import BinLiveInput
        
        input_data = BinLiveInput(bin_id="BIN-00123")
        result = await nyc_wastebin_live(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_bin_live_markdown(self):
        """Test getting live bin telemetry in markdown format."""
        from src.nyc_opendata_mcp.tools.waste_intel import BinLiveInput
        
        input_data = BinLiveInput(bin_id="BIN-00123", format="markdown")
        result = await nyc_wastebin_live(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_bin_live_json(self):
        """Test getting live bin telemetry in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import BinLiveInput
        
        input_data = BinLiveInput(bin_id="BIN-00123", format="json")
        result = await nyc_wastebin_live(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteClusterLive:
    """Test waste cluster live telemetry functionality."""

    @pytest.mark.asyncio
    async def test_cluster_live(self):
        """Test getting live cluster telemetry."""
        from src.nyc_opendata_mcp.tools.waste_intel import ClusterLiveInput
        
        input_data = ClusterLiveInput(cluster_id="CLUSTER-001")
        result = await nyc_wastecluster_live(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_cluster_live_json(self):
        """Test getting live cluster telemetry in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import ClusterLiveInput
        
        input_data = ClusterLiveInput(cluster_id="CLUSTER-001", format="json")
        result = await nyc_wastecluster_live(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteFacilityLoad:
    """Test waste facility load functionality."""

    @pytest.mark.asyncio
    async def test_facility_load(self):
        """Test getting facility load data."""
        from src.nyc_opendata_mcp.tools.waste_intel import FacilityLoadInput
        
        input_data = FacilityLoadInput(facility_id="FAC-001")
        result = await nyc_wastefacility_load(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_facility_load_json(self):
        """Test getting facility load data in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import FacilityLoadInput
        
        input_data = FacilityLoadInput(facility_id="FAC-001", format="json")
        result = await nyc_wastefacility_load(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteForecast:
    """Test waste forecasting functionality."""

    @pytest.mark.asyncio
    async def test_forecast(self):
        """Test generating waste forecast."""
        from src.nyc_opendata_mcp.tools.waste_intel import ForecastInput
        
        input_data = ForecastInput(
            features={
                "historical_tonnage": [10000, 12000, 11000, 13000, 14000],
                "day_of_week": 3,
            },
            horizon_hours=24
        )
        result = await nyc_waste_forecast(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_forecast_json(self):
        """Test generating waste forecast in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import ForecastInput
        
        input_data = ForecastInput(
            features={"historical_tonnage": [10000, 12000, 11000]},
            horizon_hours=24,
            format="json"
        )
        result = await nyc_waste_forecast(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteAnomaly:
    """Test waste anomaly detection functionality."""

    @pytest.mark.asyncio
    async def test_anomaly(self):
        """Test detecting waste anomalies."""
        from src.nyc_opendata_mcp.tools.waste_intel import AnomalyInput
        
        input_data = AnomalyInput(
            features={
                "mass_kg": 450.5,
                "filllevelpct": 85.2,
                "gas_ppm": 25.3,
            },
            threshold=0.95
        )
        result = await nyc_waste_anomaly(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_anomaly_json(self):
        """Test detecting waste anomalies in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import AnomalyInput
        
        input_data = AnomalyInput(
            features={"filllevelpct": 95.0, "gas_ppm": 50.0},
            threshold=0.9,
            format="json"
        )
        result = await nyc_waste_anomaly(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteContamination:
    """Test waste contamination detection functionality."""

    @pytest.mark.asyncio
    async def test_contamination(self):
        """Test detecting waste contamination."""
        from src.nyc_opendata_mcp.tools.waste_intel import ContaminationInput
        
        input_data = ContaminationInput(
            image_url="https://example.com/sample_waste_image.jpg",
            threshold=0.7
        )
        result = await nyc_waste_contamination(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_contamination_json(self):
        """Test detecting waste contamination in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import ContaminationInput
        
        input_data = ContaminationInput(
            image_url="https://example.com/sample_waste_image.jpg",
            threshold=0.7,
            format="json"
        )
        result = await nyc_waste_contamination(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteKGQuery:
    """Test waste knowledge graph query functionality."""

    @pytest.mark.asyncio
    async def test_kg_query(self):
        """Test querying waste knowledge graph."""
        from src.nyc_opendata_mcp.tools.waste_intel import KGQueryInput
        
        input_data = KGQueryInput(
            query="recycling pathways for plastic",
            limit=10
        )
        result = await nyc_waste_kg_query(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_kg_query_json(self):
        """Test querying waste knowledge graph in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import KGQueryInput
        
        input_data = KGQueryInput(
            query="composting process",
            limit=5,
            format="json"
        )
        result = await nyc_waste_kg_query(input_data)
        
        assert result is not None
        assert "status" in result


class TestWasteCircularEconomy:
    """Test waste circular economy suggestions functionality."""

    @pytest.mark.asyncio
    async def test_circular_economy(self):
        """Test getting circular economy suggestions."""
        from src.nyc_opendata_mcp.tools.waste_intel import CircularEconomyInput
        
        input_data = CircularEconomyInput(
            waste_type="Plastic",
            quantity_kg=1000.0,
            location="Manhattan"
        )
        result = await nyc_waste_circular_economy(input_data)
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_circular_economy_json(self):
        """Test getting circular economy suggestions in JSON format."""
        from src.nyc_opendata_mcp.tools.waste_intel import CircularEconomyInput
        
        input_data = CircularEconomyInput(
            waste_type="Organics",
            quantity_kg=500.0,
            format="json"
        )
        result = await nyc_waste_circular_economy(input_data)
        
        assert result is not None
        assert "status" in result
