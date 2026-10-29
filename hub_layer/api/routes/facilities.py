"""Facility route handlers."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from hub_layer.repositories.facility_repository import FacilityRepository

facilities_bp = Blueprint("facilities", __name__, url_prefix="/facilities")
facility_repo = FacilityRepository()


@facilities_bp.get("")
def list_facilities():
    facilities = facility_repo.list_facilities()
    return jsonify({"facilities": facilities, "count": len(facilities)})


@facilities_bp.get("/<facility_id>")
def get_facility(facility_id: str):
    facility = facility_repo.get_facility(facility_id)
    if not facility:
        return jsonify({"error": "Facility not found"}), 404
    return jsonify(facility)


@facilities_bp.post("")
def create_facility():
    data = request.get_json(silent=True) or {}
    if not data.get("facility_id"):
        return jsonify({"error": "facility_id is required"}), 400
    try:
        facility_repo.create_facility(data)
        return jsonify({"status": "created", "facility_id": data["facility_id"]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
