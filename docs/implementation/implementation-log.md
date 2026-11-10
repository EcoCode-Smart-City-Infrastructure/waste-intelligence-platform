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

## 2026-11-10 - v0.2: all remaining phases built out (win-os/initial-platform)

- Phase 6 (operations): vehicles/fleets, waste streams, recovery pathways
  (references validated; unknown diversion stays unavailable), environmental
  accounting (WIN-ENV-ACCT-1.0, formula stored per record, totals separated
  by data_status), data-quality summary endpoint.
- Phase 9 (edge/simulation): device registry, telemetry batch ingestion with
  store-and-forward idempotency, MQTT bridge with SQLite offline buffer,
  diversion scenarios labelled simulated and excluded from env totals.
- Phase 4/8: win-api-client.js for the existing web app (honest unavailable
  states, no silent demo fallback), Control Center /system/jobs, seed tool
  (refuses production), verify-deployment.sh.
- Phase 10 (hardening): security headers, per-key rate limiting (429),
  systemd unit, nginx TLS proxy template, WIN backup script
  (pg_dump + sha256 + retention guard).
- Migrations: 0002 (operations/edge tables), 0003 (PostGIS geom sync
  trigger - added after field verification showed geom stayed NULL).

### Verification actually executed on an Ubuntu 24.04 host (this environment)
- pytest: 30/30 passing (SQLite-backed suites v0.1 + v0.2 + edge buffer).
- PostgreSQL 16.15 + PostGIS 3.4 (apt-installed): Alembic upgrade head
  applied 0001-0003; 17 application tables; GiST geom indexes present;
  geom trigger verified (insert with lat/lon produced POINT geometry);
  PostGIS proximity query returned correct distance.
- WIN API run against that Postgres: verify-deployment.sh 6/6 PASS.
- Backup/restore: backup-win-os.sh produced a checksummed dump; pg_restore
  into a second database restored all rows (one cosmetic pg_restore comment
  warning about extension ownership). Restore test: PASSED.
- Compose: `docker compose config` validated for all four profiles. Docker
  daemon was started in the sandbox, but image pulls from Docker Hub timed
  out (sandbox network), so a full `compose up` remains unverified here.
- Ansible: syntax check passed; check-mode run against localhost (real
  Ubuntu 24.04) passed validation assertions and found two real role bugs,
  both fixed (invalid get_url 'creates' parameter; systemd-timesyncd now
  installed by the role before the service task, with a live-systemd guard).
