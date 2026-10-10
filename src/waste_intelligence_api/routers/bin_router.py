"""Router for waste bin telemetry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Config
from ..services.db_client import get_bin_packet
from ..services.packet_builder import validate_bin_packet

router = APIRouter(tags=["Waste Bins"])

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class BinResponse(BaseModel):
    """Response model for bin telemetry."""
    bin_id: str
    timestamp: str
    sensors: dict
    location: dict


@router.get("/bin", response_model=BinResponse)
async def get_bin(
    bin_id: str = Query(..., description="Waste bin identifier"),
    api_key: str | None = Depends(api_key_header),
):
    """Get latest telemetry packet for a waste bin.
    
    Returns real-time sensor readings including mass, fill level, and gas levels.
    
    Args:
        bin_id: Waste bin identifier (e.g., 'BIN-00123')
        
    Returns:
        Latest bin telemetry packet
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get bin packet from database
    packet = await get_bin_packet(bin_id)
    
    if not packet:
        raise HTTPException(
            status_code=404,
            detail=f"Bin {bin_id} not found",
        )
    
    # Validate packet
    validated_packet = validate_bin_packet(packet)
    
    return validated_packet


@router.get("/bin/history")
async def get_bin_history(
    bin_id: str = Query(..., description="Waste bin identifier"),
    limit: int = Query(100, description="Maximum number of packets to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """Get historical telemetry packets for a waste bin.
    
    Args:
        bin_id: Waste bin identifier
        limit: Maximum number of packets
        offset: Pagination offset
        
    Returns:
        List of historical bin telemetry packets
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get bin history from database
    packets = await get_bin_packet(bin_id, limit=limit, offset=offset, history=True)
    
    if not packets:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for bin {bin_id}",
        )
    
    # Validate and return packets
    validated_packets = [validate_bin_packet(p) for p in packets]
    
    return {
        "bin_id": bin_id,
        "count": len(validated_packets),
        "packets": validated_packets,
    }


@router.get("/bins")
async def list_bins(
    borough: str | None = Query(None, description="Filter by borough"),
    district: str | None = Query(None, description="Filter by district"),
    limit: int = Query(100, description="Maximum number of bins to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """List all waste bins with their latest status.
    
    Args:
        borough: Optional borough filter
        district: Optional district filter
        limit: Maximum number of bins
        offset: Pagination offset
        
    Returns:
        List of waste bins with latest telemetry
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get list of bins from database
    bins = await get_bin_packet(limit=limit, offset=offset, borough=borough, district=district, list_all=True)
    
    if not bins:
        raise HTTPException(
            status_code=404,
            detail="No bins found",
        )
    
    return {
        "count": len(bins),
        "bins": bins,
    }
