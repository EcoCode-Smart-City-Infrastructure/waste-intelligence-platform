"""AI Copilot provider abstraction (directive section 10.4).

Provider-independent: OpenRouter or Groq via environment configuration only.
With no provider key configured the Copilot reports status 'unavailable' and
the platform keeps working; it never pretends a live AI connection exists.
Tools are narrowly scoped and permission-checked by the router layer; the
model gets no shell, no arbitrary SQL, and no destructive capability.
"""
from __future__ import annotations
import os

GUARDED_TOOLS = (
    {"name": "metric_summary", "permission": "read",
     "description": "Counts of assets, facilities and collection events for the caller's organization."},
    {"name": "explain_forecast", "permission": "analyse",
     "description": "Explains a stored forecast run, its metrics and limitations."},
    {"name": "data_quality_summary", "permission": "read",
     "description": "Recent ingestion jobs and quarantine counts for the caller's organization."},
)

def copilot_status() -> dict:
    provider = None
    if os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API"):
        provider = "groq"
    elif os.environ.get("OPENROUTER_API_KEY"):
        provider = "openrouter"
    return {"configured": provider is not None, "provider": provider,
            "status": "available" if provider else "unavailable",
            "tools": [t["name"] for t in GUARDED_TOOLS],
            "note": None if provider else
            "No model provider key configured (GROQ_API_KEY or OPENROUTER_API_KEY). "
            "Deterministic summaries remain available; no AI connection is claimed."}
