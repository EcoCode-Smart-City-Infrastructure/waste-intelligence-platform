"""NYC Open Data datastore tools: query, SQL, and data access."""

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
from ..http_client import socrata_request
from ..models import tool_result


class DatastoreQueryInput(BaseModel):
    """Input for datastore query."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_id: str = Field(
        ...,
        description="Resource identifier (Socrata resource ID)",
        min_length=1,
        max_length=100,
    )
    query: str = Field(
        default="",
        description="SoQL query string (e.g., 'SELECT * WHERE population > 1000')",
    )
    limit: int = Field(default=100, description="Maximum number of rows to return", ge=1, le=1000)
    offset: int = Field(default=0, description="Offset for pagination", ge=0)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_datastore_query",
    annotations=ToolAnnotations(
        title="Query Dataset Resource",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_datastore_query(
    params: DatastoreQueryInput,
) -> Annotated[CallToolResult, str]:
    """Query a specific resource in a NYC Open Data dataset using SoQL.

    SoQL is similar to SQL but with some differences specific to Socrata.

    Args:
        resource_id: Socrata resource identifier
        query: SoQL query string
        limit: Maximum number of rows
        offset: Pagination offset
        format: Output format

    Returns:
        Query results in specified format
    """
    try:
        # Build query parameters
        api_params = {
            "$limit": params.limit,
            "$offset": params.offset,
        }
        
        # Add query if specified
        if params.query:
            api_params["$query"] = params.query
        
        # Execute query
        result = await socrata_request(params.resource_id, "json", **api_params)
        
        if not result:
            return tool_result({
                "status": "error",
                "error": "No data returned",
                "markdown": "Keine Daten zur\u00fcckgegeben.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
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
                    f"## Abfrageergebnisse f\u00fcr Resource {params.resource_id}",
                    f"*Zeilen: {len(result)}*",
                    "",
                    md_table(headers, rows),
                ]
                
                return tool_result({
                    "status": "success",
                    "markdown": "\n".join(lines),
                })
        
        return tool_result({
            "status": "success",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Datastore Query"),
        })


class DatastoreSqlInput(BaseModel):
    """Input for SQL query on datastore."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_id: str = Field(
        ...,
        description="Resource identifier (Socrata resource ID)",
        min_length=1,
        max_length=100,
    )
    sql: str = Field(
        ...,
        description="SQL SELECT query (only SELECT statements allowed)",
        min_length=1,
        max_length=2000,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_datastore_sql",
    annotations=ToolAnnotations(
        title="SQL Query on Dataset",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_datastore_sql(
    params: DatastoreSqlInput,
) -> Annotated[CallToolResult, str]:
    """Execute a SQL SELECT query on a NYC Open Data resource.

    Only SELECT statements are allowed. The query is executed via Socrata's
    SoQL endpoint which supports a subset of SQL.

    Args:
        resource_id: Socrata resource identifier
        sql: SQL SELECT query
        format: Output format

    Returns:
        Query results in specified format
    """
    try:
        # Validate that this is a SELECT query
        sql_upper = params.sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            return tool_result({
                "status": "error",
                "error": "Only SELECT queries are allowed",
                "markdown": "Nur SELECT-Abfragen sind erlaubt.",
            })
        
        # Execute SQL query via Socrata
        # Note: Socrata's SoQL endpoint accepts $query parameter with SQL-like syntax
        api_params = {
            "$query": params.sql,
        }
        
        result = await socrata_request(params.resource_id, "json", **api_params)
        
        if not result:
            return tool_result({
                "status": "error",
                "error": "No data returned",
                "markdown": "Keine Daten zur\u00fcckgegeben.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
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
                    f"## SQL-Abfrageergebnisse f\u00fcr Resource {params.resource_id}",
                    f"*Abfrage: {params.sql[:100]}...*",
                    f"*Zeilen: {len(result)}*",
                    "",
                    md_table(headers, rows),
                ]
                
                return tool_result({
                    "status": "success",
                    "markdown": "\n".join(lines),
                })
        
        return tool_result({
            "status": "success",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "SQL Query"),
        })


class GetResourceInput(BaseModel):
    """Input for getting resource data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_id: str = Field(
        ...,
        description="Resource identifier",
        min_length=1,
        max_length=100,
    )
    limit: int = Field(default=100, description="Maximum number of rows", ge=1, le=1000)
    offset: int = Field(default=0, description="Pagination offset", ge=0)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_get_resource",
    annotations=ToolAnnotations(
        title="Get Resource Data",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_get_resource(
    params: GetResourceInput,
) -> Annotated[CallToolResult, str]:
    """Retrieve data from a specific resource.

    Args:
        resource_id: Socrata resource identifier
        limit: Maximum number of rows
        offset: Pagination offset
        format: Output format

    Returns:
        Resource data in specified format
    """
    try:
        api_params = {
            "$limit": params.limit,
            "$offset": params.offset,
        }
        
        result = await socrata_request(params.resource_id, "json", **api_params)
        
        if not result:
            return tool_result({
                "status": "error",
                "error": "No data returned",
                "markdown": "Keine Daten zur\u00fcckgegeben.",
            })
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": result,
                "markdown": json_out(result),
            })
        
        # Format as Markdown
        if isinstance(result, list):
            lines = [
                f"## Ressource {params.resource_id}",
                f"*Zeilen: {len(result)}*",
                "",
            ]
            
            for i, row in enumerate(result[:10], 1):  # Show first 10 rows
                if isinstance(row, dict):
                    lines.append(f"### Datensatz {i}")
                    for key, value in row.items():
                        lines.append(f"- **{key}:** {value}")
                    lines.append("")
            
            if len(result) > 10:
                lines.append(f"*... und {len(result) - 10} weitere Datens\u00e4tze*")
            
            return tool_result({
                "status": "success",
                "markdown": "\n".join(lines),
            })
        
        return tool_result({
            "status": "success",
            "markdown": f"Ergebnis: {json_out(result)}",
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Get Resource"),
        })
