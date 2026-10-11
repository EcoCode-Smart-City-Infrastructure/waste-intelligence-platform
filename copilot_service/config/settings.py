"""
Configuration settings for AI Copilot Service.

Environment variables:
- OPENROUTER_API_KEY: API key for OpenRouter
- OPENROUTER_BASE_URL: Base URL for OpenRouter API (default: https://openrouter.ai/api/v1)
- OPENROUTER_MODEL: Default model to use (default: openai/gpt-4o-mini)
- COPILOT_PORT: Port for the copilot service (default: 8004)
- WASTE_INTEL_API_URL: URL for Waste Intelligence API
- MCP_SERVER_URL: URL for MCP NYC Open Data Server
- KG_API_URL: URL for Knowledge Graph API
- ML_API_URL: URL for ML Inference API
- COPILOT_API_KEY: API key for copilot service authentication
- DEBUG: Enable debug mode (default: False)
- LOG_LEVEL: Logging level (default: INFO)
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenRouter Configuration
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_default_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    openrouter_timeout: int = int(os.getenv("OPENROUTER_TIMEOUT", "60"))
    
    # Service URLs
    waste_intel_api_url: str = os.getenv("WASTE_INTEL_API_URL", "http://waste-intel-api:8001")
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://nyc-opendata-mcp:8000")
    kg_api_url: str = os.getenv("KG_API_URL", "http://kg-service:8003")
    ml_api_url: str = os.getenv("ML_API_URL", "http://ml-service:8002")
    
    # Service Configuration
    copilot_port: int = int(os.getenv("COPILOT_PORT", "8004"))
    copilot_host: str = os.getenv("COPILOT_HOST", "0.0.0.0")
    copilot_api_key: Optional[str] = os.getenv("COPILOT_API_KEY")
    require_api_key: bool = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
    
    # Model Selection Rules
    fast_models: List[str] = [
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku",
        "google/gemini-flash-1.5"
    ]
    accurate_models: List[str] = [
        "openai/gpt-4o",
        "anthropic/claude-3-sonnet",
        "google/gemini-pro-1.5"
    ]
    cheap_models: List[str] = [
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3.1-8b-instruct",
        "mistralai/mistral-7b-instruct"
    ]
    
    # Default model selection by task type
    model_by_task: dict = {
        "real_time": "openai/gpt-4o-mini",
        "planning": "openai/gpt-4o",
        "routine": "meta-llama/llama-3.1-8b-instruct",
        "debug": "anthropic/claude-3-sonnet",
        "explain": "openai/gpt-4o-mini",
        "summarize": "openai/gpt-4o-mini",
        "query": "openai/gpt-4o-mini"
    }
    
    # Rate Limiting
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    rate_limit_period: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # seconds
    
    # Security & Guardrails
    allowed_data_sources: List[str] = [
        "waste_intel_api",
        "mcp_server",
        "kg_api",
        "ml_api"
    ]
    forbidden_actions: List[str] = [
        "route", "routing", "change route", "modify route",
        "actuate", "control", "operate", "modify",
        "write", "update", "delete", "insert",
        "trigger", "activate", "deactivate",
        "execute", "run", "start", "stop"
    ]
    sensitive_fields: List[str] = [
        "bin_id", "sensor_id", "gps", "location",
        "user_id", "user", "identity", "pii",
        "address", "phone", "email"
    ]
    
    # Logging
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    audit_log_path: str = os.getenv("AUDIT_LOG_PATH", "/app/logs/audit.log")
    
    # Context Manager
    max_context_length: int = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
    context_cache_ttl: int = int(os.getenv("CONTEXT_CACHE_TTL", "300"))  # seconds
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://grafana:3000",
        "http://dashboard:3000"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessor
settings = get_settings()
