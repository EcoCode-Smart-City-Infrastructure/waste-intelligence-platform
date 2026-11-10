"""Intelligence baselines: interpretable, honestly labelled.

Forecasting starts with a linear-trend baseline (services/forecasting already
implements a Postgres-backed variant for bin fill levels; this module is the
provider-independent interface for the WIN API). No complex model is trained
on inadequate data. Every run records model id/version, training window,
residual metrics and limitations, and is stored with data_status=forecast.
"""
from __future__ import annotations
import math

MODEL_ID = "baseline-linear-trend"
MODEL_VERSION = "1.0.0"
LIMITATIONS = ("Linear-trend baseline only; assumes the recent trend continues. "
               "Not validated for operational decisions. Forecasts are not observations.")

def linear_trend_forecast(series: list[float], horizon: int) -> dict:
    n = len(series)
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(series) / n
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, series)) / denom if denom else 0.0
    intercept = my - slope * mx
    fitted = [intercept + slope * x for x in xs]
    residuals = [y - f for y, f in zip(series, fitted)]
    rmse = math.sqrt(sum(r * r for r in residuals) / n)
    predictions = []
    for h in range(1, horizon + 1):
        x = n - 1 + h
        point = intercept + slope * x
        predictions.append({
            "step": h, "value": round(point, 4),
            "lower": round(point - 1.96 * rmse, 4),
            "upper": round(point + 1.96 * rmse, 4),
            "data_status": "forecast"})
    return {"model_id": MODEL_ID, "model_version": MODEL_VERSION,
            "predictions": predictions,
            "metrics": {"rmse": round(rmse, 4), "slope_per_step": round(slope, 6),
                        "n_points": n},
            "limitations": LIMITATIONS}

def zscore_anomalies(values: list[float], z_threshold: float = 3.0) -> dict:
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(var)
    flagged = []
    if std > 0:
        for i, v in enumerate(values):
            z = (v - mean) / std
            if abs(z) >= z_threshold:
                flagged.append({"index": i, "value": v, "z_score": round(z, 3),
                                "kind": "operational"})
    return {"count": len(flagged), "anomalies": flagged,
            "method": "population z-score", "mean": round(mean, 4),
            "std": round(std, 4),
            "note": "Statistical flag for review, not proof of an operational fault."}

def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a); lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))

def nearest_neighbour_route(depot: tuple[float, float],
                            stops: list[tuple[str, float, float]]) -> dict:
    """Greedy nearest-neighbour plan. A plan only: execution_status stays
    'planned' and total distance is a derived estimate, not a driven route."""
    remaining = list(stops)
    ordered, total, cur = [], 0.0, depot
    while remaining:
        nxt = min(remaining, key=lambda s: haversine_km(cur, (s[1], s[2])))
        total += haversine_km(cur, (nxt[1], nxt[2]))
        ordered.append({"asset_id": nxt[0], "latitude": nxt[1], "longitude": nxt[2],
                        "sequence": len(ordered) + 1})
        cur = (nxt[1], nxt[2])
        remaining.remove(nxt)
    total += haversine_km(cur, depot) if ordered else 0.0
    return {"stops": ordered, "total_distance_km": round(total, 3),
            "method": "nearest-neighbour", "data_status": "derived",
            "execution_status": "planned"}
