"""Repository layer for WIN OS.

This package contains all database repository classes for the Waste Intelligence Network OS.
Each repository provides CRUD operations for a specific domain entity.
"""
from __future__ import annotations

from hub_layer.repositories.bin_repository import BinRepository
from hub_layer.repositories.facility_repository import FacilityRepository

# Export all repositories
__all__ = [
    "BinRepository",
    "FacilityRepository",
]

# Singleton instances for convenience
bin_repository = BinRepository()
facility_repository = FacilityRepository()
