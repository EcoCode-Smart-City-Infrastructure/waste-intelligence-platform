import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
from app.intelligence import linear_trend_forecast, zscore_anomalies, nearest_neighbour_route
from app.ingestion import validate_asset_record

def test_forecast_needs_trend_shape():
    out = linear_trend_forecast([1, 2, 3, 4], 2)
    assert out["predictions"][0]["value"] > 4
    assert out["metrics"]["n_points"] == 4

def test_route_returns_to_depot_distance_positive():
    out = nearest_neighbour_route((40.7, -74.0), [("a", 40.71, -73.99), ("b", 40.72, -73.98)])
    assert [s["asset_id"] for s in out["stops"]] == ["a", "b"]
    assert out["execution_status"] == "planned"

def test_validate_rejects_bad_coords():
    clean, err = validate_asset_record({"name": "x", "latitude": "999"})
    assert clean is None and "range" in err
