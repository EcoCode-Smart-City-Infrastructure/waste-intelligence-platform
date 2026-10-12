"""Data models for NYC Open Data MCP Server.

Defines Pydantic models for tool inputs and outputs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatasetSummary(BaseModel):
    """Summary of a dataset from Socrata."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Dataset identifier")
    name: str = Field(..., description="Dataset name")
    title: str = Field(default="", description="Dataset title")
    description: str = Field(default="", description="Dataset description")
    metadata_modified: str = Field(default="", description="Last modification timestamp")
    tags: list[str] = Field(default_factory=list, description="Dataset tags")


class ResourceInfo(BaseModel):
    """Information about a dataset resource."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Resource identifier")
    name: str = Field(..., description="Resource name")
    format: str = Field(default="", description="Resource format")
    url: str = Field(default="", description="Resource URL")
    description: str = Field(default="", description="Resource description")


class SearchResult(BaseModel):
    """Result of a dataset search."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    query: str = Field(..., description="Search query")
    total: int = Field(..., description="Total number of results")
    offset: int = Field(default=0, description="Pagination offset")
    datasets: list[DatasetSummary] = Field(default_factory=list, description="List of datasets")


class GetDatasetResult(BaseModel):
    """Result of getting dataset details."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Dataset identifier")
    name: str = Field(..., description="Dataset name")
    title: str = Field(default="", description="Dataset title")
    description: str = Field(default="", description="Dataset description")
    metadata_modified: str = Field(default="", description="Last modification timestamp")
    tags: list[str] = Field(default_factory=list, description="Dataset tags")
    resources: list[ResourceInfo] = Field(default_factory=list, description="Dataset resources")


class AnalysisResult(BaseModel):
    """Result of dataset analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    dataset_id: str = Field(..., description="Analyzed dataset identifier")
    field_count: int = Field(..., description="Number of fields")
    row_count: int = Field(..., description="Number of rows")
    fields: list[dict] = Field(default_factory=list, description="Field information")


class DatasetAnalysis(BaseModel):
    """Analysis of a dataset."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    results: list[AnalysisResult] = Field(default_factory=list, description="Analysis results")


class FieldInfo(BaseModel):
    """Information about a dataset field."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    description: str = Field(default="", description="Field description")
    required: bool = Field(default=False, description="Whether field is required")


# Tool result wrapper
def tool_result(data: Any) -> dict:
    """Wrap tool result with consistent structure."""
    return {
        "status": "success",
        "data": data,
    }


# Error result wrapper
def error_result(error: str, details: str = "") -> dict:
    """Wrap error result with consistent structure."""
    return {
        "status": "error",
        "error": error,
        "details": details,
    }


class BinTelemetry(BaseModel):
    """Waste bin telemetry data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    bin_id: str = Field(..., description="Bin identifier")
    timestamp: str = Field(..., description="Timestamp of reading")
    sensors: dict = Field(default_factory=dict, description="Sensor readings")
    location: dict = Field(default_factory=dict, description="Location information")


class ClusterTelemetry(BaseModel):
    """Waste cluster telemetry data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    cluster_id: str = Field(..., description="Cluster identifier")
    timestamp: str = Field(..., description="Timestamp of aggregation")
    aggregated: dict = Field(default_factory=dict, description="Aggregated metrics")


class FacilityLoad(BaseModel):
    """Waste facility load data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(default="", description="Facility name")
    timestamp: str = Field(..., description="Timestamp of reading")
    load: dict = Field(default_factory=dict, description="Load metrics")
    forecast: dict = Field(default_factory=dict, description="Forecast data")


class WeatherData(BaseModel):
    """Weather data from NOAA."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    station: str = Field(..., description="Weather station identifier")
    timestamp: str = Field(..., description="Timestamp of observation")
    temperature: float | None = Field(default=None, description="Temperature in Celsius")
    humidity: float | None = Field(default=None, description="Relative humidity in percent")
    pressure: float | None = Field(default=None, description="Atmospheric pressure in hPa")
    wind_speed: float | None = Field(default=None, description="Wind speed in m/s")
    wind_direction: float | None = Field(default=None, description="Wind direction in degrees")
    precipitation: float | None = Field(default=None, description="Precipitation in mm")


class AirQualityData(BaseModel):
    """Air quality data from EPA AirNow."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    station: str = Field(..., description="Air quality station identifier")
    timestamp: str = Field(..., description="Timestamp of observation")
    aqi: int | None = Field(default=None, description="Air Quality Index")
    pm25: float | None = Field(default=None, description="PM2.5 concentration in μg/m³")
    pm10: float | None = Field(default=None, description="PM10 concentration in μg/m³")
    ozone: float | None = Field(default=None, description="Ozone concentration in ppb")
    no2: float | None = Field(default=None, description="NO2 concentration in ppb")
    so2: float | None = Field(default=None, description="SO2 concentration in ppb")
    co: float | None = Field(default=None, description="CO concentration in ppm")


class WaterQualityData(BaseModel):
    """Water quality data from NYC DEP."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    station: str = Field(..., description="Water quality station identifier")
    timestamp: str = Field(..., description="Timestamp of observation")
    enterococcus: float | None = Field(default=None, description="Enterococcus count in MPN/100mL")
    e_coli: float | None = Field(default=None, description="E. coli count in MPN/100mL")
    dissolved_oxygen: float | None = Field(default=None, description="Dissolved oxygen in mg/L")
    ph: float | None = Field(default=None, description="pH value")
    temperature: float | None = Field(default=None, description="Water temperature in Celsius")
    turbidity: float | None = Field(default=None, description="Turbidity in NTU")


class PedestrianCount(BaseModel):
    """Pedestrian count data from NYC DOT."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    location: str = Field(..., description="Location identifier")
    timestamp: str = Field(..., description="Timestamp of count")
    count: int = Field(..., description="Number of pedestrians")
    direction: str | None = Field(default=None, description="Direction of travel")


class ParkingData(BaseModel):
    """Parking data from NYC DOT."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    lot_id: str = Field(..., description="Parking lot identifier")
    name: str = Field(default="", description="Parking lot name")
    available_spots: int = Field(..., description="Number of available spots")
    total_spots: int = Field(..., description="Total number of spots")
    occupancy_rate: float = Field(..., description="Occupancy rate in percent")
    status: str = Field(default="", description="Lot status")


class MTARidership(BaseModel):
    """MTA ridership data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    line: str = Field(..., description="Subway line identifier")
    station: str = Field(..., description="Station identifier")
    timestamp: str = Field(..., description="Timestamp of observation")
    entries: int = Field(..., description="Number of entries")
    exits: int = Field(..., description="Number of exits")


class GeoFeature(BaseModel):
    """Geographic feature data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Feature identifier")
    type: str = Field(..., description="Feature type")
    geometry: dict = Field(..., description="GeoJSON geometry")
    properties: dict = Field(default_factory=dict, description="Feature properties")


class GeoLayer(BaseModel):
    """Geographic layer data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Layer identifier")
    name: str = Field(..., description="Layer name")
    description: str = Field(default="", description="Layer description")
    features: list[GeoFeature] = Field(default_factory=list, description="Layer features")


class CouncilMember(BaseModel):
    """NYC Council member data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Member identifier")
    name: str = Field(..., description="Member name")
    district: int = Field(..., description="Council district")
    party: str = Field(default="", description="Political party")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")


class Legislation(BaseModel):
    """NYC Council legislation data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Legislation identifier")
    title: str = Field(..., description="Legislation title")
    type: str = Field(..., description="Legislation type")
    status: str = Field(default="", description="Current status")
    introduced_date: str = Field(default="", description="Introduction date")
    sponsors: list[str] = Field(default_factory=list, description="Sponsors")


class WasteDataset(BaseModel):
    """NYC waste management dataset."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    id: str = Field(..., description="Dataset identifier")
    name: str = Field(..., description="Dataset name")
    description: str = Field(default="", description="Dataset description")
    category: str = Field(default="", description="Waste category")
    update_frequency: str = Field(default="", description="Update frequency")
    last_updated: str = Field(default="", description="Last update timestamp")


class MLForecastResult(BaseModel):
    """ML forecast result."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    timestamp: str = Field(..., description="Forecast timestamp")
    predicted_value: float = Field(..., description="Predicted value")
    confidence: float = Field(..., description="Confidence score")
    model_version: str = Field(default="", description="Model version")


class MLAnomalyResult(BaseModel):
    """ML anomaly detection result."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    timestamp: str = Field(..., description="Observation timestamp")
    is_anomaly: bool = Field(..., description="Whether observation is anomalous")
    anomaly_score: float = Field(..., description="Anomaly score")
    threshold: float = Field(..., description="Anomaly threshold")


class MLContaminationResult(BaseModel):
    """ML contamination detection result."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    image_id: str = Field(..., description="Image identifier")
    contamination_type: str = Field(default="", description="Contamination type")
    confidence: float = Field(..., description="Detection confidence")
    bounding_box: dict | None = Field(default=None, description="Bounding box coordinates")


class KGQueryResult(BaseModel):
    """Knowledge Graph query result."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    query: str = Field(..., description="Original query")
    results: list[dict] = Field(default_factory=list, description="Query results")
    execution_time: float = Field(..., description="Query execution time in seconds")
