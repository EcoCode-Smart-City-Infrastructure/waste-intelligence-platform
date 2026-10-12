"""NYC government tools: council members, legislation, and mayoral orders."""

from __future__ import annotations

from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import OutputFormat
from ..formatters import (
    FORMAT_FIELD_DESC as _FORMAT_FIELD_DESC,
    handle_api_error,
    json_out,
    md_table,
)
from ..http_client import http_get_json, socrata_request, soql_str
from ..models import CouncilMember, Legislation, tool_result


class CouncilMembersInput(BaseModel):
    """Input for listing council members."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    district: int | None = Field(
        default=None,
        description="Filter by council district (1-51)",
        ge=1,
        le=51,
    )
    party: str | None = Field(
        default=None,
        description="Filter by political party",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)



# Real NYC Open Data datasets (verified October 2026)
COUNCIL_MEMBERS_DATASET = "uvw5-9znb"  # City Council Members (1999 to Present)
LEGISLATION_DATASET = "6ctv-n46c"  # City Council Legislation: Bills and Local Laws


async def _fetch_council_members(
    district: int | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list | None:
    """Fetch council members from the real dataset.

    Returns None when the request fails or yields nothing (caller falls
    back to labeled simulated data). The dataset has no party, email or
    phone columns.
    """
    params: dict = {"$limit": min(limit, 100), "$order": "district"}
    where = []
    if district:
        where.append(f"district = '{district}'")
    if search:
        clauses = ["upper(name) like " + soql_str(f"%{search.upper()}%")]
        if search.isdigit():  # district is numeric in Socrata
            clauses.append(f"district = {search}")
        where.append("(" + " OR ".join(clauses) + ")")
    if where:
        params["$where"] = " AND ".join(where)
    try:
        rows = await socrata_request(COUNCIL_MEMBERS_DATASET, "json", **params)
    except Exception:
        return None
    if not rows:
        return None
    members = []
    for r in rows:
        try:
            members.append(CouncilMember(
                id=str(r.get("council_member_id", "")),
                name=r.get("name", "Unknown"),
                district=int(r.get("district", 0)),
            ))
        except (ValueError, TypeError):
            continue
    return members or None


async def _fetch_legislation(
    status: str | None = None,
    search: str | None = None,
    sponsor: str | None = None,
    matter_id: str | None = None,
    file_num: str | None = None,
    limit: int = 50,
) -> list | None:
    """Fetch legislation from the real dataset. Returns None on failure."""
    params: dict = {"$limit": min(limit, 100), "$order": "intro_date DESC"}
    where = []
    if matter_id:
        where.append(f"matter_id = {soql_str(matter_id)}")
    if file_num:
        where.append("upper(file_num) = " + soql_str(file_num.upper()))
    if status:
        where.append("upper(status) like " + soql_str(f"%{status.upper()}%"))
    if search:
        safe = search.upper().replace("'", "''")
        where.append(
            f"(upper(name) like '%{safe}%' OR upper(title) like '%{safe}%' "
            f"OR upper(summary) like '%{safe}%')"
        )
    if sponsor:
        where.append("upper(primary_sponsor) like " + soql_str(f"%{sponsor.upper()}%"))
    if where:
        params["$where"] = " AND ".join(where)
    try:
        rows = await socrata_request(LEGISLATION_DATASET, "json", **params)
    except Exception:
        return None
    if not rows:
        return None
    items = []
    for r in rows:
        sponsors = [r["primary_sponsor"]] if r.get("primary_sponsor") else []
        items.append(Legislation(
            id=str(r.get("matter_id", "")),
            title=r.get("title") or r.get("name") or "Untitled",
            type=str(r.get("file_num", "")),
            status=r.get("status", ""),
            introduced_date=str(r.get("intro_date", "")),
            sponsors=sponsors,
        ))
    return items or None

@mcp.tool(
    name="nyc_council_members",
    annotations=ToolAnnotations(
        title="List Council Members",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_council_members(params: CouncilMembersInput) -> Annotated[CallToolResult, str]:
    """Retrieve list of NYC Council members.

    Data source: NYC Council API and Legistar.

    Args:
        district: Optional district filter
        party: Optional party filter
        format: Output format

    Returns:
        List of council members with contact information
    Data source: City Council Members dataset (NYC Open Data). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: NYC Open Data council members dataset
        members = await _fetch_council_members(district=params.district)
        simulated = not members
        if simulated:
            # Labeled simulated fallback
            members = _generate_sample_council_members()

            # Apply filters
            if params.district:
                members = [m for m in members if m.district == params.district]
            if params.party:
                members = [m for m in members if m.party.lower() == params.party.lower()]
        
        if not members:
            return tool_result({
                "status": "error",
                "error": "No council members found",
                "markdown": "No council members found.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": [m.model_dump() for m in members],
                "markdown": json_out([m.model_dump() for m in members]),
            })
        
        # Format as Markdown table
        headers = ["District", "Name"]
        rows = []
        for member in members:
            row = [
                str(member.district),
                member.name,
            ]
            if member.party or member.email:
                row += [member.party, member.email]
            rows.append(row)
        if any(len(r) > 2 for r in rows):
            headers += ["Party", "Email"]
        
        lines = [
            "## NYC Council Members",
            f"*Members: {len(members)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Council Members"),
        })


def _generate_sample_council_members() -> list[CouncilMember]:
    """Generate sample council members."""
    members = [
        CouncilMember(
            id="m001",
            name="Adrienne Adams",
            district=28,
            party="Democratic",
            email="adams@council.nyc.gov",
            phone="(212) 788-7356",
        ),
        CouncilMember(
            id="m002",
            name="Farah N. Louis",
            district=9,
            party="Democratic",
            email="louis@council.nyc.gov",
            phone="(212) 788-7369",
        ),
        CouncilMember(
            id="m003",
            name="Crystal Hudson",
            district=35,
            party="Democratic",
            email="hudson@council.nyc.gov",
            phone="(212) 788-7379",
        ),
        CouncilMember(
            id="m004",
            name="Joseph C. Borelli",
            district=51,
            party="Republican",
            email="borelli@council.nyc.gov",
            phone="(718) 984-5155",
        ),
        CouncilMember(
            id="m005",
            name="Justin L. Brannan",
            district=43,
            party="Democratic",
            email="brannan@council.nyc.gov",
            phone="(718) 748-5200",
        ),
        CouncilMember(
            id="m006",
            name="Rita Joseph",
            district=40,
            party="Democratic",
            email="joseph@council.nyc.gov",
            phone="(718) 287-8762",
        ),
        CouncilMember(
            id="m007",
            name="Shaun Abreu",
            district=7,
            party="Democratic",
            email="abreu@council.nyc.gov",
            phone="(212) 788-7362",
        ),
        CouncilMember(
            id="m008",
            name="Althea Stevens",
            district=16,
            party="Democratic",
            email="stevens@council.nyc.gov",
            phone="(212) 788-7350",
        ),
        CouncilMember(
            id="m009",
            name="Ydanis Rodriguez",
            district=10,
            party="Democratic",
            email="rodriguez@council.nyc.gov",
            phone="(212) 788-7375",
        ),
        CouncilMember(
            id="m010",
            name="Eric Dinowitz",
            district=11,
            party="Democratic",
            email="dinowitz@council.nyc.gov",
            phone="(212) 788-7370",
        ),
    ]
    return members


class CouncilSearchInput(BaseModel):
    """Input for searching council members."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search query (name, district, or keyword)",
        min_length=1,
        max_length=100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_council_search",
    annotations=ToolAnnotations(
        title="Search Council Members",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_council_search(params: CouncilSearchInput) -> Annotated[CallToolResult, str]:
    """Search NYC Council members by name, district, or keyword.

    Args:
        query: Search query
        format: Output format

    Returns:
        List of matching council members
    Data source: City Council Members dataset (NYC Open Data). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: search the NYC Open Data council members dataset
        results = await _fetch_council_members(search=params.query)
        simulated = not results
        if simulated:
            members = _generate_sample_council_members()

            # Search by name, district, or email
            query_lower = params.query.lower()
            results = []
            for member in members:
                if (
                    query_lower in member.name.lower() or
                    query_lower in str(member.district) or
                    query_lower in member.email.lower() or
                    query_lower in member.party.lower()
                ):
                    results.append(member)
        
        if not results:
            return tool_result({
                "status": "error",
                "error": "No council members found",
                "markdown": f"No council members found for '{params.query}'.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": [m.model_dump() for m in results],
                "markdown": json_out([m.model_dump() for m in results]),
            })
        
        # Format as Markdown
        lines = [
            f"## Search results for '{params.query}'",
            f"*Found: {len(results)} members*",
            "",
        ]
        
        for member in results:
            lines.append(f"### {member.name}")
            lines.append(f"- **District:** {member.district}")
            lines.append(f"- **Party:** {member.party}")
            lines.append(f"- **Email:** {member.email}")
            lines.append(f"- **Phone:** {member.phone}")
            lines.append("")
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Council Search"),
        })


class LegislationInput(BaseModel):
    """Input for listing legislation."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    type: str | None = Field(
        default=None,
        description="Filter by legislation type (e.g., 'Bill', 'Resolution')",
    )
    status: str | None = Field(
        default=None,
        description="Filter by status (e.g., 'Introduced', 'Passed')",
    )
    sponsor: str | None = Field(
        default=None,
        description="Filter by sponsor name",
    )
    limit: int = Field(default=20, description="Maximum number of results", ge=1, le=100)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_legislation",
    annotations=ToolAnnotations(
        title="List Legislation",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_legislation(params: LegislationInput) -> Annotated[CallToolResult, str]:
    """Retrieve list of NYC Council legislation.

    Data source: City Council Legislation dataset (NYC Open Data).

    Args:
        type: Optional legislation type filter
        status: Optional status filter
        sponsor: Optional sponsor filter
        limit: Maximum number of results
        format: Output format

    Returns:
        List of legislation with details
    Falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: NYC Open Data legislation dataset
        legislation = await _fetch_legislation(
            status=params.status, sponsor=params.sponsor, limit=params.limit
        )
        simulated = not legislation
        if simulated:
            # Labeled simulated fallback
            legislation = _generate_sample_legislation()

            # Apply filters
            if params.type:
                legislation = [l for l in legislation if l.type.lower() == params.type.lower()]
            if params.status:
                legislation = [l for l in legislation if l.status.lower() == params.status.lower()]
            if params.sponsor:
                legislation = [l for l in legislation if any(
                    params.sponsor.lower() in s.lower() for s in l.sponsors
                )]

            legislation = legislation[:params.limit]
        
        if not legislation:
            return tool_result({
                "status": "error",
                "error": "No legislation found",
                "markdown": "No legislation found.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": [l.model_dump() for l in legislation],
                "markdown": json_out([l.model_dump() for l in legislation]),
            })
        
        # Format as Markdown table
        headers = ["ID", "Title", "Type", "Status", "Introduced"]
        rows = []
        for leg in legislation:
            row = [
                leg.id,
                leg.title[:50] + "..." if len(leg.title) > 50 else leg.title,
                leg.type,
                leg.status,
                leg.introduced_date,
            ]
            rows.append(row)
        
        lines = [
            "## NYC Legislation",
            f"*Gesetze: {len(legislation)}*",
            "",
            md_table(headers, rows),
        ]
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Legislation"),
        })


def _generate_sample_legislation() -> list[Legislation]:
    """Generate sample legislation."""
    legislation = [
        Legislation(
            id="Int 0001-2026",
            title="Waste Management Reform Act",
            type="Bill",
            status="Introduced",
            introduced_date="2026-01-15",
            sponsors=["Adrienne Adams", "Justin Brannan"],
        ),
        Legislation(
            id="Int 0002-2026",
            title="Recycling Expansion Initiative",
            type="Bill",
            status="Committee Review",
            introduced_date="2026-01-20",
            sponsors=["Crystal Hudson", "Rita Joseph"],
        ),
        Legislation(
            id="Int 0003-2026",
            title="Composting Program Funding",
            type="Resolution",
            status="Passed",
            introduced_date="2026-02-01",
            sponsors=["Shaun Abreu", "Althea Stevens"],
        ),
        Legislation(
            id="Int 0004-2026",
            title="Zero Waste NYC Implementation Plan",
            type="Bill",
            status="Public Hearing",
            introduced_date="2026-02-15",
            sponsors=["Ydanis Rodriguez", "Eric Dinowitz"],
        ),
        Legislation(
            id="Int 0005-2026",
            title="Plastic Bag Ban Extension",
            type="Bill",
            status="Introduced",
            introduced_date="2026-03-01",
            sponsors=["Farah N. Louis", "Joseph C. Borelli"],
        ),
        Legislation(
            id="Res 0001-2026",
            title="Support for DSNY Budget Increase",
            type="Resolution",
            status="Passed",
            introduced_date="2026-01-10",
            sponsors=["Adrienne Adams"],
        ),
        Legislation(
            id="Res 0002-2026",
            title="Commercial Waste Zone Implementation",
            type="Resolution",
            status="Committee Review",
            introduced_date="2026-01-25",
            sponsors=["Justin Brannan"],
        ),
    ]
    return legislation


class LegislationDetailInput(BaseModel):
    """Input for getting legislation details."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    legislation_id: str = Field(
        ...,
        description="Legislation identifier (e.g., 'Int 0001-2026')",
        min_length=1,
        max_length=100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_legislation_detail",
    annotations=ToolAnnotations(
        title="Get Legislation Details",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_legislation_detail(params: LegislationDetailInput) -> Annotated[CallToolResult, str]:
    """Retrieve details for a specific piece of legislation.

    Args:
        legislation_id: Legislation identifier
        format: Output format

    Returns:
        Detailed information about the legislation
    Data source: City Council Legislation dataset (NYC Open Data). Falls back
    to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: look up by matter id, then by file number
        items = await _fetch_legislation(matter_id=params.legislation_id)
        if not items:
            items = await _fetch_legislation(file_num=params.legislation_id)
        simulated = not items
        leg = items[0] if items else None
        if simulated:
            legislation = _generate_sample_legislation()

            # Find matching legislation
            for l in legislation:
                if l.id == params.legislation_id:
                    leg = l
                    break
        
        if not leg:
            return tool_result({
                "status": "error",
                "error": "Legislation not found",
                "markdown": f"Legislation '{params.legislation_id}' not found.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": leg.model_dump(),
                "markdown": json_out(leg.model_dump()),
            })
        
        # Format as Markdown
        lines = [
            f"## {leg.title}",
            f"*ID: {leg.id}*",
            "",
            f"**Type:** {leg.type}",
            f"**Status:** {leg.status}",
            f"**Introduced:** {leg.introduced_date}",
            "",
            "### Sponsors",
            "",
        ]
        
        for sponsor in leg.sponsors:
            lines.append(f"- {sponsor}")
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Legislation Detail"),
        })


class MayoralOrdersInput(BaseModel):
    """Input for listing mayoral orders."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    year: int | None = Field(
        default=None,
        description="Filter by year",
        ge=2000,
        le=2100,
    )
    limit: int = Field(default=20, description="Maximum number of results", ge=1, le=100)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_mayoral_orders",
    annotations=ToolAnnotations(
        title="List Mayoral Orders",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_mayoral_orders(params: MayoralOrdersInput) -> Annotated[CallToolResult, str]:
    """Retrieve list of NYC mayoral executive orders.

    Args:
        year: Optional year filter
        limit: Maximum number of results
        format: Output format

    Returns:
        List of mayoral orders
    Note: this tool currently returns simulated sample data, not live data.
    """
    try:
        # Generate sample mayoral orders
        orders = _generate_sample_mayoral_orders()
        
        # Apply filters
        if params.year:
            orders = [o for o in orders if o.get("year") == params.year]
        
        orders = orders[:params.limit]
        
        if not orders:
            return tool_result({
                "status": "error",
                "error": "No mayoral orders found",
                "markdown": "No mayoral orders found.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated",
                "data": orders,
                "markdown": json_out(orders),
            })
        
        # Format as Markdown table
        headers = ["Order #", "Title", "Year", "Date"]
        rows = []
        for order in orders:
            row = [
                order.get("order_number", ""),
                order.get("title", ""),
                str(order.get("year", "")),
                order.get("date", ""),
            ]
            rows.append(row)
        
        lines = [
            "## NYC Mayoral Orders",
            f"*Anordnungen: {len(orders)}*",
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
            "markdown": handle_api_error(e, "Mayoral Orders"),
        })


def _generate_sample_mayoral_orders() -> list[dict]:
    """Generate sample mayoral orders."""
    orders = [
        {
            "order_number": "EO-001-2026",
            "title": "Zero Waste NYC Implementation",
            "year": 2026,
            "date": "2026-01-01",
            "description": "Executive order to implement Zero Waste NYC initiative",
        },
        {
            "order_number": "EO-002-2026",
            "title": "DSNY Fleet Electrification",
            "year": 2026,
            "date": "2026-01-15",
            "description": "Order to electrify DSNY collection fleet by 2030",
        },
        {
            "order_number": "EO-003-2026",
            "title": "Commercial Waste Zone Expansion",
            "year": 2026,
            "date": "2026-02-01",
            "description": "Expansion of commercial waste zone program",
        },
        {
            "order_number": "EO-004-2025",
            "title": "Organics Collection Mandate",
            "year": 2025,
            "date": "2025-06-01",
            "description": "Mandatory organics collection for all NYC residents",
        },
        {
            "order_number": "EO-005-2025",
            "title": "Plastic Reduction Initiative",
            "year": 2025,
            "date": "2025-03-15",
            "description": "Initiative to reduce single-use plastics in NYC",
        },
    ]
    return orders
