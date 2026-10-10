"""Router for ML inference endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Config
from ..services.ml_inference import (
    run_anomaly,
    run_contamination,
    run_forecast,
)

router = APIRouter(tags=["ML Inference"])

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ForecastRequest(BaseModel):
    """Request model for waste forecasting."""
    features: dict
    horizon_hours: int = 24


class ForecastResponse(BaseModel):
    """Response model for waste forecasting."""
    timestamp: str
    predicted_value: float
    confidence: float
    model_version: str


class AnomalyRequest(BaseModel):
    """Request model for anomaly detection."""
    features: dict
    threshold: float = 0.95


class AnomalyResponse(BaseModel):
    """Response model for anomaly detection."""
    timestamp: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float


class ContaminationRequest(BaseModel):
    """Request model for contamination detection."""
    image_tensor: list | None = None
    image_url: str | None = None
    threshold: float = 0.7


class ContaminationResponse(BaseModel):
    """Response model for contamination detection."""
    image_id: str
    contamination_type: str
    confidence: float
    bounding_box: dict | None = None


@router.post("/forecast", response_model=ForecastResponse)
async def forecast(
    request: ForecastRequest,
    api_key: str | None = Depends(api_key_header),
):
    """Generate waste collection forecasts using ML models.
    
    Args:
        request: Forecast request with features and horizon
        
    Returns:
        Forecast predictions with confidence intervals
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Run forecast
        result = await run_forecast(request.features)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Forecast failed: {str(e)}",
        )


@router.post("/anomaly", response_model=AnomalyResponse)
async def anomaly(
    request: AnomalyRequest,
    api_key: str | None = Depends(api_key_header),
):
    """Detect anomalies in waste data using ML models.
    
    Args:
        request: Anomaly detection request with features and threshold
        
    Returns:
        Anomaly detection results with scores
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Run anomaly detection
        result = await run_anomaly(request.features)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Anomaly detection failed: {str(e)}",
        )


@router.post("/contamination", response_model=ContaminationResponse)
async def contamination(
    request: ContaminationRequest,
    api_key: str | None = Depends(api_key_header),
):
    """Detect contamination in recycling streams using CNN models.
    
    Args:
        request: Contamination detection request with image data
        
    Returns:
        Contamination detection results with bounding boxes
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Run contamination detection
        result = await run_contamination(request.image_tensor or [])
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Contamination detection failed: {str(e)}",
        )


@router.post("/batch/forecast")
async def batch_forecast(
    requests: list[ForecastRequest],
    api_key: str | None = Depends(api_key_header),
):
    """Batch forecast for multiple requests.
    
    Args:
        requests: List of forecast requests
        
    Returns:
        List of forecast results
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Run batch forecast
        results = []
        for request in requests:
            result = await run_forecast(request.features)
            results.append(result)
        
        return {
            "count": len(results),
            "results": results,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch forecast failed: {str(e)}",
        )


@router.post("/batch/anomaly")
async def batch_anomaly(
    requests: list[AnomalyRequest],
    api_key: str | None = Depends(api_key_header),
):
    """Batch anomaly detection for multiple requests.
    
    Args:
        requests: List of anomaly detection requests
        
    Returns:
        List of anomaly detection results
    """
    # Check API key if required
    if Config.REQUIRE_API_KEY:
        if not api_key or api_key != Config.API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )
    
    try:
        # Run batch anomaly detection
        results = []
        for request in requests:
            result = await run_anomaly(request.features)
            results.append(result)
        
        return {
            "count": len(results),
            "results": results,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch anomaly detection failed: {str(e)}",
        )
