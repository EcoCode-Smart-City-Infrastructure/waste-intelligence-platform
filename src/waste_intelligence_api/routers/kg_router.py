"""Router for Knowledge Graph endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Config
from ..services.kg_client import query_kg, query_pathways

router = APIRouter(tags=["Knowledge Graph"])

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class KGQueryRequest(BaseModel):
    """Request model for knowledge graph query."""
    query: str
    limit: int = 10


class KGQueryResponse(BaseModel):
    """Response model for knowledge graph query."""
    query: str
    results: list[dict]
    execution_time: float


class CircularEconomyRequest(BaseModel):
    """Request model for circular economy suggestions."""
    waste_type: str
    quantity_kg: float = 100.0
    location: str | None = None


class CircularEconomyResponse(BaseModel):
    """Response model for circular economy suggestions."""
    waste_type: str
    quantity_kg: float
    suggestions: list[dict]


@router.post("/kg", response_model=KGQueryResponse)
async def kg_query(
    request: KGQueryRequest,
    api_key: str | None = Depends(api_key_header),
):
    """Query the Waste-to-Resource Knowledge Graph.
    
    Args:
        request: Knowledge graph query request
        
    Returns:
        Knowledge graph query results with entities and relationships
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Query knowledge graph
        result = await query_kg(request.query)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Knowledge graph query failed: {str(e)}",
        )


@router.post("/kg/sparql")
async def kg_sparql_query(
    query: str = Query(..., description="SPARQL query"),
    api_key: str | None = Depends(api_key_header),
):
    """Execute SPARQL query on the knowledge graph.
    
    Args:
        query: SPARQL query string
        
    Returns:
        SPARQL query results
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Execute SPARQL query
        result = await query_kg(query, query_type="sparql")
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SPARQL query failed: {str(e)}",
        )


@router.post("/circular_economy", response_model=CircularEconomyResponse)
async def circular_economy(
    request: CircularEconomyRequest,
    api_key: str | None = Depends(api_key_header),
):
    """Get circular economy suggestions for waste materials.
    
    Uses the Waste-to-Resource Knowledge Graph to suggest optimal
    waste-to-resource pathways.
    
    Args:
        request: Circular economy request with waste type and quantity
        
    Returns:
        Suggestions for recycling, composting, or waste-to-energy pathways
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Real pathway suggestions from the W2RKG engine (empty, not
        # fabricated, when the waste type is unknown to the graph)
        suggestions = await query_pathways(
            request.waste_type, request.quantity_kg, limit=5
        )

        return CircularEconomyResponse(
            waste_type=request.waste_type,
            quantity_kg=request.quantity_kg,
            suggestions=suggestions,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Circular economy query failed: {str(e)}",
        )


@router.get("/kg/entities")
async def list_kg_entities(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(100, description="Maximum number of entities to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """List entities in the knowledge graph.
    
    Args:
        entity_type: Optional entity type filter
        limit: Maximum number of entities
        offset: Pagination offset
        
    Returns:
        List of entities in the knowledge graph
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Query for entities
        query = "list all entities"
        if entity_type:
            query += f" of type {entity_type}"
        query += f" limit {limit} offset {offset}"
        
        result = await query_kg(query)
        
        return {
            "entity_type": entity_type,
            "count": len(result.get("results", [])),
            "entities": result.get("results", []),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Entity listing failed: {str(e)}",
        )


@router.get("/kg/relationships")
async def list_kg_relationships(
    source: str | None = Query(None, description="Filter by source entity"),
    target: str | None = Query(None, description="Filter by target entity"),
    relationship_type: str | None = Query(None, description="Filter by relationship type"),
    limit: int = Query(100, description="Maximum number of relationships to return"),
    offset: int = Query(0, description="Pagination offset"),
    api_key: str | None = Depends(api_key_header),
):
    """List relationships in the knowledge graph.
    
    Args:
        source: Optional source entity filter
        target: Optional target entity filter
        relationship_type: Optional relationship type filter
        limit: Maximum number of relationships
        offset: Pagination offset
        
    Returns:
        List of relationships in the knowledge graph
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Query for relationships
        query = "list all relationships"
        if source:
            query += f" from {source}"
        if target:
            query += f" to {target}"
        if relationship_type:
            query += f" of type {relationship_type}"
        query += f" limit {limit} offset {offset}"
        
        result = await query_kg(query)
        
        return {
            "source": source,
            "target": target,
            "relationship_type": relationship_type,
            "count": len(result.get("results", [])),
            "relationships": result.get("results", []),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Relationship listing failed: {str(e)}",
        )
