"""FastAPI application for Waste Intelligence Platform API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import Config
from .routers import bin_router, cluster_router, facility_router, ml_router, kg_router


# Create FastAPI application
app = FastAPI(
    title=Config.APP_NAME,
    version=Config.APP_VERSION,
    description=Config.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=Config.CORS_METHODS,
    allow_headers=Config.CORS_HEADERS,
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Include routers
app.include_router(bin_router, prefix="/mcp/waste")
app.include_router(cluster_router, prefix="/mcp/waste")
app.include_router(facility_router, prefix="/mcp/waste")
app.include_router(ml_router, prefix="/mcp/waste")
app.include_router(kg_router, prefix="/mcp/waste")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "city": Config.CITY,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "app": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "description": Config.APP_DESCRIPTION,
        "city": Config.CITY,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"City: {Config.CITY}")
    logger.info(f"Debug mode: {Config.DEBUG}")
    logger.info(f"Host: {Config.HOST}:{Config.PORT}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Shutting down {Config.APP_NAME}")
