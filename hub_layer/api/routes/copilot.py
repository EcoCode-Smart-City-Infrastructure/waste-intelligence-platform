"""Copilot route handlers for hub layer API.

Provides proxy endpoints to the AI Copilot Service for integration
with the existing Waste Intelligence Platform API.
"""

from flask import Blueprint, jsonify, request
import httpx
import os

copilot_bp = Blueprint("copilot", __name__, url_prefix="/copilot")


# Get copilot service URL from environment
COPILOT_SERVICE_URL = os.getenv("COPILOT_SERVICE_URL", "http://copilot-service:8004")


@copilot_bp.get("/health")
def copilot_health():
    """Check copilot service health."""
    return jsonify({"status": "ok", "service": "copilot-proxy"}), 200


@copilot_bp.post("/query")
async def proxy_query():
    """Proxy query to copilot service."""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Add user_id from request if not present
        if "user_id" not in data:
            # Try to get from headers or use a default
            data["user_id"] = request.headers.get("X-User-ID", "anonymous")
        
        # Forward to copilot service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{COPILOT_SERVICE_URL}/copilot/query",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code >= 400:
                return jsonify({"error": response.text}), response.status_code
            
            return jsonify(response.json()), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@copilot_bp.get("/history")
async def proxy_history():
    """Proxy history request to copilot service."""
    try:
        # Get query parameters
        user_id = request.args.get("user_id")
        session_id = request.args.get("session_id")
        limit = request.args.get("limit", "10")
        
        params = {}
        if user_id:
            params["user_id"] = user_id
        if session_id:
            params["session_id"] = session_id
        params["limit"] = limit
        
        # Forward to copilot service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COPILOT_SERVICE_URL}/copilot/history",
                params=params
            )
            
            if response.status_code >= 400:
                return jsonify({"error": response.text}), response.status_code
            
            return jsonify(response.json()), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@copilot_bp.post("/feedback")
async def proxy_feedback():
    """Proxy feedback to copilot service."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Forward to copilot service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{COPILOT_SERVICE_URL}/copilot/feedback",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code >= 400:
                return jsonify({"error": response.text}), response.status_code
            
            return jsonify(response.json()), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@copilot_bp.get("/guardrails")
async def proxy_guardrails():
    """Proxy guardrail status request to copilot service."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{COPILOT_SERVICE_URL}/guardrails"
            )
            
            if response.status_code >= 400:
                return jsonify({"error": response.text}), response.status_code
            
            return jsonify(response.json()), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
