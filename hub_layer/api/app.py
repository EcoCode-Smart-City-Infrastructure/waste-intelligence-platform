"""Flask application for the waste-intelligence hub layer."""
from __future__ import annotations

import logging
import os
from flask import Flask, jsonify


def create_app() -> Flask:
    """Create and configure the hub-layer Flask app."""
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    # CORS for the browser web app (GitHub Pages origin by default,
    # overridable with CORS_ORIGINS, comma-separated). Flask has no
    # built-in CORS middleware, so this is done in after_request plus
    # a preflight handler — no new dependency.
    import os as _os

    _cors_origins = [o.strip() for o in _os.getenv(
        "CORS_ORIGINS",
        "https://ecocode-smart-city-infrastructure.github.io,http://localhost:3000,http://localhost:8080",
    ).split(",") if o.strip()]

    @app.after_request
    def _cors_headers(response):
        from flask import request as _req

        origin = _req.headers.get("Origin", "")
        if "*" in _cors_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin in _cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.before_request
    def _cors_preflight():
        from flask import request as _req

        if _req.method == "OPTIONS":
            return ("", 204)

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
