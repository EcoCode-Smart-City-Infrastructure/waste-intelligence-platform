# AI Copilot Service Architecture

## Overview

The AI Copilot Service is a microservice that provides an embedded AI assistant for the Waste Intelligence Platform. It enables natural language queries, explanations, and recommendations while maintaining strict data boundaries and operational safety.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Operator Dashboard (Web)                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Hub Layer API (Flask)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   /bins      │  │ /facilities   │  │ /analytics    │  │ /copilot    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Copilot Service (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Copilot API (POST /copilot/query, GET /copilot/history, ...)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                      │
│        ┌───────────────────┐    ┌───────────────────┐                 │
│        │ Context Manager    │    │ Tool Router        │                 │
│        │ - Builds context   │    │ - Routes queries    │                 │
│        │ - Aggregates data   │    │ - Calls backends    │                 │
│        └───────────┬───────┘    └───────────┬───────┘                 │
│                        │                       │                        │
│        ┌───────────────────┐    ┌───────────────────┐                 │
│        │ Prompt Builder     │    │ Guardrail Engine   │                 │
│        │ - Assembles prompts│    │ - Validates queries│                 │
│        │ - Optimizes format │    │ - Enforces policies│                 │
│        └───────────────────┘    └───────────┬───────┘                 │
│                                                │                        │
│                                        ┌───────▼───────┐                 │
│                                        │ Audit Logger   │                 │
│                                        │ - Logs all      │                 │
│                                        │   interactions  │                 │
│                                        └───────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                           ▼           ▼
┌─────────────────────────┐   ┌────────────────┐   ┌────────────────┐
│  Waste Intelligence API   │   │  MCP NYC Server  │   │  KG API         │
│  (Flask)                 │   │  (FastAPI)       │   │  (FastAPI)      │
│  Port: 8001              │   │  Port: 8000      │   │  Port: 8003     │
└─────────────────────────┘   └────────────────┘   └────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OpenRouter (External SaaS)                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  LLM Models (various providers)                                    │  │
│  │  - openai/gpt-4o-mini (default)                                  │  │
│  │  - openai/gpt-4o                                                  │  │
│  │  - anthropic/claude-3-sonnet                                      │  │
│  │  - google/gemini-pro-1.5                                         │  │
│  │  - meta-llama/llama-3.1-8b-instruct                               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Platform Data Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ TimescaleDB     │  │ ML Services      │  │ Knowledge Graph  │    │
│  │ (Postgres)       │  │ (Inference)      │  │ (W2RKG)          │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Copilot API

The main API layer that provides RESTful endpoints for:
- Query processing (`POST /copilot/query`)
- History retrieval (`GET /copilot/history`)
- Feedback submission (`POST /copilot/feedback`)
- Context inspection (`POST /copilot/context`)
- Routing plan inspection (`POST /copilot/route`)
- Guardrail status (`GET /guardrails`)

**Technology**: FastAPI (async, high-performance)

### 2. Context Manager

Builds structured context from various data sources:

- **Waste Intelligence API**: Bin/cluster/facility data and telemetry
- **MCP NYC Server**: Weather, air quality, mobility, geodata
- **Knowledge Graph API**: Waste-to-resource pathways and symbiosis data
- **ML API**: Forecasting, anomaly detection, contamination classification

**Features:**
- Entity extraction from queries (cluster IDs, facility IDs, waste types, etc.)
- Intent inference (explain, query, predict, recommend, etc.)
- Context caching with TTL
- Aggregated data only (no raw sensor data)

### 3. Tool Router

Intelligently routes queries to appropriate backend services:

**Intent Detection:**
- Telemetry queries → Waste Intelligence API
- Anomaly queries → ML API
- Forecast queries → ML API
- City data queries → MCP Server
- Pathway queries → KG API
- Routing queries → Waste Intelligence API + KG API
- Facility info queries → Waste Intelligence API + KG API
- Cluster info queries → Waste Intelligence API
- Symbiosis queries → KG API

**Features:**
- Concurrent tool execution
- Result aggregation
- Error handling
- Tool validation

### 4. Prompt Builder

Assembles optimized prompts for LLM inference:

**Components:**
- **System Prompt**: Role definition, constraints, and guidelines
- **Context**: Structured data from various sources
- **User Prompt**: Question with intent-specific instructions

**Features:**
- Task-specific temperature and max_tokens
- Model selection based on task type
- Context length optimization
- Formatting for readability

### 5. Guardrail Engine

Enforces safety policies and operational constraints:

**Guardrails:**
- **Forbidden Action Detection**: Blocks queries attempting to modify routes, facilities, or databases
- **Sensitive Data Redaction**: Removes PII, GPS coordinates, and sensitive identifiers
- **Data Source Validation**: Only allows queries to approved sources
- **Response Validation**: Ensures LLM responses don't contain forbidden actions or PII
- **Rate Limiting**: Configurable request limits per user

**Features:**
- Pattern-based detection
- Model selection by task type
- Sanitization of responses
- Audit logging of violations

### 6. Audit Logger

Comprehensive logging of all interactions:

**Logged Events:**
- User queries
- Context gathered
- Tools called
- LLM responses
- Operator actions
- Guardrail violations
- Errors

**Features:**
- JSON Lines format for easy parsing
- Unique audit IDs for traceability
- Session grouping
- Timestamping
- File-based storage with rotation

## Data Flow

### Query Processing Flow

1. **Request Reception**: User query received at `/copilot/query`
2. **Guardrail Validation**: Query validated for forbidden actions
3. **Context Building**: Context Manager gathers relevant data
4. **Tool Routing**: Tool Router determines which backends to call
5. **Tool Execution**: Concurrent calls to Waste Intel API, MCP, KG, ML
6. **Context Augmentation**: Tool results added to context
7. **Prompt Building**: Prompt Builder assembles system, context, and user prompts
8. **LLM Inference**: OpenRouter called with optimized prompt
9. **Response Validation**: Guardrail Engine validates response
10. **Audit Logging**: All interactions logged for compliance
11. **Response**: Formatted response returned to user

### Example Query Flow

```
User Query: "Why is cluster BK-07 showing anomalies today?"
    │
    ▼
Guardrail Validation: ✓ Safe
    │
    ▼
Context Building:
  - Extract: cluster_id=BK-07, intent=explain
  - Gather: Cluster info, telemetry, anomalies
    │
    ▼
Tool Routing:
  - Waste Intel API: GET /clusters/BK-07
  - Waste Intel API: GET /clusters/BK-07/telemetry
  - ML API: GET /anomaly/cluster/BK-07
    │
    ▼
Tool Execution: Concurrent HTTP requests
    │
    ▼
Context Augmentation: Results added to context
    │
    ▼
Prompt Building:
  System: Role + constraints
  Context: Cluster data + anomalies
  User: Question + intent instructions
    │
    ▼
OpenRouter: POST /chat/completions (model: openai/gpt-4o-mini)
    │
    ▼
Response Validation: ✓ Safe
    │
    ▼
Audit Logging: Query, tools, response logged
    │
    ▼
Response: {"answer": "...", "used_tools": [...], "audit_id": "..."}
```

## Deployment Architecture

### Containerization

- **Docker Image**: Multi-stage build for production
- **Base Image**: python:3.11-slim
- **Dependencies**: FastAPI, httpx, pydantic, etc.
- **Port**: 8004

### Docker Compose Integration

```yaml
services:
  copilot-service:
    build:
      context: .
      dockerfile: copilot_service/Dockerfile
    ports:
      - "8004:8004"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - WASTE_INTEL_API_URL=http://waste-intel-api:8001
      - MCP_SERVER_URL=http://nyc-opendata-mcp:8000
      - KG_API_URL=http://kg-service:8003
      - ML_API_URL=http://ml-service:8002
    depends_on:
      - waste-intel-api
      - nyc-opendata-mcp
      - kg-service
      - ml-service
```

### Service Dependencies

```
copilot-service
    ├─ waste-intel-api (port 8001)
    ├─ nyc-opendata-mcp (port 8000)
    ├─ kg-service (port 8003)
    ├─ ml-service (port 8002)
    └─ openrouter.ai (external)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | API key for OpenRouter | Required |
| `OPENROUTER_BASE_URL` | Base URL for OpenRouter API | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | Default model to use | `openai/gpt-4o-mini` |
| `WASTE_INTEL_API_URL` | URL for Waste Intelligence API | `http://waste-intel-api:8001` |
| `MCP_SERVER_URL` | URL for MCP NYC Server | `http://nyc-opendata-mcp:8000` |
| `KG_API_URL` | URL for Knowledge Graph API | `http://kg-service:8003` |
| `ML_API_URL` | URL for ML Inference API | `http://ml-service:8002` |
| `COPILOT_PORT` | Port for copilot service | `8004` |
| `COPILOT_API_KEY` | API key for copilot service | None |
| `REQUIRE_API_KEY` | Require API key for requests | `false` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Model Selection Rules

The service automatically selects models based on task type:

| Task Type | Model | Reasoning |
|-----------|-------|-----------|
| `real_time` | `openai/gpt-4o-mini` | Fast, cost-effective for live queries |
| `planning` | `openai/gpt-4o` | High accuracy for strategic planning |
| `routine` | `meta-llama/llama-3.1-8b-instruct` | Cheap for routine tasks |
| `debug` | `anthropic/claude-3-sonnet` | Good at code and debugging |
| `explain` | `openai/gpt-4o-mini` | Balanced for explanations |
| `summarize` | `openai/gpt-4o-mini` | Balanced for summaries |
| `query` | `openai/gpt-4o-mini` | Balanced for general queries |

## Security Considerations

### Data Boundaries

The copilot service enforces strict data boundaries:

**Allowed Data:**
- Aggregated telemetry (cluster, facility, bin levels)
- ML outputs (forecasts, anomalies, classifications)
- Knowledge Graph results (pathways, symbiosis)
- City data (weather, air quality, mobility)

**Forbidden Data:**
- Raw sensor data (bin-level PII)
- Exact GPS coordinates
- User identities
- Sensitive facility details
- Database credentials

### Operational Safety

1. **Advisory Only**: All responses are explicitly advisory
2. **Human in the Loop**: Human approval required for any operational changes
3. **No Actuation**: Copilot cannot trigger any automated actions
4. **Audit Trail**: All interactions logged for compliance
5. **Guardrails**: Multiple layers of validation and filtering

### Network Security

- All inter-service communication via HTTP (can be upgraded to HTTPS)
- API key authentication (optional)
- CORS restrictions
- Rate limiting

## Scalability

### Horizontal Scaling

The service is stateless (except for logs) and can be horizontally scaled:
- Multiple instances can run behind a load balancer
- Each instance maintains its own connections to backend services
- Audit logs can be centralized via log aggregation

### Performance Optimization

- Concurrent tool execution
- Context caching with TTL
- Connection pooling for HTTP clients
- Async I/O throughout

### Resource Requirements

- **CPU**: Minimal (LLM inference offloaded to OpenRouter)
- **Memory**: ~256MB (Python + FastAPI + dependencies)
- **Network**: Moderate (multiple API calls per query)
- **Storage**: Minimal (logs only)

## Monitoring

### Health Checks

- `/health` endpoint for service health
- Docker health check configured
- Dependencies checked on startup

### Logging

- Structured JSON logging
- Audit logging for compliance
- Error logging for debugging
- Performance metrics (duration, tokens used)

### Metrics (Future)

Potential metrics to add:
- Query count by user
- Query count by intent
- Average response time
- Token usage by model
- Error rates
- Guardrail violations

## Integration Points

### Hub Layer API

The copilot service is integrated into the hub layer API via proxy endpoints:
- `/copilot/query` → Copilot Service `/copilot/query`
- `/copilot/history` → Copilot Service `/copilot/history`
- `/copilot/feedback` → Copilot Service `/copilot/feedback`
- `/copilot/guardrails` → Copilot Service `/guardrails`

### Dashboard Integration

The copilot can be integrated into dashboards via:
1. **Sidebar Panel**: Embedded chat interface
2. **Context Menu**: Right-click on data for copilot explanation
3. **Query Builder**: Natural language to structured query conversion
4. **Insight Generator**: Automatic insights from data patterns

### Example Dashboard Integration

```javascript
// Frontend JavaScript
async function queryCopilot(question, context) {
  const response = await fetch('/copilot/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': localStorage.getItem('apiKey')
    },
    body: JSON.stringify({
      user_id: currentUser.id,
      question: question,
      context: context,
      session_id: currentSession.id
    })
  });
  
  const data = await response.json();
  return data;
}
```

## Future Enhancements

### 1. Streaming Responses

Add WebSocket endpoint for real-time streaming of LLM responses:
```
ws://localhost:8004/copilot/stream
```

### 2. Model Caching

Cache frequent model responses to reduce costs and latency.

### 3. Advanced Guardrails

- Custom policy configuration
- User-specific permissions
- Data classification and handling

### 4. Multi-turn Conversations

- Session management
- Conversation history
- Context persistence across turns

### 5. Custom Tools

- Plug-in architecture for custom tools
- Dynamic tool registration
- Tool discovery

### 6. Performance Analytics

- Query performance metrics
- Model comparison
- Cost tracking

## Compliance

### Data Governance

- All data access logged
- Sensitive data redacted
- Access controls enforced
- Audit trail maintained

### Operational Compliance

- Advisory-only operation
- Human-in-the-loop requirement
- No automated actuation
- Liability protection

### Privacy

- PII detection and redaction
- No personal data storage
- Minimal data retention
- Compliance with data protection regulations
