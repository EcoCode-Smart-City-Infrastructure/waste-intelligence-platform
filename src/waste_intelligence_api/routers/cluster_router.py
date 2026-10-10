"""Router for waste cluster telemetry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Config
from ..services.db_client import get_cluster_packet
from ..services.packet_builder import validate_cluster_packet

router = APIRouter(tags=["Waste Clusters"])

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ClusterResponse(BaseModel):
    """Response model for cluster telemetry."""
    cluster_id: str
    timestamp: str
    aggregated: dict


@router.get("/cluster", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str = Query(..., description="Waste cluster identifier"),
    api_key: str | None = Depends(api_key_header),
):
    """Get latest aggregated telemetry packet for a waste cluster.
    
    Returns aggregated metrics including total mass, average fill level, and bin count.
    
    Args:
        cluster_id: Waste cluster identifier (e.g., 'CLUSTER-001')
        
    Returns:
        Latest cluster telemetry packet
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get cluster packet from database
    packet = await get_cluster_packet(cluster_id)
    
    if not packet:
        raise HTTPException(
            status_code=404,
            detail=f"Cluster {cluster_id} not found",
        )
    
    # Validate packet
    validated_packet = validate_cluster_packet(packet)
    
    return validated_packet


@router.get("/cluster/history")
async def get_cluster_history(
    cluster_id: str = Query(..., description="Waste cluster identifier"),
    limit: int = Query(100, description="Maximum number of packets to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """Get historical telemetry packets for a waste cluster.
    
    Args:
        cluster_id: Waste cluster identifier
        limit: Maximum number of packets
        offset: Pagination offset
        
    Returns:
        List of historical cluster telemetry packets
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get cluster history from database
    packets = await get_cluster_packet(cluster_id, limit=limit, offset=offset, history=True)
    
    if not packets:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for cluster {cluster_id}",
        )
    
    # Validate and return packets
    validated_packets = [validate_cluster_packet(p) for p in packets]
    
    return {
        "cluster_id": cluster_id,
        "count": len(validated_packets),
        "packets": validated_packets,
    }


@router.get("/clusters")
async def list_clusters(
    borough: str | None = Query(None, description="Filter by borough"),
    district: str | None = Query(None, description="Filter by district"),
    limit: int = Query(100, description="Maximum number of clusters to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """List all waste clusters with their latest status.
    
    Args:
        borough: Optional borough filter
        district: Optional district filter
        limit: Maximum number of clusters
        offset: Pagination offset
        
    Returns:
        List of waste clusters with latest telemetry
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    # Get list of clusters from database
    clusters = await get_cluster_packet(limit=limit, offset=offset, borough=borough, district=district, list_all=True)
    
    if not clusters:
        raise HTTPException(
            status_code=404,
            detail="No clusters found",
        )
    
    return {
        "count": len(clusters),
        "clusters": clusters,
    }
