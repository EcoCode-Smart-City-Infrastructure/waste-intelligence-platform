"""
Context Manager for AI Copilot Service.

Builds structured context from various data sources for LLM queries.
Aggregates data from Waste Intelligence API, MCP Server, KG API, and ML API.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache

import httpx

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context that can be gathered."""
    AGGREGATED_TELEMETRY = "aggregated_telemetry"
    ML_OUTPUTS = "ml_outputs"
    KG_RESULTS = "kg_results"
    CITY_DATA = "city_data"
    FACILITY_INFO = "facility_info"
    CLUSTER_INFO = "cluster_info"
    BIN_INFO = "bin_info"
    RAW_SENSOR = "raw_sensor"  # Not allowed - for internal use only


@dataclass
class ContextItem:
    """A single piece of context information."""
    context_type: ContextType
    source: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if this context item has expired."""
        return (datetime.utcnow() - self.timestamp).total_seconds() > self.ttl_seconds
    
    def to_summary(self, max_length: int = 1000) -> str:
        """Convert context to a summary string."""
        try:
            data_str = json.dumps(self.data, indent=2)
            if len(data_str) > max_length:
                data_str = data_str[:max_length] + "... (truncated)"
            return f"[{self.context_type.value}] from {self.source}: {data_str}"
        except:
            return f"[{self.context_type.value}] from {self.source}: {str(self.data)[:max_length]}"


@dataclass
class Context:
    """Structured context for a copilot query."""
    user_id: str
    session_id: Optional[str] = None
    query: Optional[str] = None
    items: List[ContextItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_item(self, item: ContextItem):
        """Add a context item."""
        self.items.append(item)
    
    def get_by_type(self, context_type: ContextType) -> List[ContextItem]:
        """Get all context items of a specific type."""
        return [item for item in self.items if item.context_type == context_type]
    
    def get_by_source(self, source: str) -> List[ContextItem]:
        """Get all context items from a specific source."""
        return [item for item in self.items if item.source == source]
    
    def to_prompt_context(self, max_length: int = 4000) -> str:
        """
        Convert context to a string suitable for LLM prompt.
        
        Args:
            max_length: Maximum length of the context string
        
        Returns:
            Formatted context string
        """
        parts = []
        
        # Add metadata
        if self.metadata:
            parts.append("## Metadata")
            parts.append(json.dumps(self.metadata, indent=2))
            parts.append("")
        
        # Group by context type
        grouped = {}
        for item in self.items:
            if item.context_type not in grouped:
                grouped[item.context_type] = []
            grouped[item.context_type].append(item)
        
        # Add each context type section
        for context_type, items in grouped.items():
            if context_type == ContextType.RAW_SENSOR:
                # Skip raw sensor data - should not be included
                continue
                
            parts.append(f"## {context_type.value.replace('_', ' ').title()}")
            
            for item in items:
                if not item.is_expired():
                    summary = item.to_summary()
                    parts.append(summary)
                    parts.append("")
        
        context_str = "\n".join(parts)
        
        # Truncate if too long
        if len(context_str) > max_length:
            context_str = context_str[:max_length] + "\n\n... (context truncated)"
        
        return context_str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "query": self.query,
            "items": [
                {
                    "type": item.context_type.value,
                    "source": item.source,
                    "data": item.data,
                    "timestamp": item.timestamp.isoformat()
                }
                for item in self.items
            ],
            "metadata": self.metadata
        }


class ContextManager:
    """
    Manages context gathering from various data sources.
    
    Provides methods to:
    - Gather context from Waste Intelligence API
    - Gather context from MCP NYC Server
    - Gather context from Knowledge Graph API
    - Gather context from ML API
    - Cache and manage context TTL
    """
    
    def __init__(self):
        """Initialize context manager."""
        self.settings = get_settings()
        self._cache: Dict[str, Tuple[ContextItem, datetime]] = {}
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def build_context(
        self,
        user_id: str,
        query: str,
        context_config: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Context:
        """
        Build context for a query based on the query content and configuration.
        
        Args:
            user_id: ID of the user making the query
            query: The user's query
            context_config: Configuration for context gathering
            session_id: Optional session ID for grouping
        
        Returns:
            Context object with gathered information
        """
        context = Context(
            user_id=user_id,
            query=query,
            session_id=session_id
        )
        
        # Parse context configuration
        config = context_config or {}
        
        # Extract IDs from query
        cluster_id = self._extract_id(query, "cluster")
        facility_id = self._extract_id(query, "facility")
        bin_id = self._extract_id(query, "bin")
        waste_type = self._extract_waste_type(query)
        borough = self._extract_borough(query)
        time_range = self._extract_time_range(query)
        
        # Store extracted metadata
        context.metadata = {
            "cluster_id": cluster_id,
            "facility_id": facility_id,
            "bin_id": bin_id,
            "waste_type": waste_type,
            "borough": borough,
            "time_range": time_range,
            "intent": self._infer_intent(query)
        }
        
        # Gather context based on query content
        tasks = []
        
        # Cluster information
        if cluster_id or "cluster" in query.lower():
            cluster_id_to_use = cluster_id or config.get("cluster_id")
            if cluster_id_to_use:
                tasks.append(self._gather_cluster_context(cluster_id_to_use))
        
        # Facility information
        if facility_id or "facility" in query.lower():
            facility_id_to_use = facility_id or config.get("facility_id")
            if facility_id_to_use:
                tasks.append(self._gather_facility_context(facility_id_to_use))
        
        # Bin information (aggregated, not raw)
        if bin_id or "bin" in query.lower():
            bin_id_to_use = bin_id or config.get("bin_id")
            if bin_id_to_use:
                tasks.append(self._gather_bin_context(bin_id_to_use))
        
        # Waste type and KG pathways
        if waste_type or any(word in query.lower() for word in ["waste", "organic", "recycling", "pathway", "resource"]):
            waste_type_to_use = waste_type or config.get("waste_type")
            tasks.append(self._gather_kg_context(waste_type_to_use))
        
        # ML outputs (anomaly, forecast, etc.)
        if any(word in query.lower() for word in ["anomaly", "forecast", "predict", "contamination", "load"]):
            tasks.append(self._gather_ml_context(cluster_id, facility_id, waste_type))
        
        # City data (weather, air quality, etc.)
        if any(word in query.lower() for word in ["weather", "air", "quality", "temperature", "mobility", "traffic"]):
            tasks.append(self._gather_city_context(borough))
        elif borough:
            # Include city data for borough-specific queries
            tasks.append(self._gather_city_context(borough))
        
        # Gather all context concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, ContextItem):
                context.add_item(result)
            elif isinstance(result, list):
                for item in result:
                    context.add_item(item)
            elif isinstance(result, Exception):
                logger.warning(f"Failed to gather context: {str(result)}")
        
        return context
    
    def _extract_id(self, query: str, id_type: str) -> Optional[str]:
        """Extract an ID from the query."""
        patterns = [
            rf"{id_type}[_-]?id['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]+)['\"]?",
            rf"{id_type}\s+([a-zA-Z0-9_-]+)",
            rf"([a-zA-Z0-9_-]+)\s+{id_type}",
            rf"{id_type}:([a-zA-Z0-9_-]+)",
            rf"CLUSTER-([a-zA-Z0-9_-]+)",
            rf"FACILITY-([a-zA-Z0-9_-]+)",
            rf"BIN-([a-zA-Z0-9_-]+)",
        ]
        
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _extract_waste_type(self, query: str) -> Optional[str]:
        """Extract waste type from query."""
        waste_types = [
            "organic", "food scraps", "food waste", "yard waste", "green waste",
            "recycling", "paper", "cardboard", "metal", "glass", "plastic",
            "construction", "demolition", "c&d", "electronic", "e-waste",
            "hazardous", "medical", "textiles", "spent grain", "brewery waste"
        ]
        
        query_lower = query.lower()
        for waste_type in waste_types:
            if waste_type in query_lower:
                return waste_type
        
        return None
    
    def _extract_borough(self, query: str) -> Optional[str]:
        """Extract NYC borough from query."""
        boroughs = ["manhattan", "brooklyn", "queens", "bronx", "staten island", "nyc", "new york"]
        
        query_lower = query.lower()
        for borough in boroughs:
            if borough in query_lower:
                return borough.title()
        
        return None
    
    def _extract_time_range(self, query: str) -> Optional[Dict[str, str]]:
        """Extract time range from query."""
        patterns = [
            # "today"
            (r"today", lambda: {"start": datetime.utcnow().strftime("%Y-%m-%d"), "end": (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")}),
            # "yesterday"
            (r"yesterday", lambda: {"start": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"), "end": datetime.utcnow().strftime("%Y-%m-%d")}),
            # "this week"
            (r"this\s+week", lambda: {"start": (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).strftime("%Y-%m-%d"), "end": (datetime.utcnow() + timedelta(days=7 - datetime.utcnow().weekday())).strftime("%Y-%m-%d")}),
            # Date range: "from 2024-01-01 to 2024-01-31"
            (r"from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", lambda m: {"start": m.group(1), "end": m.group(2)}),
            # Date: "2024-01-01"
            (r"(\d{4}-\d{2}-\d{2})", lambda m: {"start": m.group(1), "end": m.group(1)}),
        ]
        
        query_lower = query.lower()
        for pattern, handler in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                if callable(handler):
                    result = handler(match) if match.groups() else handler()
                    return result
        
        return None
    
    def _infer_intent(self, query: str) -> str:
        """Infer the intent of the query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["why", "explain", "reason", "cause"]):
            return "explain"
        elif any(word in query_lower for word in ["what", "list", "show", "display"]):
            return "query"
        elif any(word in query_lower for word in ["predict", "forecast", "estimate", "project"]):
            return "predict"
        elif any(word in query_lower for word in ["suggest", "recommend", "advise", "propose"]):
            return "recommend"
        elif any(word in query_lower for word in ["summarize", "summary", "overview"]):
            return "summarize"
        elif any(word in query_lower for word in ["debug", "fix", "error", "problem", "issue"]):
            return "debug"
        elif any(word in query_lower for word in ["help", "guide", "tutorial", "how"]):
            return "help"
        else:
            return "general"
    
    async def _gather_cluster_context(self, cluster_id: str) -> List[ContextItem]:
        """Gather context about a cluster."""
        items = []
        
        try:
            # Get cluster data from Waste Intelligence API
            url = f"{self.settings.waste_intel_api_url}/clusters/{cluster_id}"
            response = await self._http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            items.append(ContextItem(
                context_type=ContextType.CLUSTER_INFO,
                source="waste_intel_api",
                data={"cluster_id": cluster_id, "data": data},
                ttl_seconds=60
            ))
            
            # Get cluster telemetry
            url = f"{self.settings.waste_intel_api_url}/clusters/{cluster_id}/telemetry"
            response = await self._http_client.get(url)
            response.raise_for_status()
            telemetry = response.json()
            
            items.append(ContextItem(
                context_type=ContextType.AGGREGATED_TELEMETRY,
                source="waste_intel_api",
                data={"cluster_id": cluster_id, "telemetry": telemetry},
                ttl_seconds=30
            ))
            
            # Get cluster anomalies
            url = f"{self.settings.ml_api_url}/anomaly/cluster/{cluster_id}"
            response = await self._http_client.get(url)
            if response.status_code == 200:
                anomalies = response.json()
                items.append(ContextItem(
                    context_type=ContextType.ML_OUTPUTS,
                    source="ml_api",
                    data={"cluster_id": cluster_id, "anomalies": anomalies},
                    ttl_seconds=30
                ))
                
        except Exception as e:
            logger.warning(f"Failed to gather cluster context for {cluster_id}: {str(e)}")
        
        return items
    
    async def _gather_facility_context(self, facility_id: str) -> List[ContextItem]:
        """Gather context about a facility."""
        items = []
        
        try:
            # Get facility data from Waste Intelligence API
            url = f"{self.settings.waste_intel_api_url}/facilities/{facility_id}"
            response = await self._http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            items.append(ContextItem(
                context_type=ContextType.FACILITY_INFO,
                source="waste_intel_api",
                data={"facility_id": facility_id, "data": data},
                ttl_seconds=60
            ))
            
            # Get facility load/capacity from ML API
            url = f"{self.settings.ml_api_url}/forecast/facility/{facility_id}"
            response = await self._http_client.get(url)
            if response.status_code == 200:
                forecast = response.json()
                items.append(ContextItem(
                    context_type=ContextType.ML_OUTPUTS,
                    source="ml_api",
                    data={"facility_id": facility_id, "forecast": forecast},
                    ttl_seconds=30
                ))
                
        except Exception as e:
            logger.warning(f"Failed to gather facility context for {facility_id}: {str(e)}")
        
        return items
    
    async def _gather_bin_context(self, bin_id: str) -> List[ContextItem]:
        """Gather context about a bin (aggregated data only)."""
        items = []
        
        try:
            # Get bin data from Waste Intelligence API (aggregated, not raw sensor data)
            url = f"{self.settings.waste_intel_api_url}/bins/{bin_id}"
            response = await self._http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Remove any raw sensor data
            if "sensor_data" in data:
                del data["sensor_data"]
            if "raw_readings" in data:
                del data["raw_readings"]
            if "gps" in data:
                data["gps"] = "[REDACTED]"
            
            items.append(ContextItem(
                context_type=ContextType.BIN_INFO,
                source="waste_intel_api",
                data={"bin_id": bin_id, "data": data},
                ttl_seconds=60
            ))
            
        except Exception as e:
            logger.warning(f"Failed to gather bin context for {bin_id}: {str(e)}")
        
        return items
    
    async def _gather_kg_context(self, waste_type: Optional[str] = None) -> List[ContextItem]:
        """Gather context from Knowledge Graph."""
        items = []
        
        try:
            # Get pathways for waste type if specified
            if waste_type:
                url = f"{self.settings.kg_api_url}/pathways"
                params = {"waste_type": waste_type}
                response = await self._http_client.get(url, params=params)
                if response.status_code == 200:
                    pathways = response.json()
                    items.append(ContextItem(
                        context_type=ContextType.KG_RESULTS,
                        source="kg_api",
                        data={"waste_type": waste_type, "pathways": pathways},
                        ttl_seconds=300
                    ))
            else:
                # Get general KG summary
                url = f"{self.settings.kg_api_url}/summary"
                response = await self._http_client.get(url)
                if response.status_code == 200:
                    summary = response.json()
                    items.append(ContextItem(
                        context_type=ContextType.KG_RESULTS,
                        source="kg_api",
                        data={"summary": summary},
                        ttl_seconds=300
                    ))
                    
        except Exception as e:
            logger.warning(f"Failed to gather KG context: {str(e)}")
        
        return items
    
    async def _gather_ml_context(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        waste_type: Optional[str] = None
    ) -> List[ContextItem]:
        """Gather context from ML API."""
        items = []
        
        try:
            # Get anomalies
            if cluster_id:
                url = f"{self.settings.ml_api_url}/anomaly/cluster/{cluster_id}"
                response = await self._http_client.get(url)
                if response.status_code == 200:
                    anomalies = response.json()
                    items.append(ContextItem(
                        context_type=ContextType.ML_OUTPUTS,
                        source="ml_api",
                        data={"type": "anomaly", "cluster_id": cluster_id, "data": anomalies},
                        ttl_seconds=30
                    ))
            
            # Get forecasts
            if facility_id:
                url = f"{self.settings.ml_api_url}/forecast/facility/{facility_id}"
                response = await self._http_client.get(url)
                if response.status_code == 200:
                    forecast = response.json()
                    items.append(ContextItem(
                        context_type=ContextType.ML_OUTPUTS,
                        source="ml_api",
                        data={"type": "forecast", "facility_id": facility_id, "data": forecast},
                        ttl_seconds=30
                    ))
            
            # Get contamination detection
            if waste_type:
                url = f"{self.settings.ml_api_url}/contamination"
                params = {"waste_type": waste_type}
                response = await self._http_client.get(url, params=params)
                if response.status_code == 200:
                    contamination = response.json()
                    items.append(ContextItem(
                        context_type=ContextType.ML_OUTPUTS,
                        source="ml_api",
                        data={"type": "contamination", "waste_type": waste_type, "data": contamination},
                        ttl_seconds=30
                    ))
                    
        except Exception as e:
            logger.warning(f"Failed to gather ML context: {str(e)}")
        
        return items
    
    async def _gather_city_context(self, borough: Optional[str] = None) -> List[ContextItem]:
        """Gather context from MCP NYC Server."""
        items = []
        
        try:
            # Get weather data
            url = f"{self.settings.mcp_server_url}/weather"
            params = {}
            if borough:
                params["borough"] = borough
            response = await self._http_client.get(url, params=params)
            if response.status_code == 200:
                weather = response.json()
                items.append(ContextItem(
                    context_type=ContextType.CITY_DATA,
                    source="mcp_server",
                    data={"type": "weather", "borough": borough, "data": weather},
                    ttl_seconds=300
                ))
            
            # Get air quality data
            url = f"{self.settings.mcp_server_url}/air_quality"
            params = {}
            if borough:
                params["borough"] = borough
            response = await self._http_client.get(url, params=params)
            if response.status_code == 200:
                air_quality = response.json()
                items.append(ContextItem(
                    context_type=ContextType.CITY_DATA,
                    source="mcp_server",
                    data={"type": "air_quality", "borough": borough, "data": air_quality},
                    ttl_seconds=300
                ))
                
        except Exception as e:
            logger.warning(f"Failed to gather city context: {str(e)}")
        
        return items


# Global context manager instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create the global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


# Add import for re at the top of the file
import re
