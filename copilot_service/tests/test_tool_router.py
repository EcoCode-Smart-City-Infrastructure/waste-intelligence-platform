"""Tests for Tool Router."""

import pytest
from copilot_service.core.tool_router import ToolRouter, ToolCall, ToolType, IntentType


@pytest.fixture
def tool_router():
    return ToolRouter()


class TestIntentDetection:
    """Test intent detection from queries."""
    
    def test_detect_telemetry_intent(self, tool_router):
        """Test detecting telemetry intent."""
        intent = tool_router.detect_intent("Show me the sensor readings")
        assert intent == IntentType.TELEMETRY
    
    def test_detect_anomaly_intent(self, tool_router):
        """Test detecting anomaly intent."""
        intent = tool_router.detect_intent("Why is there an anomaly in cluster BK-07?")
        assert intent == IntentType.ANOMALY
    
    def test_detect_forecast_intent(self, tool_router):
        """Test detecting forecast intent."""
        intent = tool_router.detect_intent("Predict the waste load for tomorrow")
        assert intent == IntentType.FORECAST
    
    def test_detect_contamination_intent(self, tool_router):
        """Test detecting contamination intent."""
        intent = tool_router.detect_intent("Check for contamination in the waste")
        assert intent == IntentType.CONTAMINATION
    
    def test_detect_city_data_intent(self, tool_router):
        """Test detecting city data intent."""
        intent = tool_router.detect_intent("What is the weather in Brooklyn?")
        assert intent == IntentType.CITY_DATA
    
    def test_detect_pathways_intent(self, tool_router):
        """Test detecting pathways intent."""
        intent = tool_router.detect_intent("Show me waste-to-resource pathways")
        assert intent == IntentType.PATHWAYS
    
    def test_detect_routing_intent(self, tool_router):
        """Test detecting routing intent."""
        intent = tool_router.detect_intent("What is the best route for this waste?")
        assert intent == IntentType.ROUTING
    
    def test_detect_facility_info_intent(self, tool_router):
        """Test detecting facility info intent."""
        intent = tool_router.detect_intent("Show me information about facility COMPOST-01")
        assert intent == IntentType.FACILITY_INFO
    
    def test_detect_cluster_info_intent(self, tool_router):
        """Test detecting cluster info intent."""
        intent = tool_router.detect_intent("Show me information about cluster BK-07")
        assert intent == IntentType.CLUSTER_INFO
    
    def test_detect_symbiosis_intent(self, tool_router):
        """Test detecting symbiosis intent."""
        intent = tool_router.detect_intent("Find industrial symbiosis opportunities")
        assert intent == IntentType.SYMBIOSIS
    
    def test_detect_general_intent(self, tool_router):
        """Test detecting general intent."""
        intent = tool_router.detect_intent("What can you do?")
        assert intent == IntentType.GENERAL


class TestEntityExtraction:
    """Test entity extraction from queries."""
    
    def test_extract_cluster_id(self, tool_router):
        """Test extracting cluster ID."""
        entities = tool_router._extract_entities("Show me cluster BK-07 data")
        assert entities.get("cluster_id") == "BK-07"
    
    def test_extract_facility_id(self, tool_router):
        """Test extracting facility ID."""
        entities = tool_router._extract_entities("Show me facility COMPOST-01 data")
        assert entities.get("facility_id") == "COMPOST-01"
    
    def test_extract_bin_id(self, tool_router):
        """Test extracting bin ID."""
        entities = tool_router._extract_entities("Show me bin BIN-12345 data")
        assert entities.get("bin_id") == "BIN-12345"
    
    def test_extract_waste_type(self, tool_router):
        """Test extracting waste type."""
        entities = tool_router._extract_entities("Show me pathways for food scraps")
        assert entities.get("waste_type") == "food scraps"
    
    def test_extract_borough(self, tool_router):
        """Test extracting borough."""
        entities = tool_router._extract_entities("Show me data for Brooklyn")
        assert entities.get("borough") == "Brooklyn"


class TestRouteQuery:
    """Test query routing to tools."""
    
    def test_route_telemetry_query(self, tool_router):
        """Test routing telemetry query."""
        tool_calls = tool_router.route_query(
            "Show me telemetry for cluster BK-07",
            {"cluster_id": "BK-07"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.WASTE_INTEL_API for tc in tool_calls)
    
    def test_route_anomaly_query(self, tool_router):
        """Test routing anomaly query."""
        tool_calls = tool_router.route_query(
            "Why is cluster BK-07 showing anomalies?",
            {"cluster_id": "BK-07"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.ML_API for tc in tool_calls)
    
    def test_route_forecast_query(self, tool_router):
        """Test routing forecast query."""
        tool_calls = tool_router.route_query(
            "Predict waste load for facility COMPOST-01",
            {"facility_id": "COMPOST-01"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.ML_API for tc in tool_calls)
    
    def test_route_pathways_query(self, tool_router):
        """Test routing pathways query."""
        tool_calls = tool_router.route_query(
            "Show me pathways for food scraps",
            {"waste_type": "food scraps"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.KG_API for tc in tool_calls)
    
    def test_route_city_data_query(self, tool_router):
        """Test routing city data query."""
        tool_calls = tool_router.route_query(
            "What is the weather in Brooklyn?",
            {"borough": "Brooklyn"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.MCP_SERVER for tc in tool_calls)
    
    def test_route_facility_info_query(self, tool_router):
        """Test routing facility info query."""
        tool_calls = tool_router.route_query(
            "Show me facility COMPOST-01 info",
            {"facility_id": "COMPOST-01"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.WASTE_INTEL_API for tc in tool_calls)
    
    def test_route_cluster_info_query(self, tool_router):
        """Test routing cluster info query."""
        tool_calls = tool_router.route_query(
            "Show me cluster BK-07 info",
            {"cluster_id": "BK-07"}
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.WASTE_INTEL_API for tc in tool_calls)


class TestPrivateRouteMethods:
    """Test private routing methods."""
    
    def test_route_telemetry(self, tool_router):
        """Test _route_telemetry method."""
        tool_calls = tool_router._route_telemetry(
            cluster_id="BK-07",
            facility_id=None,
            bin_id=None
        )
        assert len(tool_calls) > 0
        assert all(tc.tool_type == ToolType.WASTE_INTEL_API for tc in tool_calls)
    
    def test_route_anomaly(self, tool_router):
        """Test _route_anomaly method."""
        tool_calls = tool_router._route_anomaly(
            cluster_id="BK-07",
            facility_id=None,
            bin_id=None
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.ML_API for tc in tool_calls)
    
    def test_route_forecast(self, tool_router):
        """Test _route_forecast method."""
        tool_calls = tool_router._route_forecast(
            cluster_id=None,
            facility_id="COMPOST-01",
            waste_type="food scraps"
        )
        assert len(tool_calls) > 0
        assert any(tc.tool_type == ToolType.ML_API for tc in tool_calls)
    
    def test_route_city_data(self, tool_router):
        """Test _route_city_data method."""
        tool_calls = tool_router._route_city_data(
            borough="Brooklyn"
        )
        assert len(tool_calls) > 0
        assert all(tc.tool_type == ToolType.MCP_SERVER for tc in tool_calls)
    
    def test_route_pathways(self, tool_router):
        """Test _route_pathways method."""
        tool_calls = tool_router._route_pathways(
            waste_type="food scraps",
            facility_id="COMPOST-01"
        )
        assert len(tool_calls) > 0
        assert all(tc.tool_type == ToolType.KG_API for tc in tool_calls)
    
    def test_route_routing(self, tool_router):
        """Test _route_routing method."""
        tool_calls = tool_router._route_routing(
            cluster_id="BK-07",
            facility_id="COMPOST-01",
            waste_type="food scraps"
        )
        assert len(tool_calls) > 0
    
    def test_route_facility_info(self, tool_router):
        """Test _route_facility_info method."""
        tool_calls = tool_router._route_facility_info(
            facility_id="COMPOST-01"
        )
        assert len(tool_calls) > 0
    
    def test_route_cluster_info(self, tool_router):
        """Test _route_cluster_info method."""
        tool_calls = tool_router._route_cluster_info(
            cluster_id="BK-07"
        )
        assert len(tool_calls) > 0
