# WIN OS v0.2 release-readiness assessment (2026-11-10)

## Implemented and tested
- Full /api/v1 surface for Core + Operations + Edge + Simulation +
  Control Center (see docs/api/win-os-api.md, updated for v0.2 routes in the
  implementation log). 30 automated tests passing.
- Data integrity: provenance + data_status everywhere; idempotent
  collections, ingestion and telemetry; unknown capacity/diversion/telemetry
  stays unavailable (null), never zero; simulated totals never merge into
  derived/observed totals.
- Security: server-side RBAC + tenant isolation (tested), audit log,
  security headers, per-key rate limiting (tested), secrets only via env,
  DB/broker not publicly exposed in the production overlay.

## Verified on a real host (Ubuntu 24.04, this development environment)
- PostgreSQL 16.15 + PostGIS 3.4 via apt; Alembic 0001-0003 applied;
  spatial index + proximity query; geom-sync trigger.
- API against Postgres: verify-deployment.sh 6/6.
- Backup (shipped script, checksummed) restored into a second database.
- Compose configuration validated for all profiles.
- Ansible syntax + check mode (assertions pass; role bugs found and fixed).

## Not yet verified / remaining before "production"
1. Full `docker compose up` on a clean Ubuntu server (image pulls were
   blocked by the development sandbox network; the Dockerfiles and Compose
   files are validated but the built images have not run together).
2. Ansible full (non-check) run against a fresh server, incl. reboot and
   the systemd unit starting the stack.
3. TLS end-to-end with a real certificate (nginx template provided).
4. A physical edge device publishing MQTT telemetry through the bridge.
5. CI workflow copied into .github/workflows/ and green on GitHub.
6. Load/performance testing - none done; single-server profile only.

## Known limitations
- API keys are the v1 auth mechanism (OIDC/JWT remains the documented
  upgrade path behind the same authenticate seam).
- Environmental factors are WIN-ENV-ACCT-1.0 planning estimates, not
  verified emissions accounting.
- Forecasting is a linear-trend baseline; anomaly detection is z-score.
  Both are labelled as such in every response.
- The API process model assumes a single app instance per database binding
  (create_app rebinds the session factory); horizontal scaling needs the
  documented dependency-injection refactor.
