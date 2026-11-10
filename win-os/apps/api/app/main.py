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

def create_app(database_url: str | None = None,
               rate_limit_per_min: int | None = None) -> FastAPI:
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

    import os as _os, time as _time
    _rate_limit = rate_limit_per_min if rate_limit_per_min is not None else int(
        _os.environ.get("WIN_RATE_LIMIT_PER_MIN", "600"))
    _hits: dict = {}

    @app.middleware("http")
    async def security_and_rate_limit(request: Request, call_next):
        if request.url.path.startswith("/api/v1") and _rate_limit > 0:
            key = request.headers.get("X-API-Key", request.client.host if request.client else "anon")
            window = int(_time.time() // 60)
            bucket = (key, window)
            _hits[bucket] = _hits.get(bucket, 0) + 1
            if _hits[bucket] > _rate_limit:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=429, content={"detail": {
                    "error": "rate_limited",
                    "message": f"More than {_rate_limit} requests per minute for this key."}})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

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
