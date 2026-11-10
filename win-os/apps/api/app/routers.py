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
from . import accounting
from . import copilot as copilot_mod
from . import intelligence
from .db import get_db
from .ingestion import ingest_assets
from .models import (Asset, AuditEvent, CollectionEvent, Device, EnvironmentalRecord,
                     Facility, ForecastRun, IngestionJob, RecoveryPathway, RoutePlan,
                     Scenario, TelemetryEvent, Vehicle, WasteStream)
from .schemas import (AnomalyIn, AssetIn, CollectionIn, CsvIngestIn, DeviceIn,
                      EnvironmentalIn, FacilityIn, ForecastIn, RecoveryPathwayIn,
                      RoutePlanIn, ScenarioIn, TelemetryBatchIn, VehicleIn,
                      WasteStreamIn)
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
    return {"service": "win-os-api", "version": "0.2.0",
            "database": "ok" if db_ok else "unavailable",
            "auth_configured": True,
            "copilot": copilot_mod.copilot_status(),
            "last_ingestion": ({"source": last_job.source, "status": last_job.status,
                                "created_at": last_job.created_at} if last_job else None),
            "health": "healthy" if db_ok else "degraded"}


# --- Vehicles and fleets (Phase 6) -----------------------------------------
@router.post("/vehicles", status_code=201)
def create_vehicle(body: VehicleIn, db: Session = Depends(get_db),
                   p: Principal = Depends(authenticate)):
    require(p, "write")
    v = Vehicle(id=f"veh-{uuid.uuid4().hex[:12]}", org_id=p.org_id, **body.model_dump())
    db.add(v); audit(db, p, "create", "vehicle", v.id); db.commit()
    return {"id": v.id, "org_id": v.org_id, "name": v.name,
            "vehicle_type": v.vehicle_type, "status": v.status,
            "capacity_kg": v.capacity_kg, "fuel_type": v.fuel_type,
            "fleet_name": v.fleet_name, "data_status": v.data_status.value}

@router.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db), p: Principal = Depends(authenticate),
                  fleet: str | None = None, limit: int = Query(50, ge=1, le=500),
                  offset: int = Query(0, ge=0)):
    require(p, "read")
    q = db.query(Vehicle).filter_by(org_id=p.org_id)
    if fleet:
        q = q.filter_by(fleet_name=fleet)
    rows = q.order_by(Vehicle.id).offset(offset).limit(limit).all()
    return {"items": [{"id": v.id, "name": v.name, "vehicle_type": v.vehicle_type,
                       "status": v.status, "capacity_kg": v.capacity_kg,
                       "fleet_name": v.fleet_name} for v in rows],
            "total": q.count()}

# --- Waste streams and recovery pathways (Phase 6) ---------------------------
@router.post("/waste-streams", status_code=201)
def create_stream(body: WasteStreamIn, db: Session = Depends(get_db),
                  p: Principal = Depends(authenticate)):
    require(p, "write")
    s = WasteStream(id=f"str-{uuid.uuid4().hex[:12]}", org_id=p.org_id, **body.model_dump())
    db.add(s); audit(db, p, "create", "waste_stream", s.id); db.commit()
    return {"id": s.id, "org_id": s.org_id, "name": s.name, "category": s.category,
            "material": s.material, "data_status": s.data_status.value}

@router.get("/waste-streams")
def list_streams(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    require(p, "read")
    rows = db.query(WasteStream).filter_by(org_id=p.org_id).order_by(WasteStream.id).all()
    return {"items": [{"id": s.id, "name": s.name, "category": s.category,
                       "material": s.material} for s in rows], "total": len(rows)}

@router.post("/recovery-pathways", status_code=201)
def create_pathway(body: RecoveryPathwayIn, db: Session = Depends(get_db),
                   p: Principal = Depends(authenticate)):
    require(p, "write")
    if not db.query(WasteStream).filter_by(org_id=p.org_id, id=body.waste_stream_id).first():
        raise HTTPException(422, {"error": "invalid_reference",
                                  "message": "waste_stream_id does not exist in your organization."})
    if not db.query(Facility).filter_by(org_id=p.org_id, id=body.facility_id).first():
        raise HTTPException(422, {"error": "invalid_reference",
                                  "message": "facility_id does not exist in your organization."})
    rp = RecoveryPathway(id=f"pat-{uuid.uuid4().hex[:12]}", org_id=p.org_id,
                         **body.model_dump())
    db.add(rp); audit(db, p, "create", "recovery_pathway", rp.id); db.commit()
    return {"id": rp.id, "waste_stream_id": rp.waste_stream_id,
            "facility_id": rp.facility_id, "pathway_type": rp.pathway_type,
            "diversion_rate_pct": rp.diversion_rate_pct,
            "diversion_status": "reported" if rp.diversion_rate_pct is not None else "unavailable"}

@router.get("/recovery-pathways")
def list_pathways(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    require(p, "read")
    rows = db.query(RecoveryPathway).filter_by(org_id=p.org_id).all()
    return {"items": [{"id": r.id, "waste_stream_id": r.waste_stream_id,
                       "facility_id": r.facility_id, "pathway_type": r.pathway_type,
                       "diversion_rate_pct": r.diversion_rate_pct} for r in rows],
            "total": len(rows)}

# --- Environmental accounting (Phase 6) --------------------------------------
@router.post("/environmental/records", status_code=201)
def create_env_record(body: EnvironmentalIn, db: Session = Depends(get_db),
                      p: Principal = Depends(authenticate)):
    require(p, "write")
    try:
        calc = accounting.compute_co2e(body.material, body.pathway_type, body.quantity_kg)
    except ValueError as exc:
        raise HTTPException(422, {"error": "no_factor", "message": str(exc)})
    rec = EnvironmentalRecord(
        id=f"env-{uuid.uuid4().hex[:12]}", org_id=p.org_id,
        material=calc["material"], pathway_type=calc["pathway_type"],
        quantity_kg=calc["quantity_kg"], co2e_kg=calc["co2e_kg"],
        formula=calc["formula"], methodology_version=calc["methodology_version"],
        assumptions=calc["assumptions"])
    db.add(rec); audit(db, p, "create", "environmental_record", rec.id); db.commit()
    return {"id": rec.id, **calc}

@router.get("/environmental/summary")
def env_summary(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    """Totals stay separated by data_status: derived estimates are never
    merged with simulated scenario numbers."""
    require(p, "read")
    out = {}
    for status in ("derived", "simulated", "observed", "reported"):
        rows = (db.query(EnvironmentalRecord)
                .filter_by(org_id=p.org_id, data_status=status).all())
        if rows:
            out[status] = {"records": len(rows),
                           "quantity_kg": round(sum(r.quantity_kg for r in rows), 3),
                           "co2e_kg": round(sum(r.co2e_kg for r in rows), 3)}
    return {"org_id": p.org_id, "by_data_status": out,
            "methodology_version": accounting.METHODOLOGY_VERSION,
            "note": "Derived planning estimates (WIN-ENV-ACCT), not verified emissions outcomes."}

# --- Data quality (Phase 6/8) --------------------------------------------------
@router.get("/data-quality/summary")
def data_quality(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    require(p, "read")
    from datetime import datetime, timezone
    def status_counts(model):
        out = {}
        for row in db.query(model).filter_by(org_id=p.org_id).all():
            key = row.data_status.value
            out[key] = out.get(key, 0) + 1
        return out
    jobs = (db.query(IngestionJob).filter_by(org_id=p.org_id)
            .order_by(IngestionJob.created_at.desc()).all())
    sources = {}
    for j in jobs:
        if j.source not in sources:
            sources[j.source] = {"last_success_at": j.created_at,
                                 "records_ok": j.records_ok,
                                 "records_quarantined": j.records_quarantined}
    return {"org_id": p.org_id,
            "assets_by_status": status_counts(Asset),
            "facilities_by_status": status_counts(Facility),
            "collections_by_status": status_counts(CollectionEvent),
            "ingestion": {
                "jobs": len(jobs),
                "records_quarantined_total": sum(j.records_quarantined for j in jobs),
                "sources": sources},
            "checked_at": datetime.now(timezone.utc)}

# --- Devices and telemetry (Phase 9, WIN Edge) ---------------------------------
@router.post("/devices", status_code=201)
def register_device(body: DeviceIn, db: Session = Depends(get_db),
                    p: Principal = Depends(authenticate)):
    require(p, "write")
    prior = db.query(Device).filter_by(org_id=p.org_id, device_id=body.device_id).first()
    if prior:
        return {"id": prior.id, "device_id": prior.device_id, "already_registered": True}
    d = Device(id=f"dev-{uuid.uuid4().hex[:12]}", org_id=p.org_id, **body.model_dump())
    db.add(d); audit(db, p, "register", "device", d.id); db.commit()
    return {"id": d.id, "device_id": d.device_id, "already_registered": False,
            "telemetry_status": "unavailable"}

@router.get("/devices")
def list_devices(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    require(p, "read")
    rows = db.query(Device).filter_by(org_id=p.org_id).order_by(Device.device_id).all()
    return {"items": [{"device_id": d.device_id, "asset_id": d.asset_id,
                       "firmware_version": d.firmware_version,
                       "last_seen_at": d.last_seen_at,
                       "telemetry_status": "reported" if d.last_seen_at else "unavailable"}
                      for d in rows], "total": len(rows)}

@router.post("/telemetry/events", status_code=201)
def ingest_telemetry(body: TelemetryBatchIn, db: Session = Depends(get_db),
                     p: Principal = Depends(authenticate)):
    """Store-and-forward friendly: batch ingest, idempotent per
    (org, device, client_event_id). Unregistered devices are quarantined,
    never silently accepted."""
    require(p, "ingest")
    accepted, replays, quarantined = 0, 0, 0
    for ev in body.events:
        device = db.query(Device).filter_by(org_id=p.org_id, device_id=ev.device_id).first()
        if not device:
            quarantined += 1
            continue
        prior = db.query(TelemetryEvent).filter_by(
            org_id=p.org_id, device_id=ev.device_id,
            client_event_id=ev.client_event_id).first()
        if prior:
            replays += 1
            continue
        db.add(TelemetryEvent(org_id=p.org_id, **ev.model_dump()))
        if device.last_seen_at is None:
            device.last_seen_at = ev.observed_at
        else:
            from datetime import timezone as _tz
            def _ts(dt):
                return dt.timestamp() if dt.tzinfo else dt.replace(tzinfo=_tz.utc).timestamp()
            if _ts(ev.observed_at) >= _ts(device.last_seen_at):
                device.last_seen_at = ev.observed_at
        db.flush()
        accepted += 1
    db.commit()
    return {"accepted": accepted, "idempotent_replays": replays,
            "quarantined_unregistered_device": quarantined}

@router.get("/telemetry/events")
def list_telemetry(db: Session = Depends(get_db), p: Principal = Depends(authenticate),
                   device_id: str | None = None,
                   limit: int = Query(50, ge=1, le=500)):
    require(p, "read")
    q = db.query(TelemetryEvent).filter_by(org_id=p.org_id)
    if device_id:
        q = q.filter_by(device_id=device_id)
    rows = q.order_by(TelemetryEvent.observed_at.desc()).limit(limit).all()
    return {"items": [{"device_id": e.device_id, "client_event_id": e.client_event_id,
                       "observed_at": e.observed_at, "received_at": e.received_at,
                       "buffered_offline": e.buffered_offline,
                       "fill_level_percent": e.fill_level_percent,
                       "weight_kg": e.weight_kg,
                       "data_status": e.data_status.value} for e in rows],
            "total": len(rows)}

# --- Simulation / digital twin scenarios (Phase 9) -------------------------------
@router.post("/simulations", status_code=201)
def run_scenario(body: ScenarioIn, db: Session = Depends(get_db),
                 p: Principal = Depends(authenticate)):
    require(p, "analyse")
    try:
        calc = accounting.compute_co2e(body.material, body.pathway_type, body.total_kg)
    except ValueError as exc:
        raise HTTPException(422, {"error": "no_factor", "message": str(exc)})
    factor = calc["factor_kg_co2e_per_kg"]
    current_kg = body.total_kg * body.current_diversion_pct / 100.0
    target_kg = body.total_kg * body.target_diversion_pct / 100.0
    results = {
        "current_diverted_kg": round(current_kg, 3),
        "target_diverted_kg": round(target_kg, 3),
        "additional_diverted_kg": round(target_kg - current_kg, 3),
        "current_co2e_avoided_kg": round(current_kg * factor, 3),
        "target_co2e_avoided_kg": round(target_kg * factor, 3),
        "data_status": "simulated",
        "note": "Scenario projection only. Not an observed or verified outcome."}
    sc = Scenario(id=f"scn-{uuid.uuid4().hex[:12]}", org_id=p.org_id, name=body.name,
                  params_json=json.dumps(body.model_dump()),
                  results_json=json.dumps(results))
    db.add(sc); audit(db, p, "simulate", "scenario", sc.id); db.commit()
    return {"id": sc.id, "name": sc.name, "results": results,
            "factor": calc}

@router.get("/simulations")
def list_scenarios(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    require(p, "read")
    rows = db.query(Scenario).filter_by(org_id=p.org_id).order_by(Scenario.created_at.desc()).all()
    return {"items": [{"id": s.id, "name": s.name, "data_status": s.data_status.value,
                       "results": json.loads(s.results_json)} for s in rows],
            "total": len(rows)}

# --- Control Center expansion (Phase 8) ------------------------------------------
@router.get("/system/jobs")
def system_jobs(db: Session = Depends(get_db), p: Principal = Depends(authenticate)):
    require(p, "admin")
    ing = (db.query(IngestionJob).filter_by(org_id=p.org_id)
           .order_by(IngestionJob.created_at.desc()).limit(20).all())
    fc = (db.query(ForecastRun).filter_by(org_id=p.org_id)
          .order_by(ForecastRun.created_at.desc()).limit(20).all())
    tel = db.query(TelemetryEvent).filter_by(org_id=p.org_id).count()
    devices = db.query(Device).filter_by(org_id=p.org_id).all()
    return {"ingestion_jobs": [{"id": j.id, "source": j.source, "status": j.status,
                                "records_ok": j.records_ok,
                                "records_quarantined": j.records_quarantined,
                                "created_at": j.created_at} for j in ing],
            "forecast_runs": [{"id": f.id, "target": f.target, "model_id": f.model_id,
                               "model_version": f.model_version,
                               "created_at": f.created_at} for f in fc],
            "telemetry_events": tel,
            "devices": {"registered": len(devices),
                        "never_reported": sum(1 for d in devices if not d.last_seen_at)}}
