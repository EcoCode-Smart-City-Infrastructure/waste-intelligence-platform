"""Knowledge Graph client for the Waste Intelligence Platform.

Backed by the in-memory Waste-to-Resource Knowledge Graph (W2RKG) engine in
``cloud_platform.analytics.kg``, loaded from the NYC waste dataset
(``w2rkg_nyc_sample.json``). There is no separate KG microservice to call -
earlier versions of this client POSTed to a ``kg-service`` URL that was
never implemented, so every query fell back to fabricated sample data.

The graph is loaded once per process and cached. Override the dataset with
the ``W2RKG_DATA`` environment variable.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_ENV = "W2RKG_DATA"
_DEFAULT_DATA = (
    Path(__file__).resolve().parents[3]
    / "cloud_platform" / "analytics" / "kg" / "data" / "w2rkg_nyc_sample.json"
)

_engine = None


def _get_engine():
    """Load and cache the W2RKG query engine."""
    global _engine
    if _engine is None:
        from cloud_platform.analytics.kg.kg_loader import KGLoader
        from cloud_platform.analytics.kg.kg_query import KGQueryEngine

        data_path = os.environ.get(_DATA_ENV, str(_DEFAULT_DATA))
        kg = KGLoader().load_json(data_path)
        _engine = KGQueryEngine(kg)
        logger.info(
            "loaded W2RKG graph from %s (%d nodes, %d edges)",
            data_path, len(kg.nodes), len(kg.edges),
        )
    return _engine


def _node_to_result(node) -> dict:
    return {
        "id": node.node_id,
        "label": node.name,
        "type": node.node_type.value,
        "description": node.description or "",
        "score": 1.0,
    }


def _keyword_search(engine, query: str, limit: int) -> list[dict]:
    """Rank nodes by keyword overlap with name + description."""
    terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
    scored = []
    for node in engine.kg.nodes.values():
        text = f"{node.name} {node.description or ''}".lower()
        score = sum(1 for t in terms if t in text)
        # full-phrase bonus
        if query.lower() in text:
            score += 2
        if score:
            result = _node_to_result(node)
            result["score"] = round(score / max(len(terms), 1), 3)
            scored.append((score, result))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [r for _, r in scored[:limit]]


def _find_waste_type_id(engine, waste_type: str) -> str | None:
    """Map a waste-type name to a WasteType node id (fuzzy)."""
    from cloud_platform.analytics.kg.kg_schema import NodeType

    needle = waste_type.lower().strip()
    candidates = [
        n for n in engine.kg.nodes.values() if n.node_type == NodeType.WASTE_TYPE
    ]
    for node in candidates:
        if node.node_id.lower() == needle or node.name.lower() == needle:
            return node.node_id
    for node in candidates:
        if needle in node.name.lower() or needle in node.node_id.lower():
            return node.node_id
    return None



def _parse_limit_offset(query: str, default_limit: int) -> tuple[int, int]:
    """Extract the ``limit N offset M`` the API routes append to listing queries."""
    limit_match = re.search(r"limit (\d+)", query)
    offset_match = re.search(r"offset (\d+)", query)
    return (
        int(limit_match.group(1)) if limit_match else default_limit,
        int(offset_match.group(1)) if offset_match else 0,
    )

def _list_entities(engine, query: str, limit: int) -> list[dict]:
    m = re.search(r"of type ([\w ]+?)(?: limit|$)", query)
    type_filter = m.group(1).strip().upper().replace(" ", "_") if m else None
    limit, offset = _parse_limit_offset(query, limit)
    results = []
    skipped = 0
    for node in engine.kg.nodes.values():
        if type_filter and node.node_type.value.upper() != type_filter:
            continue
        if skipped < offset:
            skipped += 1
            continue
        results.append(_node_to_result(node))
        if len(results) >= limit:
            break
    return results


def _list_relationships(engine, query: str, limit: int) -> list[dict]:
    source = re.search(r"from ([\w ]+?)(?: to | of type | limit|$)", query)
    target = re.search(r" to ([\w ]+?)(?: of type | limit|$)", query)
    rtype = re.search(r"of type ([\w ]+?)(?: limit|$)", query)
    limit, offset = _parse_limit_offset(query, limit)
    results = []
    skipped = 0
    for edge in engine.kg.edges:
        if source and edge.source_id.lower() != source.group(1).strip().lower():
            continue
        if target and edge.target_id.lower() != target.group(1).strip().lower():
            continue
        if rtype and edge.edge_type.value.upper() != rtype.group(1).strip().upper().replace(" ", "_"):
            continue
        if skipped < offset:
            skipped += 1
            continue
        results.append({
            "id": edge.edge_id,
            "source": edge.source_id,
            "target": edge.target_id,
            "type": edge.edge_type.value,
        })
        if len(results) >= limit:
            break
    return results


async def query_kg(
    query: str, query_type: str = "natural_language", limit: int = 10
) -> dict:
    """Query the Waste-to-Resource Knowledge Graph.

    Args:
        query: Query string (keywords, a MATCH cypher query, or one of the
            ``list all entities`` / ``list all relationships`` listings the
            API routes build).
        query_type: ``natural_language``, ``sparql`` (answered by keyword
            search - the engine has no SPARQL parser), or ``cypher``.
        limit: Maximum number of results.

    Returns:
        Dict with ``query``, ``results``, ``answer``, ``execution_time``
        and ``data_source``. ``results`` is empty (not fabricated) when
        nothing matches.
    """
    started = time.perf_counter()
    try:
        engine = _get_engine()
    except Exception as exc:  # noqa: BLE001 - KG must never break the API
        logger.error("failed to load W2RKG graph: %s", exc)
        return {
            "query": query,
            "results": [],
            "answer": f"Knowledge graph unavailable: {exc}",
            "execution_time": round(time.perf_counter() - started, 3),
            "data_source": "w2rkg-unavailable",
        }

    ql = query.strip().lower()
    try:
        if query_type == "cypher" or ql.startswith("match "):
            raw = engine.query_graph(query.strip())
            results = raw[:limit]
            answer = f"{len(results)} graph results"
        elif ql.startswith("list all relationships"):
            results = _list_relationships(engine, ql, limit)
            answer = f"{len(results)} relationships"
        elif ql.startswith("list all entities"):
            results = _list_entities(engine, ql, limit)
            answer = f"{len(results)} entities"
        else:
            # natural_language and sparql: keyword search over the graph
            results = _keyword_search(engine, query, limit)
            answer = (
                f"{len(results)} matching entities"
                if results
                else "no matching entities in the knowledge graph"
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("KG query failed: %s", exc)
        results, answer = [], f"query failed: {exc}"

    return {
        "query": query,
        "results": results,
        "answer": answer,
        "execution_time": round(time.perf_counter() - started, 3),
        "data_source": "w2rkg-in-memory",
    }


async def query_pathways(
    waste_type: str, quantity_kg: float, limit: int = 5
) -> list[dict]:
    """Waste-to-resource pathway suggestions for a waste type and quantity.

    Returns suggestion dicts shaped for the ``/circular_economy`` route:
    ``pathway``, ``type``, ``description``, ``efficiency``,
    ``carbon_footprint``, ``facilities``.
    """
    try:
        engine = _get_engine()
    except Exception as exc:  # noqa: BLE001
        logger.error("failed to load W2RKG graph: %s", exc)
        return []

    node_id = _find_waste_type_id(engine, waste_type)
    if not node_id:
        logger.info("no waste type matching %r in the knowledge graph", waste_type)
        return []

    suggestions = []
    for pathway in engine.get_top_resource_pathways(
        node_id, quantity_kg=quantity_kg, max_results=limit
    ):
        data = pathway.to_dict()
        suggestions.append({
            "pathway": data.get("process", "Unknown"),
            "type": "waste-to-resource",
            "description": (
                f"{data.get('waste_type', '')} -> {data.get('process', '')} "
                f"-> {data.get('resource', '')}"
            ),
            "efficiency": data.get("efficiency", 0),
            "carbon_footprint": data.get("carbon_footprint", 0),
            "facilities": data.get("facilities", []),
            "economic_value": data.get("economic_value", 0),
        })
    return suggestions


# Backwards-compatible alias for the old HTTP-client name.
async def query_kg_service(*args: Any, **kwargs: Any) -> dict:
    return await query_kg(*args, **kwargs)
