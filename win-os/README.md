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

## Status (honest, v0.2 - 2026-11-10)

| Area | State |
| --- | --- |
| WIN API v0.2 (`win-os/apps/api`) - assets, facilities, collections, vehicles/fleets, waste streams, recovery pathways, environmental accounting, data quality, devices + telemetry, simulations, route planning, ingestion, forecast/anomaly baselines, Copilot status/tools, Control Center | Implemented and tested (30 automated tests) |
| PostgreSQL/PostGIS | **Verified on a real Ubuntu 24.04 host**: PostgreSQL 16.15 + PostGIS 3.4, Alembic 0001-0003 applied, GiST indexes + geom-sync trigger working, API run against it (verify-deployment 6/6), backup produced and **restored into a second database successfully** |
| Compose profiles core / intelligence / edge / monitoring | Config validated for all profiles (`docker compose config`). Full `compose up` NOT yet verified: Docker Hub pulls timed out in the sandbox used for development |
| Ansible provisioning + cloud-init + preflight | Syntax-checked and check-mode run on Ubuntu 24.04; two real role bugs found and fixed. Full non-check run against a fresh server is still the last unverified step |
| Existing web app integration | API client shipped (`apps/web/win-api-client.js`); wiring it into the web-app branch is a separate change on that branch |
| Edge | Bridge + store-and-forward implemented and unit-tested; no physical device tested |
| CI workflow | **Installed** by Stephen 2026-11-10 at `.github/workflows/win-os-ci.yml` on this branch (verified, content matches `win-os/ci/win-os-ci.yml`) |
| Cross-platform | Linux native; macOS + Windows via Docker Desktop (WSL2 backend on Windows); PowerShell preflight/verify scripts; per-OS test matrix in `win-os-xplat-ci` (**installed** by Stephen 2026-11-10 at `.github/workflows/win-os-xplat-ci.yml`, verified) - see `docs/deployment/cross-platform.md` |

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
