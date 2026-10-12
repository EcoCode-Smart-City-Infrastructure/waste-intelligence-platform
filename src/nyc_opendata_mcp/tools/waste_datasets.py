"""NYC waste management datasets tools."""

from __future__ import annotations

from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import OutputFormat, WASTE_DATASETS
from ..formatters import (
    FORMAT_FIELD_DESC as _FORMAT_FIELD_DESC,
    handle_api_error,
    json_out,
    md_table,
)
from ..http_client import socrata_request, soql_str
from ..models import WasteDataset, tool_result


class WasteDatasetsInput(BaseModel):
    """Input for listing waste management datasets."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: str | None = Field(
        default=None,
        description="Filter by waste category",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_datasets",
    annotations=ToolAnnotations(
        title="List Waste Management Datasets",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_waste_datasets(params: WasteDatasetsInput) -> Annotated[CallToolResult, str]:
    """Retrieve list of NYC waste management datasets.

    Data source: NYC Open Data (Socrata) and DSNY.

    Args:
        category: Optional category filter
        format: Output format

    Returns:
        List of waste management datasets with descriptions
    """
    try:
        # Generate waste datasets
        datasets = _generate_waste_datasets()
        
        # Apply category filter
        if params.category:
            datasets = [d for d in datasets if d.category.lower() == params.category.lower()]
        
        if not datasets:
            return tool_result({
                "status": "error",
                "error": "No waste datasets found",
                "markdown": "Keine Abfalldatens\u00e4tze gefunden.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": [d.model_dump() for d in datasets],
                "markdown": json_out([d.model_dump() for d in datasets]),
            })
        
        # Format as Markdown
        lines = [
            "## NYC Abfallwirtschaft Datens\u00e4tze",
            f"*Datens\u00e4tze: {len(datasets)}*",
            "",
        ]
        
        for i, dataset in enumerate(datasets, 1):
            lines.append(f"### {i}. {dataset.name}")
            lines.append(f"- **ID:** {dataset.id}")
            lines.append(f"- **Kategorie:** {dataset.category}")
            lines.append(f"- **Aktualisierung:** {dataset.update_frequency}")
            lines.append(f"- **Letzte Aktualisierung:** {dataset.last_updated}")
            lines.append(f"- **Beschreibung:** {dataset.description}")
            lines.append("")
        
        return tool_result({
            "status": "success",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Datasets"),
        })


def _generate_waste_datasets() -> list[WasteDataset]:
    """List the real NYC Open Data waste datasets this server queries.

    All IDs below are live Socrata datasets on data.cityofnewyork.us,
    verified October 2026.
    """
    datasets = [
        WasteDataset(
            id="ebb7-mvp5",
            name="DSNY Monthly Tonnage Data",
            description="Monthly refuse, paper, metal/glass/plastic and organics tonnage collected by DSNY, by borough and month",
            category="Collection Data",
            update_frequency="Monthly",
            last_updated="2026-09-01",
        ),
        WasteDataset(
            id="6r9j-qrwz",
            name="DSNY Disposal Facilities Used by Year",
            description="Disposal facilities used by DSNY by year, with contracted and delivered tonnage",
            category="Infrastructure",
            update_frequency="Annual",
            last_updated="2026-01-01",
        ),
        WasteDataset(
            id="6yag-pnij",
            name="DSNY Other Organics Collection Tonnages",
            description="Annual organics collection tonnages (DSNY and non-DSNY) by fiscal year",
            category="Organics",
            update_frequency="Annual",
            last_updated="2026-01-01",
        ),
        WasteDataset(
            id="gaq9-z3hz",
            name="Recycling Diversion and Capture Rates",
            description="Monthly recycling diversion and capture rates by district; capture rates are the complement of contamination",
            category="Recycling",
            update_frequency="Monthly",
            last_updated="2026-01-01",
        ),
    ]
    return datasets


class TonnageInput(BaseModel):
    """Input for waste tonnage data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    borough: str | None = Field(
        default=None,
        description="Filter by borough (Manhattan, Bronx, Brooklyn, Queens, Staten Island)",
    )
    material: str | None = Field(
        default=None,
        description="Filter by material type (Refuse, Recycling, Organics)",
    )
    year: int | None = Field(
        default=None,
        description="Filter by year",
        ge=2000,
        le=2100,
    )
    month: int | None = Field(
        default=None,
        description="Filter by month (1-12)",
        ge=1,
        le=12,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_tonnage",
    annotations=ToolAnnotations(
        title="Waste Tonnage Data",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_waste_tonnage(params: TonnageInput) -> Annotated[CallToolResult, str]:
    """Retrieve DSNY monthly tonnage data.

    Data source: DSNY Monthly Tonnage Reports.

    Args:
        borough: Optional borough filter
        material: Optional material type filter
        year: Optional year filter
        month: Optional month filter
        format: Output format

    Returns:
        Monthly tonnage data for waste, recycling, and organics
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get data from Socrata
        dataset_id = "ebb7-mvp5"  # DSNY Monthly Tonnage Data

        api_params = {
            "$limit": 100,
            "$order": "month DESC",
        }

        # Apply filters (month column is "YYYY / MM")
        where_clauses = []
        if params.borough:
            where_clauses.append(f"borough = {soql_str(params.borough)}")
        if params.year and params.month:
            where_clauses.append(f"month = '{params.year} / {params.month:02d}'")
        elif params.year:
            where_clauses.append(f"starts_with(month, '{params.year}')")
        elif params.month:
            where_clauses.append(f"month like '% / {params.month:02d}'")

        # Material selects the matching tonnage columns
        material_columns = {
            "refuse": ["refusetonscollected"],
            "recycling": ["papertonscollected", "mgptonscollected"],
            "organics": ["resorganicstons", "schoolorganictons"],
        }
        if params.material:
            cols = material_columns.get(params.material.lower(),
                                        ["refusetonscollected", "papertonscollected",
                                         "mgptonscollected", "resorganicstons"])
            api_params["$select"] = ",".join(["month", "borough"] + cols)

        if where_clauses:
            api_params["$where"] = " AND ".join(where_clauses)

        result = await socrata_request(dataset_id, "json", **api_params)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_tonnage_data(params)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": result,
                "markdown": json_out(result),
            })
        
        # Format as Markdown table
        if isinstance(result, list) and len(result) > 0:
            first_row = result[0]
            if isinstance(first_row, dict):
                headers = list(first_row.keys())
                rows = [list(row.values()) for row in result]
                
                lines = [
                    "## Abfall-Tonnage NYC",
                    f"*Datens\u00e4tze: {len(result)}*",
                    "",
                    md_table(headers, rows),
                ]
                
                return tool_result({
                    "status": "success",
                    "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                    "markdown": "\n".join(lines),
                })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Tonnage"),
        })


def _generate_sample_tonnage_data(params: TonnageInput) -> list[dict]:
    """Generate sample tonnage data."""
    boroughs = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
    materials = ["Refuse", "Recycling", "Organics"]
    
    data = []
    for borough in boroughs:
        if params.borough and borough != params.borough:
            continue
        for material in materials:
            if params.material and material != params.material:
                continue
            for month in range(1, 13):
                if params.month and month != params.month:
                    continue
                if params.year and params.year != 2026:
                    continue
                    
                # Generate sample tonnage values
                base_tonnage = {
                    "Refuse": 50000,
                    "Recycling": 20000,
                    "Organics": 10000,
                }.get(material, 10000)
                
                # Add some variation
                tonnage = base_tonnage + (month * 1000) + (hash(borough + material) % 5000)
                
                data.append({
                    "borough": borough,
                    "material_type": material,
                    "date": f"2026-{month:02d}-01",
                    "tonnage_tons": tonnage,
                    "year": 2026,
                    "month": month,
                })
    
    return data


class FacilitiesInput(BaseModel):
    """Input for waste facility data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    facility_type: str | None = Field(
        default=None,
        description="Filter by facility type (Transfer Station, Composting, AD, Landfill)",
    )
    borough: str | None = Field(
        default=None,
        description="Filter by borough",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_facilities",
    annotations=ToolAnnotations(
        title="Waste Facility Data",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_waste_facilities(params: FacilitiesInput) -> Annotated[CallToolResult, str]:
    """Retrieve information about NYC waste management facilities.

    Data source: DSNY Facility Locations dataset.

    Args:
        facility_type: Optional facility type filter
        borough: Optional borough filter
        format: Output format

    Returns:
        List of waste management facilities with details
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get data from Socrata
        dataset_id = "6r9j-qrwz"  # DSNY Disposal Facilities Used by Year

        api_params = {
            "$limit": 50,
            "$order": "calendar_year DESC",
        }

        # Apply filters (the dataset has no borough column)
        where_clauses = []
        if params.facility_type:
            where_clauses.append(f"facility_type = {soql_str(params.facility_type)}")

        if where_clauses:
            api_params["$where"] = " AND ".join(where_clauses)

        result = await socrata_request(dataset_id, "json", **api_params)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_facility_data(params)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": result,
                "markdown": json_out(result),
            })
        
        # Format as Markdown
        if isinstance(result, list):
            lines = [
                "## Abfallwirtschaftseinrichtungen NYC",
                f"*Einrichtungen: {len(result)}*",
                "",
            ]
            
            for facility in result[:20]:  # Show first 20
                if isinstance(facility, dict):
                    lines.append(f"### {facility.get('facility_name', 'Unknown')}")
                    lines.append(f"- **Typ:** {facility.get('facility_type', 'Unknown')}")
                    lines.append(f"- **Eigent\u00fcmer:** {facility.get('facility_owner_dsny_or_private', 'Unknown')}")
                    lines.append(f"- **Jahr:** {facility.get('calendar_year', 'Unknown')}")
                    if facility.get('facility_contracted_tons'):
                        lines.append(f"- **Vertragstonnage:** {facility.get('facility_contracted_tons')} tons")
                    lines.append("")
            
            if len(result) > 20:
                lines.append(f"*... und {len(result) - 20} weitere Einrichtungen*")
            
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "markdown": "\n".join(lines),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Facilities"),
        })


def _generate_sample_facility_data(params: FacilitiesInput) -> list[dict]:
    """Generate sample facility data."""
    facilities = [
        {
            "facility_name": "North River Wastewater Treatment Plant",
            "facility_type": "Wastewater Treatment",
            "borough": "Manhattan",
            "address": "145th St & Riverside Drive",
            "capacity": 120000000,
            "latitude": 40.8281,
            "longitude": -73.9567,
        },
        {
            "facility_name": "Wards Island Wastewater Treatment Plant",
            "facility_type": "Wastewater Treatment",
            "borough": "Manhattan",
            "address": "Wards Island",
            "capacity": 275000000,
            "latitude": 40.7833,
            "longitude": -73.9167,
        },
        {
            "facility_name": "Hunts Point Wastewater Treatment Plant",
            "facility_type": "Wastewater Treatment",
            "borough": "Bronx",
            "address": "1950 Hunts Point Ave",
            "capacity": 200000000,
            "latitude": 40.8000,
            "longitude": -73.8667,
        },
        {
            "facility_name": "26th Ward Transfer Station",
            "facility_type": "Transfer Station",
            "borough": "Brooklyn",
            "address": "2929 West 12th St",
            "capacity": 500000,
            "latitude": 40.7484,
            "longitude": -73.9857,
        },
        {
            "facility_name": "Hamilton Avenue Marine Transfer Station",
            "facility_type": "Transfer Station",
            "borough": "Brooklyn",
            "address": "246 Hamilton Ave",
            "capacity": 400000,
            "latitude": 40.6782,
            "longitude": -73.9680,
        },
        {
            "facility_name": "Springfield Gardens Composting Facility",
            "facility_type": "Composting",
            "borough": "Queens",
            "address": "198-10 Springfield Blvd",
            "capacity": 100000,
            "latitude": 40.6667,
            "longitude": -73.7500,
        },
        {
            "facility_name": "Newtown Creek Wastewater Treatment Plant",
            "facility_type": "Wastewater Treatment",
            "borough": "Brooklyn",
            "address": "329 Greenpoint Ave",
            "capacity": 310000000,
            "latitude": 40.7281,
            "longitude": -73.9492,
        },
        {
            "facility_name": "Staten Island Transfer Station",
            "facility_type": "Transfer Station",
            "borough": "Staten Island",
            "address": "1911 Richmond Ter",
            "capacity": 200000,
            "latitude": 40.5790,
            "longitude": -74.1561,
        },
        {
            "facility_name": "Red Hook Marine Transfer Station",
            "facility_type": "Transfer Station",
            "borough": "Brooklyn",
            "address": "185 Lorraine St",
            "capacity": 350000,
            "latitude": 40.6782,
            "longitude": -74.0060,
        },
        {
            "facility_name": "Manhattan District 1 Garage",
            "facility_type": "DSNY Garage",
            "borough": "Manhattan",
            "address": "530 East 13th St",
            "capacity": None,
            "latitude": 40.7281,
            "longitude": -73.9772,
        },
    ]
    
    # Apply filters
    if params.facility_type:
        facilities = [f for f in facilities if f.get("facility_type") == params.facility_type]
    if params.borough:
        facilities = [f for f in facilities if f.get("borough") == params.borough]
    
    return facilities


class OrganicsInput(BaseModel):
    """Input for organics collection data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    borough: str | None = Field(
        default=None,
        description="Filter by borough",
    )
    community_board: str | None = Field(
        default=None,
        description="Filter by community board",
    )
    year: int | None = Field(
        default=None,
        description="Filter by year",
        ge=2000,
        le=2100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_organics_collection",
    annotations=ToolAnnotations(
        title="Organics Collection Data",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_organics_collection(params: OrganicsInput) -> Annotated[CallToolResult, str]:
    """Retrieve data on NYC's organics collection tonnages.

    Data source: DSNY Other Organics Collection Tonnages (NYC Open Data).

    Args:
        borough: Optional borough filter
        community_board: Optional community board filter
        year: Optional year filter
        format: Output format

    Returns:
        Organics collection data including participation rates and tonnage
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get data from Socrata
        dataset_id = "6yag-pnij"  # DSNY Other Organics Collection Tonnages

        api_params = {
            "$limit": 100,
            "$order": "fiscal_year DESC",
        }

        # Apply filters (annual dataset: fiscal_year only)
        where_clauses = []
        if params.year:
            where_clauses.append(f"fiscal_year = '{params.year}'")

        if where_clauses:
            api_params["$where"] = " AND ".join(where_clauses)

        result = await socrata_request(dataset_id, "json", **api_params)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_organics_data(params)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": result,
                "markdown": json_out(result),
            })
        
        # Format as Markdown
        if isinstance(result, list):
            lines = [
                "## Organics-Sammlung NYC",
                f"*Datens\u00e4tze: {len(result)}*",
                "",
            ]
            
            for data in result[:20]:  # Show first 20
                if isinstance(data, dict):
                    lines.append(f"### Fiskaljahr {data.get('fiscal_year', 'Unknown')}")
                    lines.append(f"- **DSNY gesammelt:** {data.get('tons_collected_dsny', 0)} tons")
                    lines.append(f"- **Nicht-DSNY gesammelt:** {data.get('tons_collected_non_dsny', 0)} tons")
                    lines.append(f"- **Gesamt:** {data.get('total_tons_collected_all', 0)} tons")
                    lines.append("")
            
            if len(result) > 20:
                lines.append(f"*... und {len(result) - 20} weitere Datens\u00e4tze*")
            
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "markdown": "\n".join(lines),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Organics Collection"),
        })


def _generate_sample_organics_data(params: OrganicsInput) -> list[dict]:
    """Generate sample organics collection data."""
    boroughs = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
    
    data = []
    for borough in boroughs:
        if params.borough and borough != params.borough:
            continue
        for cb in range(1, 13):  # Community boards
            if params.community_board and str(cb) != params.community_board:
                continue
            for month in range(1, 13):
                if params.year and params.year != 2026:
                    continue
                    
                # Generate sample data
                households = (cb * 1000) + (hash(borough + str(cb)) % 5000)
                tonnage = households * 0.02  # 2% participation rate
                participation_rate = 2.0 + (month * 0.1)
                
                data.append({
                    "borough": borough,
                    "community_board": f"CB {cb}",
                    "date": f"2026-{month:02d}-01",
                    "participating_households": int(households * participation_rate / 100),
                    "tonnage_tons": tonnage * participation_rate / 100,
                    "participation_rate": participation_rate,
                })
    
    return data


class ContaminationInput(BaseModel):
    """Input for recycling contamination data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    borough: str | None = Field(
        default=None,
        description="Filter by borough",
    )
    material: str | None = Field(
        default=None,
        description="Filter by material type (Paper, Plastic, Metal, Glass)",
    )
    year: int | None = Field(
        default=None,
        description="Filter by year",
        ge=2000,
        le=2100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_recycling_contamination",
    annotations=ToolAnnotations(
        title="Recycling Contamination Data",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_recycling_contamination(params: ContaminationInput) -> Annotated[CallToolResult, str]:
    """Retrieve data on NYC recycling diversion and capture rates.

    Data source: Recycling Diversion and Capture Rates (NYC Open Data).
    Capture rates are the complement of contamination: higher capture
    means less recyclable material lost to the refuse stream.

    Args:
        borough: Optional borough filter
        material: Optional material type filter
        year: Optional year filter
        format: Output format

    Returns:
        Recycling contamination data including rates and common contaminants
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get data from Socrata
        dataset_id = "gaq9-z3hz"  # Recycling Diversion and Capture Rates

        api_params = {
            "$limit": 100,
            "$order": "fiscal_year DESC, fiscal_month_number DESC",
        }

        # Apply filters (district like "BKN01"; fiscal_year as text)
        where_clauses = []
        if params.borough:
            where_clauses.append(
                "upper(district) like " + soql_str(f"%{params.borough[:3].upper()}%")
            )
        if params.year:
            where_clauses.append(f"fiscal_year = '{params.year}'")

        if where_clauses:
            api_params["$where"] = " AND ".join(where_clauses)

        result = await socrata_request(dataset_id, "json", **api_params)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_contamination_data(params)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": result,
                "markdown": json_out(result),
            })
        
        # Format as Markdown
        if isinstance(result, list):
            lines = [
                "## Recycling-Kontamination NYC",
                f"*Datens\u00e4tze: {len(result)}*",
                "",
            ]
            
            for data in result[:20]:  # Show first 20
                if isinstance(data, dict):
                    lines.append(f"### {data.get('month_name', '')} {data.get('fiscal_year', '')} - {data.get('district', 'Unknown')}")
                    lines.append(f"- **Diversionsrate:** {data.get('diversion_rate_total_total_recycling_total_waste_', '?')}%")
                    lines.append(f"- **Erfassungsrate Papier:** {data.get('capture_rate_paper_total_paper_max_paper_', '?')}%")
                    lines.append(f"- **Erfassungsrate MGP:** {data.get('capture_rate_mgp_total_mgp_max_mgp_', '?')}%")
                    lines.append("")
            
            if len(result) > 20:
                lines.append(f"*... und {len(result) - 20} weitere Datens\u00e4tze*")
            
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "markdown": "\n".join(lines),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Recycling Contamination"),
        })


def _generate_sample_contamination_data(params: ContaminationInput) -> list[dict]:
    """Generate sample contamination data."""
    boroughs = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
    materials = ["Paper", "Plastic", "Metal", "Glass"]
    
    data = []
    for borough in boroughs:
        if params.borough and borough != params.borough:
            continue
        for material in materials:
            if params.material and material != params.material:
                continue
            for month in range(1, 13):
                if params.year and params.year != 2026:
                    continue
                    
                # Generate sample data
                collected = 10000 + (hash(borough + material + str(month)) % 5000)
                contamination_rate = 15.0 + (hash(borough) % 10)
                contaminated = collected * contamination_rate / 100
                
                common_contaminants = [
                    "Plastic Bags",
                    "Food Waste",
                    "Diapers",
                    "Electronics",
                    "Clothing",
                ]
                
                data.append({
                    "borough": borough,
                    "material": material,
                    "date": f"2026-{month:02d}-01",
                    "collected_tons": collected,
                    "contamination_rate": contamination_rate,
                    "contaminated_tons": contaminated,
                    "common_contaminants": common_contaminants[:3],
                })
    
    return data
