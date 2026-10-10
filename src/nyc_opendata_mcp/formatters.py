"""Formatters and helpers for NYC Open Data MCP Server.

Provides formatting utilities for tool outputs and error handling.
"""

from __future__ import annotations

import json
from typing import Any

FORMAT_FIELD_DESC = "Ausgabeformat: 'markdown' (lesbar) oder 'json' (maschinenlesbar)"


def md_cell(value: Any) -> str:
    """Escape a value for Markdown table cell."""
    if value is None:
        return "-"
    text = str(value)
    # Escape pipe characters and newlines
    text = text.replace("|", "\\|").replace("\n", " ")
    return text


def md_row(cells: list[Any]) -> str:
    """Format a row for Markdown table."""
    return "| " + " | ".join(md_cell(c) for c in cells) + " |"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Format a Markdown table."""
    lines = [md_row(headers)]
    lines.append(md_row(["-" * len(h) for h in headers]))
    for row in rows:
        lines.append(md_row(row))
    return "\n".join(lines)


def json_out(data: Any, indent: int = 2) -> str:
    """Format data as pretty-printed JSON."""
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def handle_api_error(error: Exception, context: str) -> str:
    """Format an API error for user output."""
    error_type = type(error).__name__
    error_msg = str(error)
    return f"\n\n**Fehler bei {context}:**\n\n```\n{error_type}: {error_msg}\n```\n\nBitte versuchen Sie es sp\u00e4ter erneut oder \u00fccberpr\u00fcfen Sie die Eingabeparameter."


def format_dataset_summary(dataset: dict) -> str:
    """Format a dataset summary for display."""
    title = dataset.get("name", dataset.get("title", "Unbekannt"))
    description = dataset.get("description", "")[:200] + "..." if len(dataset.get("description", "")) > 200 else dataset.get("description", "")
    metadata_modified = dataset.get("metadata_modified", dataset.get("updated_at", ""))
    
    lines = [
        f"### {title}",
        f"*Aktualisiert: {metadata_modified}*",
        f"{description}",
        f"**ID:** `{dataset.get('id', dataset.get('dataset_id', ''))}`",
    ]
    
    if "tags" in dataset:
        tags = dataset["tags"]
        if isinstance(tags, list):
            lines.append(f"**Tags:** {', '.join(tags)}")
    
    return "\n".join(lines)


def format_resource_info(resource: dict) -> str:
    """Format a resource info for display."""
    name = resource.get("name", resource.get("title", "Unbekannt"))
    format_type = resource.get("format", resource.get("type", ""))
    url = resource.get("url", "")
    
    lines = [
        f"- **{name}** ({format_type})",
        f"  URL: {url}",
    ]
    
    if "description" in resource:
        lines.append(f"  {resource['description'][:100]}...")
    
    return "\n".join(lines)


def to_dataset_summary(dataset: dict) -> dict:
    """Convert CKAN/Socrata dataset to summary format."""
    return {
        "id": dataset.get("id", dataset.get("dataset_id", "")),
        "name": dataset.get("name", dataset.get("title", "")),
        "title": dataset.get("title", ""),
        "description": dataset.get("description", ""),
        "metadata_modified": dataset.get("metadata_modified", dataset.get("updated_at", "")),
        "tags": dataset.get("tags", []),
        "resources": dataset.get("resources", []),
    }


def to_resource_info(resource: dict) -> dict:
    """Convert CKAN/Socrata resource to info format."""
    return {
        "id": resource.get("id", resource.get("resource_id", "")),
        "name": resource.get("name", resource.get("title", "")),
        "format": resource.get("format", resource.get("type", "")),
        "url": resource.get("url", ""),
        "description": resource.get("description", ""),
    }


def format_bin_telemetry(bin_data: dict) -> str:
    """Format waste bin telemetry data."""
    bin_id = bin_data.get("bin_id", "Unknown")
    timestamp = bin_data.get("timestamp", "")
    sensors = bin_data.get("sensors", {})
    location = bin_data.get("location", {})
    
    lines = [
        f"## Waste Bin: {bin_id}",
        f"*Timestamp: {timestamp}*",
        "",
        "### Sensor Readings",
        f"- **Mass:** {sensors.get('mass_kg', 0)} kg",
        f"- **Fill Level:** {sensors.get('filllevelpct', 0)}%",
        f"- **Gas:** {sensors.get('gas_ppm', 0)} ppm",
        "",
        "### Location",
        f"- **Borough:** {location.get('borough_id', 'Unknown')}",
        f"- **Block:** {location.get('block_id', 'Unknown')}",
    ]
    
    return "\n".join(lines)


def format_cluster_telemetry(cluster_data: dict) -> str:
    """Format waste cluster telemetry data."""
    cluster_id = cluster_data.get("cluster_id", "Unknown")
    timestamp = cluster_data.get("timestamp", "")
    aggregated = cluster_data.get("aggregated", {})
    
    lines = [
        f"## Waste Cluster: {cluster_id}",
        f"*Timestamp: {timestamp}*",
        "",
        "### Aggregated Metrics",
        f"- **Total Mass:** {aggregated.get('total_mass_kg', 0)} kg",
        f"- **Average Fill Level:** {aggregated.get('avg_filllevelpct', 0)}%",
        f"- **Bin Count:** {aggregated.get('bin_count', 0)}",
    ]
    
    return "\n".join(lines)


def format_facility_load(facility_data: dict) -> str:
    """Format waste facility load data."""
    facility_id = facility_data.get("facility_id", "Unknown")
    facility_name = facility_data.get("facility_name", "")
    timestamp = facility_data.get("timestamp", "")
    load = facility_data.get("load", {})
    forecast = facility_data.get("forecast", {})
    
    lines = [
        f"## Waste Facility: {facility_name} ({facility_id})",
        f"*Timestamp: {timestamp}*",
        "",
        "### Current Load",
        f"- **Inbound Mass:** {load.get('inbound_mass_kg', 0)} kg",
        f"- **Capacity Used:** {load.get('capacity_used_pct', 0)}%",
        "",
        "### Forecast (Next 24h)",
        f"- **Predicted Inbound:** {forecast.get('predicted_inbound_kg', 0)} kg",
        f"- **Predicted Capacity:** {forecast.get('predicted_capacity_pct', 0)}%",
    ]
    
    return "\n".join(lines)


def format_ml_result(result: dict, result_type: str = "Result") -> str:
    """Format ML inference result."""
    lines = [
        f"## {result_type} Result",
        "",
    ]
    
    for key, value in result.items():
        if isinstance(value, (int, float)):
            lines.append(f"- **{key}:** {value}")
        elif isinstance(value, str):
            lines.append(f"- **{key}:** {value}")
        elif isinstance(value, dict):
            lines.append(f"- **{key}:**")
            for subkey, subvalue in value.items():
                lines.append(f"  - {subkey}: {subvalue}")
        elif isinstance(value, list):
            lines.append(f"- **{key}:** {len(value)} items")
    
    return "\n".join(lines)


def format_kg_result(result: dict) -> str:
    """Format Knowledge Graph query result."""
    lines = [
        "## Knowledge Graph Query Result",
        "",
    ]
    
    if "results" in result:
        lines.append(f"**Found {len(result['results'])} results:**")
        for i, item in enumerate(result["results"][:10], 1):  # Show first 10
            lines.append(f"\n{i}. {item.get('label', item.get('name', 'Unknown'))}")
            if "description" in item:
                lines.append(f"   {item['description'][:100]}...")
            if "type" in item:
                lines.append(f"   *Type: {item['type']}*")
    elif "answer" in result:
        lines.append(f"**Answer:** {result['answer']}")
    else:
        lines.append(json_out(result))
    
    return "\n".join(lines)
