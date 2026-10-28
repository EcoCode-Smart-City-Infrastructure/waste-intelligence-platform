# Target Architecture - WIN OS

## Overview
WIN OS is a modular, production-oriented software platform for smart-city waste intelligence.

## Deployment Profiles

### Profile A: WIN Core (Production Baseline)
- PostgreSQL with PostGIS
- WIN API (FastAPI)
- Web Application
- Authentication Service
- Data Ingestion Services
- Monitoring (Prometheus + Grafana)
- Backup & Restore

### Profile B: WIN Intelligence (Analytics Layer)
- All WIN Core components
- Forecasting Service
- Anomaly Detection Service
- Routing Optimization Service
- AI Copilot Service
- Model Versioning
- Data Quality Assessment
- Scenario Analysis

### Profile C: WIN Edge (Local Deployment)
- MQTT Broker
- Telemetry Buffering
- Local Data Storage (SQLite)
- Store-and-Forward Sync
- Offline Operation Support
- Secure Remote Updates
- Local Health Monitoring

### Profile D: WIN Simulation (Digital Twin)
- Digital Twin Engine
- Collection Route Scenarios
- Facility Capacity Scenarios
- Waste Flow Modeling
- Resource Allocation Simulations
- Environmental Impact Scenarios

## Target Repository Structure

```
win-os/
├── README.md
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
├── compose.yaml
│
├── apps/
│   ├── web/
│   ├── api/
│   └── control-center/
│
├── services/
│   ├── identity/
│   ├── data-ingestion/
│   ├── asset-management/
│   ├── collection/
│   ├── fleet/
│   ├── routing/
│   ├── facilities/
│   ├── waste-streams/
│   ├── recovery/
│   ├── environmental-accounting/
│   ├── data-quality/
│   ├── forecasting/
│   ├── anomaly-detection/
│   ├── optimization/
│   ├── ai-copilot/
│   └── digital-twin/
│
├── data-platform/
│   ├── schemas/
│   ├── migrations/
│   ├── event-contracts/
│   ├── source-registry/
│   ├── provenance/
│   └── retention-policies/
│
├── infrastructure/
│   ├── docker/
│   ├── compose/
│   ├── ansible/
│   ├── cloud-init/
│   ├── networking/
│   ├── security/
│   ├── secrets/
│   ├── monitoring/
│   ├── backup-recovery/
│   └── deployment/
│
├── os-image/
│   ├── build/
│   ├── profiles/
│   │   ├── core/
│   │   ├── intelligence/
│   │   ├── edge/
│   │   └── simulation/
│   └── provisioning/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── security/
│   ├── end-to-end/
│   └── performance/
│
└── docs/
    ├── architecture/
    ├── deployment/
    ├── security/
    ├── operations/
    ├── api/
    └── development/
```

## Technology Stack

- **OS**: Ubuntu Server 22.04 LTS
- **Containerization**: Docker + Docker Compose
- **Database**: PostgreSQL 15 + PostGIS 3 + TimescaleDB
- **Backend**: FastAPI (primary) + Flask (legacy)
- **Frontend**: React 18 + TypeScript + MapLibre GL JS
- **AI/ML**: OpenRouter, Groq, scikit-learn, XGBoost, OR-Tools
- **Monitoring**: Prometheus + Grafana
- **Infrastructure**: Ansible + cloud-init
- **Message Queue**: MQTT (Mosquitto)

## API Structure

```
/api/v1/
├── auth/
├── organizations/
├── users/
├── assets/
├── bins/
├── facilities/
├── routes/
├── collections/
├── waste-streams/
├── recovery/
├── environmental/
├── analytics/
├── kg/
├── copilot/
└── system/
```

## Security Architecture

- **Authentication**: JWT with OAuth2
- **Authorization**: RBAC with tenant isolation
- **Multi-Tenancy**: Row-Level Security (RLS)
- **Network**: Firewall, TLS 1.3, rate limiting
- **Data**: Encryption at rest and in transit
- **Container**: Non-root, read-only filesystems, capability restrictions

## Data Model Highlights

- Full domain model with provenance tracking
- Data status classification (observed, reported, derived, forecast, simulated, unavailable)
- PostGIS for geospatial queries
- TimescaleDB for time-series data

## Next Steps
1. Complete Phase 1 assessment
2. Begin Phase 2 - Enhance database schema
3. Implement authentication and authorization
4. Create Ansible playbooks
