"""ML inference service for Waste Intelligence Platform.

Provides interfaces to ML models for forecasting, anomaly detection, 
and contamination detection.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from ..config import Config

logger = logging.getLogger(__name__)


async def run_forecast(features: dict) -> dict:
    """Forecast bin fill level from real telemetry history.

    Fits a linear trend to the bin's recent ``telemetry`` readings and
    projects the fill level ``horizon_hours`` ahead. No trained model is
    involved; the confidence reflects the goodness of fit (R^2).

    Args:
        features: must contain ``bin_id``; may contain ``horizon_hours``
            (default 24) and ``history_limit`` (default 50).

    Returns:
        Dict with ``timestamp``, ``predicted_value`` (fill % at horizon),
        ``confidence``, ``model_version``, ``horizon_hours`` and
        ``hours_until_full``.

    Raises:
        ValueError: if ``bin_id`` is missing or fewer than 2 readings exist.
    """
    from datetime import datetime, timezone

    from .db_client import get_conn, return_conn

    bin_id = features.get("bin_id")
    if not bin_id:
        raise ValueError("run_forecast requires features['bin_id']")
    horizon_hours = float(features.get("horizon_hours", 24))
    history_limit = int(features.get("history_limit", 50))

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT extract(epoch FROM reported_at), fill_level_percent
            FROM telemetry
            WHERE bin_id = %s AND fill_level_percent IS NOT NULL
            ORDER BY reported_at DESC
            LIMIT %s
            """,
            (bin_id, history_limit),
        )
        rows = cur.fetchall()
    finally:
        if conn:
            return_conn(conn)

    if len(rows) < 2:
        raise ValueError(f"not enough telemetry history for bin {bin_id}")

    # Oldest-first for the regression
    rows = sorted(rows, key=lambda r: r[0])
    t0 = rows[0][0]
    xs = [(r[0] - t0) / 3600.0 for r in rows]  # hours since first reading
    ys = [float(r[1]) for r in rows]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom if denom else 0.0
    intercept = mean_y - slope * mean_x
    # R^2 as confidence
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0

    current = ys[-1]
    predicted = min(100.0, max(0.0, current + slope * horizon_hours))
    hours_until_full = (100.0 - current) / slope if slope > 0 else None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "predicted_value": round(predicted, 2),
        "confidence": round(max(0.0, min(1.0, r2)), 3),
        "model_version": "telemetry-trend-v1",
        "horizon_hours": horizon_hours,
        "hours_until_full": round(hours_until_full, 1) if hours_until_full is not None else None,
        "trend_percent_per_hour": round(slope, 3),
        "readings_used": n,
    }


async def run_anomaly(features: dict) -> dict:
    """Detect anomalous bin readings with a z-score over telemetry history.

    Compares the latest ``fill_level_percent`` reading against the mean/std
    of the bin's history. The |z|-score is normalized to a 0..1
    ``anomaly_score``; a reading is anomalous when the score meets the
    ``threshold`` (default 0.5).

    Args:
        features: must contain ``bin_id``; may contain ``threshold`` and
            ``history_limit`` (default 50).

    Returns:
        Dict with ``timestamp``, ``is_anomaly``, ``anomaly_score`` (0..1),
        ``threshold``, ``z_score`` and ``model_version``.

    Raises:
        ValueError: if ``bin_id`` is missing or history is too short.
    """
    from datetime import datetime, timezone

    from .db_client import get_conn, return_conn

    bin_id = features.get("bin_id")
    if not bin_id:
        raise ValueError("run_anomaly requires features['bin_id']")
    # Threshold is on the 0..1 anomaly-score scale (score = min(|z|/5, 1)).
    threshold = float(features.get("threshold", 0.5))
    history_limit = int(features.get("history_limit", 50))

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT fill_level_percent, mass_kg
            FROM telemetry
            WHERE bin_id = %s AND fill_level_percent IS NOT NULL
            ORDER BY reported_at DESC
            LIMIT %s
            """,
            (bin_id, history_limit),
        )
        rows = cur.fetchall()
    finally:
        if conn:
            return_conn(conn)

    if len(rows) < 5:
        raise ValueError(f"not enough telemetry history for bin {bin_id}")

    latest = rows[0]
    history = rows[1:]
    fills = [float(r[0]) for r in history]
    mean = sum(fills) / len(fills)
    var = sum((f - mean) ** 2 for f in fills) / len(fills)
    std = var ** 0.5
    latest_fill = float(latest[0])
    z = abs(latest_fill - mean) / std if std > 0 else 0.0
    score = min(z / 5.0, 1.0)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_anomaly": bool(score >= threshold),
        "anomaly_score": round(score, 3),
        "threshold": threshold,
        "z_score": round(z, 3),
        "latest_fill_percent": latest_fill,
        "history_mean_fill_percent": round(mean, 2),
        "model_version": "telemetry-zscore-v1",
    }


async def run_contamination(image_tensor: list | None = None) -> dict:
    """Contamination detection is not available.

    No contamination vision model has been trained or deployed in this
    repository, so image-based contamination detection cannot run. This
    raises instead of returning fabricated random detections.
    """
    raise RuntimeError(
        "contamination vision model is not trained or deployed; "
        "image-based contamination detection is unavailable"
    )
