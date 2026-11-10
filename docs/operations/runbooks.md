# WIN OS runbooks

## API unhealthy
1. `curl /health/live` (process) vs `/health/ready` (database).
2. Live OK + ready failing: check Postgres container health and
   `WIN_DATABASE_URL`; restart only the API after the DB is healthy.
3. Both failing: `docker compose -f win-os/compose.yaml ps` and API logs
   (structured lines carry the correlation id from the failing request).

## Ingestion failing / quarantines rising
GET /api/v1/ingestion/jobs (admin) shows per-job ok/quarantined counts and
the quarantine reasons. Fix the source records; replay is safe - ingestion
is idempotent on (org, source_record_id).

## Backup
`make -f win-os/Makefile backup` (wraps devops/backup/backup.sh). Confirm a
new file lands in the backup directory and note its size.

## Restore validation (separate environment only)
1. Start a throwaway Postgres/PostGIS.
2. `bash win-os/infrastructure/backup-restore/restore-check.sh`
3. Restore the newest dump into the throwaway instance, run
   `alembic current` and the API test suite against it.
4. Record date + backup id in the implementation log. Never practise
   restores on the production database.

## Copilot unavailable
Expected when no provider key is set: GET /api/v1/copilot/status reports
`unavailable` with the reason. The platform is fully functional without it.

## Security event
Rotate the affected WIN_OS_KEYS entry (keys are stateless), review
`audit_events` for the key id, and check Grafana/Prometheus access logs.
