# Architecture Decisions - WIN OS

## Decision Log

### 1. Modular Monolith vs Microservices

**Decision**: Start with a modular monolith, extract services only when justified

**Rationale**:
- Reduced complexity for initial development
- Easier debugging and testing
- Lower operational overhead
- Can extract services later when scaling needs justify it

**Consequences**:
- Single deployment unit initially
- Shared database connection pool
- Simpler inter-service communication (function calls)
- Future service extraction requires careful planning

### 2. PostgreSQL with PostGIS as Primary Database

**Decision**: Use PostgreSQL with PostGIS extension as the authoritative operational database

**Rationale**:
- Single source of truth for all operational data
- PostGIS provides excellent geospatial support
- TimescaleDB extension for time-series data
- Strong consistency guarantees
- Mature, production-ready technology

**Consequences**:
- No separate graph database (use PostgreSQL for KG storage)
- Knowledge Graph stored as nodes and edges in relational tables
- Complex queries may require optimization
- Need to implement graph traversal in application code or use recursive CTEs

### 3. FastAPI as Primary Backend Framework

**Decision**: Use FastAPI for new backend services, maintain Flask for existing routes

**Rationale**:
- FastAPI provides async support, automatic OpenAPI documentation
- Type hints and Pydantic validation improve code quality
- High performance comparable to Node.js/Go
- Easy integration with existing Flask code

**Consequences**:
- Two frameworks to maintain (temporarily)
- Migration path for existing Flask routes to FastAPI
- Consistent API style across services

### 4. Docker Compose for Initial Orchestration

**Decision**: Use Docker Compose for container orchestration, not Kubernetes initially

**Rationale**:
- Simpler setup and management
- Sufficient for single-server deployment
- Lower learning curve
- Can migrate to Kubernetes later when scale justifies it

**Consequences**:
- No automatic scaling
- Manual service discovery
- Single-host deployment
- Future migration to Kubernetes requires container adjustments

### 5. Ubuntu Server 22.04 LTS as Primary OS

**Decision**: Target Ubuntu Server 22.04 LTS (Jammy Jellyfish)

**Rationale**:
- Long-term support (April 2022 - April 2032)
- Wide compatibility with software packages
- Enterprise adoption and documentation
- Good balance of features and stability

**Consequences**:
- Must validate all dependencies work on 22.04
- Security updates managed via apt
- Package versions pinned to 22.04 repositories

### 6. Row-Level Security for Multi-Tenancy

**Decision**: Implement multi-tenancy using PostgreSQL Row-Level Security (RLS)

**Rationale**:
- Built-in PostgreSQL feature
- Automatic tenant isolation at database level
- No application code changes for tenant filtering
- Fine-grained control over access policies

**Consequences**:
- Requires PostgreSQL 9.5+
- Policy definitions must be maintained
- Query performance may be impacted
- Tenant context must be set for each connection

### 7. JWT with OAuth2 for Authentication

**Decision**: Use JWT tokens with OAuth2 flow for authentication

**Rationale**:
- Industry standard approach
- Stateless authentication
- Scalable across services
- Good library support (FastAPI, Flask)

**Consequences**:
- Token management complexity
- Need for refresh token rotation
- Token revocation requires additional infrastructure
- Must handle token expiration gracefully

### 8. In-Memory Knowledge Graph with PostgreSQL Backing

**Decision**: Load W2RKG into memory for query performance, persist to PostgreSQL

**Rationale**:
- Fast query performance for graph operations
- Existing W2RKG implementation already in-memory
- Can reload from PostgreSQL on startup
- Changes persisted to database

**Consequences**:
- Memory usage scales with graph size
- Need to handle graph reloads
- Cache invalidation complexity
- Graph too large for memory may require alternative approach

### 9. MQTT for Device Telemetry

**Decision**: Use MQTT protocol for IoT device telemetry

**Rationale**:
- Lightweight protocol suitable for constrained devices
- Built-in QoS levels for message delivery
- Pub/Sub model fits telemetry data well
- Good support in ESP32 firmware

**Consequences**:
- Need MQTT broker (Mosquitto)
- Message ordering not guaranteed
- Need to handle connection drops and reconnects
- Security configuration (TLS, authentication)

### 10. Ansible for Infrastructure Automation

**Decision**: Use Ansible for server provisioning and configuration management

**Rationale**:
- Agentless architecture
- Idempotent operations
- YAML-based configuration (easy to read and maintain)
- Good Ubuntu support
- Can be run from development machine

**Consequences**:
- Requires Python on target hosts
- SSH access required
- Playbook development and testing needed
- Inventory management complexity

### 11. Prometheus + Grafana for Monitoring

**Decision**: Use Prometheus for metrics collection and Grafana for visualization

**Rationale**:
- Industry standard for cloud-native monitoring
- Rich ecosystem of exporters
- Flexible querying language (PromQL)
- Good dashboarding capabilities

**Consequences**:
- Additional services to maintain
- Metrics collection overhead
- Storage requirements for metrics data
- Alerting configuration needed

### 12. Data Status Classification System

**Decision**: Implement explicit data classification (observed, reported, derived, forecast, simulated, unavailable)

**Rationale**:
- Clear distinction between data types
- Prevents confusion between actual and predicted data
- Enables appropriate UI presentation
- Supports data quality assessment

**Consequences**:
- Additional field on all data records
- Application logic must respect classifications
- UI must handle different classifications appropriately
- Query complexity increased

### 13. OpenRouter + Groq for LLM Access

**Decision**: Support multiple LLM providers with OpenRouter as primary and Groq as fallback

**Rationale**:
- Avoid vendor lock-in
- Groq provides fast inference for certain models
- OpenRouter provides access to multiple model providers
- Can switch providers based on cost/performance

**Consequences**:
- Multiple API integrations to maintain
- Different pricing models
- Need for provider abstraction layer
- Fallback logic complexity

### 14. Google OR-Tools for Route Optimization

**Decision**: Use Google OR-Tools for vehicle routing and optimization

**Rationale**:
- Industry-standard optimization library
- Supports complex constraints (capacity, time windows, etc.)
- Good Python support
- Open source and free to use

**Consequences**:
- Complex API to learn and use
- May require custom integration for specific constraints
- Performance characteristics vary by problem size
- Need to handle edge cases gracefully

### 15. Structured Logging with JSON Format

**Decision**: Use structured JSON logging throughout the application

**Rationale**:
- Easier parsing and analysis
- Better integration with log management tools
- Consistent format across services
- Supports correlation IDs for tracing

**Consequences**:
- Slightly more verbose than plain text logs
- Need for JSON parsing in log viewers
- Log rotation and management needed

## Decision Summary

| Decision | Choice | Rationale | Reversible |
|----------|--------|-----------|------------|
| Architecture | Modular Monolith | Reduced complexity | Yes |
| Database | PostgreSQL + PostGIS | Single source of truth | Medium |
| Backend | FastAPI | Async, OpenAPI, validation | Yes |
| Orchestration | Docker Compose | Simplicity | Yes |
| OS | Ubuntu 22.04 LTS | Support and stability | Medium |
| Multi-Tenancy | RLS | Built-in, automatic | Medium |
| Authentication | JWT + OAuth2 | Industry standard | Yes |
| KG Storage | In-memory + PostgreSQL | Performance | Yes |
| Telemetry | MQTT | Lightweight, suitable | Medium |
| Provisioning | Ansible | Agentless, idempotent | Yes |
| Monitoring | Prometheus + Grafana | Industry standard | Yes |
| Data Classification | Explicit status | Clarity, quality | Yes |
| LLM Access | OpenRouter + Groq | Avoid lock-in | Yes |
| Optimization | OR-Tools | Industry standard | Yes |
| Logging | JSON structured | Analysis, integration | Yes |

## Future Decisions to Make

1. **Kubernetes Adoption**: When to migrate from Docker Compose to Kubernetes
2. **Graph Database**: Whether to add dedicated graph database (Neo4j) for very large KG
3. **Message Queue**: When to add Kafka/Redpanda for high-throughput event streaming
4. **Frontend Framework**: Whether to add React/Vue alongside Streamlit
5. **Edge Deployment**: Specific requirements for edge device deployment
6. **Data Lake**: Whether to add data lake for analytical workloads
7. **Real-time Analytics**: Streaming analytics requirements and technology choices

## Decision-Making Process

1. **Identify the decision**: Clearly state what needs to be decided
2. **Gather information**: Research options, constraints, and requirements
3. **Identify alternatives**: List all viable options
4. **Evaluate alternatives**: Assess pros, cons, and trade-offs
5. **Make decision**: Choose the best option based on current needs
6. **Document decision**: Record the decision and rationale (this document)
7. **Review periodically**: Re-evaluate decisions as requirements change

## Change Log

| Date | Decision | Changed From | Changed To | Reason |
|------|----------|--------------|-----------|--------|
| Initial | All | N/A | Current | Initial documentation |
