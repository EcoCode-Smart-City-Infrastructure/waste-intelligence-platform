"""WIN OS API configuration. All secrets come from the environment only."""
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    environment: str = os.environ.get("WIN_ENVIRONMENT", "development")
    profile: str = os.environ.get("WIN_PROFILE", "core")
    version: str = "0.2.0"
    database_url: str = os.environ.get(
        "WIN_DATABASE_URL", "sqlite:///./win-os.db")
    cors_origins: tuple = tuple(
        o for o in os.environ.get(
            "WIN_CORS_ORIGINS",
            "https://ecocode-smart-city-infrastructure.github.io").split(",") if o)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

def get_settings() -> Settings:
    return Settings(
        environment=os.environ.get("WIN_ENVIRONMENT", "development"),
        profile=os.environ.get("WIN_PROFILE", "core"),
        database_url=os.environ.get("WIN_DATABASE_URL", "sqlite:///./win-os.db"),
        cors_origins=tuple(o for o in os.environ.get(
            "WIN_CORS_ORIGINS",
            "https://ecocode-smart-city-infrastructure.github.io").split(",") if o),
    )

def validate_production(s: Settings, auth_configured: bool) -> None:
    """Fail fast in production on insecure or incomplete configuration."""
    if not s.is_production:
        return
    problems = []
    if s.database_url.startswith("sqlite"):
        problems.append("WIN_DATABASE_URL must point to PostgreSQL/PostGIS in production")
    if not auth_configured:
        problems.append("WIN_OS_KEYS must configure at least one API key in production")
    if problems:
        raise RuntimeError("WIN OS refusing to start: " + "; ".join(problems))
