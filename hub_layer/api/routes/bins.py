"""Bin route handlers — DB-backed via BinRepository.

Previously these returned hardcoded empty results, which is why the
web app always reported "hub returns no bins". An empty database
still returns an empty list, but that is now a true DB result; a
missing/unreachable database returns 503 instead of a fake empty list.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request

bins_bp = Blueprint("bins", __name__, url_prefix="/bins")


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


@bins_bp.get("")
def list_bins():
    try:
        from hub_layer.repositories.bin_repository import BinRepository

        rows = BinRepository().list_bins()
    except Exception as e:
        return jsonify({"error": f"database unavailable: {e}"}), 503
    rows = [_jsonable(r) for r in rows]
    return jsonify({"bins": rows, "count": len(rows)})


@bins_bp.get("/<bin_id>")
def get_bin(bin_id: str):
    try:
        from hub_layer.repositories.bin_repository import BinRepository

        row = BinRepository().get_bin(bin_id)
    except Exception as e:
        return jsonify({"error": f"database unavailable: {e}"}), 503
    if not row:
        return jsonify({"bin_id": bin_id, "status": "not found"}), 404
    return jsonify(_jsonable(row))


@bins_bp.post("")
def create_bin():
    data = request.get_json(silent=True) or {}
    if not data.get("bin_id"):
        return jsonify({"error": "bin_id is required"}), 400
    try:
        from hub_layer.repositories.bin_repository import BinRepository

        BinRepository().create_bin(data)
    except Exception as e:
        return jsonify({"error": f"database unavailable: {e}"}), 503
    return jsonify({"status": "created", "bin_id": data["bin_id"]}), 201
