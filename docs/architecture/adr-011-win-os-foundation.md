# ADR-011 - WIN OS foundation decisions (2026-11-09)

Supplements ADR-001..010 in architecture-decisions.md; nothing there is
removed. Where this ADR differs, it governs the `win-os/` tree only.

1. **Dedicated branch** `win-os/initial-platform`, created from the most
   complete existing WIN foundation (`vibe/win-os-master-engineering-69eeb0`,
   Phase 1 docs/schema + Phase 2 environment) - foundation rule: build on
   what exists, never restart.
2. **Ubuntu 24.04 LTS is the primary target** (supersedes ADR-005's 22.04 for
   new WIN OS work): supported to 2029 (ESM to 2034), ships Python 3.12 and
   PostgreSQL 16 / PostGIS 3.4. 22.04 remains an accepted fallback and is
   still validated by preflight/Ansible.
3. **WIN OS lives in `win-os/`** rather than restructuring the whole repo:
   the platform already has working trees (hub_layer, src/, services/,
   copilot_service, web app on its own branch). A contained tree avoids
   breaking them and can absorb them incrementally.
4. **Canonical database**: PostgreSQL + PostGIS (postgis/postgis:16-3.4) for
   WIN OS. The legacy stack's TimescaleDB image remains for the existing
   platform; WIN OS telemetry hypertables are a future migration decision,
   not a v1 requirement.
5. **API keys -> OIDC path**: v1 authenticates with environment-configured
   API keys mapped to role+organization principals (server-side RBAC,
   tenant scoping on every query, tested). Passwords are never handled.
   ADR-007's JWT/OIDC direction is preserved as the upgrade path behind the
   same `authenticate` seam.
6. **Alembic owns WIN OS schema**; the SQLAlchemy models mirror migration
   0001. SQLite exists only so tests/dev run without Docker; production
   refuses SQLite.
7. **Profiles over microservices**: Compose profiles (core / intelligence /
   edge / monitoring) keep one modular monolith for business logic; the
   pre-existing forecasting and copilot services join the intelligence
   profile unchanged.
