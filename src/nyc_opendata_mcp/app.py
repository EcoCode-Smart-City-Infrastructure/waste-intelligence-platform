"""Shared MCPServer instance for NYC Open Data MCP Server.

Lives in its own module so tool/resource modules can import it without
creating a cycle through ``server.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer

from .config import PACKAGE_VERSION, REPO_URL
from .http_client import close_client


@asynccontextmanager
async def _lifespan(_server: MCPServer) -> AsyncIterator[None]:
    """Close the shared HTTP client's connection pool on server shutdown."""
    try:
        yield
    finally:
        await close_client()


# Cache configuration for list methods
LIST_CACHE_TTL_MS = 300_000

CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "resources/templates/list": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
    "server/discover": CacheHint(ttl_ms=LIST_CACHE_TTL_MS, scope="public"),
}

# Server metadata
SERVER_TITLE = "New York City Open Data"
SERVER_DESCRIPTION = (
    "Open data for New York City: datasets, geodata, government, "
    "environmental feeds, mobility data, and Waste Intelligence Platform integration."
)

SERVER_INSTRUCTIONS = """\
Open data for New York City from public APIs, without API keys (except where noted).

Entry point for tabular data is through dataset search: `nyc_search_datasets`
finds datasets, `nyc_get_dataset` returns resource IDs, and then
`nyc_datastore_query` and `nyc_datastore_sql` work with those resource IDs.

Real-time tools (weather, air quality, water quality, pedestrians, MTA ridership,
parking) provide live measurements with timestamps. Always cite the timestamp
and do not treat values as current beyond the request.

Waste Intelligence Platform tools provide real-time telemetry, ML forecasting,
and knowledge graph queries for NYC waste management operations.

All tools are prefixed with `nyc_` to distinguish them from other MCP servers.
"""

mcp = MCPServer(
    "nyc_opendata_mcp",
    title=SERVER_TITLE,
    description=SERVER_DESCRIPTION,
    instructions=SERVER_INSTRUCTIONS,
    website_url=REPO_URL,
    version=PACKAGE_VERSION,
    lifespan=_lifespan,
    cache_hints=CACHE_HINTS,
)
