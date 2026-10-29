"""Analytics route handlers."""
from __future__ import annotations

from flask import Blueprint, jsonify
from hub_layer.repositories.bin_repository import BinRepository
from hub_layer.repositories.facility_repository import FacilityRepository

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")
bin_repo = BinRepository()
facility_repo = FacilityRepository()


@analytics_bp.get("/summary")
def summary():
    bins = bin_repo.list_bins()
    facilities = facility_repo.list_facilities()
    
    total_fill = sum(b.get("current_fill_level_percent", 0) for b in bins) if bins else 0
    avg_fill = total_fill / len(bins) if bins else 0.0
    
    return jsonify({
        "total_bins": len(bins),
        "total_facilities": len(facilities),
        "average_fill_percent": round(avg_fill, 2),
        "forecast_status": "pending",
    })


@analytics_bp.get("/bins/status")
def bin_status():
    bins = bin_repo.list_bins()
    
    status_counts = {}
    for bin_data in bins:
        status = bin_data.get("bin_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return jsonify({
        "status_distribution": status_counts,
        "total_bins": len(bins),
    })


@analytics_bp.get("/facilities/status")
def facility_status():
    facilities = facility_repo.list_facilities()
    
    status_counts = {}
    type_counts = {}
    for facility in facilities:
        status = facility.get("operational_status", "unknown")
        facility_type = facility.get("facility_type", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[facility_type] = type_counts.get(facility_type, 0) + 1
    
    return jsonify({
        "status_distribution": status_counts,
        "type_distribution": type_counts,
        "total_facilities": len(facilities),
    })
