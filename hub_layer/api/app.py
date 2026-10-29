"""Flask application for the waste-intelligence hub layer."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from flask import Flask, jsonify

from hub_layer.repositories.bin_repository import BinRepository
from hub_layer.repositories.facility_repository import FacilityRepository


def create_app() -> Flask:
    """Create and configure the hub-layer Flask app."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @app.get("/health")
    def healthcheck():
        bin_repo = BinRepository()
        facility_repo = FacilityRepository()
        
        try:
            bins = bin_repo.list_bins(limit=1)
            facilities = facility_repo.list_facilities(limit=1)
            
            return jsonify({
                "status": "healthy",
                "service": "hub-layer",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": {
                    "database": "connected",
                    "bins_table": "accessible",
                    "facilities_table": "accessible",
                },
                "stats": {
                    "bins_count": len(bins),
                    "facilities_count": len(facilities),
                }
            }), 200
        except Exception as e:
            return jsonify({
                "status": "degraded",
                "service": "hub-layer",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "checks": {
                    "database": "error",
                }
            }), 503

    @app.get("/ready")
    def readiness():
        return jsonify({"status": "ready", "service": "hub-layer"}), 200

    @app.get("/version")
    def version():
        return jsonify({
            "service": "hub-layer",
            "version": "1.0.0",
            "build_date": "2024-01-01",
            "commit": os.getenv("GIT_COMMIT", "unknown"),
        }), 200

    from hub_layer.api.routes.bins import bins_bp
    from hub_layer.api.routes.facilities import facilities_bp
    from hub_layer.api.routes.analytics import analytics_bp
    from hub_layer.api.routes.copilot import copilot_bp

    app.register_blueprint(bins_bp)
    app.register_blueprint(facilities_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(copilot_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("HUB_HOST", "0.0.0.0")
    port = int(os.getenv("HUB_PORT", "5000"))
    debug = os.getenv("HUB_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
