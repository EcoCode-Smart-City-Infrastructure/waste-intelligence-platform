"""Flask application for the waste-intelligence hub layer."""
from __future__ import annotations

import logging
import os
from flask import Flask, jsonify


def create_app() -> Flask:
    """Create and configure the hub-layer Flask app."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @app.get("/health")
    def healthcheck():
        return jsonify({"status": "ok", "service": "hub-layer"}), 200

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
    app.run(host=host, port=port, debug=False)
