"""Tests for Context Manager."""

import pytest
from datetime import datetime, timedelta
from copilot_service.core.context_manager import ContextManager, Context, ContextItem, ContextType


@pytest.fixture
def context_manager():
    return ContextManager()


class TestContextItem:
    """Test ContextItem functionality."""
    
    def test_context_item_creation(self):
        """Test creating a context item."""
        item = ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="waste_intel_api",
            data={"test": "value"}
        )
        assert item.context_type == ContextType.AGGREGATED_TELEMETRY
        assert item.source == "waste_intel_api"
        assert item.data == {"test": "value"}
    
    def test_context_item_expiration(self):
        """Test context item expiration."""
        # Create item with very short TTL
        item = ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="test",
            data={},
            timestamp=datetime.utcnow() - timedelta(seconds=10),
            ttl_seconds=5
        )
        assert item.is_expired()
    
    def test_context_item_not_expired(self):
        """Test that fresh context items are not expired."""
        item = ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="test",
            data={},
            ttl_seconds=60
        )
        assert not item.is_expired()


class TestContext:
    """Test Context functionality."""
    
    def test_context_creation(self):
        """Test creating a context."""
        context = Context(user_id="user-123")
        assert context.user_id == "user-123"
        assert len(context.items) == 0
    
    def test_add_item(self):
        """Test adding items to context."""
        context = Context(user_id="user-123")
        item = ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="test",
            data={"key": "value"}
        )
        context.add_item(item)
        assert len(context.items) == 1
    
    def test_get_by_type(self):
        """Test filtering context by type."""
        context = Context(user_id="user-123")
        context.add_item(ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="test1",
            data={}
        ))
        context.add_item(ContextItem(
            context_type=ContextType.ML_OUTPUTS,
            source="test2",
            data={}
        ))
        context.add_item(ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="test3",
            data={}
        ))
        
        telemetry_items = context.get_by_type(ContextType.AGGREGATED_TELEMETRY)
        assert len(telemetry_items) == 2
    
    def test_get_by_source(self):
        """Test filtering context by source."""
        context = Context(user_id="user-123")
        context.add_item(ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="waste_intel_api",
            data={}
        ))
        context.add_item(ContextItem(
            context_type=ContextType.ML_OUTPUTS,
            source="waste_intel_api",
            data={}
        ))
        context.add_item(ContextItem(
            context_type=ContextType.CITY_DATA,
            source="mcp_server",
            data={}
        ))
        
        waste_items = context.get_by_source("waste_intel_api")
        assert len(waste_items) == 2
    
    def test_to_dict(self):
        """Test converting context to dictionary."""
        context = Context(
            user_id="user-123",
            query="test query",
            session_id="session-456"
        )
        context.add_item(ContextItem(
            context_type=ContextType.AGGREGATED_TELEMETRY,
            source="test",
            data={"key": "value"}
        ))
        
        result = context.to_dict()
        assert result["user_id"] == "user-123"
        assert result["query"] == "test query"
        assert len(result["items"]) == 1


class TestEntityExtraction:
    """Test entity extraction from queries."""
    
    def test_extract_cluster_id(self, context_manager):
        """Test extracting cluster ID from query."""
        cluster_id = context_manager._extract_id("What is the status of cluster BK-07?", "cluster")
        assert cluster_id == "BK-07"
    
    def test_extract_facility_id(self, context_manager):
        """Test extracting facility ID from query."""
        facility_id = context_manager._extract_id("Show me facility COMPOST-01 data", "facility")
        assert facility_id == "COMPOST-01"
    
    def test_extract_bin_id(self, context_manager):
        """Test extracting bin ID from query."""
        bin_id = context_manager._extract_id("Bin BIN-12345 has high readings", "bin")
        assert bin_id == "BIN-12345"
    
    def test_extract_waste_type(self, context_manager):
        """Test extracting waste type from query."""
        waste_type = context_manager._extract_waste_type("What are the pathways for food scraps?")
        assert waste_type == "food scraps"
    
    def test_extract_borough(self, context_manager):
        """Test extracting borough from query."""
        borough = context_manager._extract_borough("Show me data for Brooklyn")
        assert borough == "Brooklyn"
    
    def test_extract_time_range_today(self, context_manager):
        """Test extracting 'today' time range."""
        time_range = context_manager._extract_time_range("Show me data for today")
        assert time_range is not None
        # The handler returns actual dates, not the string "today"
        assert "start" in time_range
        assert "end" in time_range
    
    def test_extract_time_range_date(self, context_manager):
        """Test extracting date range."""
        time_range = context_manager._extract_time_range("from 2024-01-01 to 2024-01-31")
        assert time_range is not None
        assert time_range["start"] == "2024-01-01"
        assert time_range["end"] == "2024-01-31"


class TestIntentInference:
    """Test intent inference from queries."""
    
    def test_infer_explain_intent(self, context_manager):
        """Test inferring explain intent."""
        intent = context_manager._infer_intent("Why is cluster BK-07 showing anomalies?")
        assert intent == "explain"
    
    def test_infer_query_intent(self, context_manager):
        """Test inferring query intent."""
        intent = context_manager._infer_intent("What is the waste level in cluster BK-07?")
        assert intent == "query"
    
    def test_infer_predict_intent(self, context_manager):
        """Test inferring predict intent."""
        intent = context_manager._infer_intent("Predict the waste load for tomorrow")
        assert intent == "predict"
    
    def test_infer_recommend_intent(self, context_manager):
        """Test inferring recommend intent."""
        intent = context_manager._infer_intent("Suggest the best route for this waste")
        assert intent == "recommend"
    
    def test_infer_summarize_intent(self, context_manager):
        """Test inferring summarize intent."""
        intent = context_manager._infer_intent("Summarize the current status")
        assert intent == "summarize"
    
    def test_infer_debug_intent(self, context_manager):
        """Test inferring debug intent."""
        intent = context_manager._infer_intent("Debug the anomaly detection")
        assert intent == "debug"
    
    def test_infer_help_intent(self, context_manager):
        """Test inferring help intent."""
        intent = context_manager._infer_intent("How do I use this system?")
        assert intent == "help"
