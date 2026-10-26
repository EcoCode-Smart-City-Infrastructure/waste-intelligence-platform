"""Forecasting and anomaly detection microservice.

Provides real statistical forecasting for waste bin fill levels and
z-score anomaly detection over telemetry history. Backed by Postgres;
no fabricated data — insufficient history raises a 422.

Endpoints:
    GET  /health    liveness + DB reachability
    POST /forecast  fill-level forecast for a bin
    POST /anomaly   anomaly verdict for current readings
"""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://timescale:password@postgres:5432/wasteintel",
)

MODEL_VERSION = "waste-forecast-v1.0"

app = FastAPI(title="Waste Forecasting Service")

# CORS: browsers calling this service from the GitHub Pages web app
# (https://ecocode-smart-city-infrastructure.github.io) were blocked
# because the service shipped no CORS middleware at all. Origins are
# env-driven; a literal "*" disables credentials (browsers reject
# Access-Control-Allow-Credentials with "*").
from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware

_CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "https://ecocode-smart-city-infrastructure.github.io,http://localhost:3000,http://localhost:8080",
).split(",") if o.strip()]
app.add_middleware(
    _CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=("*" not in _CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# DB
# --------------------------------------------------------------------------- #
def query_telemetry(bin_id: str, limit: int = 200) -> list[tuple[float, float]]:
    """Return (epoch_seconds, fill_level_percent) for a bin, oldest first."""
    conn = psycopg2.connect(DB_URL)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT extract(epoch FROM reported_at), fill_level_percent
            FROM telemetry
            WHERE bin_id = %s AND fill_level_percent IS NOT NULL
            ORDER BY reported_at DESC
            LIMIT %s
            """,
            (bin_id, limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [(float(ts), float(fill)) for ts, fill in reversed(rows)]


def query_metric_history(
    bin_id: str, column: str, limit: int = 100
) -> list[float]:
    conn = psycopg2.connect(DB_URL)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT {column} FROM telemetry
            WHERE bin_id = %s AND {column} IS NOT NULL
            ORDER BY reported_at DESC LIMIT %s
            """,
            (bin_id, limit),
        )
        rows = [float(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class ForecastRequest(BaseModel):
    bin_id: str | None = None
    features: dict | None = None
    horizon_hours: int = 24
    history_limit: int = 200


class AnomalyRequest(BaseModel):
    bin_id: str | None = None
    features: dict | None = None
    threshold: float = 0.95


def _linear_fit(points: list[tuple[float, float]]):
    """Least-squares fit; returns (slope_per_hour, intercept, r_squared)."""
    n = len(points)
    t0 = points[0][0]
    xs = [(t - t0) / 3600.0 for t, _ in points]
    ys = [y for _, y in points]
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my, 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    syy = sum((y - my) ** 2 for y in ys)
    r2 = (sxy * sxy) / (sxx * syy) if sxx * syy else 0.0
    return slope, intercept, r2, t0


def _current_cycle(points: list[tuple[float, float]]):
    """Drop pre-collection history: a fill drop > 30 points starts a new cycle."""
    for i in range(len(points) - 1, 0, -1):
        if points[i - 1][1] - points[i][1] > 30:
            return points[i:]
    return points


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(DB_URL)
        conn.close()
        db = "ok"
    except Exception as e:
        db = f"unreachable: {e}"
    return {"status": "ok", "db": db, "model_version": MODEL_VERSION}


@app.post("/forecast")
def forecast(req: ForecastRequest):
    features = req.features or {}
    bin_id = req.bin_id or features.get("bin_id")
    if not bin_id:
        raise HTTPException(422, "bin_id is required")

    horizon = req.horizon_hours or int(features.get("horizon_hours", 24))
    try:
        points = query_telemetry(bin_id, req.history_limit)
    except Exception as e:
        logger.error("DB query failed: %s", e)
        raise HTTPException(503, f"telemetry unavailable: {e}")

    if len(points) < 2:
        raise HTTPException(
            422, f"insufficient telemetry for bin {bin_id} (need >= 2 readings)"
        )

    cycle = _current_cycle(points)
    slope, intercept, r2, t0 = _linear_fit(cycle)
    now_epoch = points[-1][0]
    hours_ahead = (now_epoch - t0) / 3600.0 + horizon
    predicted = max(0.0, min(150.0, slope * hours_ahead + intercept))

    # Confidence: goodness of fit, discounted for thin or stale data.
    confidence = max(0.05, min(0.99, r2 * min(1.0, len(cycle) / 20)))

    hours_until_full = None
    if slope > 0.01:
        hours_until_full = round((100.0 - points[-1][1]) / slope, 1)

    return JSONResponse(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "predicted_value": round(predicted, 2),
            "confidence": round(confidence, 3),
            "model_version": MODEL_VERSION,
            "horizon_hours": horizon,
            "hours_until_full": hours_until_full,
            "trend_fill_per_hour": round(slope, 3),
            "r_squared": round(r2, 3),
            "readings_used": len(cycle),
        }
    )


@app.post("/anomaly")
def anomaly(req: AnomalyRequest):
    features = req.features or {}
    bin_id = req.bin_id or features.get("bin_id")
    if not bin_id:
        raise HTTPException(422, "bin_id is required")

    # Candidate signals: telemetry columns we actually store.
    signals = {
        "fill_level_percent": features.get("filllevelpct"),
        "mass_kg": features.get("mass_kg"),
    }
    signals = {k: v for k, v in signals.items() if v is not None}
    if not signals:
        raise HTTPException(422, "no measurable features provided")

    columns = {"fill_level_percent": "fill_level_percent", "mass_kg": "mass_kg"}
    scores: dict[str, float] = {}
    try:
        for name, value in signals.items():
            hist = query_metric_history(bin_id, columns[name])
            if len(hist) < 5:
                continue
            mean = sum(hist) / len(hist)
            var = sum((x - mean) ** 2 for x in hist) / len(hist)
            std = math.sqrt(var) if var > 0 else 0.0
            z = abs(value - mean) / std if std > 0 else 0.0
            scores[name] = round(z, 3)
    except Exception as e:
        logger.error("DB query failed: %s", e)
        raise HTTPException(503, f"telemetry unavailable: {e}")

    if not scores:
        raise HTTPException(
            422, f"insufficient history for bin {bin_id} (need >= 5 readings)"
        )

    max_z = max(scores.values())
    # Map z-score to a 0..1 anomaly score; threshold default ~2 sigma.
    z_threshold = 2.0 if req.threshold >= 1 else req.threshold * 4
    is_anomaly = max_z > z_threshold
    anomaly_score = round(min(1.0, max_z / (z_threshold * 2)), 3)

    return JSONResponse(
        {
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "threshold": req.threshold,
            "z_scores": scores,
            "model_version": MODEL_VERSION,
        }
    )
