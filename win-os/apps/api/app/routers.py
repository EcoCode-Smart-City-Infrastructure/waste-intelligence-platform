"""HTTP routers for the WIN OS API. Transport only: validation, tenant
scoping and permission checks live here; domain logic lives in models /
ingestion / intelligence modules. Every query is filtered by the caller's
organization - tenant isolation is enforced server-side on every route.
"""
from __future__ import annotations
import json, uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from . import copilot as copilot_mod
from . import intelligence
from .db import get_db
from .ingestion import ingest_assets
from .models import (Asset, AuditEvent, CollectionEvent, Facility, ForecastRun,
                     IngestionJob, RoutePlan)
from .schemas import (AnomalyIn, AssetIn, CollectionIn, CsvIngestIn, FacilityIn,
                      ForecastIn, RoutePlanIn)
from .security import Principal, authenticate, require

router = APIRouter(prefix="/api/v1")

def audit(db: Session, p: Principal, action: str, entity: str, entity_id: str | None):
    db.add(AuditEvent(org_id=p.org_id, actor_key_id=p.key_id, actor_role=p.role,
                      action=action, entity=entity, entity_id=entity_id))

def asset_out(a: Asset) -> dict:
    return {"id": a.id, "org_id": a.org_id, "name": a.name, "asset_type": a.asset_type,
            "status": a.status, "latitude": a.latitude, "longitude": a.longitude,
            "capacity_liters": a.capacity_liters, "service_area": a.service_area,
            "data_status": a.data_status.value, "source_system": a.source_system,
            "source_record_id": a.source_record_id, "observed_at": a.observed_at,
            "ingested_at": a.ingested_at, "quality_status": a.quality_status}

def facility_out(f: Facility) -> dict:
    return {"id": f.id, "org_id": f.org_id, "name": f.name,
            "facility_type": f.facility_type, "operational_status": f.operational_status,
            "latitude": f.latitude, "longitude": f.longitude,
            "accepted_materials": f.accepted_materials,
            "capacity_tons_per_day": f.capacity_tons_per_day,
            "capacity_status": "reported" if f.capacity_tons_per_day is not None else "unavailable",
            "data_status": f.data_status.value, "source_system": f.source_system,
            "source_record_id": f.source_record_id, "observed_at": f.observed_at,
            "ingested_at": f.ingested_at, "quality_status": f.quality_status}

# --- Assets ---------------------------------------------------------------
@router.post("/assets", status_code=201)
def create_asset(body: AssetIn, db: Session = Depends(get_db),
                 p: Principal = Depends(authenticate)):
    require(p, "write")
    a = Asset(id=f"ast-{uuid.uuid4().hex[:12]}", org_id=p.org_id, **body.model_dump())
    db.add(a); audit(db, p, "create", "asset", a.id); db.commit()
    return asset_out(a)

@router.get("/assets")
def list_assets(db: Session = Depends(get_db),
                p: Principal = Depends(authenticate),
                limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    require(p, "read")
    rows = (db.query(Asset).filter_by(org_id=p.org_id)
            .order_by(Asset.id).offset(offset).limit(limit).all())
    total = db.query(Asset).filter_by(org_id=p.org_id).count()
    return {"items": [asset_out(a) for a in rows], "total": total,
            "limit": limit, "offset": offset}

@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, db: Session = Depends(get_db),
              p: Principal = Depends(authenticate)):
    require(p, "read")
    a = db.query(Asset).filter_by(org_id=p.org_id, id=asset_id).first()
    if not a:
        raise HTTPException(404, {"error": "not_found", "message": "Asset not found in your organization."})
    return asset_out(a)

# --- Facilities -----------------------------------------------------------
@router.post("/facilities", status_code=201)
def create_facility(body: FacilityIn, db: Session = Depends(get_db),
                    p: Principal = Depends(authenticate)):
    require(p, "write")
    f = Facility(id=f"fac-{uuid.uuid4().hex[:12]}", org_id=p.org_id, **body.model_dump())
    db.add(f); audit(db, p, "create", "facility", f.id); db.commit()
    return facility_out(f)

@router.get("/facilities")
def list_facilities(db: Session = Depends(get_db),
                    p: Principal = Depends(authenticate),
                    limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    require(p, "read")
    rows = (db.query(Facility).filter_by(org_id=p.org_id)
            .order_by(Facility.id).offset(offset).limit(limit).all())
    total = db.query(Facility).filter_by(org_id=p.org_id).count()
    return {"items": [facility_out(f) for f in rows], "total": total,
            "limit": limit, "offset": offset}

# --- Collection events ------------------------------------------------------
@router.post("/collections", status_code=201)
def create_collection(body: CollectionIn, db: Session = Depends(get_db),
                      p: Principal = Depends(authenticate),
                      idempotency_key: str | None = Header(default=None)):
    require(p, "write")
    asset = db.query(Asset).filter_by(org_id=p.org_id, id=body.asset_id).first()
    if not asset:
        raise HTTPException(422, {"error": "invalid_reference",
                                  "message": "asset_id does not exist in your organization."})
    if idempotency_key:
        prior = db.query(CollectionEvent).filter_by(
            org_id=p.org_id, idempotency_key=idempotency_key).first()
        if prior:
            return {"id": prior.id, "status": prior.status, "idempotent_replay": True}
    ev = CollectionEvent(id=f"col-{uuid.uuid4().hex[:12]}", org_id=p.org_id,
                         idempotency_key=idempotency_key, **body.model_dump())
    db.add(ev); audit(db, p, "create", "collection_event", ev.id); db.commit()
    return {"id": ev.id, "status": ev.status, "idempotent_replay": False,
            "data_status": ev.data_status.value, "quantity_kg": ev.quantity_kg}

@router.get("/collections")
def list_collections(db: Session = Depends(get_db),
                     p: Principal = Depends(authenticate),
                     limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    require(p, "read")
    rows = (db.query(CollectionEvent).filter_by(org_id=p.org_id)
            .order_by(CollectionEvent.id).offset(offset).limit(limit).all())
    return {"items": [{"id": e.id, "asset_id": e.asset_id, "status": e.status,
                       "quantity_kg": e.quantity_kg, "data_status": e.data_status.value,
                       "planned_at": e.planned_at, "occurred_at": e.occurred_at}
                      for e in rows],
            "total": db.query(CollectionEvent).filter_by(org_id=p.org_id).count()}

# --- Route planning ---------------------------------------------------------
@router.post("/routes/plan", status_code=201)
def plan_route(body: RoutePlanIn, db: Session = Depends(get_db),
               p: Principal = Depends(authenticate)):
    require(p, "plan")
    stops = []
    for aid in body.asset_ids:
        a = db.query(Asset).filter_by(org_id=p.org_id, id=aid).first()
        if not a or a.latitude is None or a.longitude is None:
            raise HTTPException(422, {"error": "unplannable_asset",
                "message": f"Asset {aid} is missing or has no location; it cannot be routed."})
        stops.append((a.id, a.latitude, a.longitude))
    plan = intelligence.nearest_neighbour_route(
        (body.depot_latitude, body.depot_longitude), stops)
    rp = RoutePlan(id=f"rte-{uuid.uuid4().hex[:12]}", org_id=p.org_id, name=body.name,
                   stops_json=json.dumps(plan["stops"]),
                   total_distance_km=plan["total_distance_km"])
    db.add(rp); audit(db, p, "plan", "route_plan", rp.id); db.commit()
    return {"id": rp.id, **plan}

# --- Intelligence -----------------------------------------------------------
@router.post("/intelligence/forecast", status_code=201)
def forecast(body: ForecastIn, db: Session = Depends(get_db),
             p: Principal = Depends(authenticate)):
    require(p, "analyse")
    result = intelligence.linear_trend_forecast(body.series, body.horizon)
    run = ForecastRun(id=f"fc-{uuid.uuid4().hex[:12]}", org_id=p.org_id,
                      target=body.target,
                      training_window=f"{len(body.series)} most recent points supplied by caller",
                      predictions_json=json.dumps(result["predictions"]),
                      metrics_json=json.dumps(result["metrics"]),
                      limitations=result["limitations"])
    db.add(run); audit(db, p, "forecast", "forecast_run", run.id); db.commit()
    return {"run_id": run.id, "target": body.target, "data_status": "forecast", **result}

@router.post("/intelligence/anomaly")
def anomaly(body: AnomalyIn, p: Principal = Depends(authenticate)):
    require(p, "analyse")
    return intelligence.zscore_anomalies(body.values, body.z_threshold)

# --- Ingestion ----------------------------------------------------------------
@router.post("/ingestion/assets", status_code=201)
def ingest(body: CsvIngestIn, db: Session = Depends(get_db),
           p: Principal = Depends(authenticate)):
    require(p, "ingest")
    job = ingest_assets(db, p.org_id, body.source, body.records)
    audit(db, p, "ingest", "ingestion_job", job.id); db.commit()
    return {"job_id": job.id, "source": job.source, "status": job.status,
            "records_ok": job.records_ok,
            "records_quarantined": job.records_quarantined, "detail": job.detail}

@router.get("/ingestion/jobs")
def ingestion_jobs(db: Session = Depends(get_db),
                   p: Principal = Depends(authenticate)):
    require(p, "read")
    rows = (db.query(IngestionJob).filter_by(org_id=p.org_id)
            .order_by(IngestionJob.created_at.desc()).limit(50).all())
    return {"items": [{"id": j.id, "source": j.source, "status": j.status,
                       "records_ok": j.records_ok,
                       "records_quarantined": j.records_quarantined,
                       "created_at": j.created_at} for j in rows]}

# --- Copilot ------------------------------------------------------------------
@router.get("/copilot/status")
def copilot_status(p: Principal = Depends(authenticate)):
    require(p, "read")
    return copilot_mod.copilot_status()

@router.get("/copilot/metric-summary")
def metric_summary(db: Session = Depends(get_db),
                   p: Principal = Depends(authenticate)):
    """Deterministic, non-AI summary tool. Labelled as such; never presented
    as a model response."""
    require(p, "read")
    return {"kind": "deterministic_summary", "generated_by": "win-os-api (no model)",
            "org_id": p.org_id,
            "assets": db.query(Asset).filter_by(org_id=p.org_id).count(),
            "facilities": db.query(Facility).filter_by(org_id=p.org_id).count(),
            "collection_events": db.query(CollectionEvent).filter_by(org_id=p.org_id).count(),
            "forecast_runs": db.query(ForecastRun).filter_by(org_id=p.org_id).count()}

# --- WIN Control Center ---------------------------------------------------------
@router.get("/system/status")
def system_status(db: Session = Depends(get_db),
                  p: Principal = Depends(authenticate)):
    require(p, "admin")
    try:
        db.execute(sql_text("SELECT 1")); db_ok = True
    except Exception:
        db_ok = False
    last_job = (db.query(IngestionJob).filter_by(org_id=p.org_id)
                .order_by(IngestionJob.created_at.desc()).first())
    return {"service": "win-os-api", "version": "0.1.0",
            "database": "ok" if db_ok else "unavailable",
            "auth_configured": True,
            "copilot": copilot_mod.copilot_status(),
            "last_ingestion": ({"source": last_job.source, "status": last_job.status,
                                "created_at": last_job.created_at} if last_job else None),
            "health": "healthy" if db_ok else "degraded"}
