# AI Copilot Service API Documentation

## Overview

The AI Copilot Service provides an embedded AI assistant for the Waste Intelligence Platform. It offers natural language interface to the platform's data, ML outputs, and knowledge graph through a RESTful API.

## Base URL

```
http://localhost:8004
```

## Authentication

The service optionally requires an API key for authentication. Set `REQUIRE_API_KEY=true` and `COPILOT_API_KEY` environment variables to enable authentication.

When enabled, include the API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:8004/copilot/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"user_id": "user-123", "question": "What is the waste level?"}'
```

## Endpoints

### POST /copilot/query

Submit a query to the AI Copilot.

**Request:**
```json
{
  "user_id": "string (required)",
  "question": "string (required)",
  "context": "object (optional)",
  "session_id": "string (optional)",
  "task_type": "string (optional)",
  "model": "string (optional)"
}
```

**Response:**
```json
{
  "answer": "string",
  "used_tools": ["string"],
  "context_summary": "object",
  "audit_id": "string",
  "model": "string",
  "tokens_used": "integer",
  "duration_ms": "number",
  "timestamp": "string"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/copilot/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "Why is cluster BK-07 showing anomalies today?",
    "context": {
      "cluster_id": "BK-07",
      "time_range": "2024-01-01T00:00:00Z/2024-01-01T23:59:59Z"
    }
  }'
```

### GET /copilot/history

Retrieve query history.

**Query Parameters:**
- `user_id` (optional): Filter by user ID
- `session_id` (optional): Filter by session ID
- `limit` (optional, default: 10): Maximum number of records to return

**Response:**
```json
[
  {
    "timestamp": "string",
    "audit_id": "string",
    "event_type": "string",
    "user_id": "string",
    "session_id": "string",
    "data": "object"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8004/copilot/history?user_id=operator-123&limit=5"
```

### GET /copilot/sessions/{session_id}

Retrieve all records for a specific session.

**Response:**
```json
[
  {
    "timestamp": "string",
    "audit_id": "string",
    "event_type": "string",
    "user_id": "string",
    "session_id": "string",
    "data": "object"
  }
]
```

**Example:**
```bash
curl -X GET http://localhost:8004/copilot/sessions/session-abc-123
```

### POST /copilot/feedback

Submit feedback for a copilot response.

**Request:**
```json
{
  "audit_id": "string (required)",
  "user_id": "string (required)",
  "rating": "integer (required, 1-5)",
  "comment": "string (optional)",
  "useful": "boolean (optional, default: true)"
}
```

**Response:**
```json
{
  "status": "received",
  "audit_id": "string",
  "timestamp": "string"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/copilot/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "audit_id": "AUDIT-20240101-123456",
    "user_id": "operator-123",
    "rating": 5,
    "comment": "Very helpful response",
    "useful": true
  }'
```

### GET /copilot/context

Get context for a query without generating an LLM response.

**Request:**
```json
{
  "user_id": "string (required)",
  "question": "string (required)",
  "context": "object (optional)",
  "session_id": "string (optional)"
}
```

**Response:**
```json
{
  "user_id": "string",
  "query": "string",
  "session_id": "string",
  "items": [
    {
      "type": "string",
      "source": "string",
      "data": "object",
      "timestamp": "string"
    }
  ],
  "metadata": "object"
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/copilot/context \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "What is the waste level in cluster BK-07?"
  }'
```

### POST /copilot/route

Get the tool routing plan for a query without executing.

**Request:**
```json
{
  "user_id": "string (required)",
  "question": "string (required)",
  "context": "object (optional)"
}
```

**Response:**
```json
{
  "query": "string",
  "tool_calls": [
    {
      "tool_type": "string",
      "endpoint": "string",
      "method": "string",
      "params": "object",
      "description": "string"
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8004/copilot/route \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "Why is cluster BK-07 showing anomalies?"
  }'
```

### GET /guardrails

Get current guardrail configuration.

**Response:**
```json
{
  "status": {
    "forbidden_actions": ["string"],
    "sensitive_fields": ["string"],
    "allowed_data_sources": ["string"],
    "rate_limit_requests": "integer",
    "rate_limit_period": "integer",
    "model_selection_rules": "object"
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8004/guardrails
```

### GET /health

Check service health.

**Response:**
```json
{
  "status": "healthy",
  "version": "string",
  "timestamp": "string"
}
```

**Example:**
```bash
curl -X GET http://localhost:8004/health
```

## Hub Layer Integration

The copilot service is also integrated into the hub layer API at `/copilot` endpoints:

- `POST /copilot/query` - Proxy to copilot service
- `GET /copilot/history` - Proxy to copilot service
- `POST /copilot/feedback` - Proxy to copilot service
- `GET /copilot/guardrails` - Proxy to copilot service

These endpoints are available at the hub layer API port (default: 5000).

## Example Use Cases

### 1. Explain Anomalies

```bash
curl -X POST http://localhost:8004/copilot/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "Why is cluster BK-07 showing anomalies today?",
    "context": {
      "cluster_id": "BK-07",
      "time_range": "2024-01-01T00:00:00Z/2024-01-01T23:59:59Z"
    }
  }'
```

### 2. Get Facility Load Insights

```bash
curl -X POST http://localhost:8004/copilot/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "What is the predicted organic waste load for Brooklyn tomorrow?",
    "context": {
      "borough": "Brooklyn"
    }
  }'
```

### 3. Suggest Routing Adjustments

```bash
curl -X POST http://localhost:8004/copilot/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "Which facilities can process 2 tons of food scraps?",
    "context": {
      "waste_type": "food scraps",
      "quantity": 2000
    }
  }'
```

### 4. Discover Symbiosis Pathways

```bash
curl -X POST http://localhost:8004/copilot/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator-123",
    "question": "What symbiosis pathways exist for spent grain in NYC?",
    "context": {
      "waste_type": "spent grain"
    }
  }'
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid request (missing parameters, validation errors)
- `401 Unauthorized` - Missing or invalid API key (when authentication is enabled)
- `403 Forbidden` - Forbidden action detected
- `500 Internal Server Error` - Unexpected error

## Rate Limiting

Rate limiting can be configured via environment variables:
- `RATE_LIMIT_REQUESTS` - Maximum requests per period (default: 100)
- `RATE_LIMIT_PERIOD` - Period in seconds (default: 60)

When rate limited, the API returns `429 Too Many Requests`.

## Guardrails

The service enforces several guardrails to ensure safe operation:

1. **Forbidden Actions**: Blocks queries that attempt to perform actions like routing changes, facility modifications, or database writes.

2. **Sensitive Data Redaction**: Automatically redacts PII, GPS coordinates, and sensitive identifiers from responses.

3. **Data Source Validation**: Only allows queries to approved data sources (Waste Intelligence API, MCP Server, KG API, ML API).

4. **Response Validation**: Validates LLM responses to ensure they don't contain forbidden actions or sensitive data.

5. **Read-Only Enforcement**: The copilot is strictly advisory and cannot trigger any automated actions.

## WebSocket Streaming (Future)

For real-time streaming responses, a WebSocket endpoint may be added in the future:

```
ws://localhost:8004/copilot/stream
```

This would allow for streaming LLM responses as they are generated.
