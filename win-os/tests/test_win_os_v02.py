"""WIN OS v0.2 tests: Phase 6 operations, Phase 9 edge/simulation,
Phase 10 hardening. Same isolated-SQLite approach as the v0.1 suite."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
os.environ["WIN_OS_KEYS"] = (
    "admin-key:platform_admin:org-a,"
    "op-key:operator:org-a,"
    "view-key:viewer:org-a,"
    "other-key:operator:org-b,"
    "svc-key:integration:org-a")

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
    db = tmp_path_factory.mktemp("db2") / "test2.db"
    return TestClient(create_app(f"sqlite:///{db}"))

def test_vehicle_crud_and_fleet_filter(client):
    r = client.post("/api/v1/vehicles", headers=OP, json={
        "name": "Truck 7", "fleet_name": "North", "capacity_kg": 8000,
        "status": "available"})
    assert r.status_code == 201, r.text
    bad = client.post("/api/v1/vehicles", headers=OP, json={
        "name": "Truck X", "status": "flying"})
    assert bad.status_code == 422
    rows = client.get("/api/v1/vehicles?fleet=North", headers=VIEW).json()
    assert rows["total"] == 1 and rows["items"][0]["name"] == "Truck 7"
    assert client.get("/api/v1/vehicles", headers=OTHER).json()["total"] == 0

def test_pathway_requires_real_stream_and_facility(client):
    bad = client.post("/api/v1/recovery-pathways", headers=OP, json={
        "waste_stream_id": "nope", "facility_id": "nope"})
    assert bad.status_code == 422
    s = client.post("/api/v1/waste-streams", headers=OP, json={
        "name": "Curbside organics", "material": "food_organics"}).json()
    f = client.post("/api/v1/facilities", headers=OP, json={"name": "Compost Co"}).json()
    ok = client.post("/api/v1/recovery-pathways", headers=OP, json={
        "waste_stream_id": s["id"], "facility_id": f["id"],
        "pathway_type": "composting"})
    assert ok.status_code == 201, ok.text
    # no rate reported -> performance is unavailable, not a number
    assert ok.json()["diversion_rate_pct"] is None
    assert ok.json()["diversion_status"] == "unavailable"

def test_environmental_accounting_math_and_formula(client):
    r = client.post("/api/v1/environmental/records", headers=OP, json={
        "material": "food_organics", "pathway_type": "composting",
        "quantity_kg": 1000})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["co2e_kg"] == 120.0  # 1000 x 0.12
    assert "quantity_kg (1000" in body["formula"]
    assert body["methodology_version"] == "WIN-ENV-ACCT-1.0"
    assert body["data_status"] == "derived"
    bad = client.post("/api/v1/environmental/records", headers=OP, json={
        "material": "unobtainium", "pathway_type": "recycling", "quantity_kg": 5})
    assert bad.status_code == 422
    s = client.get("/api/v1/environmental/summary", headers=VIEW).json()
    assert s["by_data_status"]["derived"]["co2e_kg"] == 120.0
    assert "simulated" not in s["by_data_status"]

def test_data_quality_summary(client):
    client.post("/api/v1/assets", headers=OP, json={
        "name": "DQ bin", "data_status": "simulated"})
    r = client.get("/api/v1/data-quality/summary", headers=VIEW)
    assert r.status_code == 200
    assert r.json()["assets_by_status"].get("simulated", 0) >= 1
    assert "ingestion" in r.json()

def test_device_never_reported_is_unavailable(client):
    client.post("/api/v1/devices", headers=OP, json={"device_id": "bin-sensor-1"})
    rows = client.get("/api/v1/devices", headers=VIEW).json()
    d = [x for x in rows["items"] if x["device_id"] == "bin-sensor-1"][0]
    assert d["telemetry_status"] == "unavailable" and d["last_seen_at"] is None

def test_telemetry_store_and_forward_idempotent(client):
    client.post("/api/v1/devices", headers=OP, json={"device_id": "bin-sensor-2"})
    payload = {"events": [
        {"device_id": "bin-sensor-2", "client_event_id": "e1",
         "observed_at": "2026-11-10T10:00:00+00:00", "fill_level_percent": 55,
         "buffered_offline": True},
        {"device_id": "bin-sensor-2", "client_event_id": "e1",
         "observed_at": "2026-11-10T10:00:00+00:00", "fill_level_percent": 55,
         "buffered_offline": True},
        {"device_id": "ghost-device", "client_event_id": "e9",
         "observed_at": "2026-11-10T10:00:00+00:00"}]}
    r = client.post("/api/v1/telemetry/events", headers=SVC, json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["accepted"] == 1 and body["idempotent_replays"] == 1
    assert body["quarantined_unregistered_device"] == 1
    rows = client.get("/api/v1/telemetry/events?device_id=bin-sensor-2", headers=VIEW).json()
    assert rows["total"] == 1 and rows["items"][0]["buffered_offline"] is True
    d = [x for x in client.get("/api/v1/devices", headers=VIEW).json()["items"]
         if x["device_id"] == "bin-sensor-2"][0]
    assert d["telemetry_status"] == "reported"

def test_simulation_is_labelled_and_separate(client):
    r = client.post("/api/v1/simulations", headers=ADMIN, json={
        "name": "Raise diversion", "total_kg": 10000,
        "current_diversion_pct": 20, "target_diversion_pct": 40})
    assert r.status_code == 201, r.text
    res = r.json()["results"]
    assert res["data_status"] == "simulated"
    assert res["additional_diverted_kg"] == 2000.0
    # simulated numbers must not leak into the environmental summary
    s = client.get("/api/v1/environmental/summary", headers=VIEW).json()
    assert "simulated" not in s["by_data_status"]

def test_security_headers(client):
    r = client.get("/api/v1/assets", headers=VIEW)
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("cache-control") == "no-store"

def test_rate_limit(tmp_path):
    c = TestClient(create_app(f"sqlite:///{tmp_path}/rl.db", rate_limit_per_min=3))
    codes = [c.get("/api/v1/assets", headers=VIEW).status_code for _ in range(5)]
    assert 429 in codes

def test_system_jobs_admin_only(client):
    assert client.get("/api/v1/system/jobs", headers=OP).status_code == 403
    # Register via the same client so the count is checked against the same
    # database the app is currently bound to (single-app process model).
    client.post("/api/v1/devices", headers=OP, json={"device_id": "jobs-sensor"})
    r = client.get("/api/v1/system/jobs", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["devices"]["registered"] >= 1
