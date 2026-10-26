"""Analytics route handlers — computed from the database.

Previously hardcoded zeros with forecast_status "pending". Now the
counts and average fill come from the bins/facilities/telemetry
tables; a missing database returns 503 instead of fake zeros.
"""
from __future__ import annotations

from flask import Blueprint, jsonify

from hub_layer.db import fetch_all

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.get("/summary")
def summary():
    try:
        bins = fetch_all("SELECT COUNT(*) AS n FROM bins;")
        facilities = fetch_all("SELECT COUNT(*) AS n FROM facilities;")
        fill = fetch_all("SELECT AVG(fill_level_percent) AS avg_fill, COUNT(*) AS n FROM telemetry;")
    except Exception as e:
        return jsonify({"error": f"database unavailable: {e}"}), 503
    avg = fill[0]["avg_fill"] if fill else None
    return jsonify({
        "total_bins": int(bins[0]["n"]) if bins else 0,
        "total_facilities": int(facilities[0]["n"]) if facilities else 0,
        "average_fill_percent": float(avg) if avg is not None else 0.0,
        "forecast_status": "ok" if (fill and fill[0]["n"]) else "pending",
    })
