"""
FastAPI application for AI Copilot Service.

Provides REST API endpoints for the AI Copilot functionality.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from ..config.settings import get_settings, Settings
from ..utils.openrouter_client import get_openrouter_client, OpenRouterClient
from ..utils.groq_client import get_groq_client, GroqClient
from ..utils.audit_logger import get_audit_logger, AuditLogger
from ..core.context_manager import get_context_manager, ContextManager, Context
from ..core.tool_router import get_tool_router, ToolRouter, ToolCall, ToolResult
from ..core.guardrail_engine import get_guardrail_engine, GuardrailEngine, GuardrailViolation
from ..core.prompt_builder import get_prompt_builder, PromptBuilder, Prompt

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Copilot Service",
    description="Embedded AI co-pilot assistant for the Waste Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Dependency to get settings
def get_app_settings() -> Settings:
    return get_settings()


# Dependency to get OpenRouter client
async def get_router_client() -> OpenRouterClient:
    return get_openrouter_client()


# Dependency to get the LLM client for a query — Groq wins when a Groq key
# is configured (env GROQ_API / GROQ_API_KEY), otherwise OpenRouter.
# Groq and OpenRouter share the OpenAI chat-completions message format,
# so the same prompt messages work for both clients.
async def get_llm_client():
    settings = get_settings()
    if settings.groq_api_key:
        return get_groq_client()
    return get_openrouter_client()


# Dependency to get audit logger
async def get_audit() -> AuditLogger:
    return get_audit_logger()


# Dependency to get context manager
async def get_context_mgr() -> ContextManager:
    return get_context_manager()


# Dependency to get tool router
async def get_tool_router_dep() -> ToolRouter:
    return get_tool_router()


# Dependency to get guardrail engine
async def get_guardrail() -> GuardrailEngine:
    return get_guardrail_engine()


# Dependency to get prompt builder
async def get_prompt_builder_dep() -> PromptBuilder:
    return get_prompt_builder()


# API Key security (optional)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    settings: Settings = Depends(get_app_settings)
) -> bool:
    """Verify API key if required."""
    if settings.require_api_key:
        if not api_key or api_key != settings.copilot_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key"
            )
    return True


# CORS middleware
@app.on_event("startup")
async def startup_event():
    """Configure CORS on startup."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("AI Copilot Service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("AI Copilot Service shutting down")


# Pydantic models
class QueryRequest(BaseModel):
    """Request model for copilot query."""
    user_id: str = Field(..., description="ID of the user making the query")
    question: str = Field(..., description="The user's question or query")
    context: Optional[dict] = Field(
        default=None,
        description="Optional context configuration"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for grouping queries"
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Optional task type for model selection"
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional specific model to use"
    )


class QueryResponse(BaseModel):
    """Response model for copilot query."""
    answer: str = Field(..., description="The AI's answer to the query")
    used_tools: List[str] = Field(
        default_factory=list,
        description="List of tools used to gather context"
    )
    context_summary: dict = Field(
        default_factory=dict,
        description="Summary of context used"
    )
    audit_id: str = Field(..., description="Unique audit ID for this query")
    model: str = Field(..., description="Model used for the response")
    tokens_used: int = Field(default=0, description="Number of tokens used")
    duration_ms: float = Field(default=0.0, description="Processing time in milliseconds")
    timestamp: str = Field(..., description="Timestamp of the response")


class FeedbackRequest(BaseModel):
    """Request model for feedback submission."""
    audit_id: str = Field(..., description="The audit ID of the query")
    user_id: str = Field(..., description="ID of the user providing feedback")
    rating: int = Field(..., description="Rating (1-5)", ge=1, le=5)
    comment: Optional[str] = Field(
        default=None,
        description="Optional feedback comment"
    )
    useful: bool = Field(
        default=True,
        description="Whether the response was useful"
    )


class HistoryRequest(BaseModel):
    """Request model for query history."""
    user_id: Optional[str] = Field(
        default=None,
        description="Filter by user ID"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Filter by session ID"
    )
    limit: int = Field(
        default=10,
        description="Maximum number of records to return",
        ge=1,
        le=100
    )


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Timestamp of the check")


class GuardrailStatusResponse(BaseModel):
    """Response model for guardrail status."""
    status: dict = Field(..., description="Guardrail configuration status")


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/guardrails", response_model=GuardrailStatusResponse)
async def get_guardrail_status(
    guardrail: GuardrailEngine = Depends(get_guardrail)
):
    """Get current guardrail configuration."""
    return {"status": guardrail.get_guardrail_status()}


@app.post("/copilot/query", response_model=QueryResponse)
async def query_copilot(
    request: QueryRequest,
    _: bool = Depends(verify_api_key),
    settings: Settings = Depends(get_app_settings),
    audit_logger: AuditLogger = Depends(get_audit),
    guardrail: GuardrailEngine = Depends(get_guardrail),
    context_manager: ContextManager = Depends(get_context_mgr),
    tool_router: ToolRouter = Depends(get_tool_router_dep),
    prompt_builder: PromptBuilder = Depends(get_prompt_builder_dep),
    llm_client = Depends(get_llm_client)
):
    """
    Main endpoint for copilot queries.
    
    Processes a user query by:
    1. Validating the query with guardrails
    2. Building context from available data sources
    3. Routing to appropriate tools
    4. Generating a response with Groq (when GROQ_API is set) or OpenRouter
    5. Logging the interaction
    """
    start_time = time.time()
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Step 1: Validate query with guardrails
    is_valid, error_msg = guardrail.validate_query(request.question)
    if not is_valid:
        audit_id = audit_logger.log_query(
            user_id=request.user_id,
            question=request.question,
            context=request.context or {},
            session_id=session_id
        )
        audit_logger.log_guardrail_violation(
            audit_id=audit_id,
            violation_type="query_validation",
            details=error_msg or "Unknown validation error",
            action="rejected"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query validation failed: {error_msg}"
        )
    
    # Step 2: Build context
    context: Context = await context_manager.build_context(
        user_id=request.user_id,
        query=request.question,
        context_config=request.context,
        session_id=session_id
    )
    
    # Step 3: Route to tools and gather additional context
    tool_calls: List[ToolCall] = tool_router.route_query(
        query=request.question,
        context=context.metadata
    )
    
    # Execute tool calls
    used_tools = []
    tool_results = []
    
    for tool_call in tool_calls:
        # Validate tool call
        is_valid_tool, error_msg = guardrail.validate_tool_call(
            tool_call.tool_type.value,
            tool_call.params
        )
        
        if not is_valid_tool:
            logger.warning(f"Tool validation failed: {error_msg}")
            continue
        
        # Execute tool call
        result: ToolResult = await tool_router.execute_tool_call(tool_call)
        
        if result.success:
            used_tools.append(tool_call.description or tool_call.endpoint)
            tool_results.append(result)
            
            # Add tool result to context
            context.add_item(context_manager._create_context_item_from_tool_result(result))
        else:
            logger.warning(f"Tool call failed: {result.error}")
    
    # Step 4: Build prompt
    task_type = request.task_type or context.metadata.get("intent", "general")
    
    prompt: Prompt = prompt_builder.build_prompt(
        user_id=request.user_id,
        question=request.question,
        context=context,
        task_type=task_type
    )
    
    # Use specified model or default
    model = request.model or prompt.model
    
    # Step 5: Send to OpenRouter
    messages = prompt.to_openrouter_format()
    
    try:
        response_data = await openrouter_client.chat(
            messages=messages,
            model=model,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens
        )
        
        # Extract answer
        answer = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Validate response
        is_valid_response, error_msg = guardrail.validate_response(answer, request.question)
        if not is_valid_response:
            audit_id = audit_logger.log_query(
                user_id=request.user_id,
                question=request.question,
                context=context.to_dict(),
                session_id=session_id
            )
            audit_logger.log_guardrail_violation(
                audit_id=audit_id,
                violation_type="response_validation",
                details=error_msg or "Unknown validation error",
                action="sanitized"
            )
            # Sanitize the response
            answer = guardrail.sanitize_response(answer, context.to_dict())
        
        # Step 6: Log the interaction
        audit_id = audit_logger.log_query(
            user_id=request.user_id,
            question=request.question,
            context=context.to_dict(),
            session_id=session_id
        )
        
        # Log tool calls
        for result in tool_results:
            audit_logger.log_tool_call(
                audit_id=audit_id,
                tool_name=result.tool_call.endpoint,
                tool_input=result.tool_call.params,
                tool_output=result.data,
                duration_ms=result.duration_ms
            )
        
        # Log response
        tokens_used = response_data.get("usage", {}).get("total_tokens", 0)
        audit_logger.log_response(
            audit_id=audit_id,
            answer=answer,
            used_tools=used_tools,
            context_summary=context.to_dict(),
            model=model,
            tokens_used=tokens_used
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Step 7: Return response
        return {
            "answer": answer,
            "used_tools": used_tools,
            "context_summary": context.to_dict(),
            "audit_id": audit_id,
            "model": model,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        audit_id = audit_logger.log_query(
            user_id=request.user_id,
            question=request.question,
            context=context.to_dict(),
            session_id=session_id
        )
        audit_logger.log_error(
            audit_id=audit_id,
            error_type="query_processing",
            error_message=str(e),
            stack_trace=str(e.__traceback__) if hasattr(e, '__traceback__') else None
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@app.get("/copilot/history", response_model=List[dict])
async def get_history(
    request: HistoryRequest,
    _: bool = Depends(verify_api_key),
    audit_logger: AuditLogger = Depends(get_audit)
):
    """Get query history."""
    records = audit_logger.get_audit_records(
        user_id=request.user_id,
        session_id=request.session_id,
        limit=request.limit
    )
    
    # Filter to only query events
    query_records = [
        record for record in records 
        if record.get("event_type") == "query"
    ]
    
    return query_records


@app.get("/copilot/sessions/{session_id}", response_model=List[dict])
async def get_session_history(
    session_id: str,
    _: bool = Depends(verify_api_key),
    audit_logger: AuditLogger = Depends(get_audit)
):
    """Get all records for a specific session."""
    return audit_logger.get_session_history(session_id)


@app.post("/copilot/feedback", response_model=dict)
async def submit_feedback(
    request: FeedbackRequest,
    _: bool = Depends(verify_api_key),
    audit_logger: AuditLogger = Depends(get_audit)
):
    """Submit feedback for a copilot response."""
    # Log feedback as an audit event
    audit_logger.log(
        event_type="feedback",
        user_id=request.user_id,
        audit_id=request.audit_id,
        data={
            "rating": request.rating,
            "comment": request.comment,
            "useful": request.useful,
            "action": "feedback_submitted"
        }
    )
    
    return {
        "status": "received",
        "audit_id": request.audit_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/copilot/context", response_model=dict)
async def get_context(
    request: QueryRequest,
    _: bool = Depends(verify_api_key),
    context_manager: ContextManager = Depends(get_context_mgr)
):
    """
    Get context for a query without generating an LLM response.
    
    Useful for debugging and understanding what context would be gathered.
    """
    context: Context = await context_manager.build_context(
        user_id=request.user_id,
        query=request.question,
        context_config=request.context,
        session_id=request.session_id
    )
    
    return context.to_dict()


@app.post("/copilot/route", response_model=dict)
async def get_route_plan(
    request: QueryRequest,
    _: bool = Depends(verify_api_key),
    tool_router: ToolRouter = Depends(get_tool_router_dep)
):
    """
    Get the tool routing plan for a query without executing.
    
    Useful for debugging and understanding what tools would be called.
    """
    tool_calls: List[ToolCall] = tool_router.route_query(
        query=request.question,
        context=request.context
    )
    
    return {
        "query": request.question,
        "tool_calls": [
            {
                "tool_type": tc.tool_type.value,
                "endpoint": tc.endpoint,
                "method": tc.method,
                "params": tc.params,
                "description": tc.description
            }
            for tc in tool_calls
        ]
    }


# Add helper method to ContextManager for creating context items from tool results
import sys
from ..core.context_manager import ContextItem, ContextType

# Monkey-patch the method
async def _create_context_item_from_tool_result(self, result: ToolResult) -> ContextItem:
    """Create a context item from a tool result."""
    # Map tool type to context type
    type_map = {
        "waste_intel_api": ContextType.AGGREGATED_TELEMETRY,
        "mcp_server": ContextType.CITY_DATA,
        "kg_api": ContextType.KG_RESULTS,
        "ml_api": ContextType.ML_OUTPUTS
    }
    
    context_type = type_map.get(result.tool_call.tool_type.value, ContextType.AGGREGATED_TELEMETRY)
    
    return ContextItem(
        context_type=context_type,
        source=result.tool_call.tool_type.value,
        data={
            "endpoint": result.tool_call.endpoint,
            "result": result.data,
            "success": result.success
        },
        ttl_seconds=60
    )

# Add the method to ContextManager
from ..core.context_manager import ContextManager as CM
CM._create_context_item_from_tool_result = _create_context_item_from_tool_result


# Add import for Optional
from typing import Optional


# Add startup logging
@app.on_event("startup")
async def log_startup():
    logger.info("AI Copilot Service API started")
    settings = get_settings()
    logger.info(f"LLM provider: {"Groq" if settings.groq_api_key else "OpenRouter"} model: {settings.groq_default_model if settings.groq_api_key else settings.openrouter_default_model}")
    logger.info(f"Service port: {settings.copilot_port}")
