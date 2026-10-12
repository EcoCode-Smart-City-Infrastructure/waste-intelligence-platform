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
from ..http_client import get_client, mta_request, socrata_request
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



# MTA NYCT GTFS-Realtime feed groups (verified keyless, October 2026)
MTA_GTFS_RT_BASE = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds"
MTA_FEED_GROUPS: dict[str, list[str]] = {
    "nyct%2Fgtfs": ["1", "2", "3", "4", "5", "6", "7", "S"],
    "nyct%2Fgtfs-ace": ["A", "C", "E"],
    "nyct%2Fgtfs-bdfm": ["B", "D", "F", "M"],
    "nyct%2Fgtfs-g": ["G"],
    "nyct%2Fgtfs-jz": ["J", "Z"],
    "nyct%2Fgtfs-l": ["L"],
    "nyct%2Fgtfs-nqrw": ["N", "Q", "R", "W"],
    "nyct%2Fgtfs-si": ["SI"],
}

# Citi Bike GBFS endpoints (keyless, verified October 2026)
GBFS_STATION_INFO = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
GBFS_STATION_STATUS = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"


async def _fetch_gtfs_feed(feed_suffix: str):
    """Fetch and parse one GTFS-Realtime feed. Returns None on failure."""
    from google.transit import gtfs_realtime_pb2

    try:
        client = await get_client()
        async with client.get(f"{MTA_GTFS_RT_BASE}/{feed_suffix}") as resp:
            resp.raise_for_status()
            payload = await resp.read()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(payload)
        return feed
    except Exception:
        return None


async def _fetch_mta_alerts() -> dict[str, list[str]] | None:
    """Active service alerts per route from all feed groups.

    Returns None when every feed fails (caller falls back to labeled
    simulated data).
    """
    alerts: dict[str, list[str]] = {}
    any_ok = False
    for suffix, lines in MTA_FEED_GROUPS.items():
        feed = await _fetch_gtfs_feed(suffix)
        if feed is None:
            continue
        any_ok = True
        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue
            alert = entity.alert
            header = ""
            if alert.header_text.translation:
                header = alert.header_text.translation[0].text
            routes = {
                ie.route_id for ie in alert.informed_entity if ie.route_id
            } or set(lines)
            for route in routes:
                alerts.setdefault(route, []).append(header)
    return alerts if any_ok else None


async def _fetch_mta_arrivals() -> dict[str, list[dict]] | None:
    """Upcoming arrivals per stop from trip updates.

    Returns {stop_id: [{route_id, arrival_epoch, minutes_away}]} or None
    when all feeds fail.
    """
    import time

    now = int(time.time())
    arrivals: dict[str, list[dict]] = {}
    any_ok = False
    for suffix in MTA_FEED_GROUPS:
        feed = await _fetch_gtfs_feed(suffix)
        if feed is None:
            continue
        any_ok = True
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            tu = entity.trip_update
            route_id = tu.trip.route_id or ""
            for stu in tu.stop_time_update:
                arr = stu.arrival.time if stu.HasField("arrival") else 0
                if arr and arr >= now - 60:
                    arrivals.setdefault(stu.stop_id, []).append(
                        {"route_id": route_id, "arrival_epoch": arr,
                         "minutes_away": max(0, round((arr - now) / 60))}
                    )
    if not any_ok:
        return None
    for stop_id in arrivals:
        arrivals[stop_id].sort(key=lambda a: a["arrival_epoch"])
    return arrivals


async def _fetch_bike_share() -> list[dict] | None:
    """Live Citi Bike station availability. None on failure."""
    from ..http_client import http_get_json

    try:
        info = await http_get_json(GBFS_STATION_INFO)
        status = await http_get_json(GBFS_STATION_STATUS)
    except Exception:
        return None
    info_stations = {s["station_id"]: s for s in info.get("data", {}).get("stations", [])}
    status_stations = status.get("data", {}).get("stations", [])
    if not status_stations:
        return None
    out = []
    for s in status_stations:
        meta = info_stations.get(s.get("station_id"), {})
        out.append({
            "station_id": s.get("station_id"),
            "name": meta.get("name", "Unknown"),
            "bikes_available": s.get("num_bikes_available", 0),
            "docks_available": s.get("num_docks_available", 0),
            "is_renting": bool(s.get("is_renting")),
            "last_updated": s.get("last_reported"),
            "lat": meta.get("lat"),
            "lon": meta.get("lon"),
        })
    return out or None


async def _fetch_traffic_incidents(limit: int = 50) -> list[dict] | None:
    """Recent NYPD motor vehicle collisions. None on failure."""
    try:
        rows = await socrata_request(
            "h9gi-nx95", "json",
            **{"$limit": min(limit, 100), "$order": "crash_date DESC, crash_time DESC"},
        )
    except Exception:
        return None
    if not rows:
        return None
    out = []
    for r in rows:
        try:
            injured = int(r.get("number_of_persons_injured") or 0)
            killed = int(r.get("number_of_persons_killed") or 0)
        except (ValueError, TypeError):
            injured, killed = 0, 0
        out.append({
            "date": r.get("crash_date", "")[:10],
            "time": r.get("crash_time", ""),
            "borough": r.get("borough", "Unknown"),
            "location": r.get("on_street_name") or r.get("off_street_name") or "Unknown",
            "severity": "Fatal" if killed else ("Injury" if injured else "Property damage"),
            "persons_injured": injured,
            "persons_killed": killed,
        })
    return out or None

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
    Data source: MTA GTFS-Realtime service alerts (keyless). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: live GTFS-Realtime service alerts per line
        from datetime import datetime, timezone

        alerts = await _fetch_mta_alerts()
        simulated = alerts is None
        if simulated:
            status_data = _generate_sample_mta_status()
        else:
            status_data = []
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for _suffix, lines in MTA_FEED_GROUPS.items():
                for line in lines:
                    line_alerts = alerts.get(line, [])
                    if line_alerts:
                        seen = list(dict.fromkeys(line_alerts))[:3]
                        status_data.append({
                            "line": line,
                            "status": "Delays",
                            "last_updated": now,
                            "details": " | ".join(seen),
                        })
                    else:
                        status_data.append({
                            "line": line,
                            "status": "Good Service",
                            "last_updated": now,
                            "details": "",
                        })

        if params.line:
            status_data = [s for s in status_data if s.get("line") == params.line]
        
        if not status_data:
            return tool_result({
                "status": "error",
                "error": "No status data available",
                "markdown": "No status data available.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "mta-gtfs-realtime",
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
            f"*Lines: {len(status_data)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "data_source": "simulated",
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
    Data source: MTA GTFS-Realtime trip updates (keyless). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: live arrivals per stop from GTFS-Realtime trip updates.
        # station matches a stop_id prefix (e.g. "127" for 127N/127S);
        # station names need the static GTFS and are not resolved here.
        from datetime import datetime, timezone

        arrivals = await _fetch_mta_arrivals()
        simulated = arrivals is None
        if simulated:
            station_data = _generate_sample_station_status()

            if params.station:
                station_data = [s for s in station_data if params.station.lower() in s.get("station", "").lower()]
            if params.line:
                station_data = [s for s in station_data if params.line in s.get("lines", [])]
        else:
            station_data = []
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for stop_id, stop_arrivals in sorted(arrivals.items()):
                if params.station and params.station.upper() not in stop_id.upper():
                    continue
                if params.line:
                    stop_arrivals = [a for a in stop_arrivals if a["route_id"] == params.line]
                if not stop_arrivals:
                    continue
                next3 = stop_arrivals[:3]
                station_data.append({
                    "station": stop_id,
                    "lines": sorted({a["route_id"] for a in next3}),
                    "status": "In Service",
                    "last_updated": now,
                    "next_arrivals_min": [a["minutes_away"] for a in next3],
                })
            station_data = station_data[:50]
        
        if not station_data:
            return tool_result({
                "status": "error",
                "error": "No station data available",
                "markdown": "No station data available.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "mta-gtfs-realtime",
                "data": station_data,
                "markdown": json_out(station_data),
            })
        
        # Format as Markdown table
        headers = ["Station", "Lines", "Status", "Next Arrivals (min)"]
        rows = []
        for station in station_data:
            status_emoji = "\U0001F7E2" if station.get("status") in ("Good Service", "In Service") else "\U0001F534"
            arrivals_txt = ", ".join(str(m) for m in station.get("next_arrivals_min", []))
            row = [
                station.get("station", ""),
                ", ".join(station.get("lines", [])),
                f"{status_emoji} {station.get('status', 'Unknown')}",
                arrivals_txt or station.get("last_updated", ""),
            ]
            rows.append(row)
        
        lines = [
            "## MTA Station Status",
            f"*Stations: {len(station_data)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "data_source": "simulated",
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
    Data source: NYPD Motor Vehicle Collisions (NYC Open Data). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: recent NYPD motor vehicle collisions (NYC Open Data)
        incidents = await _fetch_traffic_incidents(limit=params.limit * 2)
        simulated = incidents is None
        if simulated:
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
                "markdown": "No traffic incidents found.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": incidents,
                "markdown": json_out(incidents),
            })
        
        # Format as Markdown table
        headers = ["Date", "Borough", "Location", "Severity", "Injured/Killed"]
        rows = []
        for incident in incidents:
            severity_emoji = {
                "Property damage": "\U0001F7E2",
                "Injury": "\U0001F7E1",
                "Fatal": "\U0001F534",
                "Low": "\U0001F7E2",
                "Medium": "\U0001F7E1",
                "High": "\U0001F534",
            }.get(incident.get("severity", ""), "")
            row = [
                f"{incident.get('date', '')} {incident.get('time', '')}".strip(),
                incident.get("borough", ""),
                incident.get("location", ""),
                f"{severity_emoji} {incident.get('severity', 'Unknown')}",
                f"{incident.get('persons_injured', incident.get('injured', 0))}/"
                f"{incident.get('persons_killed', incident.get('killed', 0))}",
            ]
            rows.append(row)
        
        lines = [
            "## NYC Traffic Incidents",
            f"*Incidents: {len(incidents)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "data_source": "simulated",
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
    Data source: Citi Bike GBFS (keyless, live). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: live Citi Bike GBFS availability
        stations = await _fetch_bike_share()
        simulated = stations is None
        if simulated:
            stations = _generate_sample_bike_share()

        if params.station_id:
            stations = [s for s in stations if s.get("station_id") == params.station_id]

        stations = stations[:params.limit]
        
        if not stations:
            return tool_result({
                "status": "error",
                "error": "No bike share data available",
                "markdown": "No bike share data available.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "citibike-gbfs",
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
            "## Citi Bike Stations",
            f"*Stations: {len(stations)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "data_source": "simulated",
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
