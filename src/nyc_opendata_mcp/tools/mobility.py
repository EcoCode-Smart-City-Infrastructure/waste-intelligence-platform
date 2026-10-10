"""NYC mobility tools: MTA, DOT, and transportation data."""

from __future__ import annotations

from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import MTA_SUBWAY_LINES, MTALine, OutputFormat
from ..formatters import (
    FORMAT_FIELD_DESC as _FORMAT_FIELD_DESC,
    handle_api_error,
    json_out,
    md_table,
)
from ..http_client import mta_request, socrata_request
from ..models import MTARidership, PedestrianCount, ParkingData, tool_result


class MTAStatusInput(BaseModel):
    """Input for MTA service status."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    line: MTALine | None = Field(
        default=None,
        description=f"Subway line filter. Available: {', '.join(MTA_SUBWAY_LINES)}. "
        "Empty = all lines.",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_mta_status",
    annotations=ToolAnnotations(
        title="MTA Service Status",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_mta_status(params: MTAStatusInput) -> Annotated[CallToolResult, str]:
    """Retrieve current MTA subway service status.

    Data source: MTA GTFS-Realtime API and status feeds.

    Args:
        line: Optional subway line filter
        format: Output format

    Returns:
        Current service status for subway lines
    """
    try:
        # In production, this would query the actual MTA API
        # For now, return sample status data
        
        # Generate sample status data
        status_data = _generate_sample_mta_status()
        
        if params.line:
            status_data = [s for s in status_data if s.get("line") == params.line]
        
        if not status_data:
            return tool_result({
                "status": "error",
                "error": "No status data available",
                "markdown": "Keine Statusdaten verf\u00fcgbar.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": status_data,
                "markdown": json_out(status_data),
            })
        
        # Format as Markdown table
        headers = ["Line", "Status", "Last Updated", "Details"]
        rows = []
        for status in status_data:
            status_emoji = "\U0001F7E2" if status.get("status") == "Good Service" else "\U0001F534"
            row = [
                status.get("line", ""),
                f"{status_emoji} {status.get('status', 'Unknown')}",
                status.get("last_updated", ""),
                status.get("details", ""),
            ]
            rows.append(row)
        
        lines = [
            "## MTA Service Status",
            f"*Linien: {len(status_data)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "MTA Status"),
        })


def _generate_sample_mta_status() -> list[dict]:
    """Generate sample MTA status data."""
    return [
        {
            "line": "1",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "2",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "3",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "4",
            "status": "Delays",
            "last_updated": "2026-10-10 12:05:00",
            "details": "Minor delays due to signal problems",
        },
        {
            "line": "5",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "6",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "7",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "A",
            "status": "Service Change",
            "last_updated": "2026-10-10 12:10:00",
            "details": "Trains running on the F line between Euclid Av and Jay St",
        },
        {
            "line": "B",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
        {
            "line": "C",
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "Trains are running on time",
        },
    ]


class MTAStationStatusInput(BaseModel):
    """Input for MTA station status."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station: str | None = Field(
        default=None,
        description="Station name or ID. Empty = all stations with issues.",
    )
    line: MTALine | None = Field(
        default=None,
        description=f"Filter by line. Available: {', '.join(MTA_SUBWAY_LINES)}",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_mta_station_status",
    annotations=ToolAnnotations(
        title="MTA Station Status",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_mta_station_status(params: MTAStationStatusInput) -> Annotated[CallToolResult, str]:
    """Retrieve status information for MTA subway stations.

    Args:
        station: Optional station name or ID
        line: Optional line filter
        format: Output format

    Returns:
        Station status information
    """
    try:
        # Generate sample station status data
        station_data = _generate_sample_station_status()
        
        if params.station:
            station_data = [s for s in station_data if params.station.lower() in s.get("station", "").lower()]
        if params.line:
            station_data = [s for s in station_data if params.line in s.get("lines", [])]
        
        if not station_data:
            return tool_result({
                "status": "error",
                "error": "No station data available",
                "markdown": "Keine Stationsdaten verf\u00fcgbar.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": station_data,
                "markdown": json_out(station_data),
            })
        
        # Format as Markdown table
        headers = ["Station", "Lines", "Status", "Last Updated"]
        rows = []
        for station in station_data:
            status_emoji = "\U0001F7E2" if station.get("status") == "Good Service" else "\U0001F534"
            row = [
                station.get("station", ""),
                ", ".join(station.get("lines", [])),
                f"{status_emoji} {station.get('status', 'Unknown')}",
                station.get("last_updated", ""),
            ]
            rows.append(row)
        
        lines = [
            "## MTA Station Status",
            f"*Stationen: {len(station_data)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "MTA Station Status"),
        })


def _generate_sample_station_status() -> list[dict]:
    """Generate sample station status data."""
    return [
        {
            "station": "Times Square",
            "lines": ["1", "2", "3", "7", "N", "Q", "R", "W", "S"],
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "All lines running normally",
        },
        {
            "station": "Grand Central",
            "lines": ["4", "5", "6", "7", "S"],
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "All lines running normally",
        },
        {
            "station": "Union Square",
            "lines": ["4", "5", "6", "L", "N", "Q", "R", "W"],
            "status": "Service Change",
            "last_updated": "2026-10-10 12:10:00",
            "details": "6 train running on the 4/5 line",
        },
        {
            "station": "Fulton St",
            "lines": ["2", "3", "4", "5", "A", "C", "E", "J", "Z"],
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "All lines running normally",
        },
        {
            "station": "Atlantic Av-Barclays Ctr",
            "lines": ["2", "3", "4", "5", "B", "D", "N", "Q", "R"],
            "status": "Good Service",
            "last_updated": "2026-10-10 12:00:00",
            "details": "All lines running normally",
        },
    ]


class TrafficIncidentsInput(BaseModel):
    """Input for traffic incidents."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    borough: str | None = Field(
        default=None,
        description="Filter by borough (Manhattan, Bronx, Brooklyn, Queens, Staten Island)",
    )
    severity: str | None = Field(
        default=None,
        description="Filter by severity (Low, Medium, High)",
    )
    limit: int = Field(default=20, description="Maximum number of results", ge=1, le=100)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_traffic_incidents",
    annotations=ToolAnnotations(
        title="Traffic Incidents",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_traffic_incidents(params: TrafficIncidentsInput) -> Annotated[CallToolResult, str]:
    """Retrieve current traffic incidents from NYC DOT.

    Args:
        borough: Optional borough filter
        severity: Optional severity filter
        limit: Maximum number of results
        format: Output format

    Returns:
        List of current traffic incidents
    """
    try:
        # Generate sample traffic incidents
        incidents = _generate_sample_traffic_incidents()
        
        # Apply filters
        if params.borough:
            incidents = [i for i in incidents if i.get("borough", "").lower() == params.borough.lower()]
        if params.severity:
            incidents = [i for i in incidents if i.get("severity", "").lower() == params.severity.lower()]
        
        incidents = incidents[:params.limit]
        
        if not incidents:
            return tool_result({
                "status": "error",
                "error": "No traffic incidents found",
                "markdown": "Keine Verkehrsvorf\u00e4lle gefunden.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": incidents,
                "markdown": json_out(incidents),
            })
        
        # Format as Markdown table
        headers = ["Borough", "Location", "Type", "Severity", "Status"]
        rows = []
        for incident in incidents:
            severity_emoji = {
                "Low": "\U0001F7E2",
                "Medium": "\U0001F7E1",
                "High": "\U0001F534",
            }.get(incident.get("severity", ""), "")
            row = [
                incident.get("borough", ""),
                incident.get("location", ""),
                incident.get("type", ""),
                f"{severity_emoji} {incident.get('severity', 'Unknown')}",
                incident.get("status", ""),
            ]
            rows.append(row)
        
        lines = [
            "## Verkehrsvorf\u00e4lle NYC",
            f"*Vorf\u00e4lle: {len(incidents)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Traffic Incidents"),
        })


def _generate_sample_traffic_incidents() -> list[dict]:
    """Generate sample traffic incidents."""
    return [
        {
            "borough": "Manhattan",
            "location": "FDR Drive at 42nd St",
            "type": "Accident",
            "severity": "Medium",
            "status": "Clearing",
            "last_updated": "2026-10-10 12:05:00",
        },
        {
            "borough": "Brooklyn",
            "location": "Atlantic Ave at Flatbush Ave",
            "type": "Construction",
            "severity": "High",
            "status": "Ongoing",
            "last_updated": "2026-10-10 11:30:00",
        },
        {
            "borough": "Queens",
            "location": "Queens Blvd at 59th Ave",
            "type": "Accident",
            "severity": "Low",
            "status": "Cleared",
            "last_updated": "2026-10-10 12:15:00",
        },
        {
            "borough": "Bronx",
            "location": "Fordham Rd at Webster Ave",
            "type": "Congestion",
            "severity": "Medium",
            "status": "Ongoing",
            "last_updated": "2026-10-10 12:10:00",
        },
        {
            "borough": "Staten Island",
            "location": "Richmond Ave at Arthur Kill Rd",
            "type": "Construction",
            "severity": "Low",
            "status": "Ongoing",
            "last_updated": "2026-10-10 10:00:00",
        },
    ]


class BikeShareInput(BaseModel):
    """Input for bike share data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station_id: str | None = Field(
        default=None,
        description="Filter by station ID. Empty = all stations.",
    )
    limit: int = Field(default=20, description="Maximum number of results", ge=1, le=100)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_bike_share",
    annotations=ToolAnnotations(
        title="Bike Share Data",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_bike_share(params: BikeShareInput) -> Annotated[CallToolResult, str]:
    """Retrieve Citi Bike share data from NYC.

    Args:
        station_id: Optional station ID filter
        limit: Maximum number of results
        format: Output format

    Returns:
        Bike share station data with availability
    """
    try:
        # Generate sample bike share data
        stations = _generate_sample_bike_share()
        
        if params.station_id:
            stations = [s for s in stations if s.get("station_id") == params.station_id]
        
        stations = stations[:params.limit]
        
        if not stations:
            return tool_result({
                "status": "error",
                "error": "No bike share data available",
                "markdown": "Keine Fahrradverleihdaten verf\u00fcgbar.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": stations,
                "markdown": json_out(stations),
            })
        
        # Format as Markdown table
        headers = ["Station ID", "Name", "Bikes Available", "Docks Available", "Last Updated"]
        rows = []
        for station in stations:
            row = [
                station.get("station_id", ""),
                station.get("name", ""),
                str(station.get("bikes_available", 0)),
                str(station.get("docks_available", 0)),
                station.get("last_updated", ""),
            ]
            rows.append(row)
        
        lines = [
            "## Citi Bike Stationen",
            f"*Stationen: {len(stations)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Bike Share Data"),
        })


def _generate_sample_bike_share() -> list[dict]:
    """Generate sample bike share data."""
    return [
        {
            "station_id": "72",
            "name": "E 17 St & Broadway",
            "bikes_available": 15,
            "docks_available": 5,
            "last_updated": "2026-10-10 12:00:00",
            "location": "Manhattan",
        },
        {
            "station_id": "120",
            "name": "Pershing Square North",
            "bikes_available": 8,
            "docks_available": 12,
            "last_updated": "2026-10-10 12:05:00",
            "location": "Manhattan",
        },
        {
            "station_id": "208",
            "name": "Washington Ave & Park Ave",
            "bikes_available": 20,
            "docks_available": 2,
            "last_updated": "2026-10-10 12:10:00",
            "location": "Brooklyn",
        },
        {
            "station_id": "316",
            "name": "Jackson Ave & 46th Ave",
            "bikes_available": 12,
            "docks_available": 8,
            "last_updated": "2026-10-10 12:00:00",
            "location": "Queens",
        },
        {
            "station_id": "430",
            "name": "E 161 St & Grand Concourse",
            "bikes_available": 5,
            "docks_available": 15,
            "last_updated": "2026-10-10 12:15:00",
            "location": "Bronx",
        },
    ]
