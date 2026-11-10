# WIN OS - Waste Intelligence Network Operating System

A modular, production-oriented software platform on **Ubuntu Server 24.04 LTS**
that turns the existing Waste Intelligence Platform into a cohesive WIN OS:
reproducible deployment, a canonical PostgreSQL/PostGIS data platform, a
secured FastAPI core, ingestion with provenance, baseline intelligence, and a
clear path to edge and simulation profiles. WIN OS is **not** a Linux
distribution - it is a version-controlled platform + deployment profile.

Branch: `win-os/initial-platform` (based on the Phase 1/2 foundation in
`init/repository-scaffold` @ 0b2dc67 and `vibe/win-os-master-engineering-69eeb0`
@ e74b33a - that work is preserved and built on, not replaced).

## Status (honest, 2026-11-09)

| Area | State |
| --- | --- |
| Phase 0/1 architecture docs + full PostGIS DDL | Implemented (pre-existing foundation, verified in repo) |
| WIN API (`win-os/apps/api`) - assets, facilities, collections, route planning, ingestion, forecast/anomaly baselines, Copilot status/tools, Control Center status | Implemented and tested (18 automated tests, SQLite-backed) |
| PostgreSQL/PostGIS schema for WIN OS | Implemented as Alembic migration 0001 (not yet executed against a live Postgres in this environment - no Docker/Postgres available here) |
| Compose profiles core / intelligence / edge / monitoring | Implemented (base + production overlay); not yet run in this environment (no Docker here) - validated by config review, must be smoke-tested on an Ubuntu host |
| Ansible provisioning + cloud-init + preflight | Implemented, syntax-reviewed; not yet executed against a real host |
| Existing web app integration | Documented mapping + backend contract; app unchanged on `web-app` branch |
| Edge devices, simulation, cluster | Interfaces/contracts defined; not implemented (see profiles) |
| CI workflow | Provided at `win-os/ci/win-os-ci.yml`; must be copied to `.github/workflows/` manually (GitHub App cannot write workflows) |

## Quick start (development, no Docker)

```bash
python3 -m venv .venv && .venv/bin/pip install -r win-os/apps/api/requirements-dev.txt
export WIN_OS_KEYS="dev-admin-key:platform_admin:org-dev"
.venv/bin/uvicorn app.main:app --app-dir win-os/apps/api --port 8080
# http://127.0.0.1:8080/health/live  and  /docs
make -f win-os/Makefile test
```

## Quick start (Ubuntu server, Docker)

```bash
cp win-os/.env.example .env   # fill in real secrets
bash win-os/infrastructure/deployment/preflight.sh
make -f win-os/Makefile deploy
```

## Layout

```
win-os/
  compose.yaml / compose.prod.yaml   profile-based deployment
  apps/api/                          FastAPI modular monolith (/api/v1)
  apps/web/                          integration notes for the existing web app
  data-platform/                     Alembic migrations, event contracts,
                                     source registry, data-status vocabulary
  infrastructure/                    Ansible, cloud-init, monitoring,
                                     backup-restore, deployment preflight
  os-image/profiles/                 core / intelligence / edge / simulation / cluster
  tests/                             pytest suite (18 tests)
  ci/                                copy-ready GitHub Actions workflow
```

Docs: `docs/architecture/` (current state, target, ADRs incl. ADR-011),
`docs/implementation/implementation-log.md`, `docs/deployment/ubuntu-24.04.md`,
`docs/operations/runbooks.md`, `docs/api/win-os-api.md`.
