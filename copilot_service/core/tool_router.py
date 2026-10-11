"""
Tool Router for AI Copilot Service.

Routes queries to appropriate backend services based on intent.
Decides which tools (APIs) to call for gathering information.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

import httpx

from ..config.settings import get_settings
from .context_manager import ContextManager, ContextType

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Types of tools available."""
    WASTE_INTEL_API = "waste_intel_api"
    MCP_SERVER = "mcp_server"
    KG_API = "kg_api"
    ML_API = "ml_api"


class IntentType(Enum):
    """Types of user intent."""
    TELEMETRY = "telemetry"
    ANOMALY = "anomaly"
    FORECAST = "forecast"
    CONTAMINATION = "contamination"
    CITY_DATA = "city_data"
    PATHWAYS = "pathways"
    ROUTING = "routing"
    FACILITY_INFO = "facility_info"
    CLUSTER_INFO = "cluster_info"
    SYMBIOSIS = "symbiosis"
    GENERAL = "general"


@dataclass
class ToolCall:
    """Represents a tool call to be made."""
    tool_type: ToolType
    endpoint: str
    method: str = "GET"
    params: Dict[str, Any] = None
    data: Dict[str, Any] = None
    description: str = ""
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}
        if self.data is None:
            self.data = {}


@dataclass
class ToolResult:
    """Result from a tool call."""
    tool_call: ToolCall
    data: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    duration_ms: float = 0.0


class ToolRouter:
    """
    Routes queries to appropriate backend services.
    
    Analyzes user queries to determine:
    - Which backend services to call
    - What parameters to use
    - How to combine results
    """
    
    def __init__(self):
        """Initialize tool router."""
        self.settings = get_settings()
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def detect_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntentType:
        """
        Detect the intent of a user query.
        
        Args:
            query: The user's query
            context: Optional context from previous interactions
        
        Returns:
            Detected intent type
        """
        query_lower = query.lower()
        
        # Check for specific patterns
        patterns = [
            # Telemetry queries
            (r"\b(telemetry|sensor|reading|level|mass|volume|weight)\b", IntentType.TELEMETRY),
            
            # Anomaly queries
            (r"\b(anomaly|anomalies|unusual|abnormal|outlier|spike|alert)\b", IntentType.ANOMALY),
            
            # Forecast queries
            (r"\b(forecast|predict|prediction|estimate|projection|future|tomorrow|next week)\b", IntentType.FORECAST),
            
            # Contamination queries
            (r"\b(contamination|contaminant|purity|quality|clean|dirty|mixed)\b", IntentType.CONTAMINATION),
            
            # City data queries
            (r"\b(weather|air quality|temperature|humidity|rain|snow|traffic|mobility|airnow)\b", IntentType.CITY_DATA),
            
            # Pathway queries
            (r"\b(pathway|pathways|resource|convert|process|processing|recycling|composting|w2rkg)\b", IntentType.PATHWAYS),
            
            # Routing queries
            (r"\b(route|routing|transport|delivery|pickup|collection|logistics)\b", IntentType.ROUTING),
            
            # Facility queries
            (r"\b(facility|facilities|plant|compost|recycling center|transfer station|landfill)\b", IntentType.FACILITY_INFO),
            
            # Cluster queries
            (r"\b(cluster|block|building|neighborhood|borough|district|zone)\b", IntentType.CLUSTER_INFO),
            
            # Symbiosis queries
            (r"\b(symbiosis|industrial symbiosis|partnership|collaboration|synergy|waste exchange)\b", IntentType.SYMBIOSIS),
        ]
        
        for pattern, intent in patterns:
            if re.search(pattern, query_lower):
                return intent
        
        # Check context for IDs
        if context:
            if context.get("cluster_id"):
                return IntentType.CLUSTER_INFO
            if context.get("facility_id"):
                return IntentType.FACILITY_INFO
            if context.get("waste_type"):
                return IntentType.PATHWAYS
        
        return IntentType.GENERAL
    
    def route_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ToolCall]:
        """
        Route a query to appropriate tools.
        
        Args:
            query: The user's query
            context: Optional context from previous interactions
        
        Returns:
            List of tool calls to make
        """
        intent = self.detect_intent(query, context)
        extracted = self._extract_entities(query, context)
        
        tool_calls = []
        
        # Extract IDs and entities
        cluster_id = extracted.get("cluster_id") or (context and context.get("cluster_id"))
        facility_id = extracted.get("facility_id") or (context and context.get("facility_id"))
        bin_id = extracted.get("bin_id") or (context and context.get("bin_id"))
        waste_type = extracted.get("waste_type") or (context and context.get("waste_type"))
        borough = extracted.get("borough") or (context and context.get("borough"))
        time_range = extracted.get("time_range") or (context and context.get("time_range"))
        
        logger.info(f"Routing query: intent={intent.value}, cluster={cluster_id}, facility={facility_id}, waste_type={waste_type}")
        
        # Route based on intent
        if intent == IntentType.TELEMETRY:
            tool_calls = self._route_telemetry(cluster_id, facility_id, bin_id, time_range)
        elif intent == IntentType.ANOMALY:
            tool_calls = self._route_anomaly(cluster_id, facility_id, bin_id, time_range)
        elif intent == IntentType.FORECAST:
            tool_calls = self._route_forecast(cluster_id, facility_id, waste_type, time_range)
        elif intent == IntentType.CONTAMINATION:
            tool_calls = self._route_contamination(cluster_id, facility_id, waste_type)
        elif intent == IntentType.CITY_DATA:
            tool_calls = self._route_city_data(borough, time_range)
        elif intent == IntentType.PATHWAYS:
            tool_calls = self._route_pathways(waste_type, facility_id)
        elif intent == IntentType.ROUTING:
            tool_calls = self._route_routing(cluster_id, facility_id, waste_type)
        elif intent == IntentType.FACILITY_INFO:
            tool_calls = self._route_facility_info(facility_id)
        elif intent == IntentType.CLUSTER_INFO:
            tool_calls = self._route_cluster_info(cluster_id)
        elif intent == IntentType.SYMBIOSIS:
            tool_calls = self._route_symbiosis(facility_id, waste_type)
        else:
            # General query - try to gather relevant context
            tool_calls = self._route_general(cluster_id, facility_id, waste_type, borough)
        
        return tool_calls
    
    def _extract_entities(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract entities from query and context."""
        entities = {}
        
        # Extract IDs
        entities["cluster_id"] = self._extract_id(query, "cluster")
        entities["facility_id"] = self._extract_id(query, "facility")
        entities["bin_id"] = self._extract_id(query, "bin")
        
        # Extract waste type
        entities["waste_type"] = self._extract_waste_type(query)
        
        # Extract borough
        entities["borough"] = self._extract_borough(query)
        
        # Extract time range
        entities["time_range"] = self._extract_time_range(query)
        
        # Override with context if provided
        if context:
            for key, value in context.items():
                if value and key in entities:
                    entities[key] = value
        
        return entities
    
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
            (r"today", lambda: {"start": "today", "end": "today"}),
            (r"yesterday", lambda: {"start": "yesterday", "end": "yesterday"}),
            (r"this\s+week", lambda: {"start": "this_week", "end": "this_week"}),
            (r"from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", lambda m: {"start": m.group(1), "end": m.group(2)}),
            (r"(\d{4}-\d{2}-\d{2})", lambda m: {"start": m.group(1), "end": m.group(1)}),
        ]
        
        query_lower = query.lower()
        for pattern, handler in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                if callable(handler):
                    return handler(match) if match.groups() else handler()
        
        return None
    
    def _route_telemetry(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        bin_id: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> List[ToolCall]:
        """Route telemetry query."""
        tool_calls = []
        
        if cluster_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/clusters/{cluster_id}/telemetry",
                params={"time_range": time_range} if time_range else {},
                description=f"Get telemetry for cluster {cluster_id}"
            ))
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/facilities/{facility_id}/telemetry",
                params={"time_range": time_range} if time_range else {},
                description=f"Get telemetry for facility {facility_id}"
            ))
        
        if bin_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/bins/{bin_id}/telemetry",
                params={"time_range": time_range} if time_range else {},
                description=f"Get telemetry for bin {bin_id}"
            ))
        
        return tool_calls
    
    def _route_anomaly(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        bin_id: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> List[ToolCall]:
        """Route anomaly query."""
        tool_calls = []
        
        # Get anomaly detection from ML API
        if cluster_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/anomaly/cluster/{cluster_id}",
                params={"time_range": time_range} if time_range else {},
                description=f"Get anomalies for cluster {cluster_id}"
            ))
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/anomaly/facility/{facility_id}",
                params={"time_range": time_range} if time_range else {},
                description=f"Get anomalies for facility {facility_id}"
            ))
        
        if bin_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/anomaly/bin/{bin_id}",
                params={"time_range": time_range} if time_range else {},
                description=f"Get anomalies for bin {bin_id}"
            ))
        
        # Also get telemetry for context
        tool_calls.extend(self._route_telemetry(cluster_id, facility_id, bin_id, time_range))
        
        return tool_calls
    
    def _route_forecast(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        waste_type: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> List[ToolCall]:
        """Route forecast query."""
        tool_calls = []
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/forecast/facility/{facility_id}",
                params={"waste_type": waste_type, "time_range": time_range} if waste_type or time_range else {},
                description=f"Get forecast for facility {facility_id}"
            ))
        
        if cluster_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/forecast/cluster/{cluster_id}",
                params={"waste_type": waste_type, "time_range": time_range} if waste_type or time_range else {},
                description=f"Get forecast for cluster {cluster_id}"
            ))
        
        if waste_type:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint="/forecast/diversion",
                params={"waste_type": waste_type, "time_range": time_range} if time_range else {"waste_type": waste_type},
                description=f"Get diversion forecast for {waste_type}"
            ))
        
        return tool_calls
    
    def _route_contamination(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        waste_type: Optional[str] = None
    ) -> List[ToolCall]:
        """Route contamination query."""
        tool_calls = []
        
        if waste_type:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint="/contamination/detect",
                params={"waste_type": waste_type},
                description=f"Detect contamination for {waste_type}"
            ))
        
        if cluster_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/contamination/cluster/{cluster_id}",
                description=f"Get contamination for cluster {cluster_id}"
            ))
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.ML_API,
                endpoint=f"/contamination/facility/{facility_id}",
                description=f"Get contamination for facility {facility_id}"
            ))
        
        return tool_calls
    
    def _route_city_data(
        self,
        borough: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> List[ToolCall]:
        """Route city data query."""
        tool_calls = []
        
        # Weather
        params = {}
        if borough:
            params["borough"] = borough
        if time_range:
            params["time_range"] = time_range
        
        tool_calls.append(ToolCall(
            tool_type=ToolType.MCP_SERVER,
            endpoint="/weather",
            params=params,
            description="Get weather data"
        ))
        
        # Air quality
        tool_calls.append(ToolCall(
            tool_type=ToolType.MCP_SERVER,
            endpoint="/air_quality",
            params=params,
            description="Get air quality data"
        ))
        
        # Mobility/Traffic
        tool_calls.append(ToolCall(
            tool_type=ToolType.MCP_SERVER,
            endpoint="/mobility",
            params=params,
            description="Get mobility data"
        ))
        
        return tool_calls
    
    def _route_pathways(
        self,
        waste_type: Optional[str] = None,
        facility_id: Optional[str] = None
    ) -> List[ToolCall]:
        """Route pathways query."""
        tool_calls = []
        
        if waste_type:
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint="/pathways",
                params={"waste_type": waste_type},
                description=f"Get pathways for {waste_type}"
            ))
            
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint="/resources",
                params={"waste_type": waste_type},
                description=f"Get resources from {waste_type}"
            ))
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint=f"/facility/{facility_id}/pathways",
                description=f"Get pathways for facility {facility_id}"
            ))
        
        return tool_calls
    
    def _route_routing(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        waste_type: Optional[str] = None
    ) -> List[ToolCall]:
        """Route routing query."""
        tool_calls = []
        
        # Get current routing info
        if cluster_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/clusters/{cluster_id}/routing",
                description=f"Get routing info for cluster {cluster_id}"
            ))
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/facilities/{facility_id}/capacity",
                description=f"Get capacity for facility {facility_id}"
            ))
        
        # Get pathway suggestions for routing decisions
        if waste_type:
            tool_calls.extend(self._route_pathways(waste_type, facility_id))
        
        return tool_calls
    
    def _route_facility_info(self, facility_id: Optional[str] = None) -> List[ToolCall]:
        """Route facility info query."""
        tool_calls = []
        
        if facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/facilities/{facility_id}",
                description=f"Get info for facility {facility_id}"
            ))
            
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/facilities/{facility_id}/capacity",
                description=f"Get capacity for facility {facility_id}"
            ))
            
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint=f"/facility/{facility_id}",
                description=f"Get KG info for facility {facility_id}"
            ))
        
        return tool_calls
    
    def _route_cluster_info(self, cluster_id: Optional[str] = None) -> List[ToolCall]:
        """Route cluster info query."""
        tool_calls = []
        
        if cluster_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/clusters/{cluster_id}",
                description=f"Get info for cluster {cluster_id}"
            ))
            
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/clusters/{cluster_id}/bins",
                description=f"Get bins for cluster {cluster_id}"
            ))
            
            tool_calls.append(ToolCall(
                tool_type=ToolType.WASTE_INTEL_API,
                endpoint=f"/clusters/{cluster_id}/telemetry",
                description=f"Get telemetry for cluster {cluster_id}"
            ))
        
        return tool_calls
    
    def _route_symbiosis(
        self,
        facility_id: Optional[str] = None,
        waste_type: Optional[str] = None
    ) -> List[ToolCall]:
        """Route symbiosis query."""
        tool_calls = []
        
        if facility_id and waste_type:
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint="/symbiosis",
                params={"facility_id": facility_id, "waste_type": waste_type},
                description=f"Get symbiosis for {facility_id} with {waste_type}"
            ))
        elif facility_id:
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint=f"/facility/{facility_id}/symbiosis",
                description=f"Get symbiosis for facility {facility_id}"
            ))
        elif waste_type:
            tool_calls.append(ToolCall(
                tool_type=ToolType.KG_API,
                endpoint="/symbiosis",
                params={"waste_type": waste_type},
                description=f"Get symbiosis for {waste_type}"
            ))
        
        return tool_calls
    
    def _route_general(
        self,
        cluster_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        waste_type: Optional[str] = None,
        borough: Optional[str] = None
    ) -> List[ToolCall]:
        """Route general query - gather broad context."""
        tool_calls = []
        
        # Add basic info for any specified entities
        if cluster_id:
            tool_calls.extend(self._route_cluster_info(cluster_id))
        
        if facility_id:
            tool_calls.extend(self._route_facility_info(facility_id))
        
        if waste_type:
            tool_calls.extend(self._route_pathways(waste_type))
        
        if borough:
            tool_calls.extend(self._route_city_data(borough))
        
        # If nothing specific, get general summaries
        if not tool_calls:
            tool_calls.extend([
                ToolCall(
                    tool_type=ToolType.WASTE_INTEL_API,
                    endpoint="/clusters",
                    params={"limit": 5},
                    description="Get top clusters"
                ),
                ToolCall(
                    tool_type=ToolType.WASTE_INTEL_API,
                    endpoint="/facilities",
                    params={"limit": 5},
                    description="Get top facilities"
                ),
                ToolCall(
                    tool_type=ToolType.KG_API,
                    endpoint="/summary",
                    description="Get KG summary"
                ),
            ])
        
        return tool_calls
    
    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call.
        
        Args:
            tool_call: The tool call to execute
        
        Returns:
            Result of the tool call
        """
        import time
        
        start_time = time.time()
        
        try:
            # Determine base URL based on tool type
            base_url = self._get_base_url(tool_call.tool_type)
            
            # Build full URL
            url = f"{base_url}{tool_call.endpoint}"
            
            # Execute request
            if tool_call.method.upper() == "GET":
                response = await self._http_client.get(url, params=tool_call.params)
            elif tool_call.method.upper() == "POST":
                response = await self._http_client.post(url, json=tool_call.data, params=tool_call.params)
            else:
                raise ValueError(f"Unsupported method: {tool_call.method}")
            
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code >= 400:
                return ToolResult(
                    tool_call=tool_call,
                    data={},
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                    duration_ms=duration_ms
                )
            
            try:
                data = response.json()
            except:
                data = {"raw": response.text}
            
            return ToolResult(
                tool_call=tool_call,
                data=data,
                success=True,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_call=tool_call,
                data={},
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    def _get_base_url(self, tool_type: ToolType) -> str:
        """Get base URL for a tool type."""
        urls = {
            ToolType.WASTE_INTEL_API: self.settings.waste_intel_api_url,
            ToolType.MCP_SERVER: self.settings.mcp_server_url,
            ToolType.KG_API: self.settings.kg_api_url,
            ToolType.ML_API: self.settings.ml_api_url,
        }
        return urls.get(tool_type, "")


# Global tool router instance
_tool_router: Optional[ToolRouter] = None


def get_tool_router() -> ToolRouter:
    """Get or create the global tool router."""
    global _tool_router
    if _tool_router is None:
        _tool_router = ToolRouter()
    return _tool_router
