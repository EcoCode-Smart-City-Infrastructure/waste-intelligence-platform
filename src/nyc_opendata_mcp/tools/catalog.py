"""NYC Open Data catalog tools: dataset search, details, categories, tags, analysis."""

from __future__ import annotations

import asyncio
from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import NYC_CATEGORIES, NYCCategory, OutputFormat
from ..formatters import (
    FORMAT_FIELD_DESC as _FORMAT_FIELD_DESC,
    format_dataset_summary,
    handle_api_error,
    json_out,
    to_dataset_summary,
    to_resource_info,
)
from ..http_client import socrata_request, soql_str
from ..models import (
    AnalysisResult,
    DatasetAnalysis,
    GetDatasetResult,
    SearchResult,
    tool_result,
)


class SearchDatasetsInput(BaseModel):
    """Input for dataset search."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search term(s), e.g., 'waste', 'recycling', 'air quality'. "
        "Supports Solr syntax: AND, OR, NOT, wildcards (*), fuzzy (~).",
        min_length=1,
        max_length=500,
    )
    rows: int = Field(default=10, description="Number of results (max. 50)", ge=1, le=50)
    offset: int = Field(default=0, description="Offset for pagination", ge=0)
    sort: str | None = Field(
        default=None,
        description="Sort order, e.g., 'modified desc', 'title asc', 'score desc'",
    )
    filter_category: NYCCategory | None = Field(
        default=None,
        description=f"Filter by category. Available: {', '.join(NYC_CATEGORIES)}",
    )


@mcp.tool(
    name="nyc_search_datasets",
    annotations=ToolAnnotations(
        title="Search NYC Datasets",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_search_datasets(
    params: SearchDatasetsInput,
) -> Annotated[CallToolResult, SearchResult]:
    """Search NYC Open Data catalog for datasets.

    Uses Socrata search engine (Solr) for full-text search across titles,
    descriptions, tags, and metadata of all 2000+ datasets.

    Returns:
        Structured ``SearchResult`` (JSON, machine-readable IDs for
        chaining with ``nyc_get_dataset``) plus readable Markdown.
    """
    try:
        # Solr treats q=* differently from q=*:* - only latter returns all datasets
        query = "*:*" if params.query.strip() == "*" else params.query

        api_params: dict = {
            "$query": query,
            "$limit": params.rows,
            "$offset": params.offset,
        }
        
        # Socrata uses different parameter names
        if params.sort:
            api_params["$order"] = params.sort
        
        # Filter by category if specified
        if params.filter_category:
            api_params["$where"] = f"category={soql_str(params.filter_category)}"

        # Use the dataset search endpoint
        result = await socrata_request("", "json", **api_params)
        
        # Parse Socrata response format
        total = len(result) if isinstance(result, list) else 0
        summaries = [to_dataset_summary(ds) for ds in result[:params.rows]] if isinstance(result, list) else []

        next_offset = (
            params.offset + len(summaries) if total > params.offset + len(summaries) else None
        )
        
        model = SearchResult(
            query=params.query,
            total=total,
            offset=params.offset,
            datasets=summaries,
        )

        # Build Markdown output
        lines = [
            f"## Search results for '{params.query}'",
            f"*Total: {total} datasets, showing: {len(summaries)}*",
            "",
        ]

        for ds in summaries:
            lines.append(format_dataset_summary(ds))
            lines.append("")

        if next_offset is not None:
            lines.append(f"*[More results available from offset {next_offset}]*")

        return tool_result({
            "model": model.model_dump(),
            "markdown": "\n".join(lines),
        })

    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Dataset Search"),
        })


class GetDatasetInput(BaseModel):
    """Input for getting dataset details."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dataset_id: str = Field(
        ...,
        description="Dataset identifier (Socrata dataset ID, e.g., '7c3d-6b2j')",
        min_length=1,
        max_length=100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_get_dataset",
    annotations=ToolAnnotations(
        title="Get Dataset Details",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_get_dataset(params: GetDatasetInput) -> str:
    """Retrieve details for a specific NYC Open Data dataset.

    Returns dataset metadata, description, tags, and resource information.

    Args:
        dataset_id: Socrata dataset identifier
        format: Output format ('markdown' or 'json')

    Returns:
        Dataset details in specified format
    """
    try:
        # Get dataset metadata from Socrata
        result = await socrata_request(params.dataset_id, "json")
        
        if not result:
            return handle_api_error(Exception("Dataset not found"), "Get Dataset")
        
        # Parse dataset info
        dataset_info = {
            "id": params.dataset_id,
            "name": result.get("name", ""),
            "title": result.get("title", result.get("name", "")),
            "description": result.get("description", ""),
            "metadata_modified": result.get("modified", ""),
            "tags": result.get("tags", []),
            "resources": result.get("resources", []),
        }
        
        model = GetDatasetResult(**dataset_info)
        
        if params.format == "json":
            return json_out(model.model_dump())
        
        # Build Markdown output
        lines = [
            f"## Dataset: {model.title or model.name}",
            f"*ID: {model.id}*",
            "",
            f"{model.description}",
            "",
            f"**Aktualisiert:** {model.metadata_modified}",
            f"**Tags:** {', '.join(model.tags)}" if model.tags else "",
            "",
            "### Ressourcen",
            "",
        ]
        
        for resource in model.resources:
            lines.append(f"- **{resource.name}** ({resource.format})")
            lines.append(f"  URL: {resource.url}")
            lines.append("")
        
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "Get Dataset")


class ListCategoriesInput(BaseModel):
    """Input for listing categories."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_list_categories",
    annotations=ToolAnnotations(
        title="List Dataset Categories",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_list_categories(params: ListCategoriesInput) -> str:
    """List available dataset categories in NYC Open Data.

    Returns:
        List of category names
    """
    if params.format == "json":
        return json_out({"categories": NYC_CATEGORIES})
    
    lines = [
        "## Available Categories",
        "",
    ]
    
    for i, category in enumerate(NYC_CATEGORIES, 1):
        lines.append(f"{i}. {category}")
    
    return "\n".join(lines)


class ListTagsInput(BaseModel):
    """Input for listing tags."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: NYCCategory | None = Field(
        default=None,
        description=f"Filter tags by category. Available: {', '.join(NYC_CATEGORIES)}",
    )
    limit: int = Field(default=50, description="Maximum number of tags to return", ge=1, le=100)


@mcp.tool(
    name="nyc_list_tags",
    annotations=ToolAnnotations(
        title="List Dataset Tags",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_list_tags(params: ListTagsInput) -> str:
    """List popular tags from NYC Open Data datasets.

    Args:
        category: Optional category filter
        limit: Maximum number of tags to return

    Returns:
        List of tags
    """
    # For now, return a sample of common NYC Open Data tags
    # In production, this would query the Socrata API for popular tags
    common_tags = [
        "waste", "recycling", "trash", "sanitation", "dsny",
        "air quality", "environment", "pollution", "emissions",
        "transportation", "mta", "subway", "bus", "taxi",
        "housing", "buildings", "pluto", "zoning",
        "health", "hospitals", "covid", "diseases",
        "education", "schools", "students", "teachers",
        "public safety", "police", "fire", "911",
        "economy", "business", "jobs", "tax",
        "demographics", "population", "census", "race",
        "budget", "finance", "spending", "contracts",
    ]
    
    if params.category:
        # Filter tags by category (simplified mapping)
        category_tags = {
            "waste-management": ["waste", "recycling", "trash", "sanitation", "dsny"],
            "environment": ["air quality", "environment", "pollution", "emissions"],
            "transportation": ["transportation", "mta", "subway", "bus", "taxi"],
            "housing-development": ["housing", "buildings", "pluto", "zoning"],
            "health": ["health", "hospitals", "covid", "diseases"],
            "education": ["education", "schools", "students", "teachers"],
            "public-safety": ["public safety", "police", "fire", "911"],
            "business": ["economy", "business", "jobs", "tax"],
            "city-government": ["budget", "finance", "spending", "contracts"],
        }
        tags = category_tags.get(params.category, [])
    else:
        tags = common_tags
    
    tags = tags[:params.limit]
    
    return "\n".join([f"- {tag}" for tag in tags])


class TagSearchInput(BaseModel):
    """Input for searching datasets by tag."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tag: str = Field(
        ...,
        description="Tag to search for",
        min_length=1,
        max_length=100,
    )
    rows: int = Field(default=10, description="Number of results (max. 50)", ge=1, le=50)


@mcp.tool(
    name="nyc_find_datasets_by_tag",
    annotations=ToolAnnotations(
        title="Find Datasets by Tag",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_find_datasets_by_tag(params: TagSearchInput) -> str:
    """Find datasets that have a specific tag.

    Args:
        tag: Tag to search for
        rows: Maximum number of results

    Returns:
        List of datasets with the specified tag
    """
    try:
        # Search for datasets with this tag
        api_params = {
            "$query": params.tag,
            "$limit": params.rows,
        }
        
        result = await socrata_request("", "json", **api_params)
        
        if isinstance(result, list):
            summaries = [to_dataset_summary(ds) for ds in result[:params.rows]]
            
            lines = [
                f"## Datasets tagged '{params.tag}'",
                f"*Found: {len(summaries)} datasets*",
                "",
            ]
            
            for ds in summaries:
                lines.append(format_dataset_summary(ds))
                lines.append("")
            
            return "\n".join(lines)
        else:
            return handle_api_error(Exception("Unexpected response format"), "Tag Search")
            
    except Exception as e:
        return handle_api_error(e, "Tag Search")


class AnalyzeDatasetInput(BaseModel):
    """Input for analyzing a dataset."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dataset_id: str = Field(
        ...,
        description="Dataset identifier to analyze",
        min_length=1,
        max_length=100,
    )


@mcp.tool(
    name="nyc_analyze_dataset",
    annotations=ToolAnnotations(
        title="Analyze Dataset Structure",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_analyze_dataset(params: AnalyzeDatasetInput) -> str:
    """Analyze the structure of a specific dataset.

    Returns information about fields, data types, and sample values.

    Args:
        dataset_id: Dataset identifier

    Returns:
        Analysis of dataset structure
    """
    try:
        # Get dataset metadata
        result = await socrata_request(params.dataset_id, "json")
        
        if not result:
            return handle_api_error(Exception("Dataset not found"), "Analyze Dataset")
        
        # Extract field information
        columns = result.get("columns", [])
        field_count = len(columns)
        
        fields = []
        for col in columns:
            field_info = {
                "name": col.get("name", ""),
                "type": col.get("type", "string"),
                "description": col.get("description", ""),
            }
            fields.append(field_info)
        
        # Get sample data to estimate row count
        sample_result = await socrata_request(params.dataset_id, "json", **{"$limit": 1})
        row_count = len(sample_result) if isinstance(sample_result, list) else 0
        
        analysis = AnalysisResult(
            dataset_id=params.dataset_id,
            field_count=field_count,
            row_count=row_count,
            fields=fields,
        )
        
        lines = [
            f"## Analyse: {result.get('name', params.dataset_id)}",
            "",
            f"**Felder:** {field_count}",
            f"**Rows (estimated):** {row_count}",
            "",
            "### Felder",
            "",
        ]
        
        for field in fields:
            lines.append(f"- **{field['name']}** ({field['type']})")
            if field.get("description"):
                lines.append(f"  {field['description']}")
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "Analyze Dataset")


@mcp.tool(
    name="nyc_catalog_stats",
    annotations=ToolAnnotations(
        title="Catalog Statistics",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_catalog_stats() -> str:
    """Get statistics about the NYC Open Data catalog.

    Returns:
        Overview statistics about available datasets and categories
    """
    lines = [
        "## NYC Open Data Katalog Statistik",
        "",
        f"**Categories:** {len(NYC_CATEGORIES)}",
        f"**Available:** {', '.join(NYC_CATEGORIES)}",
        "",
        "### Popular Datasets",
        "",
        "- DSNY Monthly Tonnage Reports",
        "- NYC Organics Collection Pilot",
        "- Commercial Waste Zones",
        "- Facility Locations (Transfer Stations, Composting, AD)",
        "- Recycling Contamination Datasets",
        "- Zero Waste NYC Datasets",
        "",
        "### API-Endpunkte",
        "",
        "- Socrata API: https://data.cityofnewyork.us/api/views",
        "- NOAA Weather: https://api.weather.gov",
        "- EPA AirNow: https://www.airnowapi.org",
        "- MTA GTFS-Realtime: https://api.mta.info",
    ]
    
    return "\n".join(lines)
