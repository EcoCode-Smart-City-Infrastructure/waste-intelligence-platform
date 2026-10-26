"""Facility route handlers — DB-backed via FacilityRepository.

Previously a hardcoded empty list; now a true DB result, with 503
when the database is unreachable.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request

facilities_bp = Blueprint("facilities", __name__, url_prefix="/facilities")


def _jsonable(row: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@facilities_bp.get("")
def list_facilities():
    try:
        from hub_layer.repositories.facility_repository import FacilityRepository

        rows = FacilityRepository().list_facilities()
    except Exception as e:
        return jsonify({"error": f"database unavailable: {e}"}), 503
    rows = [_jsonable(r) for r in rows]
    return jsonify({"facilities": rows, "count": len(rows)})


@facilities_bp.post("")
def create_facility():
    data = request.get_json(silent=True) or {}
    if not data.get("facility_id"):
        return jsonify({"error": "facility_id is required"}), 400
    try:
        from hub_layer.repositories.facility_repository import FacilityRepository

        FacilityRepository().create_facility(data)
    except Exception as e:
        return jsonify({"error": f"database unavailable: {e}"}), 503
    return jsonify({"status": "created", "facility_id": data["facility_id"]}), 201
