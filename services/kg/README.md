# Knowledge Graph Service (kg-service, :8003)

Implements the KG service that `docker-compose.yml` (and the Platform
API's `KG_URL` / copilot's `KG_API_URL`) referenced but that never
existed. It serves the repo's own W2RKG engine
(`cloud_platform/analytics/kg`) loaded from the NYC sample dataset.

Endpoints: `GET /health`, `POST /kg {query, limit}`,
`GET /kg/nodes?type=&limit=`, `POST /kg/pathways
{waste_type_id, quantity_kg, max_results}`.

Environment: `KG_DATA` (dataset path, default
`cloud_platform/analytics/kg/data/w2rkg_nyc_sample.json`),
`CORS_ORIGINS` (comma-separated; defaults include the Waste
Intelligence GitHub Pages origin so the web app can call it from the
browser).

Run: `docker compose up kg-service`, or locally
`uvicorn app:app --port 8003` from `services/kg/` with the repo root
on `PYTHONPATH`.
