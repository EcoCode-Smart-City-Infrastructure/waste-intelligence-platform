"""Bin route handlers."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from hub_layer.repositories.bin_repository import BinRepository

bins_bp = Blueprint("bins", __name__, url_prefix="/bins")
bin_repo = BinRepository()


@bins_bp.get("")
def list_bins():
    bins = bin_repo.list_bins()
    return jsonify({"bins": bins, "count": len(bins)})


@bins_bp.get("/<bin_id>")
def get_bin(bin_id: str):
    bin_data = bin_repo.get_bin(bin_id)
    if not bin_data:
        return jsonify({"error": "Bin not found"}), 404
    return jsonify(bin_data)


@bins_bp.post("")
def create_bin():
    data = request.get_json(silent=True) or {}
    if not data.get("bin_id"):
        return jsonify({"error": "bin_id is required"}), 400
    try:
        bin_repo.create_bin(data)
        return jsonify({"status": "created", "bin_id": data["bin_id"]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
