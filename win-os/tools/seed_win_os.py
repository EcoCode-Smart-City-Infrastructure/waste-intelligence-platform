"""Seed a WIN OS deployment with clearly labelled demonstration data.

Refuses to run when WIN_ENVIRONMENT=production. Every record is created
through the public API with data_status 'reported' (assets/facilities) -
the seed is a starting dataset for a field demo, not operational data.
Usage: WIN_API_URL=http://127.0.0.1:8080 WIN_API_KEY=<operator key> \
       python win-os/tools/seed_win_os.py
"""
import os, sys
import httpx

BASE = os.environ.get("WIN_API_URL", "http://127.0.0.1:8080")
KEY = os.environ.get("WIN_API_KEY", "")
if os.environ.get("WIN_ENVIRONMENT") == "production":
    sys.exit("Refusing to seed demonstration data into a production environment.")
if not KEY:
    sys.exit("WIN_API_KEY (operator role or above) is required.")

H = {"X-API-Key": KEY}
assets = [
    {"name": "Demo bin - Depot North 1", "latitude": 40.7128, "longitude": -74.0060,
     "capacity_liters": 240, "source_record_id": "seed-bin-1"},
    {"name": "Demo bin - Depot North 2", "latitude": 40.7218, "longitude": -73.9990,
     "capacity_liters": 240, "source_record_id": "seed-bin-2"},
    {"name": "Demo bin - Riverside 1", "latitude": 40.7050, "longitude": -74.0120,
     "capacity_liters": 1100, "source_record_id": "seed-bin-3"},
]
for a in assets:
    r = httpx.post(f"{BASE}/api/v1/assets", headers=H, json=a, timeout=15)
    print("asset", a["source_record_id"], r.status_code)
r = httpx.post(f"{BASE}/api/v1/facilities", headers=H, timeout=15, json={
    "name": "Demo transfer station", "facility_type": "transfer_station",
    "latitude": 40.7300, "longitude": -73.9900,
    "accepted_materials": "mixed_recyclables, food_organics",
    "source_record_id": "seed-fac-1"})
print("facility", r.status_code)
r = httpx.post(f"{BASE}/api/v1/devices", headers=H, timeout=15, json={
    "device_id": "demo-sensor-1", "firmware_version": "seed"})
print("device (telemetry stays 'unavailable' until it really reports)", r.status_code)
print("Seed complete. All records are demonstration data, labelled in their names.")
