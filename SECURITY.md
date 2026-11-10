# Security Policy - Waste Intelligence Platform / WIN OS

## Reporting
Report vulnerabilities privately to the repository maintainers. Do not open
public issues for security reports.

## WIN OS security baseline
- Secrets live only in environment variables / a secrets manager. `.env` is
  never committed; `.env.example` files contain placeholders only.
- The WIN API enforces authentication and role-based authorization on the
  server for every `/api/v1` route; tenant (organization) scoping is applied
  to every query and is covered by automated tests.
- Database and MQTT ports are not published publicly by default (localhost
  binding in the base Compose file, unpublished in the production overlay).
- Containers run with `no-new-privileges`; the API image runs as a non-root
  user and mounts a read-only filesystem.
- The AI Copilot has narrowly scoped, permission-checked tools only: no
  shell, no arbitrary SQL, no destructive actions.
- Administrative actions are written to the audit log (`audit_events`).

## Supported versions
WIN OS v0.1.x on branch `win-os/initial-platform`.
