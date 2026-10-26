"""Knowledge Graph microservice (kg-service, :8003).

This service was referenced by docker-compose.yml (KG_URL /
KG_API_URL) and by earlier clients, but never implemented — every
caller fell back to in-memory or sample data. This implements it for
real on the repo's own W2RKG engine (cloud_platform/analytics/kg),
loaded from the NYC sample dataset (override with KG_DATA).

Endpoints (chosen to match what callers already POST):
  GET  /health            liveness + node/edge counts
  POST /kg                {query, limit} -> matching nodes + edges
  GET  /kg/nodes          ?type=&limit=  node listing
  POST /kg/pathways       {waste_type_id, quantity_kg, max_results}
                          -> top resource pathways for a waste type
CORS is env-driven (CORS_ORIGINS); the GitHub Pages origin is in the
defaults so the web app can call this service from the browser.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "https://ecocode-smart-city-infrastructure.github.io,http://localhost:3000,http://localhost:8080",
).split(",") if o.strip()]

app = FastAPI(title="Waste Knowledge Graph Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=("*" not in _CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)

_DEFAULT_DATA = (
    Path(__file__).resolve().parents[2]
    / "cloud_platform" / "analytics" / "kg" / "data" / "w2rkg_nyc_sample.json"
)


class KGQueryRequest(BaseModel):
    query: str
    limit: int = 10


class PathwayRequest(BaseModel):
    waste_type_id: str
    quantity_kg: float = 1000.0
    max_results: int = 3


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from cloud_platform.analytics.kg.kg_loader import KGLoader
        from cloud_platform.analytics.kg.kg_query import KGQueryEngine

        data_path = os.environ.get("KG_DATA", str(_DEFAULT_DATA))
        loader = KGLoader()
        kg = loader.load_json(data_path)
        _engine = KGQueryEngine(kg)
        logger.info("KG loaded: %d nodes, %d edges from %s",
                    len(kg.nodes), len(kg.edges), data_path)
    return _engine


def _node_dict(node):
    d = {"id": getattr(node, "node_id", getattr(node, "id", "?")), "name": node.name,
         "type": node.node_type.name if hasattr(node.node_type, "name") else str(node.node_type)}
    props = getattr(node, "properties", None) or {}
    if isinstance(props, dict):
        d.update({k: v for k, v in props.items() if k not in d})
    for attr in ("description", "capacity", "demand"):
        v = getattr(node, attr, None)
        if v is not None:
            d[attr] = v
    return d


def _edge_dict(edge):
    d = {"id": getattr(edge, "edge_id", getattr(edge, "id", "?")), "source_id": edge.source_id, "target_id": edge.target_id,
         "type": edge.edge_type.name if hasattr(edge.edge_type, "name") else str(edge.edge_type)}
    props = getattr(edge, "properties", None) or {}
    if isinstance(props, dict):
        d.update({k: v for k, v in props.items() if k not in d})
    return d


@app.get("/health")
def health():
    engine = _get_engine()
    return {"status": "ok", "service": "kg-service",
            "nodes": len(engine.kg.nodes), "edges": len(engine.kg.edges)}


@app.post("/kg")
def kg_query(req: KGQueryRequest):
    t0 = time.time()
    engine = _get_engine()
    q = (req.query or "").strip().lower()
    if not q:
        raise HTTPException(422, "query is required")
    matched = []
    for node in engine.kg.nodes.values():
        nid = getattr(node, "node_id", getattr(node, "id", ""))
        if q in str(nid).lower() or q in node.name.lower():
            neighbours = [_edge_dict(e) for e in engine._edges_by_source.get(nid, [])]
            matched.append({"node": _node_dict(node), "outgoing_edges": neighbours})
        if len(matched) >= max(1, req.limit):
            break
    return JSONResponse({"query": req.query, "results": matched,
                         "execution_time": round(time.time() - t0, 3)})


@app.get("/kg/nodes")
def kg_nodes(type: str | None = None, limit: int = 50):
    engine = _get_engine()
    nodes = list(engine.kg.nodes.values())
    if type:
        nodes = [n for n in nodes
                 if type.lower() in str(getattr(n.node_type, "name", n.node_type)).lower()]
    return {"nodes": [_node_dict(n) for n in nodes[:max(1, limit)]],
            "count": len(nodes)}


@app.post("/kg/pathways")
def kg_pathways(req: PathwayRequest):
    from cloud_platform.analytics.kg.kg_query import get_top_pathways

    engine = _get_engine()
    try:
        pathways = get_top_pathways(engine.kg, req.waste_type_id,
                                    req.quantity_kg, req.max_results)
    except Exception as e:
        raise HTTPException(422, f"pathway lookup failed: {e}")
    return {"waste_type_id": req.waste_type_id,
            "quantity_kg": req.quantity_kg,
            "pathways": [p.to_dict() for p in pathways]}
