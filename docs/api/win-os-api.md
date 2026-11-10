# WIN OS API (/api/v1)

Base: the WIN API service (win-os/apps/api). Interactive contract: `/docs`
(OpenAPI JSON at `/api/v1/openapi.json`).

Auth: `X-API-Key` header. Keys are configured server-side as
`key:role:org_id` (WIN_OS_KEYS). Roles: platform_admin, org_admin,
operations_manager, analyst, operator, viewer, integration. Every route is
permission-checked and organization-scoped on the server.

| Route | Permission | Notes |
| --- | --- | --- |
| GET /health/live, /health/ready | none | liveness vs readiness |
| POST/GET /api/v1/assets, GET /assets/{id} | write / read | provenance + data_status on every record |
| POST/GET /api/v1/facilities | write / read | capacity null = unavailable, never 0 |
| POST/GET /api/v1/collections | write / read | Idempotency-Key header supported; asset must exist in your org |
| POST /api/v1/routes/plan | plan | nearest-neighbour plan; execution_status stays "planned" |
| POST /api/v1/intelligence/forecast | analyse | baseline linear trend; returns model metadata + limitations |
| POST /api/v1/intelligence/anomaly | analyse | z-score flags for review |
| POST /api/v1/ingestion/assets, GET /ingestion/jobs | ingest / read | idempotent on source_record_id; invalid records quarantined with reasons |
| GET /api/v1/copilot/status, /copilot/metric-summary | read | honest unavailable state; summary is deterministic, not a model |
| GET /api/v1/system/status | admin | WIN Control Center: DB, copilot, last ingestion |

Errors are consistent JSON: {"detail": {"error": ..., "message": ...}}.
Lists support limit/offset pagination. Responses carry X-Correlation-ID.
