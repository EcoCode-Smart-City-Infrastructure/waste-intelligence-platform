"""WIN OS API tests: health, RBAC, tenant isolation, provenance, idempotency.
Run: cd win-os && ../.venv/bin/python -m pytest tests -q  (see win-os/Makefile)
Uses an isolated SQLite database; PostgreSQL/PostGIS behaviour is covered by
the Alembic migration and the deployment runbook, not by these tests.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
os.environ["WIN_OS_KEYS"] = (
    "admin-key:platform_admin:org-a,"
    "op-key:operator:org-a,"
    "view-key:viewer:org-a,"
    "other-key:operator:org-b,"
    "svc-key:integration:org-a")
os.environ.pop("WIN_ENVIRONMENT", None)

import pytest
from fastapi.testclient import TestClient
from app.main import create_app

ADMIN = {"X-API-Key": "admin-key"}
OP = {"X-API-Key": "op-key"}
VIEW = {"X-API-Key": "view-key"}
OTHER = {"X-API-Key": "other-key"}
SVC = {"X-API-Key": "svc-key"}

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db = tmp_path_factory.mktemp("db") / "test.db"
    return TestClient(create_app(f"sqlite:///{db}"))

def test_health_live_and_ready(client):
    assert client.get("/health/live").json()["status"] == "live"
    assert client.get("/health/ready").json()["database"] == "ok"

def test_auth_required(client):
    assert client.get("/api/v1/assets").status_code == 401
    assert client.get("/api/v1/assets", headers={"X-API-Key": "nope"}).status_code == 401

def test_viewer_cannot_write(client):
    r = client.post("/api/v1/assets", headers=VIEW, json={"name": "Bin V"})
    assert r.status_code == 403

def test_asset_crud_and_provenance(client):
    r = client.post("/api/v1/assets", headers=OP, json={
        "name": "Bin 1", "latitude": 40.7, "longitude": -73.9,
        "source_record_id": "src-1", "data_status": "observed"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["org_id"] == "org-a" and body["source_record_id"] == "src-1"
    assert body["data_status"] == "observed" and body["ingested_at"]
    got = client.get(f"/api/v1/assets/{body['id']}", headers=VIEW)
    assert got.status_code == 200

def test_tenant_isolation(client):
    r = client.post("/api/v1/assets", headers=OP, json={"name": "Org A only"})
    aid = r.json()["id"]
    assert client.get(f"/api/v1/assets/{aid}", headers=OTHER).status_code == 404
    listing = client.get("/api/v1/assets", headers=OTHER).json()
    assert all(i["org_id"] == "org-b" for i in listing["items"])

def test_invalid_data_status_rejected(client):
    r = client.post("/api/v1/assets", headers=OP,
                    json={"name": "X", "data_status": "live"})
    assert r.status_code == 422

def test_facility_capacity_unknown_not_zero(client):
    r = client.post("/api/v1/facilities", headers=OP, json={"name": "MRF Unknown"})
    assert r.status_code == 201
    assert r.json()["capacity_tons_per_day"] is None
    assert r.json()["capacity_status"] == "unavailable"

def test_collection_idempotency_and_ref_validation(client):
    bad = client.post("/api/v1/collections", headers=OP, json={"asset_id": "missing"})
    assert bad.status_code == 422
    a = client.post("/api/v1/assets", headers=OP, json={"name": "Bin C"}).json()
    h = {**OP, "Idempotency-Key": "evt-1"}
    r1 = client.post("/api/v1/collections", headers=h,
                     json={"asset_id": a["id"], "status": "completed", "quantity_kg": 12.5})
    r2 = client.post("/api/v1/collections", headers=h,
                     json={"asset_id": a["id"], "status": "completed", "quantity_kg": 12.5})
    assert r1.status_code == 201 and r2.json()["idempotent_replay"] is True
    assert r1.json()["id"] == r2.json()["id"]

def test_route_plan_is_labelled_planned(client):
    a = client.post("/api/v1/assets", headers=OP, json={
        "name": "Bin R1", "latitude": 40.71, "longitude": -73.99}).json()
    b = client.post("/api/v1/assets", headers=OP, json={
        "name": "Bin R2", "latitude": 40.72, "longitude": -73.98}).json()
    assert client.post("/api/v1/routes/plan", headers=OP, json={
        "depot_latitude": 40.70, "depot_longitude": -74.0,
        "asset_ids": [a["id"]]}).status_code == 403  # operator cannot plan routes
    r = client.post("/api/v1/routes/plan", headers=ADMIN, json={
        "depot_latitude": 40.70, "depot_longitude": -74.0,
        "asset_ids": [a["id"], b["id"]]})
    assert r.status_code == 201, r.text
    assert r.json()["execution_status"] == "planned"
    assert r.json()["data_status"] == "derived"
    assert r.json()["total_distance_km"] > 0

def test_forecast_records_metadata_and_is_labelled(client):
    r = client.post("/api/v1/intelligence/forecast", headers=OP, json={
        "series": [10, 12, 11, 13, 14, 15], "horizon": 2})
    assert r.status_code == 403  # operator lacks 'analyse'
    from fastapi.testclient import TestClient  # noqa
    r = client.post("/api/v1/intelligence/forecast", headers=ADMIN, json={
        "series": [10, 12, 11, 13, 14, 15], "horizon": 2})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["data_status"] == "forecast" and body["model_id"]
    assert all(p["data_status"] == "forecast" for p in body["predictions"])
    assert "baseline" in body["limitations"].lower() or "Linear" in body["limitations"]

def test_anomaly_flags_outlier(client):
    r = client.post("/api/v1/intelligence/anomaly", headers=ADMIN,
                    json={"values": [10, 10, 11, 9, 10, 11, 10, 100],
                          "z_threshold": 2.0})
    assert r.status_code == 200 and r.json()["count"] >= 1

def test_ingestion_idempotent_and_quarantine(client):
    payload = {"source": "csv-upload", "records": [
        {"name": "Ingested 1", "source_record_id": "csv-1"},
        {"name": "Ingested 1 replay", "source_record_id": "csv-1"},
        {"latitude": "not-a-number", "name": "Bad coords"},
        {"source_record_id": "no-name"}]}
    r = client.post("/api/v1/ingestion/assets", headers=SVC, json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["records_quarantined"] == 2
    again = client.post("/api/v1/ingestion/assets", headers=SVC, json=payload)
    assert again.status_code == 201
    names = [i["name"] for i in client.get("/api/v1/assets", headers=ADMIN).json()["items"]]
    assert names.count("Ingested 1") == 1

def test_system_status_requires_admin(client):
    assert client.get("/api/v1/system/status", headers=OP).status_code == 403
    r = client.get("/api/v1/system/status", headers=ADMIN)
    assert r.status_code == 200 and r.json()["database"] == "ok"

def test_copilot_honest_when_unconfigured(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API", raising=False)
    r = client.get("/api/v1/copilot/status", headers=VIEW)
    assert r.status_code == 200
    assert r.json()["status"] in ("available", "unavailable")
    s = client.get("/api/v1/copilot/metric-summary", headers=VIEW)
    assert s.json()["generated_by"].startswith("win-os-api (no model)")

def test_correlation_header(client):
    r = client.get("/health/live", headers={"X-Correlation-ID": "test-123"})
    assert r.headers.get("x-correlation-id") == "test-123"
