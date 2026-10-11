"""
Guardrail & Policy Engine for AI Copilot Service.

Enforces safety policies, data boundaries, and operational constraints
to ensure the copilot operates within defined limits.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple

from ..config.settings import get_settings
from .context_manager import ContextType

logger = logging.getLogger(__name__)


class GuardrailViolation(Exception):
    """Exception raised when a guardrail is violated."""
    
    def __init__(self, violation_type: str, message: str, details: Optional[str] = None):
        self.violation_type = violation_type
        self.message = message
        self.details = details
        super().__init__(f"{violation_type}: {message}")


class GuardrailEngine:
    """
    Engine that enforces guardrails and policies on copilot operations.
    
    Guardrails include:
    - Forbidden action detection
    - Sensitive data redaction
    - Data source validation
    - Response validation
    - Rate limiting
    """
    
    def __init__(self):
        """Initialize guardrail engine."""
        self.settings = get_settings()
        
        # Compile forbidden action patterns
        self._forbidden_patterns = [
            re.compile(r'\b' + re.escape(action) + r'\b', re.IGNORECASE)
            for action in self.settings.forbidden_actions
        ]
        
        # Compile sensitive field patterns
        self._sensitive_patterns = [
            re.compile(r'\b' + re.escape(field) + r'\b', re.IGNORECASE)
            for field in self.settings.sensitive_fields
        ]
        
        # Patterns for detecting PII
        self._pii_patterns = [
            # Email addresses
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            # Phone numbers (various formats)
            re.compile(r'\b(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            # Social Security Numbers
            re.compile(r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'),
            # Credit card numbers (simplified)
            re.compile(r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'),
            # IP addresses
            re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            # GPS coordinates (latitude/longitude)
            re.compile(r'\b-?[0-9]{1,3}\.[0-9]+\s*,\s*-?[0-9]{1,3}\.[0-9]+\b'),
        ]
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a user query for forbidden actions.
        
        Args:
            query: The user's query string
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for forbidden action patterns
        for pattern in self._forbidden_patterns:
            if pattern.search(query):
                matched = pattern.search(query).group()
                return False, f"Forbidden action detected: '{matched}'"
        
        # Check for actuation commands
        actuation_patterns = [
            r'\b(route|routing)\b.*\b(change|modify|update|set|adjust)\b',
            r'\b(trigger|activate|deactivate|start|stop)\b.*\b(facility|route|sensor)\b',
            r'\b(write|delete|insert|update)\b.*\b(database|db|timescale)\b',
            r'\b(control|operate|manage)\b.*\b(system|facility|route)\b',
            r'\b(route)\b.*\b(waste|to|facility)\b',
            r'\b(modify|change)\b.*\b(route|facility)\b',
            r'\b(automatically adjust)\b'
        ]
        
        for pattern in actuation_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Actuation command not allowed: {query[:100]}..."
        
        return True, None
    
    def redact_sensitive_data(self, text: str, context_type: Optional[ContextType] = None) -> str:
        """
        Redact sensitive data from text.
        
        Args:
            text: Text to redact
            context_type: Optional context type for additional checks
        
        Returns:
            Text with sensitive data redacted
        """
        redacted = text
        
        # Redact PII patterns
        for pattern in self._pii_patterns:
            redacted = pattern.sub("[REDACTED]", redacted)
        
        # Redact sensitive field mentions
        for pattern in self._sensitive_patterns:
            redacted = pattern.sub("[FIELD_REDACTED]", redacted)
        
        # Additional redaction for specific context types
        if context_type == ContextType.RAW_SENSOR:
            # Redact any bin/sensor IDs
            redacted = re.sub(r'\b(bin|sensor)[_-]?[a-zA-Z0-9]+\b', '[ID_REDACTED]', redacted, flags=re.IGNORECASE)
        
        return redacted
    
    def validate_data_source(self, source: str) -> bool:
        """
        Validate that a data source is allowed.
        
        Args:
            source: Name of the data source
        
        Returns:
            True if allowed, False otherwise
        """
        return source.lower() in [s.lower() for s in self.settings.allowed_data_sources]
    
    def validate_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a tool call for safety.
        
        Args:
            tool_name: Name of the tool to call
            tool_input: Input parameters for the tool
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if tool is from allowed sources
        allowed_tools = {
            "waste_intel_api": ["get_bin", "get_cluster", "get_facility", "list_bins", "list_clusters", "list_facilities"],
            "mcp_server": ["get_weather", "get_air_quality", "get_mobility", "get_geodata"],
            "kg_api": ["query", "suggest_pathways", "suggest_routes", "get_symbiosis"],
            "ml_api": ["predict", "detect_anomaly", "forecast", "classify"]
        }
        
        # Extract tool category from name
        tool_category = tool_name.split(":")[0] if ":" in tool_name else tool_name.split("_")[0]
        
        # Check if tool is in allowed list
        is_allowed = True  # Default to allowed for flexibility
        for category, tools in allowed_tools.items():
            if tool_category == category or tool_name in tools:
                is_allowed = True
                break
        
        if not is_allowed:
            return False, f"Tool not allowed: {tool_name}"
        
        # Check for write operations in tool input
        write_patterns = [
            "create", "update", "delete", "insert", "write",
            "modify", "change", "set", "replace"
        ]
        
        for key, value in tool_input.items():
            key_lower = str(key).lower()
            if any(pattern in key_lower for pattern in write_patterns):
                return False, f"Write operation detected in tool input: {key}"
            
            if isinstance(value, str):
                value_lower = value.lower()
                if any(pattern in value_lower for pattern in write_patterns):
                    return False, f"Write operation detected in tool value: {key}={value[:50]}..."
        
        return True, None
    
    def validate_response(self, response: str, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an LLM response for safety.
        
        Args:
            response: The LLM's response text
            query: The original query
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for forbidden action suggestions
        for pattern in self._forbidden_patterns:
            if pattern.search(response):
                return False, f"Response contains forbidden action: {pattern.pattern}"
        
        # Check for actuation suggestions
        actuation_indicators = [
            "you should change the route",
            "modify the facility",
            "update the database",
            "trigger the sensor",
            "activate the system",
            "automatically adjust",
            "without human approval",
            "bypass the operator"
        ]
        
        response_lower = response.lower()
        for indicator in actuation_indicators:
            if indicator in response_lower:
                return False, f"Response suggests actuation: {indicator}"
        
        # Check for PII in response
        for pattern in self._pii_patterns:
            if pattern.search(response):
                return False, "Response contains potential PII"
        
        # Ensure response is advisory
        advisory_keywords = [
            "suggest", "recommend", "consider", "might", "could",
            "should", "advisable", "propose", "advise"
        ]
        
        has_advisory = any(kw in response_lower for kw in advisory_keywords)
        has_imperative = any(
            word in response_lower 
            for word in ["must", "will", "do it", "execute", "run"]
        )
        
        # If imperative but not advisory, flag it
        if has_imperative and not has_advisory:
            return False, "Response is imperative without advisory context"
        
        return True, None
    
    def sanitize_response(self, response: str, context: Dict[str, Any]) -> str:
        """
        Sanitize an LLM response by redacting sensitive information.
        
        Args:
            response: The raw response text
            context: The context used for the query
        
        Returns:
            Sanitized response text
        """
        # Redact sensitive data
        sanitized = self.redact_sensitive_data(response)
        
        # Add disclaimer if response contains recommendations
        if any(word in sanitized.lower() for word in ["recommend", "suggest", "advise"]):
            sanitized += "\n\n**Note: All recommendations are advisory only. Human approval is required for any operational changes.**"
        
        return sanitized
    
    def check_rate_limit(self, user_id: str, current_count: int, period: int) -> Tuple[bool, Optional[str]]:
        """
        Check if a user has exceeded rate limits.
        
        Args:
            user_id: ID of the user
            current_count: Number of requests in current period
            period: Length of period in seconds
        
        Returns:
            Tuple of (is_allowed, error_message)
        """
        max_requests = self.settings.rate_limit_requests
        
        if current_count >= max_requests:
            return False, f"Rate limit exceeded: {max_requests} requests per {period} seconds"
        
        return True, None
    
    def select_model(
        self,
        task_type: Optional[str] = None,
        user_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> str:
        """
        Select the appropriate model based on task type and constraints.
        
        Args:
            task_type: Type of task (real_time, planning, routine, etc.)
            user_id: ID of the user (for rate limiting considerations)
            query: The user query (for content-based selection)
        
        Returns:
            Model identifier string
        """
        settings = self.settings
        
        # Use task-based selection if provided
        if task_type and task_type in settings.model_by_task:
            return settings.model_by_task[task_type]
        
        # Analyze query for task type
        if query:
            query_lower = query.lower()
            
            if any(word in query_lower for word in ["plan", "planning", "forecast", "predict"]):
                return settings.model_by_task.get("planning", settings.openrouter_default_model)
            elif any(word in query_lower for word in ["real-time", "live", "now", "current"]):
                return settings.model_by_task.get("real_time", settings.openrouter_default_model)
            elif any(word in query_lower for word in ["debug", "fix", "error", "problem"]):
                return settings.model_by_task.get("debug", settings.openrouter_default_model)
        
        # Default to configured default
        return settings.openrouter_default_model
    
    def get_guardrail_status(self) -> Dict[str, Any]:
        """
        Get the current guardrail configuration status.
        
        Returns:
            Dictionary with guardrail configuration
        """
        return {
            "forbidden_actions": self.settings.forbidden_actions,
            "sensitive_fields": self.settings.sensitive_fields,
            "allowed_data_sources": self.settings.allowed_data_sources,
            "rate_limit_requests": self.settings.rate_limit_requests,
            "rate_limit_period": self.settings.rate_limit_period,
            "model_selection_rules": {
                "by_task": self.settings.model_by_task,
                "fast_models": self.settings.fast_models,
                "accurate_models": self.settings.accurate_models,
                "cheap_models": self.settings.cheap_models
            }
        }


# Global guardrail engine instance
_guardrail_engine: Optional[GuardrailEngine] = None


def get_guardrail_engine() -> GuardrailEngine:
    """Get or create the global guardrail engine."""
    global _guardrail_engine
    if _guardrail_engine is None:
        _guardrail_engine = GuardrailEngine()
    return _guardrail_engine
