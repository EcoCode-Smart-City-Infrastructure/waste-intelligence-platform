# WIN OS task interface (supplements the repo-root Makefile).
# Run from the repository root:  make -f win-os/Makefile <target>
COMPOSE ?= docker compose -f win-os/compose.yaml
PY ?= python3

.PHONY: help setup dev build test lint health backup restore-check deploy down
help: ## Show WIN OS targets
	@grep -E '^[a-zA-Z_-]+:.*##' win-os/Makefile | sed 's/:.*## /  - /'

setup: ## Create .env from the example if missing (never overwrites)
	@test -f .env || cp win-os/.env.example .env && echo "edit .env before deploying"

dev: ## Start the WIN Core profile
	$(COMPOSE) --profile core up -d --build

build: ## Build the WIN API image
	$(COMPOSE) build api

test: ## Run the WIN OS test suite (SQLite-backed, no Docker required)
	cd win-os && $(PY) -m pytest tests -q

lint: ## Syntax-check the WIN API
	$(PY) -m compileall -q win-os/apps/api/app win-os/tests

health: ## Check API liveness/readiness on the configured port
	curl -fsS http://127.0.0.1:$${WIN_API_PORT:-8080}/health/live && echo
	curl -fsS http://127.0.0.1:$${WIN_API_PORT:-8080}/health/ready && echo

db-migrate: ## Apply Alembic migrations (PostgreSQL/PostGIS deployments)
	cd win-os/data-platform/migrations && alembic upgrade head

backup: ## Database backup via the existing platform backup script
	bash devops/backup/backup.sh

restore-check: ## Validate the latest backup can be listed/restored (dry check)
	bash win-os/infrastructure/backup-restore/restore-check.sh

deploy: ## Deploy WIN Core on this host via Compose (preflight first)
	bash win-os/infrastructure/deployment/preflight.sh
	$(COMPOSE) --profile core -f win-os/compose.prod.yaml up -d --build

down: ## Stop WIN OS services (keeps volumes)
	$(COMPOSE) --profile core --profile intelligence --profile edge --profile monitoring down
