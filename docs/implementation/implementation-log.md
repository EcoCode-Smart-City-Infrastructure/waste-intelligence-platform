# WIN OS implementation log

## 2026-11-09 - win-os/initial-platform created

- Inspected the repository (all branches). Found the prior WIN work:
  Phase 1 (architecture docs, modular PostGIS DDL 01-05, Makefile) already
  merged into `init/repository-scaffold` @ 0b2dc67, and Phase 2 (reproducible
  dev environment: production/dev Compose, expanded .env.example, backup,
  Prometheus/Mosquitto config, health checks, seed/setup scripts) on
  `vibe/win-os-master-engineering-69eeb0` @ e74b33a.
- Created dedicated branch `win-os/initial-platform` from e74b33a via the
  GitHub connector (ref verified at that SHA). No existing work deleted.
- Added the `win-os/` tree: FastAPI modular-monolith API (/api/v1: assets,
  facilities, collections with idempotency, nearest-neighbour route planning
  labelled planned/derived, CSV ingestion with quarantine + idempotent
  replay, linear-trend forecast baseline with model metadata, z-score
  anomaly flags, Copilot provider status + deterministic metric summary,
  Control Center system status), RBAC (7 roles) + tenant isolation, audit
  log, correlation IDs, liveness/readiness health.
- Added profiled Compose (core/intelligence/edge/monitoring) + production
  overlay, .env.example (placeholders only), WIN Makefile, Ubuntu preflight.
- Added Alembic migration 0001 (PostGIS core schema), event contracts v1,
  source registry with explicit non-claims, data-status vocabulary.
- Added Ansible roles (validate/docker/deploy, confirmed-host guard, SSH and
  firewall changes opt-in/off by default), cloud-init profile, backup/restore
  docs + restore-check script, monitoring scrape config, MQTT config.
- Added docs: ADR-011, Ubuntu 24.04 deployment guide, runbooks, API guide,
  SECURITY.md, copy-ready CI workflow.
- Tests: 18 pytest tests - all passing locally (SQLite-backed). Defects found
  and fixed during testing: in-batch ingestion duplicates (missing flush),
  and two test-data/permission corrections (route planning is an
  operations-manager action; anomaly threshold made explicit).
- Not executed here (no Docker/Postgres/Ubuntu host in this environment):
  Compose startup, Alembic against live PostGIS, Ansible against a real
  host, restore test. Each is scripted and listed as the next verification
  step - none is claimed done.
