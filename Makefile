# Waste Intelligence Network Operating System (WIN OS)
# Makefile for development and deployment tasks

# Configuration
PROJECT_NAME := waste-intelligence-platform
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_FILES := -f docker-compose.yml -f docker-compose.dev.yml
PYTHON := python3
PIP := pip3
SHELL := /bin/bash

# Directories
SRC_DIR := src
HUB_DIR := hub_layer
CLOUD_DIR := cloud-platform
COPILOT_DIR := copilot_service
SCRIPTS_DIR := scripts
DOCS_DIR := docs
TESTS_DIR := tests
INFRA_DIR := infrastructure

# Environment
ENV_FILE := .env
ENV_EXAMPLE := .env.example

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help

# ============================================================================
# MAIN TARGETS
# ============================================================================

help: ## Show this help message
	@echo "Waste Intelligence Network OS - Makefile"
	@echo "========================================"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Core Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[0;32m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "For more information, see: https://github.com/EcoCode-Smart-City-Infrastructure/waste-intelligence-platform"

# ============================================================================
# SETUP AND INSTALLATION
# ============================================================================

setup: .env ## Set up development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(YELLOW)Created $(ENV_FILE) from $(ENV_EXAMPLE). Please configure your settings.$(NC)"; \
	fi
	@echo "$(GREEN)Development environment ready!$(NC)"

install: ## Install Python dependencies
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

install-dev: install ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt -r requirements.dev.txt 2>/dev/null || $(PIP) install -r requirements.txt
	@echo "$(GREEN)Development dependencies installed!$(NC)"

# ============================================================================
# DOCKER AND CONTAINERS
# ============================================================================

docker-build: ## Build all Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)Docker images built!$(NC)"

docker-up: ## Start all services with Docker Compose
	@echo "$(GREEN)Starting services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started!$(NC)"

docker-up-dev: ## Start all services with development configuration
	@echo "$(GREEN)Starting services with development configuration...$(NC)"
	$(DOCKER_COMPOSE) $(DOCKER_COMPOSE_FILES) up -d
	@echo "$(GREEN)Services started with development configuration!$(NC)"

docker-down: ## Stop and remove all containers
	@echo "$(GREEN)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Services stopped!$(NC)"

docker-down-v: ## Stop and remove all containers and volumes
	@echo "$(YELLOW)WARNING: This will remove all data volumes!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
		echo; \
		if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			$(DOCKER_COMPOSE) down -v; \
			echo "$(GREEN)Services and volumes removed!$(NC)"; \
		else \
			echo "$(GREEN)Cancelled.$(NC)"; \
		fi

docker-restart: ## Restart all services
	@echo "$(GREEN)Restarting services...$(NC)"
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)Services restarted!$(NC)"

docker-logs: ## Show logs for all services
	@echo "$(GREEN)Showing logs for all services...$(NC)"
	$(DOCKER_COMPOSE) logs -f

docker-logs-%: ## Show logs for a specific service
	@echo "$(GREEN)Showing logs for $(*) service...$(NC)"
	$(DOCKER_COMPOSE) logs -f $(*)

docker-ps: ## List running containers
	@echo "$(GREEN)Running containers:$(NC)"
	$(DOCKER_COMPOSE) ps

# ============================================================================
# DATABASE
# ============================================================================

db-init: ## Initialize database with schema
	@echo "$(GREEN)Initializing database...$(NC)"
	@echo "Waiting for PostgreSQL to be ready..."
	@until $(DOCKER_COMPOSE) exec postgres pg_isready -U timescale -d wasteintel; do \
		sleep 1; \
	done
	@echo "PostgreSQL is ready!"
	@echo "Loading schema..."
	@$(DOCKER_COMPOSE) exec postgres psql -U timescale -d wasteintel \
		-f hub_layer/database/01_extensions_and_types.sql \
		-f hub_layer/database/02_core_tables.sql \
		-f hub_layer/database/03_operations_tables.sql \
		-f hub_layer/database/04_environmental_tables.sql \
		-f hub_layer/database/05_intelligence_tables.sql
	@echo "$(GREEN)Database initialized!$(NC)"

db-seed: ## Seed database with sample data
	@echo "$(GREEN)Seeding database with sample data...$(NC)"
	$(PYTHON) scripts/seed_data.py
	@echo "$(GREEN)Database seeded!$(NC)"

db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(NC)"
	@if [ -d "hub_layer/database/migrations" ]; then \
		$(PYTHON) -m alembic -c hub_layer/database/alembic.ini upgrade head; \
	else \
		@echo "$(YELLOW)No migrations directory found. Using schema files instead.$(NC)"; \
		$(MAKE) db-init; \
	fi
	@echo "$(GREEN)Migrations applied!$(NC)"

db-reset: ## Reset database (DANGER: deletes all data!)
	@echo "$(RED)WARNING: This will delete all data in the database!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
		echo; \
		if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			$(DOCKER_COMPOSE) exec postgres psql -U timescale -d wasteintel -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
			$(MAKE) db-init; \
			$(MAKE) db-seed; \
			echo "$(GREEN)Database reset and reinitialized!$(NC)"; \
		else \
			echo "$(GREEN)Cancelled.$(NC)"; \
		fi

db-shell: ## Open PostgreSQL shell
	@echo "$(GREEN)Opening PostgreSQL shell...$(NC)"
	$(DOCKER_COMPOSE) exec postgres psql -U timescale -d wasteintel

db-backup: ## Create database backup
	@echo "$(GREEN)Creating database backup...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec postgres pg_dump -U timescale -d wasteintel -F c -f /backups/wasteintel_$$(date +%Y%m%d_%H%M%S).dump
	@echo "$(GREEN)Backup created in backups/ directory!$(NC)"

db-restore: ## Restore database from backup
	@echo "$(RED)WARNING: This will overwrite the current database!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
		echo; \
		if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			@echo "Available backups:"; \
			@ls -lh backups/; \
			@read -p "Enter backup filename: " backup_file; \
			$(DOCKER_COMPOSE) exec postgres pg_restore -U timescale -d wasteintel -c /backups/$$backup_file; \
			echo "$(GREEN)Database restored!$(NC)"; \
		else \
			echo "$(GREEN)Cancelled.$(NC)"; \
		fi

# ============================================================================
# DEVELOPMENT
# ============================================================================

dev: setup install-dev db-init db-seed ## Set up complete development environment
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo ""
	@echo "Services available at:"
	@echo "  - API:        http://localhost:8001"
	@echo "  - Copilot:    http://localhost:8004"
	@echo "  - Grafana:    http://localhost:3000"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - PostgreSQL:  localhost:5432"
	@echo "  - Redis:      localhost:6379"
	@echo "  - MQTT:       localhost:1883"

run: ## Start the application (API)
	@echo "$(GREEN)Starting application...$(NC)"
	cd hub_layer && $(PYTHON) api/app.py

run-copilot: ## Start the Copilot service
	@echo "$(GREEN)Starting Copilot service...$(NC)"
	cd copilot_service && $(PYTHON) -m uvicorn api.app:app --reload --port 8004

run-ml: ## Start the ML service
	@echo "$(GREEN)Starting ML service...$(NC)"
	cd services/forecasting && $(PYTHON) app.py

# ============================================================================
# TESTING
# ============================================================================

test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --tb=short

test-unit: ## Run unit tests
	@echo "$(GREEN)Running unit tests...$(NC)"
	$(PYTHON) -m pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(PYTHON) -m pytest tests/integration/ -v --tb=short

test-contract: ## Run API contract tests
	@echo "$(GREEN)Running API contract tests...$(NC)"
	$(PYTHON) -m pytest tests/contract/ -v --tb=short

test-security: ## Run security tests
	@echo "$(GREEN)Running security tests...$(NC)"
	$(PYTHON) -m pytest tests/security/ -v --tb=short

test-e2e: ## Run end-to-end tests
	@echo "$(GREEN)Running end-to-end tests...$(NC)"
	$(PYTHON) -m pytest tests/end-to-end/ -v --tb=short

test-coverage: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=src --cov=hub_layer --cov=services --cov-report=html
	@echo "Coverage report available in htmlcov/"

lint: ## Run linting
	@echo "$(GREEN)Running linting...$(NC)"
	@$(PYTHON) -m flake8 src/ hub_layer/ services/ copilot_service/ --max-line-length=100 --extend-ignore=E203
	@echo "$(GREEN)Linting complete!$(NC)"

typecheck: ## Run type checking
	@echo "$(GREEN)Running type checking...$(NC)"
	@$(PYTHON) -m mypy src/ hub_layer/ services/ copilot_service/ --ignore-missing-imports
	@echo "$(GREEN)Type checking complete!$(NC)"

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	@$(PYTHON) -m black src/ hub_layer/ services/ copilot_service/
	@echo "$(GREEN)Code formatted!$(NC)"

# ============================================================================
# HEALTH AND STATUS
# ============================================================================

health: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(NC)"
	@echo ""
	@echo "PostgreSQL:"
	@$(DOCKER_COMPOSE) exec postgres pg_isready -U timescale -d wasteintel && echo "  $(GREEN)Healthy$(NC)" || echo "  $(RED)Unhealthy$(NC)"
	@echo ""
	@echo "Redis:"
	@$(DOCKER_COMPOSE) exec redis redis-cli ping && echo "  $(GREEN)Healthy$(NC)" || echo "  $(RED)Unhealthy$(NC)"
	@echo ""
	@echo "API:"
	@curl -s -o /dev/null -w "  %{http_code}" http://localhost:8001/health || echo "  $(RED)Unreachable$(NC)"
	@echo ""
	@echo "Copilot:"
	@curl -s -o /dev/null -w "  %{http_code}" http://localhost:8004/health || echo "  $(RED)Unreachable$(NC)"

status: ## Show status of all services
	@echo "$(GREEN)Service Status:$(NC)"
	$(DOCKER_COMPOSE) ps

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Clean build artifacts
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .cache 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-docker: ## Clean Docker artifacts
	@echo "$(GREEN)Cleaning Docker artifacts...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)Docker cleanup complete!$(NC)"

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	@mkdir -p docs/generated
	@echo "Documentation generated in docs/generated/"

# ============================================================================
# DEPLOYMENT
# ============================================================================

deploy: ## Deploy to production (placeholder - see infrastructure/ansible)
	@echo "$(YELLOW)Production deployment should be done via Ansible playbooks.$(NC)"
	@echo "See: infrastructure/ansible/"
	@echo "Run: make deploy-ansible"

deploy-ansible: ## Deploy using Ansible
	@echo "$(GREEN)Deploying with Ansible...$(NC)"
	@if [ -d "infrastructure/ansible" ]; then \
		cd infrastructure/ansible && \
		ansible-playbook -i inventory/production.ini playbooks/site.yml; \
	else \
		@echo "$(YELLOW)Ansible playbooks not found.$(NC)"; \
	fi

deploy-core: ## Deploy WIN Core profile
	@echo "$(GREEN)Deploying WIN Core profile...$(NC)"
	@if [ -d "infrastructure/ansible" ]; then \
		cd infrastructure/ansible && \
		ansible-playbook -i inventory/production.ini playbooks/deploy-core.yml; \
	else \
		@echo "$(YELLOW)Ansible playbooks not found.$(NC)"; \
	fi

deploy-intelligence: ## Deploy WIN Intelligence profile
	@echo "$(GREEN)Deploying WIN Intelligence profile...$(NC)"
	@if [ -d "infrastructure/ansible" ]; then \
		cd infrastructure/ansible && \
		ansible-playbook -i inventory/production.ini playbooks/deploy-intelligence.yml; \
	else \
		@echo "$(YELLOW)Ansible playbooks not found.$(NC)"; \
	fi

# ============================================================================
# BACKUP AND RESTORE
# ============================================================================

backup: db-backup ## Create database backup

backup-full: ## Create full system backup
	@echo "$(GREEN)Creating full system backup...$(NC)"
	@mkdir -p backups
	@echo "Backing up database..."
	$(MAKE) db-backup
	@echo "Backing up configuration..."
	@tar -czf backups/config_$$(date +%Y%m%d_%H%M%S).tar.gz \
		.env.example \
		docker-compose.yml \
		Dockerfile* \
		Makefile \
		pyproject.toml \
		requirements*.txt
	@echo "$(GREEN)Full backup created in backups/ directory!$(NC)"

restore: db-restore ## Restore database from backup

# ============================================================================
# UTILITY
# ============================================================================

shell: ## Open shell in API container
	@echo "$(GREEN)Opening shell in API container...$(NC)"
	$(DOCKER_COMPOSE) exec waste-intel-api sh

shell-copilot: ## Open shell in Copilot container
	@echo "$(GREEN)Opening shell in Copilot container...$(NC)"
	$(DOCKER_COMPOSE) exec copilot-service sh

shell-db: db-shell ## Open PostgreSQL shell

logs: docker-logs ## Show logs for all services

ps: docker-ps ## List running containers

# ============================================================================
# VERSION INFO
# ============================================================================

version: ## Show version information
	@echo "$(GREEN)Waste Intelligence Network OS - Version Information$(NC)"
	@echo ""
	@echo "Platform: WIN OS"
	@echo "Repository: EcoCode-Smart-City-Infrastructure/waste-intelligence-platform"
	@echo "Branch: $(shell git branch --show-current 2>/dev/null || echo 'unknown')"
	@echo "Commit: $(shell git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
	@echo "Date: $(shell git log -1 --format=%cd 2>/dev/null || date)"
	@echo ""
	@echo "Components:"
	@echo "  - PostgreSQL with PostGIS and TimescaleDB"
	@echo "  - Redis Cache"
	@echo "  - MQTT Broker (Mosquitto)"
	@echo "  - WIN API (FastAPI/Flask)"
	@echo "  - AI Copilot (FastAPI)"
	@echo "  - ML Services"
	@echo "  - Prometheus + Grafana"
