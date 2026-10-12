"""Shared HTTP client for NYC Open Data MCP Server.

Provides async HTTP requests with caching, retries, and rate limiting.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
import backoff

from .config import REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

# Shared client instance
_client: aiohttp.ClientSession | None = None
_rate_limit_semaphore: asyncio.Semaphore | None = None

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.environ.get("NYC_OPENDATA_RATE_LIMIT", "10"))
RATE_LIMIT_SECONDS = float(os.environ.get("NYC_OPENDATA_RATE_LIMIT_SECONDS", "1.0"))


async def get_client() -> aiohttp.ClientSession:
    """Get or create the shared HTTP client."""
    global _client, _rate_limit_semaphore
    if _client is None:
        _client = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            # Honor proxy env vars when present (no-op otherwise)
            trust_env=True,
        )
        _rate_limit_semaphore = asyncio.Semaphore(RATE_LIMIT_REQUESTS)
    return _client


@asynccontextmanager
async def _get_client() -> asyncio.AsyncIterator[aiohttp.ClientSession]:
    """Context manager for HTTP client."""
    client = await get_client()
    try:
        yield client
    finally:
        pass  # Don't close here, let close_client() handle it


async def close_client() -> None:
    """Close the shared HTTP client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def _rate_limited_request(
    client: aiohttp.ClientSession,
    method: str,
    url: str,
    **kwargs: Any,
) -> Any:
    """Make a rate-limited HTTP request."""
    global _rate_limit_semaphore
    if _rate_limit_semaphore is None:
        _rate_limit_semaphore = asyncio.Semaphore(RATE_LIMIT_REQUESTS)
    
    async with _rate_limit_semaphore:
        async with client.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()


@backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientError, asyncio.TimeoutError),
    max_tries=3,
    jitter=backoff.full_jitter,
)
async def http_get_json(url: str, params: dict | None = None) -> Any:
    """Make a GET request and return JSON response."""
    client = await get_client()
    return await _rate_limited_request(client, "GET", url, params=params)


@backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientError, asyncio.TimeoutError),
    max_tries=3,
    jitter=backoff.full_jitter,
)
async def http_post_json(url: str, data: dict | None = None) -> Any:
    """Make a POST request and return JSON response."""
    client = await get_client()
    return await _rate_limited_request(client, "POST", url, json=data)


_SOQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def soql_str(value: object) -> str:
    """Quote a value as a SoQL string literal.

    Single quotes are escaped by doubling, which is SoQL's escaping
    rule. Use for every user-supplied string interpolated into $where.
    """
    return "'" + str(value).replace("'", "''") + "'"


def soql_id(identifier: str, allowed: set[str] | frozenset[str] | None = None) -> str:
    """Validate an identifier interpolated into a SoQL query.

    SoQL has no identifier-quoting for $where/$order/$select, so dynamic
    column names must be validated against an allowlist pattern (and,
    when given, an explicit set of permitted names).
    """
    if not _SOQL_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"invalid SoQL identifier: {identifier!r}")
    if allowed is not None and identifier not in allowed:
        raise ValueError(f"unexpected SoQL identifier: {identifier!r}")
    return identifier


async def socrata_request(dataset_id: str, endpoint: str = "json", **params: Any) -> Any:
    """Make a request to Socrata API.
    
    Args:
        dataset_id: Socrata dataset identifier (e.g., "7c3d-6b2j")
        endpoint: API endpoint (default: "json")
        params: Query parameters
        
    Returns:
        JSON response from Socrata API
    """
    from .config import SOCRATA_API_URL
    
    url = f"{SOCRATA_API_URL}/{dataset_id}.{endpoint}"
    
    # Add app_token if available (optional for public datasets)
    app_token = os.environ.get("SOCRATA_APP_TOKEN")
    if app_token:
        params["$$app_token"] = app_token
    
    return await http_get_json(url, params=params)


async def noaa_request(endpoint: str, **params: Any) -> Any:
    """Make a request to NOAA API.
    
    Args:
        endpoint: API endpoint path
        params: Query parameters
        
    Returns:
        JSON response from NOAA API
    """
    from .config import NOAA_BASE_URL
    
    url = f"{NOAA_BASE_URL}/{endpoint}"
    
    # Add User-Agent for NOAA
    headers = {"User-Agent": USER_AGENT}
    
    client = await get_client()
    async with _rate_limit_semaphore:
        async with client.get(url, params=params, headers=headers) as response:
            response.raise_for_status()
            return await response.json()


async def airnow_request(**params: Any) -> Any:
    """Make a request to AirNow API.
    
    Args:
        params: Query parameters
        
    Returns:
        JSON response from AirNow API
    """
    from .config import AIRNOW_API_URL
    
    # Add API key if available
    api_key = os.environ.get("AIRNOW_API_KEY")
    if api_key:
        params["API_KEY"] = api_key
    
    return await http_get_json(AIRNOW_API_URL, params=params)


async def mta_request(endpoint: str, **params: Any) -> Any:
    """Make a request to MTA GTFS-Realtime API.
    
    Args:
        endpoint: API endpoint path
        params: Query parameters
        
    Returns:
        JSON response from MTA API
    """
    from .config import MTA_GTFS_REALTIME_URL
    
    url = f"{MTA_GTFS_REALTIME_URL}/{endpoint}"
    
    # Add API key if available
    api_key = os.environ.get("MTA_API_KEY")
    if api_key:
        params["api_key"] = api_key
    
    return await http_get_json(url, params=params)


async def waste_intel_request(endpoint: str, **params: Any) -> Any:
    """Make a request to Waste Intelligence Platform API.
    
    Args:
        endpoint: API endpoint path
        params: Query parameters
        
    Returns:
        JSON response from Waste Intelligence API
    """
    from .config import WASTE_INTEL_API_URL
    
    url = f"{WASTE_INTEL_API_URL}/{endpoint}"
    
    # Add authentication if available
    api_key = os.environ.get("WASTE_INTEL_API_KEY")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    client = await get_client()
    async with _rate_limit_semaphore:
        async with client.get(url, params=params, headers=headers) as response:
            response.raise_for_status()
            return await response.json()


async def waste_intel_post(endpoint: str, data: dict | None = None) -> Any:
    """Make a POST request to Waste Intelligence Platform API.
    
    Args:
        endpoint: API endpoint path
        data: Request body
        
    Returns:
        JSON response from Waste Intelligence API
    """
    from .config import WASTE_INTEL_API_URL
    
    url = f"{WASTE_INTEL_API_URL}/{endpoint}"
    
    # Add authentication if available
    api_key = os.environ.get("WASTE_INTEL_API_KEY")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    client = await get_client()
    async with _rate_limit_semaphore:
        async with client.post(url, json=data, headers=headers) as response:
            response.raise_for_status()
            return await response.json()
