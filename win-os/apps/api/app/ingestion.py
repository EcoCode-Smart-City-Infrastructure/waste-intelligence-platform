"""Reusable ingestion framework.

Adapters implement fetch() -> list of raw dicts. The ingest service validates,
assigns provenance, quarantines invalid records (reported, never silently
dropped), and persists idempotently on (org_id, source_record_id): replaying
the same source record updates nothing and creates no duplicate.
"""
from __future__ import annotations
import csv, io, uuid
import httpx
from sqlalchemy.orm import Session
from .models import Asset, IngestionJob

REQUIRED = ("name",)

def validate_asset_record(raw: dict) -> tuple[dict | None, str | None]:
    for field in REQUIRED:
        if not raw.get(field):
            return None, f"missing required field: {field}"
    try:
        lat = float(raw["latitude"]) if raw.get("latitude") not in (None, "") else None
        lon = float(raw["longitude"]) if raw.get("longitude") not in (None, "") else None
        if lat is not None and not -90 <= lat <= 90:
            return None, "latitude out of range"
        if lon is not None and not -180 <= lon <= 180:
            return None, "longitude out of range"
    except (TypeError, ValueError):
        return None, "latitude/longitude not numeric"
    return {
        "name": str(raw["name"])[:200],
        "asset_type": str(raw.get("asset_type") or "bin"),
        "latitude": lat, "longitude": lon,
        "source_record_id": str(raw["source_record_id"]) if raw.get("source_record_id") else None,
        "source_system": str(raw.get("source_system") or "ingestion"),
    }, None

def ingest_assets(db: Session, org_id: str, source: str, records: list[dict]) -> IngestionJob:
    ok, quarantined, notes = 0, 0, []
    for raw in records:
        clean, err = validate_asset_record(raw)
        if err:
            quarantined += 1
            notes.append(err)
            continue
        existing = None
        if clean["source_record_id"]:
            existing = db.query(Asset).filter_by(
                org_id=org_id, source_record_id=clean["source_record_id"]).first()
        if existing:
            ok += 1  # idempotent replay: no duplicate, no silent overwrite
            continue
        db.add(Asset(id=f"ast-{uuid.uuid4().hex[:12]}", org_id=org_id, **clean))
        db.flush()  # make the row visible to the next record's idempotency check
        ok += 1
    job = IngestionJob(id=f"job-{uuid.uuid4().hex[:12]}", org_id=org_id, source=source,
                       status="completed", records_ok=ok,
                       records_quarantined=quarantined,
                       detail="; ".join(sorted(set(notes)))[:1000] or None)
    db.add(job)
    db.commit()
    return job

class CsvAdapter:
    """Manual CSV upload adapter (directive section 8)."""
    source = "csv-upload"
    def __init__(self, text: str):
        self.text = text
    def fetch(self) -> list[dict]:
        return list(csv.DictReader(io.StringIO(self.text)))

class SocrataAdapter:
    """NYC Open Data (Socrata) adapter. Claims are limited to what the dataset
    itself publishes; no live GPS / sensor / capacity claims are made."""
    source = "nyc-socrata"
    def __init__(self, dataset_id: str, app_token: str | None = None, limit: int = 100):
        self.dataset_id, self.app_token, self.limit = dataset_id, app_token, limit
    def fetch(self) -> list[dict]:
        headers = {"X-App-Token": self.app_token} if self.app_token else {}
        resp = httpx.get(
            f"https://data.cityofnewyork.us/resource/{self.dataset_id}.json",
            params={"$limit": self.limit}, headers=headers, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
