"""Tests for Guardrail Engine."""

import pytest
from copilot_service.core.guardrail_engine import GuardrailEngine


@pytest.fixture
def guardrail():
    return GuardrailEngine()


class TestQueryValidation:
    """Test query validation functionality."""
    
    def test_allow_safe_query(self, guardrail):
        """Test that safe queries are allowed."""
        is_valid, error = guardrail.validate_query("What is the waste level in cluster BK-07?")
        assert is_valid
        assert error is None
    
    def test_block_forbidden_actions(self, guardrail):
        """Test that forbidden actions are blocked."""
        forbidden_queries = [
            "Change the route for cluster BK-07",
            "Modify facility operations",
            "Trigger routing update",
            "Write to database",
            "Delete the bin data",
            "Activate the sensor",
            "Execute the command"
        ]
        
        for query in forbidden_queries:
            is_valid, error = guardrail.validate_query(query)
            assert not is_valid
            assert error is not None
            assert any(word in error.lower() for word in ["forbidden", "not allowed"])
    
    def test_block_actuation_commands(self, guardrail):
        """Test that actuation commands are blocked."""
        actuation_queries = [
            "Route the waste to facility XYZ",
            "Modify the route for cluster A",
            "Change facility operations now",
            "Automatically adjust routing"
        ]
        
        for query in actuation_queries:
            is_valid, error = guardrail.validate_query(query)
            assert not is_valid
            assert error is not None


class TestSensitiveDataRedaction:
    """Test sensitive data redaction."""
    
    def test_redact_email(self, guardrail):
        """Test email redaction."""
        text = "Contact user@example.com for more info"
        redacted = guardrail.redact_sensitive_data(text)
        assert "example.com" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_phone(self, guardrail):
        """Test phone number redaction."""
        text = "Call 212-555-1234 for support"
        redacted = guardrail.redact_sensitive_data(text)
        assert "212-555-1234" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_gps(self, guardrail):
        """Test GPS coordinate redaction."""
        text = "Location: 40.7128, -74.0060"
        redacted = guardrail.redact_sensitive_data(text, None)
        assert "40.7128" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_bin_id(self, guardrail):
        """Test bin ID redaction for raw sensor context."""
        from copilot_service.core.context_manager import ContextType
        text = "Sensor BIN-12345 has high readings"
        redacted = guardrail.redact_sensitive_data(text, ContextType.RAW_SENSOR)
        assert "BIN-12345" not in redacted
        assert "[ID_REDACTED]" in redacted


class TestToolValidation:
    """Test tool call validation."""
    
    def test_allow_read_only_tools(self, guardrail):
        """Test that read-only tools are allowed."""
        is_valid, error = guardrail.validate_tool_call(
            "waste_intel_api",
            {"cluster_id": "BK-07"}
        )
        assert is_valid
        assert error is None
    
    def test_block_write_tools(self, guardrail):
        """Test that write tools are blocked."""
        is_valid, error = guardrail.validate_tool_call(
            "waste_intel_api",
            {"action": "update", "data": "test"}
        )
        assert not is_valid
        assert error is not None


class TestResponseValidation:
    """Test response validation."""
    
    def test_allow_safe_response(self, guardrail):
        """Test that safe responses are allowed."""
        is_valid, error = guardrail.validate_response(
            "The waste level is 85% in cluster BK-07. I recommend monitoring it.",
            "What is the waste level?"
        )
        assert is_valid
        assert error is None
    
    def test_block_actuation_response(self, guardrail):
        """Test that actuation responses are blocked."""
        is_valid, error = guardrail.validate_response(
            "You should change the route immediately to avoid overflow.",
            "What should I do?"
        )
        assert not is_valid
        assert error is not None
    
    def test_block_pii_response(self, guardrail):
        """Test that responses with PII are blocked."""
        is_valid, error = guardrail.validate_response(
            "The user john@example.com reported an issue.",
            "What issues were reported?"
        )
        assert not is_valid
        assert error is not None


class TestModelSelection:
    """Test model selection."""
    
    def test_select_by_task_type(self, guardrail):
        """Test model selection by task type."""
        model = guardrail.select_model(task_type="real_time")
        assert model is not None
        assert isinstance(model, str)
    
    def test_select_by_query(self, guardrail):
        """Test model selection based on query content."""
        model = guardrail.select_model(query="Predict the waste load for tomorrow")
        assert model is not None


class TestGuardrailStatus:
    """Test guardrail status reporting."""
    
    def test_get_status(self, guardrail):
        """Test getting guardrail status."""
        status = guardrail.get_guardrail_status()
        assert isinstance(status, dict)
        assert "forbidden_actions" in status
        assert "sensitive_fields" in status
        assert "allowed_data_sources" in status
