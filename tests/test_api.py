"""Tests for Waste Intelligence Platform API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.waste_intelligence_api.app import app


@pytest.fixture
def test_client():
    """Test fixture for FastAPI client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_check_app_info(self, test_client):
        """Test health check returns app info."""
        response = test_client.get("/health")
        data = response.json()
        
        assert "app" in data
        assert "version" in data
        assert "city" in data


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        assert "app" in response.json()
        assert "version" in response.json()
        assert "docs" in response.json()

    def test_root_endpoint_info(self, test_client):
        """Test root endpoint returns API info."""
        response = test_client.get("/")
        data = response.json()
        
        assert data["app"] == "Waste Intelligence Platform API"
        assert data["version"] == "1.0.0"
        assert data["city"] == "New York City"


class TestBinEndpoints:
    """Test bin telemetry endpoints."""

    def test_get_bin(self, test_client):
        """Test getting bin telemetry."""
        response = test_client.get("/mcp/waste/bin?bin_id=BIN-00123")
        
        assert response.status_code == 200
        assert "bin_id" in response.json()

    def test_get_bin_history(self, test_client):
        """Test getting bin history."""
        response = test_client.get(
            "/mcp/waste/bin/history?bin_id=BIN-00123&limit=10"
        )
        
        assert response.status_code == 200
        assert "bin_id" in response.json()
        assert "count" in response.json()

    def test_list_bins(self, test_client):
        """Test listing bins."""
        response = test_client.get("/mcp/waste/bins?limit=10")
        
        assert response.status_code == 200
        assert "count" in response.json()
        assert "bins" in response.json()


class TestClusterEndpoints:
    """Test cluster telemetry endpoints."""

    def test_get_cluster(self, test_client):
        """Test getting cluster telemetry."""
        response = test_client.get("/mcp/waste/cluster?cluster_id=CLUSTER-001")
        
        assert response.status_code == 200
        assert "cluster_id" in response.json()

    def test_get_cluster_history(self, test_client):
        """Test getting cluster history."""
        response = test_client.get(
            "/mcp/waste/cluster/history?cluster_id=CLUSTER-001&limit=10"
        )
        
        assert response.status_code == 200
        assert "cluster_id" in response.json()
        assert "count" in response.json()

    def test_list_clusters(self, test_client):
        """Test listing clusters."""
        response = test_client.get("/mcp/waste/clusters?limit=10")
        
        assert response.status_code == 200
        assert "count" in response.json()
        assert "clusters" in response.json()


class TestFacilityEndpoints:
    """Test facility telemetry endpoints."""

    def test_get_facility(self, test_client):
        """Test getting facility telemetry."""
        response = test_client.get("/mcp/waste/facility?facility_id=FAC-001")
        
        assert response.status_code == 200
        assert "facility_id" in response.json()

    def test_get_facility_history(self, test_client):
        """Test getting facility history."""
        response = test_client.get(
            "/mcp/waste/facility/history?facility_id=FAC-001&limit=10"
        )
        
        assert response.status_code == 200
        assert "facility_id" in response.json()
        assert "count" in response.json()

    def test_list_facilities(self, test_client):
        """Test listing facilities."""
        response = test_client.get("/mcp/waste/facilities?limit=10")
        
        assert response.status_code == 200
        assert "count" in response.json()
        assert "facilities" in response.json()

    def test_get_facility_load(self, test_client):
        """Test getting facility load."""
        response = test_client.get("/mcp/waste/facility/load?facility_id=FAC-001")
        
        assert response.status_code == 200
        assert "facility_id" in response.json()
        assert "load" in response.json()

    def test_get_facility_forecast(self, test_client):
        """Test getting facility forecast."""
        response = test_client.get(
            "/mcp/waste/facility/forecast?facility_id=FAC-001&hours=24"
        )
        
        assert response.status_code == 200
        assert "facility_id" in response.json()
        assert "forecast" in response.json()


class TestMLEndpoints:
    """Test ML inference endpoints."""

    def test_forecast(self, test_client):
        """Test waste forecasting."""
        request_data = {
            "features": {
                "historical_tonnage": [10000, 12000, 11000, 13000, 14000],
                "day_of_week": 3,
            },
            "horizon_hours": 24
        }
        response = test_client.post("/mcp/waste/forecast", json=request_data)
        
        assert response.status_code == 200
        assert "predicted_value" in response.json()
        assert "confidence" in response.json()

    def test_anomaly(self, test_client):
        """Test anomaly detection."""
        request_data = {
            "features": {
                "mass_kg": 450.5,
                "filllevelpct": 85.2,
                "gas_ppm": 25.3,
            },
            "threshold": 0.95
        }
        response = test_client.post("/mcp/waste/anomaly", json=request_data)
        
        assert response.status_code == 200
        assert "is_anomaly" in response.json()
        assert "anomaly_score" in response.json()

    def test_contamination(self, test_client):
        """Test contamination detection."""
        request_data = {
            "image_url": "https://example.com/sample_waste_image.jpg",
            "threshold": 0.7
        }
        response = test_client.post("/mcp/waste/contamination", json=request_data)
        
        assert response.status_code == 200
        assert "contamination_type" in response.json()
        assert "confidence" in response.json()


class TestKGEndpoints:
    """Test Knowledge Graph endpoints."""

    def test_kg_query(self, test_client):
        """Test knowledge graph query."""
        request_data = {
            "query": "recycling pathways for plastic",
            "limit": 10
        }
        response = test_client.post("/mcp/waste/kg", json=request_data)
        
        assert response.status_code == 200
        assert "query" in response.json()
        assert "results" in response.json()

    def test_circular_economy(self, test_client):
        """Test circular economy suggestions."""
        request_data = {
            "waste_type": "Plastic",
            "quantity_kg": 1000.0,
            "location": "Manhattan"
        }
        response = test_client.post("/mcp/waste/circular_economy", json=request_data)
        
        assert response.status_code == 200
        assert "waste_type" in response.json()
        assert "suggestions" in response.json()


class TestBatchEndpoints:
    """Test batch processing endpoints."""

    def test_batch_forecast(self, test_client):
        """Test batch forecasting."""
        request_data = {
            "requests": [
                {
                    "features": {"historical_tonnage": [10000, 12000]},
                    "horizon_hours": 24
                },
                {
                    "features": {"historical_tonnage": [15000, 13000]},
                    "horizon_hours": 48
                }
            ]
        }
        response = test_client.post("/mcp/waste/batch/forecast", json=request_data)
        
        assert response.status_code == 200
        assert "count" in response.json()
        assert "results" in response.json()

    def test_batch_anomaly(self, test_client):
        """Test batch anomaly detection."""
        request_data = {
            "requests": [
                {
                    "features": {"filllevelpct": 85.0, "gas_ppm": 25.0},
                    "threshold": 0.95
                },
                {
                    "features": {"filllevelpct": 95.0, "gas_ppm": 50.0},
                    "threshold": 0.9
                }
            ]
        }
        response = test_client.post("/mcp/waste/batch/anomaly", json=request_data)
        
        assert response.status_code == 200
        assert "count" in response.json()
        assert "results" in response.json()
