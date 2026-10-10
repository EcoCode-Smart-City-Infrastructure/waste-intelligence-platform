"""Routers for Waste Intelligence Platform API."""

from .bin_router import router as bin_router
from .cluster_router import router as cluster_router
from .facility_router import router as facility_router
from .kg_router import router as kg_router
from .ml_router import router as ml_router

__all__ = [
    "bin_router",
    "cluster_router",
    "facility_router",
    "kg_router",
    "ml_router",
]
