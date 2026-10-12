"""NYC geodata tools: layers, features, and spatial queries."""

from __future__ import annotations

from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import GEOHUB_LAYERS, GeoLayerId, OutputFormat
from ..formatters import (
    FORMAT_FIELD_DESC as _FORMAT_FIELD_DESC,
    handle_api_error,
    json_out,
    md_table,
)
from ..http_client import http_get_json, socrata_request
from ..models import GeoFeature, GeoLayer, tool_result


class GeoLayersInput(BaseModel):
    """Input for listing geographic layers."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)



# Real NYC Open Data geospatial datasets backing the conceptual layers.
# layer_id -> (socrata dataset id, geometry column, label column)
# Layers not listed here fall back to labeled simulated data.
GEO_DATASETS: dict[str, tuple[str, str, str]] = {
    "boroughs": ("gthc-hcne", "the_geom", "boroname"),
    "neighborhoods": ("9nt8-h7nd", "the_geom", "ntaname"),
    "parks": ("enfh-gkve", "location", "name"),
    "zip_codes": ("pri4-ifjk", "the_geom", "modzcta"),
}


def _row_to_feature(row: dict, geom_col: str) -> GeoFeature:
    """Shape a Socrata geospatial row as a GeoFeature."""
    geom = row.get(geom_col) or {}
    if isinstance(geom, str):
        try:
            import json as _json
            geom = _json.loads(geom)
        except Exception:
            geom = {}
    properties = {
        k: v for k, v in row.items()
        if not k.startswith(":") and k != geom_col and v is not None
    }
    return GeoFeature(
        id=str(row.get(":id", properties.get("gispropnum", "unknown"))),
        type=geom.get("type", "Unknown") if isinstance(geom, dict) else "Unknown",
        geometry=geom if isinstance(geom, dict) else {},
        properties=properties,
    )


async def _query_geo_layer(
    layer_id: str,
    limit: int,
    where: str | None = None,
) -> list[GeoFeature] | None:
    """Query the real geospatial dataset for a layer.

    Returns None when the layer has no real backing (caller falls back
    to labeled simulated data) or when the request fails.
    """
    mapping = GEO_DATASETS.get(layer_id)
    if not mapping:
        return None
    dataset_id, geom_col, _label = mapping
    params: dict = {"$limit": min(limit, 100)}
    if where:
        params["$where"] = where
    try:
        rows = await socrata_request(dataset_id, "json", **params)
    except Exception:
        return None
    if not rows:
        return None
    return [_row_to_feature(r, geom_col) for r in rows if isinstance(r, dict)]

@mcp.tool(
    name="nyc_geo_layers",
    annotations=ToolAnnotations(
        title="List Geographic Layers",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_geo_layers(params: GeoLayersInput) -> Annotated[CallToolResult, str]:
    """List available geographic layers from NYC GeoHub.

    Returns:
        List of available geographic layers with descriptions
    """
    try:
        layers = []
        for layer_id, (service_name, typename, description) in GEOHUB_LAYERS.items():
            layer = GeoLayer(
                id=layer_id,
                name=service_name,
                description=description,
                features=[],
            )
            layers.append(layer)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data": [layer.model_dump() for layer in layers],
                "markdown": json_out([layer.model_dump() for layer in layers]),
            })
        
        # Format as Markdown
        lines = [
            "## Available Geo Data Layers NYC",
            f"*Total: {len(layers)} layers*",
            "",
        ]
        
        for i, layer in enumerate(layers, 1):
            lines.append(f"{i}. **{layer.name}** ({layer.id})")
            lines.append(f"   {layer.description}")
            lines.append("")
        
        return tool_result({
            "status": "success",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Geo Layers"),
        })


class GeoFeaturesInput(BaseModel):
    """Input for getting geographic features."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    layer_id: GeoLayerId = Field(
        ...,
        description=f"Layer identifier. Available: {', '.join(GEOHUB_LAYERS.keys())}",
    )
    limit: int = Field(default=100, description="Maximum number of features", ge=1, le=1000)
    bbox: str | None = Field(
        default=None,
        description="Bounding box filter (minx,miny,maxx,maxy)",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_geo_features",
    annotations=ToolAnnotations(
        title="Get Geographic Features",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_geo_features(params: GeoFeaturesInput) -> Annotated[CallToolResult, str]:
    """Retrieve features from a specific geographic layer.

    Args:
        layer_id: Layer identifier
        limit: Maximum number of features
        bbox: Optional bounding box filter
        format: Output format

    Returns:
        Features from the specified layer
    Layers with a real NYC Open Data backing return live data; others fall
    back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get layer info
        if params.layer_id not in GEOHUB_LAYERS:
            return tool_result({
                "status": "error",
                "error": f"Unknown layer: {params.layer_id}",
                "markdown": f"Unknown layer: {params.layer_id}",
            })
        
        service_name, typename, description = GEOHUB_LAYERS[params.layer_id]

        # Real path: query the NYC Open Data geospatial dataset
        where = None
        if params.bbox:
            mapping = GEO_DATASETS.get(params.layer_id)
            if mapping:
                _ds, geom_col, _lb = mapping
                minx, miny, maxx, maxy = params.bbox
                where = (
                    f"within_box({geom_col}, {miny}, {minx}, {maxy}, {maxx})"
                )
        features = await _query_geo_layer(params.layer_id, params.limit, where)
        simulated = not features
        if simulated:
            # Labeled simulated fallback for layers without a real dataset
            features = _generate_sample_features(params.layer_id, params.limit)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": {
                    "layer_id": params.layer_id,
                    "layer_name": service_name,
                    "description": description,
                    "features": [f.model_dump() for f in features],
                },
                "markdown": json_out({
                    "layer_id": params.layer_id,
                    "layer_name": service_name,
                    "description": description,
                    "features": [f.model_dump() for f in features],
                }),
            })
        
        # Format as Markdown
        lines = [
            f"## Geo Data: {service_name}",
            f"*Layer: {params.layer_id}*",
            f"*Description: {description}*",
            f"*Features: {len(features)}*",
            "",
        ]
        
        for i, feature in enumerate(features[:10], 1):  # Show first 10
            lines.append(f"### Feature {i}")
            lines.append(f"- **ID:** {feature.id}")
            lines.append(f"- **Type:** {feature.type}")
            
            # Show geometry summary
            geom = feature.geometry
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                lines.append(f"- **Coordinates:** {coords[1]:.6f}, {coords[0]:.6f}")
            elif geom.get("type") == "Polygon":
                lines.append(f"- **Polygon with {len(geom.get('coordinates', [[]]))} points")
            
            # Show properties
            if feature.properties:
                lines.append("  **Properties:**")
                for key, value in list(feature.properties.items())[:5]:
                    lines.append(f"  - {key}: {value}")
            
            lines.append("")
        
        if len(features) > 10:
            lines.append(f"*... and {len(features) - 10} more features*")
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Geo Features"),
        })


def _generate_sample_features(layer_id: str, limit: int) -> list[GeoFeature]:
    """Generate sample features for a given layer."""
    features = []
    
    # Sample coordinates for NYC
    manhattan_coords = (-73.9857, 40.7484)
    brooklyn_coords = (-73.9680, 40.6782)
    queens_coords = (-73.8334, 40.7421)
    bronx_coords = (-73.9254, 40.8496)
    staten_island_coords = (-74.1561, 40.5790)
    
    # Borough boundaries
    if layer_id == "boroughs":
        boroughs = [
            ("Manhattan", manhattan_coords, {"population": 1600000, "area_km2": 59.1}),
            ("Brooklyn", brooklyn_coords, {"population": 2600000, "area_km2": 183.0}),
            ("Queens", queens_coords, {"population": 2400000, "area_km2": 283.9}),
            ("Bronx", bronx_coords, {"population": 1500000, "area_km2": 109.0}),
            ("Staten Island", staten_island_coords, {"population": 500000, "area_km2": 151.5}),
        ]
        
        for i, (name, coords, props) in enumerate(boroughs[:limit]):
            feature = GeoFeature(
                id=f"borough_{i+1}",
                type="Feature",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[
                        [coords[0] - 0.1, coords[1] - 0.1],
                        [coords[0] + 0.1, coords[1] - 0.1],
                        [coords[0] + 0.1, coords[1] + 0.1],
                        [coords[0] - 0.1, coords[1] + 0.1],
                        [coords[0] - 0.1, coords[1] - 0.1],
                    ]],
                },
                properties={"name": name, **props},
            )
            features.append(feature)
    
    # Neighborhoods
    elif layer_id == "neighborhoods":
        neighborhoods = [
            ("Times Square", (-73.9851, 40.7580), {"borough": "Manhattan"}),
            ("Central Park", (-73.9683, 40.7829), {"borough": "Manhattan"}),
            ("Williamsburg", (-73.9596, 40.7081), {"borough": "Brooklyn"}),
            ("Astoria", (-73.9238, 40.7722), {"borough": "Queens"}),
            ("Fordham", (-73.8986, 40.8652), {"borough": "Bronx"}),
        ]
        
        for i, (name, coords, props) in enumerate(neighborhoods[:limit]):
            feature = GeoFeature(
                id=f"neighborhood_{i+1}",
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": list(coords),
                },
                properties={"name": name, **props},
            )
            features.append(feature)
    
    # Council districts
    elif layer_id == "council_districts":
        for i in range(1, min(51, limit + 1)):
            feature = GeoFeature(
                id=f"council_{i}",
                type="Feature",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[
                        [-74.0, 40.7],
                        [-73.9, 40.7],
                        [-73.9, 40.8],
                        [-74.0, 40.8],
                        [-74.0, 40.7],
                    ]],
                },
                properties={"district": i, "name": f"Council District {i}"},
            )
            features.append(feature)
    
    # Subway stations
    elif layer_id == "subway_stations":
        stations = [
            ("Times Square", (-73.9851, 40.7580), {"lines": ["1", "2", "3", "7", "N", "Q", "R", "W", "S"]}),
            ("Grand Central", (-73.9772, 40.7527), {"lines": ["4", "5", "6", "7", "S"]}),
            ("Union Square", (-73.9900, 40.7350), {"lines": ["4", "5", "6", "L", "N", "Q", "R", "W"]}),
            ("Fulton St", (-74.0060, 40.7128), {"lines": ["2", "3", "4", "5", "A", "C", "E", "J", "Z"]}),
            ("Atlantic Av", (-73.9683, 40.6728), {"lines": ["2", "3", "4", "5", "B", "D", "N", "Q", "R"]}),
        ]
        
        for i, (name, coords, props) in enumerate(stations[:limit]):
            feature = GeoFeature(
                id=f"station_{i+1}",
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": list(coords),
                },
                properties={"name": name, **props},
            )
            features.append(feature)
    
    # Waste facilities
    elif layer_id == "waste_facilities":
        facilities = [
            ("North River WPCP", (-74.0060, 40.7580), {"type": "Wastewater Treatment", "capacity": 120000000}),
            ("Wards Island WPCP", (-73.9167, 40.7833), {"type": "Wastewater Treatment", "capacity": 275000000}),
            ("Hunts Point WPCP", (-73.8667, 40.8000), {"type": "Wastewater Treatment", "capacity": 200000000}),
            ("26th Ward Transfer Station", (-73.9857, 40.7484), {"type": "Transfer Station", "capacity": 500000}),
            ("Springfield Gardens Composting", (-73.7500, 40.6667), {"type": "Composting Facility", "capacity": 100000}),
        ]
        
        for i, (name, coords, props) in enumerate(facilities[:limit]):
            feature = GeoFeature(
                id=f"facility_{i+1}",
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": list(coords),
                },
                properties={"name": name, **props},
            )
            features.append(feature)
    
    # Recycling centers
    elif layer_id == "recycling_centers":
        centers = [
            ("Manhattan Recycling Center", (-73.9857, 40.7484), {"type": "Recycling", "materials": ["Paper", "Plastic", "Metal"]}),
            ("Brooklyn Recycling Center", (-73.9680, 40.6782), {"type": "Recycling", "materials": ["Paper", "Plastic", "Metal", "Glass"]}),
            ("Queens Recycling Center", (-73.8334, 40.7421), {"type": "Recycling", "materials": ["Paper", "Plastic", "Metal"]}),
            ("Bronx Recycling Center", (-73.9254, 40.8496), {"type": "Recycling", "materials": ["Paper", "Plastic", "Metal", "Glass"]}),
            ("Staten Island Recycling Center", (-74.1561, 40.5790), {"type": "Recycling", "materials": ["Paper", "Plastic", "Metal"]}),
        ]
        
        for i, (name, coords, props) in enumerate(centers[:limit]):
            feature = GeoFeature(
                id=f"recycling_{i+1}",
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": list(coords),
                },
                properties={"name": name, **props},
            )
            features.append(feature)
    
    # Default: Points for other layers
    else:
        for i in range(limit):
            feature = GeoFeature(
                id=f"feature_{layer_id}_{i+1}",
                type="Feature",
                geometry={
                    "type": "Point",
                    "coordinates": [
                        -73.9857 + (i * 0.01),
                        40.7484 + (i * 0.01),
                    ],
                },
                properties={"name": f"Feature {i+1}", "layer": layer_id},
            )
            features.append(feature)
    
    return features


class SpatialQueryInput(BaseModel):
    """Input for spatial queries."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    layer_id: GeoLayerId = Field(
        ...,
        description=f"Layer identifier. Available: {', '.join(GEOHUB_LAYERS.keys())}",
    )
    latitude: float = Field(..., description="Latitude (WGS84)", ge=-90, le=90)
    longitude: float = Field(..., description="Longitude (WGS84)", ge=-180, le=180)
    radius_meters: float = Field(default=1000, description="Search radius in meters", ge=1, le=10000)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_geo_spatial_query",
    annotations=ToolAnnotations(
        title="Spatial Query",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_geo_spatial_query(params: SpatialQueryInput) -> Annotated[CallToolResult, str]:
    """Query features within a radius of a point.

    Args:
        layer_id: Layer identifier
        latitude: Latitude in WGS84
        longitude: Longitude in WGS84
        radius_meters: Search radius in meters
        format: Output format

    Returns:
        Features within the specified radius
    Layers with a real NYC Open Data backing return live data; others fall
    back to simulated sample data, labeled as such in the response.
    """
    try:
        # Real path: server-side radius query on the layer's dataset.
        # Falls back to labeled simulated data when the layer has no
        # spatial backing (or the query fails).
        mapping = GEO_DATASETS.get(params.layer_id)
        where = None
        if mapping:
            _ds, geom_col, _lb = mapping
            where = (
                f"within_circle({geom_col}, {params.latitude}, "
                f"{params.longitude}, {params.radius_meters})"
            )
        features = await _query_geo_layer(params.layer_id, 10, where)
        simulated = not features
        if simulated:
            features = _generate_sample_features(params.layer_id, 10)

        # Filter features that are "near" the point (simplified)
        filtered_features = []
        for feature in features:
            if feature.geometry.get("type") == "Point":
                coords = feature.geometry.get("coordinates", [])
                if coords:
                    # Simple distance check (not actual geodesic distance)
                    lat_diff = abs(coords[1] - params.latitude)
                    lon_diff = abs(coords[0] - params.longitude)
                    # Approximate: 1 degree latitude ~ 111km, 1 degree longitude ~ 111km * cos(lat)
                    distance_km = (lat_diff * 111 + lon_diff * 111 * abs(params.latitude) / 90)
                    if distance_km <= (params.radius_meters / 1000):
                        filtered_features.append(feature)
            else:
                # For polygons, include if center is near
                filtered_features.append(feature)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "nyc-open-data-socrata",
                "data": [f.model_dump() for f in filtered_features],
                "markdown": json_out([f.model_dump() for f in filtered_features]),
            })
        
        # Format as Markdown
        lines = [
            f"## Spatial Query: {params.layer_id}",
            f"*Coordinates: {params.latitude:.6f}, {params.longitude:.6f}*",
            f"*Radius: {params.radius_meters}m*",
            f"*Features found: {len(filtered_features)}*",
            "",
        ]
        
        for i, feature in enumerate(filtered_features[:10], 1):
            lines.append(f"### Feature {i}")
            lines.append(f"- **ID:** {feature.id}")
            lines.append(f"- **Type:** {feature.type}")
            
            if feature.geometry.get("type") == "Point":
                coords = feature.geometry.get("coordinates", [])
                lines.append(f"- **Coordinates:** {coords[1]:.6f}, {coords[0]:.6f}")
            
            if feature.properties:
                lines.append("  **Properties:**")
                for key, value in list(feature.properties.items())[:5]:
                    lines.append(f"  - {key}: {value}")
            
            lines.append("")
        
        if len(filtered_features) > 10:
            lines.append(f"*... and {len(filtered_features) - 10} more features*")
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "nyc-open-data-socrata",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Spatial Query"),
        })
