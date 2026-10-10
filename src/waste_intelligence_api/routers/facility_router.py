"""Router for waste facility telemetry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Config
from ..services.db_client import get_facility_packet
from ..services.packet_builder import validate_facility_packet

router = APIRouter(tags=["Waste Facilities"])

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class FacilityResponse(BaseModel):
    """Response model for facility telemetry."""
    facility_id: str
    facility_name: str
    timestamp: str
    load: dict
    forecast: dict


@router.get("/facility", response_model=FacilityResponse)
async def get_facility(
    facility_id: str = Query(..., description="Waste facility identifier"),
    api_key: str | None = Depends(api_key_header),
):
    """Get current load and forecast data for a waste facility.
    
    Returns current load metrics and 24-hour forecast.
    
    Args:
        facility_id: Waste facility identifier (e.g., 'FAC-001')
        
    Returns:
        Current facility load and forecast packet
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get facility packet from database
    packet = await get_facility_packet(facility_id)
    
    if not packet:
        raise HTTPException(
            status_code=404,
            detail=f"Facility {facility_id} not found",
        )
    
    # Validate packet
    validated_packet = validate_facility_packet(packet)
    
    return validated_packet


@router.get("/facility/history")
async def get_facility_history(
    facility_id: str = Query(..., description="Waste facility identifier"),
    limit: int = Query(100, description="Maximum number of packets to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """Get historical telemetry packets for a waste facility.
    
    Args:
        facility_id: Waste facility identifier
        limit: Maximum number of packets
        offset: Pagination offset
        
    Returns:
        List of historical facility telemetry packets
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get facility history from database
    packets = await get_facility_packet(facility_id, limit=limit, offset=offset, history=True)
    
    if not packets:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for facility {facility_id}",
        )
    
    # Validate and return packets
    validated_packets = [validate_facility_packet(p) for p in packets]
    
    return {
        "facility_id": facility_id,
        "count": len(validated_packets),
        "packets": validated_packets,
    }


@router.get("/facilities")
async def list_facilities(
    facility_type: str | None = Query(None, description="Filter by facility type"),
    borough: str | None = Query(None, description="Filter by borough"),
    limit: int = Query(100, description="Maximum number of facilities to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """List all waste facilities with their latest status.
    
    Args:
        facility_type: Optional facility type filter
        borough: Optional borough filter
        limit: Maximum number of facilities
        offset: Pagination offset
        
    Returns:
        List of waste facilities with latest telemetry
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get list of facilities from database
    facilities = await get_facility_packet(
        limit=limit, 
        offset=offset, 
        facility_type=facility_type, 
        borough=borough, 
        list_all=True
    )
    
    if not facilities:
        raise HTTPException(
            status_code=404,
            detail="No facilities found",
        )
    
    return {
        "count": len(facilities),
        "facilities": facilities,
    }


@router.get("/facility/load")
async def get_facility_load(
    facility_id: str = Query(..., description="Waste facility identifier"),
    api_key: str | None = Depends(api_key_header),
):
    """Get current load data for a waste facility.
    
    Args:
        facility_id: Waste facility identifier
        
    Returns:
        Current load metrics for the facility
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get facility packet
    packet = await get_facility_packet(facility_id)
    
    if not packet:
        raise HTTPException(
            status_code=404,
            detail=f"Facility {facility_id} not found",
        )
    
    # Return only the load data
    return {
        "facility_id": facility_id,
        "facility_name": packet.get("facility_name", ""),
        "load": packet.get("load", {}),
    }


@router.get("/facility/forecast")
async def get_facility_forecast(
    facility_id: str = Query(..., description="Waste facility identifier"),
    hours: int = Query(24, description="Forecast horizon in hours"),
    api_key: str | None = Depends(api_key_header),
):
    """Get forecast data for a waste facility.
    
    Args:
        facility_id: Waste facility identifier
        hours: Forecast horizon in hours
        
    Returns:
        Forecast data for the facility
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get facility packet
    packet = await get_facility_packet(facility_id)
    
    if not packet:
        raise HTTPException(
            status_code=404,
            detail=f"Facility {facility_id} not found",
        )
    
    # Return only the forecast data
    return {
        "facility_id": facility_id,
        "facility_name": packet.get("facility_name", ""),
        "forecast_hours": hours,
        "forecast": packet.get("forecast", {}),
    }
