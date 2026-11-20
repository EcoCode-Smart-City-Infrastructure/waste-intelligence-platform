"""Seed a WIN OS deployment with clearly labelled demonstration data.

Refuses to run when WIN_ENVIRONMENT=production. Every record is created
through the public API with data_status 'reported' (assets/facilities) -
the seed is a starting dataset for a field demo, not operational data.
Usage: WIN_API_URL=http://127.0.0.1:8080 WIN_API_KEY=<operator key> \
       python win-os/tools/seed_win_os.py

Stdlib only (urllib): this script runs on the bare GitHub runner host in
the deploy-verify workflow, where third-party packages such as httpx are
not installed. Run #3 failed with ModuleNotFoundError: No module named
'httpx' - do not reintroduce a third-party HTTP dependency here.
"""
import json
import os, sys
import urllib.error
import urllib.request

BASE = os.environ.get("WIN_API_URL", "http://127.0.0.1:8080")
KEY = os.environ.get("WIN_API_KEY", "")
if os.environ.get("WIN_ENVIRONMENT") == "production":
    sys.exit("Refusing to seed demonstration data into a production environment.")
if not KEY:
    sys.exit("WIN_API_KEY (operator role or above) is required.")


def post(path, payload):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"X-API-Key": KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        # httpx.post never raised on error status; neither do we - the
        # caller prints the status and the workflow's curl smoke checks
        # decide pass/fail.
        return e.code


assets = [
    {"name": "Demo bin - Depot North 1", "latitude": 40.7128, "longitude": -74.0060,
     "capacity_liters": 240, "source_record_id": "seed-bin-1"},
    {"name": "Demo bin - Depot North 2", "latitude": 40.7218, "longitude": -73.9990,
     "capacity_liters": 240, "source_record_id": "seed-bin-2"},
    {"name": "Demo bin - Riverside 1", "latitude": 40.7050, "longitude": -74.0120,
     "capacity_liters": 1100, "source_record_id": "seed-bin-3"},
]
for a in assets:
    print("asset", a["source_record_id"], post("/api/v1/assets", a))
print("facility", post("/api/v1/facilities", {
    "name": "Demo transfer station", "facility_type": "transfer_station",
    "latitude": 40.7300, "longitude": -73.9900,
    "accepted_materials": "mixed_recyclables, food_organics",
    "source_record_id": "seed-fac-1"}))
print("device (telemetry stays 'unavailable' until it really reports)",
      post("/api/v1/devices", {
          "device_id": "demo-sensor-1", "firmware_version": "seed"}))
print("Seed complete. All records are demonstration data, labelled in their names.")
