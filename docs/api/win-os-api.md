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

## v0.2 additions

| Route | Permission | Notes |
| --- | --- | --- |
| POST/GET /api/v1/vehicles | write / read | fleet filter via ?fleet= |
| POST/GET /api/v1/waste-streams | write / read | |
| POST/GET /api/v1/recovery-pathways | write / read | stream + facility must exist in your org; unknown diversion = unavailable |
| POST /api/v1/environmental/records, GET /environmental/summary | write / read | WIN-ENV-ACCT-1.0 factors; formula stored; totals split by data_status |
| GET /api/v1/data-quality/summary | read | records by data_status + per-source ingestion freshness/quarantine |
| POST/GET /api/v1/devices | write / read | never-reported device = telemetry unavailable |
| POST/GET /api/v1/telemetry/events | ingest / read | batch, store-and-forward idempotent; unregistered devices quarantined |
| POST/GET /api/v1/simulations | analyse / read | diversion scenarios; results are data_status=simulated |
| GET /api/v1/system/jobs | admin | ingestion + forecast jobs, telemetry count, device reporting state |

All /api responses carry security headers; /api/v1 is rate-limited per API
key (default 600/min, WIN_RATE_LIMIT_PER_MIN) with 429 on excess.
