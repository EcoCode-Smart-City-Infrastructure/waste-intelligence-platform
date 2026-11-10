"""WIN OS API application factory.

Run: uvicorn app.main:app --host 0.0.0.0 --port 8080
Health: /health/live (process up) vs /health/ready (database reachable).
Every response carries X-Correlation-ID; logs are structured single lines.
"""
from __future__ import annotations
import logging, uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text as sql_text
from . import db as db_mod
from .config import get_settings, validate_production
from .security import auth_configured
from .routers import router

logging.basicConfig(level=logging.INFO,
                    format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}')
log = logging.getLogger("win-os-api")

def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings()
    validate_production(settings, auth_configured())
    db_mod.init_db(database_url or settings.database_url)
    db_mod.create_tables()

    app = FastAPI(title="WIN OS API", version=settings.version,
                  description="Waste Intelligence Network Operating System - core API.",
                  openapi_url="/api/v1/openapi.json", docs_url="/docs")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                       allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key",
                                      "X-Correlation-ID"])

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        log.info("request method=%s path=%s status=%s correlation=%s",
                 request.method, request.url.path, response.status_code, cid)
        return response

    @app.get("/health/live")
    def live():
        return {"status": "live", "service": "win-os-api",
                "version": settings.version, "profile": settings.profile}

    @app.get("/health/ready")
    def ready():
        try:
            with db_mod.engine().connect() as conn:
                conn.execute(sql_text("SELECT 1"))
            return {"status": "ready", "database": "ok"}
        except Exception as exc:  # readiness must report, never crash
            return {"status": "not_ready", "database": "unavailable",
                    "detail": type(exc).__name__}

    @app.get("/")
    def root():
        return {"service": "win-os-api", "version": settings.version,
                "docs": "/docs", "openapi": "/api/v1/openapi.json",
                "health": {"live": "/health/live", "ready": "/health/ready"}}

    app.include_router(router)
    return app

app = create_app()
