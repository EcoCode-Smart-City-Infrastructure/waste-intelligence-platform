# Deploying WIN OS on Ubuntu Server 24.04 LTS

Primary target: Ubuntu Server 24.04 LTS (22.04 accepted). Requirements:
2+ vCPU, 4 GB RAM (Core), 20 GB disk, Docker Engine + Compose plugin.

## Path A - Ansible + Compose (recommended)

1. Provision: `ansible-playbook -i inventory.ini win-os/infrastructure/ansible/site.yml`
   (check mode first: `--check --diff`). The playbook refuses unidentified
   hosts and never changes SSH/firewall unless you opt in.
2. Clone branch `win-os/initial-platform` to `/opt/win-os`.
3. `cp win-os/.env.example .env` and set real secrets (passwords via
   `openssl rand -hex 24`; API keys in `key:role:org_id` form).
4. `bash win-os/infrastructure/deployment/preflight.sh`
5. `make -f win-os/Makefile deploy` (Core profile + production overlay:
   only the API is published, on localhost - put your TLS reverse proxy in
   front; databases and brokers stay unpublished).
6. Migrate: `make -f win-os/Makefile db-migrate`
7. Verify: `make -f win-os/Makefile health`, then create an asset with an
   operator key and read it back with a viewer key.

## Path B - cloud-init
Use `win-os/infrastructure/cloud-init/win-core.yaml` for first boot, then
follow Path A from step 2. Secrets are never in cloud-init.

## Upgrades
Pull the branch, re-run preflight, `alembic upgrade head`, rebuild the API
image, restart the profile. Rollback: check out the previous commit, rebuild,
and if a migration must be reversed use its documented downgrade in a
maintenance window after a backup.

## Pinning
Production should pin image digests for postgis/postgis, redis, prometheus
and grafana in win-os/compose.yaml and record them in the change log.
