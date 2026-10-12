"""Waste Intelligence Platform integration tools.

Provides real-time telemetry, ML forecasting, anomaly detection, 
contamination detection, and knowledge graph queries for NYC waste management.
"""

from __future__ import annotations

from typing import Annotated

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from ..app import mcp
from ..config import OutputFormat
from ..formatters import (
    FORMAT_FIELD_DESC as _FORMAT_FIELD_DESC,
    format_bin_telemetry,
    format_cluster_telemetry,
    format_facility_load,
    format_kg_result,
    format_ml_result,
    handle_api_error,
    json_out,
)
from ..http_client import waste_intel_post, waste_intel_request
from ..models import (
    BinTelemetry,
    ClusterTelemetry,
    FacilityLoad,
    KGQueryResult,
    MLAnomalyResult,
    MLContaminationResult,
    MLForecastResult,
    tool_result,
)


class BinLiveInput(BaseModel):
    """Input for live waste bin telemetry."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    bin_id: str = Field(
        ...,
        description="Waste bin identifier (e.g., 'BIN-00123')",
        min_length=1,
        max_length=100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_wastebin_live",
    annotations=ToolAnnotations(
        title="Live Waste Bin Telemetry",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_wastebin_live(params: BinLiveInput) -> Annotated[CallToolResult, str]:
    """Retrieve real-time telemetry data from a waste bin.

    Data source: Waste Intelligence Platform MQTT/LoRaWAN ingestion layer.

    Args:
        bin_id: Waste bin identifier
        format: Output format

    Returns:
        Latest sensor readings including mass, fill level, and gas levels
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get bin data from Waste Intelligence API
        result = await waste_intel_request("mcp/waste/bin", bin_id=params.bin_id)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_bin_data(params.bin_id)
        
        bin_data = BinTelemetry(**result) if isinstance(result, dict) else BinTelemetry(
            bin_id=params.bin_id,
            timestamp="2026-10-10T12:00:00Z",
            sensors={},
            location={},
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": bin_data.model_dump(),
                "markdown": json_out(bin_data.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_bin_telemetry(bin_data.model_dump()),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Bin Telemetry"),
        })


def _generate_sample_bin_data(bin_id: str) -> dict:
    """Generate sample bin telemetry data."""
    import random
    
    boroughs = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
    borough = random.choice(boroughs)
    
    return {
        "bin_id": bin_id,
        "timestamp": "2026-10-10T12:00:00Z",
        "sensors": {
            "mass_kg": round(random.uniform(0, 500), 2),
            "filllevelpct": round(random.uniform(0, 100), 1),
            "gas_ppm": round(random.uniform(0, 50), 1),
            "temperature_c": round(random.uniform(10, 40), 1),
            "battery_pct": round(random.uniform(50, 100), 1),
        },
        "location": {
            "borough_id": borough,
            "block_id": f"{borough[:3]}-{random.randint(100, 999)}-BLK-{random.randint(1, 50)}",
            "latitude": round(random.uniform(40.5, 40.9), 6),
            "longitude": round(random.uniform(-74.2, -73.7), 6),
        },
    }


class ClusterLiveInput(BaseModel):
    """Input for live waste cluster telemetry."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cluster_id: str = Field(
        ...,
        description="Waste cluster identifier (e.g., 'CLUSTER-001')",
        min_length=1,
        max_length=100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_wastecluster_live",
    annotations=ToolAnnotations(
        title="Live Waste Cluster Telemetry",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_wastecluster_live(params: ClusterLiveInput) -> Annotated[CallToolResult, str]:
    """Retrieve aggregated telemetry data for a waste cluster.

    Data source: Waste Intelligence Platform cluster aggregation layer.

    Args:
        cluster_id: Waste cluster identifier
        format: Output format

    Returns:
        Aggregated metrics including total mass, average fill level, and bin count
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get cluster data from Waste Intelligence API
        result = await waste_intel_request("mcp/waste/cluster", cluster_id=params.cluster_id)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_cluster_data(params.cluster_id)
        
        cluster_data = ClusterTelemetry(**result) if isinstance(result, dict) else ClusterTelemetry(
            cluster_id=params.cluster_id,
            timestamp="2026-10-10T12:00:00Z",
            aggregated={},
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": cluster_data.model_dump(),
                "markdown": json_out(cluster_data.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_cluster_telemetry(cluster_data.model_dump()),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Cluster Telemetry"),
        })


def _generate_sample_cluster_data(cluster_id: str) -> dict:
    """Generate sample cluster telemetry data."""
    import random
    
    return {
        "cluster_id": cluster_id,
        "timestamp": "2026-10-10T12:00:00Z",
        "aggregated": {
            "total_mass_kg": round(random.uniform(1000, 10000), 2),
            "avg_filllevelpct": round(random.uniform(30, 90), 1),
            "max_filllevelpct": round(random.uniform(70, 100), 1),
            "bin_count": random.randint(10, 100),
            "bins_near_full": random.randint(1, 10),
            "avg_gas_ppm": round(random.uniform(0, 50), 1),
            "avg_temperature_c": round(random.uniform(10, 40), 1),
        },
    }


class FacilityLoadInput(BaseModel):
    """Input for waste facility load data."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    facility_id: str = Field(
        ...,
        description="Waste facility identifier (e.g., 'FAC-001')",
        min_length=1,
        max_length=100,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_wastefacility_load",
    annotations=ToolAnnotations(
        title="Waste Facility Load",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_wastefacility_load(params: FacilityLoadInput) -> Annotated[CallToolResult, str]:
    """Retrieve current load and forecast data for a waste facility.

    Data source: Waste Intelligence Platform ML forecasting layer.

    Args:
        facility_id: Waste facility identifier
        format: Output format

    Returns:
        Current load metrics and 24-hour forecast
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Get facility data from Waste Intelligence API
        result = await waste_intel_request("mcp/waste/facility", facility_id=params.facility_id)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_facility_data(params.facility_id)
        
        facility_data = FacilityLoad(**result) if isinstance(result, dict) else FacilityLoad(
            facility_id=params.facility_id,
            facility_name="",
            timestamp="2026-10-10T12:00:00Z",
            load={},
            forecast={},
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": facility_data.model_dump(),
                "markdown": json_out(facility_data.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_facility_load(facility_data.model_dump()),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Facility Load"),
        })


def _generate_sample_facility_data(facility_id: str) -> dict:
    """Generate sample facility load data."""
    import random
    
    facility_names = {
        "FAC-001": "North River Transfer Station",
        "FAC-002": "Hunts Point Transfer Station",
        "FAC-003": "26th Ward Transfer Station",
        "FAC-004": "Springfield Gardens Composting",
        "FAC-005": "Wards Island WPCP",
    }
    
    return {
        "facility_id": facility_id,
        "facility_name": facility_names.get(facility_id, "Unknown Facility"),
        "timestamp": "2026-10-10T12:00:00Z",
        "load": {
            "inbound_mass_kg": round(random.uniform(10000, 100000), 2),
            "outbound_mass_kg": round(random.uniform(5000, 80000), 2),
            "capacity_used_pct": round(random.uniform(30, 95), 1),
            "current_throughput_kg_per_hour": round(random.uniform(1000, 5000), 2),
        },
        "forecast": {
            "predicted_inbound_kg": round(random.uniform(15000, 120000), 2),
            "predicted_outbound_kg": round(random.uniform(8000, 90000), 2),
            "predicted_capacity_pct": round(random.uniform(40, 100), 1),
            "forecast_timestamp": "2026-10-11T12:00:00Z",
        },
    }


class ForecastInput(BaseModel):
    """Input for waste forecasting."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    bin_id: str = Field(
        default="esp32-bin-001",
        description="Waste bin identifier whose telemetry history is forecast",
    )
    features: dict = Field(
        default_factory=dict,
        description="Input features for forecasting (e.g., historical data, weather, events)",
    )
    horizon_hours: int = Field(
        default=24,
        description="Forecast horizon in hours",
        ge=1,
        le=168,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_forecast",
    annotations=ToolAnnotations(
        title="Waste Forecast",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_waste_forecast(params: ForecastInput) -> Annotated[CallToolResult, str]:
    """Generate waste collection forecasts using ML models.

    Data source: Waste Intelligence Platform ML inference engine.

    Args:
        features: Input features for forecasting
        horizon_hours: Forecast horizon in hours
        format: Output format

    Returns:
        Forecast predictions with confidence intervals
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Add default features if none provided
        if not params.features:
            params.features = {
                "historical_tonnage": [10000, 12000, 11000, 13000, 14000],
                "day_of_week": 3,  # Wednesday
                "is_weekend": False,
                "temperature_c": 22.5,
                "precipitation_mm": 0.0,
                "special_events": [],
            }
        
        # Add forecast horizon and bin identity
        params.features["horizon_hours"] = params.horizon_hours
        params.features.setdefault("bin_id", params.bin_id)

        # Get forecast from Waste Intelligence API
        result = await waste_intel_post("mcp/waste/forecast", params.features)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_forecast(params)
        
        forecast = MLForecastResult(**result) if isinstance(result, dict) else MLForecastResult(
            timestamp="2026-10-10T12:00:00Z",
            predicted_value=0.0,
            confidence=0.0,
            model_version="",
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": forecast.model_dump(),
                "markdown": json_out(forecast.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_ml_result(forecast.model_dump(), "Forecast"),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Forecast"),
        })


def _generate_sample_forecast(params: ForecastInput) -> dict:
    """Generate sample forecast data."""
    import random
    
    base_value = sum(params.features.get("historical_tonnage", [10000])) / len(params.features.get("historical_tonnage", [10000]))
    predicted = base_value * (1 + random.uniform(-0.1, 0.1))
    
    return {
        "timestamp": "2026-10-10T12:00:00Z",
        "predicted_value": round(predicted, 2),
        "confidence": round(random.uniform(0.8, 0.99), 3),
        "model_version": "waste-forecast-v2.1",
        "horizon_hours": params.horizon_hours,
        "features_used": list(params.features.keys()),
    }


class AnomalyInput(BaseModel):
    """Input for anomaly detection."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    bin_id: str = Field(
        default="esp32-bin-001",
        description="Waste bin identifier whose latest reading is checked",
    )
    features: dict = Field(
        default_factory=dict,
        description="Input features for anomaly detection (e.g., sensor readings)",
    )
    threshold: float = Field(
        default=0.95,
        description="Anomaly detection threshold (0-1)",
        ge=0,
        le=1,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_anomaly",
    annotations=ToolAnnotations(
        title="Waste Anomaly Detection",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_waste_anomaly(params: AnomalyInput) -> Annotated[CallToolResult, str]:
    """Detect anomalies in waste data using ML models.

    Data source: Waste Intelligence Platform ML inference engine.

    Args:
        features: Input features for anomaly detection
        threshold: Anomaly detection threshold
        format: Output format

    Returns:
        Anomaly detection results with scores
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Add default features if none provided
        if not params.features:
            params.features = {
                "mass_kg": 450.5,
                "filllevelpct": 85.2,
                "gas_ppm": 25.3,
                "temperature_c": 28.1,
            }
        
        # Add threshold and bin identity
        params.features["threshold"] = params.threshold
        params.features.setdefault("bin_id", params.bin_id)

        # Get anomaly detection from Waste Intelligence API
        result = await waste_intel_post("mcp/waste/anomaly", params.features)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_anomaly(params)
        
        anomaly = MLAnomalyResult(**result) if isinstance(result, dict) else MLAnomalyResult(
            timestamp="2026-10-10T12:00:00Z",
            is_anomaly=False,
            anomaly_score=0.0,
            threshold=params.threshold,
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": anomaly.model_dump(),
                "markdown": json_out(anomaly.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_ml_result(anomaly.model_dump(), "Anomaly Detection"),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Waste Anomaly Detection"),
        })


def _generate_sample_anomaly(params: AnomalyInput) -> dict:
    """Generate sample anomaly detection data."""
    import random
    
    # Determine if it's an anomaly based on features
    fill_level = params.features.get("filllevelpct", 50)
    gas_ppm = params.features.get("gas_ppm", 10)
    
    # Higher values are more likely to be anomalies
    anomaly_score = (fill_level / 100) * 0.5 + (gas_ppm / 50) * 0.5
    is_anomaly = anomaly_score > params.threshold
    
    return {
        "timestamp": "2026-10-10T12:00:00Z",
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 3),
        "threshold": params.threshold,
        "features_analyzed": list(params.features.keys()),
    }


class ContaminationInput(BaseModel):
    """Input for contamination detection."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    image_tensor: list | None = Field(
        default=None,
        description="Image tensor for CNN contamination detection",
    )
    image_url: str | None = Field(
        default=None,
        description="URL of image for contamination detection",
    )
    threshold: float = Field(
        default=0.7,
        description="Detection confidence threshold",
        ge=0,
        le=1,
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_contamination",
    annotations=ToolAnnotations(
        title="Contamination Detection",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def nyc_waste_contamination(params: ContaminationInput) -> Annotated[CallToolResult, str]:
    """Detect contamination in recycling streams using CNN models.

    Data source: Waste Intelligence Platform ML inference engine.

    Args:
        image_tensor: Image tensor for CNN detection
        image_url: URL of image for detection
        threshold: Detection confidence threshold
        format: Output format

    Returns:
        Contamination detection results with bounding boxes
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Prepare request data
        request_data = {
            "threshold": params.threshold,
        }
        
        if params.image_tensor:
            request_data["image_tensor"] = params.image_tensor
        if params.image_url:
            request_data["image_url"] = params.image_url
        
        # If no image data provided, use sample
        if not params.image_tensor and not params.image_url:
            request_data["image_url"] = "https://example.com/sample_waste_image.jpg"
        
        # Get contamination detection from Waste Intelligence API
        result = await waste_intel_post("mcp/waste/contamination", request_data)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_contamination(params)
        
        contamination = MLContaminationResult(**result) if isinstance(result, dict) else MLContaminationResult(
            image_id="",
            contamination_type="",
            confidence=0.0,
            bounding_box=None,
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": contamination.model_dump(),
                "markdown": json_out(contamination.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_ml_result(contamination.model_dump(), "Contamination Detection"),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Contamination Detection"),
        })


def _generate_sample_contamination(params: ContaminationInput) -> dict:
    """Generate sample contamination detection data."""
    import random
    
    contamination_types = [
        "Plastic Bag",
        "Food Waste",
        "Diaper",
        "Electronics",
        "Clothing",
        "Hazardous Waste",
        "Construction Debris",
    ]
    
    type_idx = random.randint(0, len(contamination_types) - 1)
    
    return {
        "image_id": "img_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8)),
        "contamination_type": contamination_types[type_idx],
        "confidence": round(random.uniform(params.threshold, 0.99), 3),
        "bounding_box": {
            "x_min": round(random.uniform(0, 0.8), 3),
            "y_min": round(random.uniform(0, 0.8), 3),
            "x_max": round(random.uniform(0.2, 1.0), 3),
            "y_max": round(random.uniform(0.2, 1.0), 3),
        },
    }


class KGQueryInput(BaseModel):
    """Input for knowledge graph queries."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Query for the Waste-to-Resource Knowledge Graph",
        min_length=1,
        max_length=1000,
    )
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_kg_query",
    annotations=ToolAnnotations(
        title="Knowledge Graph Query",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_waste_kg_query(params: KGQueryInput) -> Annotated[CallToolResult, str]:
    """Query the Waste-to-Resource Knowledge Graph.

    Data source: Waste Intelligence Platform Knowledge Graph (W2RKG).

    Args:
        query: Query string for the knowledge graph
        limit: Maximum number of results
        format: Output format

    Returns:
        Knowledge graph query results with entities and relationships
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Prepare request data
        request_data = {
            "query": params.query,
            "limit": params.limit,
        }
        
        # Query knowledge graph via Waste Intelligence API
        result = await waste_intel_post("mcp/waste/kg", request_data)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_kg_result(params)
        
        kg_result = KGQueryResult(**result) if isinstance(result, dict) else KGQueryResult(
            query=params.query,
            results=[],
            execution_time=0.0,
        )
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": kg_result.model_dump(),
                "markdown": json_out(kg_result.model_dump()),
            })
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": format_kg_result(kg_result.model_dump()),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Knowledge Graph Query"),
        })


def _generate_sample_kg_result(params: KGQueryInput) -> dict:
    """Generate sample knowledge graph query results."""
    import random
    
    # Sample entities based on query
    query_lower = params.query.lower()
    
    if "recycling" in query_lower:
        results = [
            {
                "id": "Q12345",
                "label": "Plastic Recycling",
                "type": "Process",
                "description": "Process of recycling plastic materials into new products",
                "score": 0.95,
            },
            {
                "id": "Q67890",
                "label": "Paper Recycling",
                "type": "Process",
                "description": "Process of recycling paper and cardboard materials",
                "score": 0.92,
            },
            {
                "id": "Q24680",
                "label": "Recycling Facility",
                "type": "Infrastructure",
                "description": "Facility that processes recyclable materials",
                "score": 0.88,
            },
        ]
    elif "composting" in query_lower:
        results = [
            {
                "id": "Q13579",
                "label": "Composting",
                "type": "Process",
                "description": "Biological decomposition of organic waste into compost",
                "score": 0.97,
            },
            {
                "id": "Q35791",
                "label": "Organic Waste",
                "type": "Waste Type",
                "description": "Biodegradable waste materials suitable for composting",
                "score": 0.94,
            },
            {
                "id": "Q57913",
                "label": "Compost",
                "type": "Product",
                "description": "Finished compost product used as soil amendment",
                "score": 0.91,
            },
        ]
    elif "waste to energy" in query_lower or "wte" in query_lower:
        results = [
            {
                "id": "Q11111",
                "label": "Waste-to-Energy",
                "type": "Process",
                "description": "Conversion of waste materials into energy through combustion or other methods",
                "score": 0.99,
            },
            {
                "id": "Q22222",
                "label": "Anaerobic Digestion",
                "type": "Process",
                "description": "Biological process that produces biogas from organic waste",
                "score": 0.96,
            },
            {
                "id": "Q33333",
                "label": "Biogas",
                "type": "Energy Source",
                "description": "Gaseous fuel produced from anaerobic digestion of organic waste",
                "score": 0.93,
            },
        ]
    else:
        results = [
            {
                "id": "Q10001",
                "label": "Waste Management",
                "type": "Domain",
                "description": "Collection, transportation, processing, and disposal of waste materials",
                "score": 0.98,
            },
            {
                "id": "Q10002",
                "label": "Circular Economy",
                "type": "Concept",
                "description": "Economic system aimed at eliminating waste and the continual use of resources",
                "score": 0.95,
            },
            {
                "id": "Q10003",
                "label": "Sustainability",
                "type": "Goal",
                "description": "Ability to meet present needs without compromising future generations",
                "score": 0.92,
            },
        ]
    
    # Limit results
    results = results[:params.limit]
    
    return {
        "query": params.query,
        "results": results,
        "execution_time": round(random.uniform(0.1, 0.5), 3),
    }


class CircularEconomyInput(BaseModel):
    """Input for circular economy suggestions."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    waste_type: str = Field(
        ...,
        description="Type of waste material (e.g., 'Plastic', 'Paper', 'Organics', 'Metal')",
        min_length=1,
        max_length=100,
    )
    quantity_kg: float = Field(
        default=100.0,
        description="Quantity of waste in kilograms",
        ge=0.1,
    )
    location: str | None = Field(
        default=None,
        description="Location (borough or district)",
    )
    format: OutputFormat = Field(default="markdown", description=_FORMAT_FIELD_DESC)


@mcp.tool(
    name="nyc_waste_circular_economy",
    annotations=ToolAnnotations(
        title="Circular Economy Suggestions",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def nyc_waste_circular_economy(params: CircularEconomyInput) -> Annotated[CallToolResult, str]:
    """Get circular economy suggestions for waste materials.

    Uses the Waste-to-Resource Knowledge Graph to suggest optimal
    waste-to-resource pathways based on material type, quantity, and location.

    Args:
        waste_type: Type of waste material
        quantity_kg: Quantity of waste
        location: Optional location
        format: Output format

    Returns:
        Suggestions for recycling, composting, or waste-to-energy pathways
    When live data is unavailable, this tool falls back to simulated sample data, labeled as such in the response.
    """
    try:
        # Prepare request data
        request_data = {
            "waste_type": params.waste_type,
            "quantity_kg": params.quantity_kg,
        }
        
        if params.location:
            request_data["location"] = params.location
        
        # Query circular economy suggestions from Waste Intelligence API
        result = await waste_intel_post("mcp/waste/circular_economy", request_data)
        
        simulated = not result
        if simulated:
            # Sample data fallback (labeled as simulated in the response)
            result = _generate_sample_circular_economy(params)
        
        if params.format == "json":
            return tool_result({
                "status": "success",
                "data_source": "simulated" if simulated else "waste-intelligence-api",
                "data": result,
                "markdown": json_out(result),
            })
        
        # Format as Markdown
        lines = [
            f"## Circular economy suggestions for {params.quantity_kg} kg {params.waste_type}",
            "",
        ]
        
        if isinstance(result, list):
            for i, suggestion in enumerate(result, 1):
                lines.append(f"### {i}. {suggestion.get('pathway', 'Unknown')}")
                lines.append(f"- **Type:** {suggestion.get('type', 'Unknown')}")
                lines.append(f"- **Description:** {suggestion.get('description', 'N/A')}")
                lines.append(f"- **Effizienz:** {suggestion.get('efficiency', 0)}%")
                lines.append(f"- **Carbon footprint:** {suggestion.get('carbon_footprint', 0)} kg CO2e")
                if suggestion.get('facilities'):
                    lines.append(f"- **Facilities:** {', '.join(suggestion.get('facilities', []))}")
                lines.append("")
        elif isinstance(result, dict):
            for key, value in result.items():
                lines.append(f"- **{key}:** {value}")
                lines.append("")
        
        return tool_result({
            "status": "success",
            "data_source": "simulated" if simulated else "waste-intelligence-api",
            "markdown": "\n".join(lines),
        })
        
    except Exception as e:
        return tool_result({
            "status": "error",
            "error": str(e),
            "markdown": handle_api_error(e, "Circular Economy Suggestions"),
        })


def _generate_sample_circular_economy(params: CircularEconomyInput) -> list[dict]:
    """Generate sample circular economy suggestions."""
    waste_type_lower = params.waste_type.lower()
    
    if "plastic" in waste_type_lower:
        return [
            {
                "pathway": "Mechanical Recycling",
                "type": "Recycling",
                "description": "Plastic bottles and containers can be mechanically recycled into new plastic products",
                "efficiency": 85,
                "carbon_footprint": params.quantity_kg * 0.5,
                "facilities": ["Sims Municipal Recycling", "Plastic Recycling Inc"],
            },
            {
                "pathway": "Chemical Recycling",
                "type": "Advanced Recycling",
                "description": "Plastic waste can be chemically broken down into monomers for new plastic production",
                "efficiency": 75,
                "carbon_footprint": params.quantity_kg * 0.8,
                "facilities": ["Loop Industries", "Eastman Chemical"],
            },
            {
                "pathway": "Waste-to-Energy",
                "type": "Energy Recovery",
                "description": "Non-recyclable plastics can be used as fuel in waste-to-energy facilities",
                "efficiency": 60,
                "carbon_footprint": params.quantity_kg * 1.2,
                "facilities": ["Covanta Energy", "Wheelabrator"],
            },
        ]
    elif "paper" in waste_type_lower or "cardboard" in waste_type_lower:
        return [
            {
                "pathway": "Paper Recycling",
                "type": "Recycling",
                "description": "Paper and cardboard can be recycled into new paper products",
                "efficiency": 90,
                "carbon_footprint": params.quantity_kg * 0.3,
                "facilities": ["Sims Municipal Recycling", "Paper Recycling Co"],
            },
            {
                "pathway": "Composting",
                "type": "Organic Processing",
                "description": "Soiled paper and cardboard can be composted with organic waste",
                "efficiency": 70,
                "carbon_footprint": params.quantity_kg * 0.4,
                "facilities": ["DSNY Composting Sites", "Private Composters"],
            },
            {
                "pathway": "Waste-to-Energy",
                "type": "Energy Recovery",
                "description": "Non-recyclable paper can be used as fuel",
                "efficiency": 50,
                "carbon_footprint": params.quantity_kg * 1.0,
                "facilities": ["Covanta Energy"],
            },
        ]
    elif "organic" in waste_type_lower or "food" in waste_type_lower:
        return [
            {
                "pathway": "Composting",
                "type": "Organic Processing",
                "description": "Organic waste can be composted to produce soil amendment",
                "efficiency": 85,
                "carbon_footprint": params.quantity_kg * 0.2,
                "facilities": ["DSNY Composting Sites", "Springfield Gardens", "Big Reuse"],
            },
            {
                "pathway": "Anaerobic Digestion",
                "type": "Energy Recovery",
                "description": "Organic waste can be processed via anaerobic digestion to produce biogas",
                "efficiency": 75,
                "carbon_footprint": params.quantity_kg * 0.3,
                "facilities": ["Newtown Creek WPCP", "Wards Island WPCP"],
            },
            {
                "pathway": "Animal Feed",
                "type": "Resource Recovery",
                "description": "Certain food waste can be processed into animal feed",
                "efficiency": 60,
                "carbon_footprint": params.quantity_kg * 0.4,
                "facilities": ["Commercial Animal Feed Producers"],
            },
        ]
    elif "metal" in waste_type_lower:
        return [
            {
                "pathway": "Metal Recycling",
                "type": "Recycling",
                "description": "Metals can be recycled with high efficiency into new metal products",
                "efficiency": 95,
                "carbon_footprint": params.quantity_kg * 0.1,
                "facilities": ["Sims Municipal Recycling", "Metal Recyclers Inc"],
            },
            {
                "pathway": "Scrap Metal",
                "type": "Resource Recovery",
                "description": "Scrap metal can be sold to scrap dealers for recycling",
                "efficiency": 85,
                "carbon_footprint": params.quantity_kg * 0.2,
                "facilities": ["Local Scrap Dealers", "Regional Metal Processors"],
            },
        ]
    else:
        return [
            {
                "pathway": "Material Recovery Facility",
                "type": "Sorting",
                "description": "Mixed waste can be sorted at MRF to recover recyclables",
                "efficiency": 60,
                "carbon_footprint": params.quantity_kg * 0.6,
                "facilities": ["Sims Municipal Recycling", "Action Carting"],
            },
            {
                "pathway": "Waste-to-Energy",
                "type": "Energy Recovery",
                "description": "Non-recyclable waste can be used for energy generation",
                "efficiency": 50,
                "carbon_footprint": params.quantity_kg * 1.1,
                "facilities": ["Covanta Energy", "Wheelabrator"],
            },
            {
                "pathway": "Landfill",
                "type": "Disposal",
                "description": "Last resort disposal option",
                "efficiency": 10,
                "carbon_footprint": params.quantity_kg * 2.0,
                "facilities": ["Out-of-State Landfills"],
            },
        ]
