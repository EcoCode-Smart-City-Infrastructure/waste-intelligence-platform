# Backup, restore, disaster recovery

- Database backups: existing platform script `devops/backup/backup.sh`
  (pg_dump based) plus Compose volume snapshots for the WIN OS Postgres.
- Configuration backups exclude secrets: back up `win-os/` and a redacted
  `.env` key list, never the secret values.
- Retention: keep at least daily backups for 14 days and weekly for 8 weeks
  (configure in the backup script environment); never auto-delete before the
  retention check in the runbook passes.
- Recovery objectives (initial): RPO 24h, RTO 4h for the single-server Core
  profile. Point-in-time recovery (WAL archiving) is documented as a future
  upgrade, not configured in v1.
- Reliability rule: backups are not claimed reliable until a restore into a
  separate environment has succeeded. `restore-check.sh` is only the first
  step; the full procedure is in docs/operations/runbooks.md.
