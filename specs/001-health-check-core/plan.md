# Implementation Plan: Cribl Health Check Core

**Branch**: `001-health-check-core` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-health-check-core/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a comprehensive health checking tool for Cribl Stream deployments that provides actionable insights across 15 objectives including health assessment, configuration validation, performance optimization, security auditing, and cost management. The tool operates exclusively via read-only API access, completes analysis in under 5 minutes using fewer than 100 API calls, and delivers prioritized recommendations with clear remediation steps and documentation links. The MVP focuses on P1 (Quick Health Assessment) delivering immediate value through overall health scoring and critical issue identification, with subsequent priorities adding configuration validation, optimization, security, cost management, fleet operations, and predictive analytics capabilities.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: httpx (async HTTP client), pydantic (data validation), typer (CLI framework), rich (terminal formatting)
**Storage**: Local JSON files for optional historical trending (stateless by default per Constitution Principle V)
**Testing**: pytest (unit/integration), pytest-asyncio (async tests), respx (HTTP mocking)
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)
**Project Type**: Single CLI application with API-first library architecture
**Performance Goals**: < 5 minutes analysis time, < 100 API calls per run, < 30 seconds report generation
**Constraints**: Read-only API access only, no agent installation, < 1% Cribl resource overhead, air-gapped deployment support
**Scale/Scope**: Support deployments with 100+ workers, analyze 15 objectives across 7 prioritized user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Read-Only by Default
- ✅ **PASS**: All API interactions are read-only GET requests
- ✅ **PASS**: No configuration modification capabilities in scope
- ✅ **PASS**: Audit trail via structured logging of all API calls
- ✅ **PASS**: Recommendations only, zero auto-remediation per requirements

### Principle II: Actionability First
- ✅ **PASS**: FR-086 mandates clear remediation steps for every finding
- ✅ **PASS**: FR-087 requires prioritization by impact and effort
- ✅ **PASS**: FR-088 mandates documentation links for all recommendations
- ✅ **PASS**: FR-089 requires before/after comparisons for optimizations

### Principle III: API-First Design
- ✅ **PASS**: Core library exposes all analysis functions
- ✅ **PASS**: CLI is thin wrapper calling library functions
- ✅ **PASS**: Future Web UI can consume same library (architecture supports)
- ✅ **PASS**: Designed for third-party integration via Python package

### Principle IV: Minimal Data Collection
- ✅ **PASS**: FR-076 enforces read-only access, no log content extraction
- ✅ **PASS**: FR-083 requires air-gapped deployment support
- ✅ **PASS**: Metrics-only collection per FR-003 (CPU, memory, disk stats)
- ✅ **PASS**: Configurable retention for optional historical data

### Principle V: Stateless Analysis
- ✅ **PASS**: Each analysis run is independent per FR design
- ✅ **PASS**: No database dependencies; optional local file storage only
- ✅ **PASS**: Historical data optional for trending (FR-004, FR-021)
- ✅ **PASS**: Reproducible results from same inputs per constitution

### Principle VI: Graceful Degradation
- ✅ **PASS**: FR-084 mandates graceful API error handling with partial reports
- ✅ **PASS**: FR error messages include remediation steps
- ✅ **PASS**: Partial report generation explicitly designed (SC-018)
- ✅ **PASS**: Incomplete sections marked per constitution requirement

### Principle VII: Performance Efficiency
- ✅ **PASS**: FR-078 enforces < 5 minute analysis (SC-005)
- ✅ **PASS**: FR-079 enforces < 100 API calls per run (SC-008)
- ✅ **PASS**: FR-080 implements rate limit handling with backoff
- ✅ **PASS**: Parallel API requests where possible to maximize throughput

### Principle VIII: Pluggable Architecture
- ✅ **PASS**: Module-based analyzer design for each objective
- ✅ **PASS**: Configuration-driven best practice rules (FR-018, FR-019)
- ✅ **PASS**: Extensible report formatters and output handlers
- ✅ **PASS**: Plugin system for custom analyzers (Phase 2+)

### Principle IX: Test-Driven Development
- ✅ **PASS**: TDD workflow mandatory per constitution
- ✅ **PASS**: 80%+ code coverage target enforced
- ✅ **PASS**: Integration tests for ALL Cribl API interactions per constitution
- ✅ **PASS**: Validation against known-good deployments per constitution

### Principle X: Security by Design
- ✅ **PASS**: Secure credential management with encrypted storage
- ✅ **PASS**: API token authentication support (FR-081)
- ✅ **PASS**: No sensitive data in logs/reports per constitution
- ✅ **PASS**: Dependency vulnerability scanning in CI/CD

### Principle XI: Version Compatibility
- ✅ **PASS**: Support Cribl Stream N through N-2 per FR
- ✅ **PASS**: Version detection and adaptive feature set per FR
- ✅ **PASS**: Compatibility matrix in documentation
- ✅ **PASS**: Graceful handling of deprecated endpoints (FR-080)

### Principle XII: Transparent Methodology
- ✅ **PASS**: FR-001 requires documented health score calculation
- ✅ **PASS**: Issue findings include confidence levels (FR-090)
- ✅ **PASS**: Open-source codebase enables validation
- ✅ **PASS**: Documentation explains all scoring and recommendations

**Constitution Compliance**: ✅ ALL PRINCIPLES PASS - No violations, proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-health-check-core/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-spec.yaml    # OpenAPI 3.1 specification for library API
│   └── cribl-api.yaml   # Cribl Stream API subset used by tool
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── cribl_hc/
│   ├── __init__.py
│   ├── cli/                    # CLI interface (thin wrapper)
│   │   ├── __init__.py
│   │   ├── main.py            # Typer CLI application
│   │   ├── commands/          # Command implementations
│   │   └── output.py          # Rich formatting for terminal output
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── api_client.py      # Cribl API client with rate limiting
│   │   ├── analyzer.py        # Main analysis orchestrator
│   │   ├── health_scorer.py   # Health score calculation engine
│   │   └── report_generator.py # Report generation
│   ├── analyzers/              # Pluggable analyzer modules (15 objectives)
│   │   ├── __init__.py
│   │   ├── base.py            # Base analyzer interface
│   │   ├── health.py          # Objective 1: Health Assessment
│   │   ├── sizing.py          # Objective 2: Sizing & Scaling
│   │   ├── config_audit.py    # Objective 3: Configuration Auditing
│   │   ├── best_practices.py  # Objective 4: Best Practices
│   │   ├── storage.py         # Objective 5: Storage Optimization
│   │   ├── performance.py     # Objective 6: Performance Optimization
│   │   ├── security.py        # Objective 7: Security & Compliance
│   │   ├── disaster_recovery.py # Objective 8: DR & Reliability
│   │   ├── cost.py            # Objective 9: License & Cost Management
│   │   ├── data_quality.py    # Objective 10: Data Quality & Routing
│   │   ├── change_impact.py   # Objective 11: Change Impact Analysis
│   │   ├── benchmarking.py    # Objective 12: Comparative Benchmarking
│   │   ├── documentation.py   # Objective 13: Documentation & Knowledge Transfer
│   │   ├── predictive.py      # Objective 14: Predictive Analytics
│   │   └── fleet.py           # Objective 15: Fleet Management
│   ├── models/                 # Pydantic data models
│   │   ├── __init__.py
│   │   ├── deployment.py      # Deployment entity
│   │   ├── health.py          # HealthScore entity
│   │   ├── finding.py         # Issue/Finding entity
│   │   ├── worker.py          # WorkerNode entity
│   │   ├── config.py          # ConfigurationElement entity
│   │   ├── recommendation.py  # Recommendation entity
│   │   ├── analysis.py        # AnalysisRun entity
│   │   ├── trend.py           # HistoricalTrend entity
│   │   └── rule.py            # BestPracticeRule entity
│   ├── storage/                # Optional historical data storage
│   │   ├── __init__.py
│   │   ├── base.py            # Storage interface
│   │   └── json_store.py      # JSON file-based storage
│   ├── rules/                  # Best practice rules (configuration-driven)
│   │   ├── __init__.py
│   │   ├── loader.py          # Rule loading and validation
│   │   └── cribl_rules.yaml   # Cribl best practices rules
│   ├── utils/                  # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py          # Structured logging with audit trail
│   │   ├── rate_limiter.py    # API rate limiting with backoff
│   │   ├── crypto.py          # Credential encryption
│   │   └── version.py         # Cribl version detection and compatibility
│   └── config.py              # Configuration management

tests/
├── unit/                       # Unit tests (isolated, mocked dependencies)
│   ├── __init__.py
│   ├── test_analyzers/
│   ├── test_models/
│   ├── test_core/
│   └── test_utils/
├── integration/                # Integration tests (real API interactions - mocked)
│   ├── __init__.py
│   ├── test_api_client.py
│   ├── test_end_to_end.py
│   └── fixtures/              # Mock Cribl API responses
├── contract/                   # Contract tests (API schema validation)
│   ├── __init__.py
│   └── test_cribl_api.py
└── conftest.py                 # Pytest configuration and shared fixtures
```

**Structure Decision**: Single project structure selected. This is a CLI tool with library-first architecture where the CLI is a thin wrapper around the core library (`src/cribl_hc/`). The modular analyzer design enables independent development and testing of each objective. Tests are organized by type (unit, integration, contract) per constitution Principle IX (Test-Driven Development).

## Complexity Tracking

> **No constitution violations - this section intentionally left empty**

The design adheres to all 12 constitution principles without requiring complexity justification. The architecture is straightforward: a CLI tool that wraps a Python library, using pluggable analyzers for each objective, with read-only API access and optional stateless operation.

## Phase 0: Research & Technology Decisions

**Status**: Completed during plan creation

### Decision 1: Programming Language

**Decision**: Python 3.11+

**Rationale**:
- Excellent HTTP/API client libraries (httpx with async support)
- Rich CLI tooling ecosystem (typer, rich for beautiful terminal output)
- Strong data validation with Pydantic (matches our entity modeling needs)
- Cribl administrators commonly use Python for automation
- Cross-platform support (Linux, macOS, Windows)
- Easy distribution via PyPI and standalone executables (PyInstaller)

**Alternatives Considered**:
- **Go**: Better performance, single binary distribution. Rejected because Python's ecosystem better matches Cribl admin workflows and faster development for complex data analysis
- **TypeScript/Node.js**: Good async support. Rejected due to weaker data validation libraries and less common in Cribl admin tooling
- **Rust**: Best performance and safety. Rejected due to longer development time and steeper learning curve for contributors

### Decision 2: HTTP Client

**Decision**: httpx (async HTTP client)

**Rationale**:
- Native async/await support for parallel API calls (critical for < 100 call budget)
- Built-in connection pooling and keepalive (reduces overhead)
- Clean API compatible with requests library (familiar to Python developers)
- Excellent error handling and retry mechanisms
- HTTP/2 support for multiplexing (future optimization)

**Alternatives Considered**:
- **requests**: Synchronous only, would require threading for parallelism. Rejected for performance
- **aiohttp**: More complex API, less familiar. Rejected for developer ergonomics

### Decision 3: CLI Framework

**Decision**: typer + rich

**Rationale**:
- typer provides modern CLI with automatic help generation and type hints
- rich enables beautiful terminal output (tables, progress bars, syntax highlighting)
- Both are well-maintained with strong community support
- Aligns with Actionability First principle (clear, visual output)

**Alternatives Considered**:
- **click**: Popular but older, less type-safe. Rejected for modern Python experience
- **argparse**: Standard library but verbose. Rejected for developer productivity

### Decision 4: Data Validation

**Decision**: pydantic

**Rationale**:
- Strong type validation matches our entity-heavy design
- Automatic JSON serialization/deserialization
- Clear error messages for validation failures (Graceful Degradation principle)
- Wide adoption in Python API projects

**Alternatives Considered**:
- **marshmallow**: More flexible but more verbose. Rejected for simplicity
- **dataclasses + manual validation**: Less boilerplate but weaker validation. Rejected for safety

### Decision 5: Testing Framework

**Decision**: pytest + pytest-asyncio + respx (HTTP mocking)

**Rationale**:
- pytest is Python standard for testing with excellent fixture support
- pytest-asyncio handles async test cases
- respx mocks HTTP requests for integration tests
- Supports 80%+ coverage reporting (TDD principle)
- Easy contract testing with schema validation

**Alternatives Considered**:
- **unittest**: Standard library but more verbose. Rejected for productivity
- **responses** (HTTP mocking): Less async support. Rejected for respx

### Decision 6: Storage

**Decision**: Optional local JSON files (stateless by default)

**Rationale**:
- Stateless Analysis principle (V) - no mandatory persistence
- JSON files simple and human-readable for optional historical tracking
- No database dependencies simplifies deployment
- Supports air-gapped environments (Minimal Data Collection principle IV)

**Alternatives Considered**:
- **SQLite**: More structure but adds persistence complexity. Rejected for stateless principle
- **PostgreSQL/MySQL**: Over-engineered for optional trending. Rejected for simplicity

### Decision 7: Credential Management

**Decision**: cryptography library (Fernet symmetric encryption)

**Rationale**:
- Strong encryption for API tokens (Security by Design principle X)
- Simple key derivation from master password
- Standard Python cryptography library (well-audited)
- Supports encrypted credential files for secure storage

**Alternatives Considered**:
- **keyring**: OS-specific keychains. Rejected for cross-platform consistency and air-gapped support
- **plaintext config**: Violates Security principle. Rejected

### Decision 8: Rate Limiting

**Decision**: Custom rate limiter with exponential backoff

**Rationale**:
- Cribl API rate limits vary by deployment type
- Exponential backoff prevents thundering herd
- Aligns with Performance Efficiency principle (VII)
- Simple implementation with asyncio primitives

**Alternatives Considered**:
- **pyrate-limiter**: Feature-rich but heavy. Rejected for simplicity
- **aiolimiter**: Good but less flexible for varying limits. Rejected

### Decision 9: Report Generation

**Decision**: Multiple formatters (JSON, YAML, Markdown, HTML) with pluggable architecture

**Rationale**:
- JSON for programmatic consumption (API-First principle III)
- Markdown for human-readable reports
- HTML for browser viewing with styling
- YAML for config-style output
- Pluggable design supports future formats (CSV, PDF)

**Alternatives Considered**:
- **JSON only**: Too technical for Actionability. Rejected
- **PDF generation**: Complex dependencies (WeasyPrint, ReportLab). Deferred to Phase 2

### Decision 10: Logging & Audit Trail

**Decision**: structlog with JSON output

**Rationale**:
- Structured logging for audit trail (Read-Only principle I)
- JSON output for log aggregation tools
- Performance-efficient with lazy formatting
- Clear context for troubleshooting

**Alternatives Considered**:
- **standard logging**: Unstructured, hard to parse. Rejected
- **loguru**: Nice API but less structured. Rejected

## Phase 1: Design Artifacts

**Status**: Artifacts generated below

### Data Model Summary

See [data-model.md](./data-model.md) for complete entity definitions with fields, relationships, and validation rules.

**Key Entities**:
- **Deployment**: Cribl Stream environment with API credentials and metadata
- **HealthScore**: Calculated health metrics (0-100) with component breakdowns
- **Finding**: Identified issues or improvements with severity, remediation, and documentation links
- **WorkerNode**: Individual worker with resource utilization and health status
- **ConfigurationElement**: Pipelines, routes, functions, destinations with validation status
- **Recommendation**: Actionable suggestions with impact estimates and priorities
- **AnalysisRun**: Single analysis execution with metadata and results
- **HistoricalTrend**: Time-series data for metrics tracking
- **BestPracticeRule**: Validation rules from Cribl documentation

### API Contract Summary

See [contracts/api-spec.yaml](./contracts/api-spec.yaml) for complete OpenAPI 3.1 specification.

**Core Library Endpoints** (Python API, not HTTP REST):
- `analyze_deployment(credentials, objectives) -> AnalysisRun`
- `calculate_health_score(deployment_data) -> HealthScore`
- `generate_report(analysis_run, format) -> str`
- `load_historical_trends(deployment_id) -> List[HistoricalTrend]`
- `validate_credentials(credentials) -> bool`

**Cribl API Endpoints Used** (read-only GET only):
- GET `/api/v1/system/status` - System health and version
- GET `/api/v1/master/workers` - Worker list and status
- GET `/api/v1/master/groups` - Worker groups
- GET `/api/v1/m/{group}/pipelines` - Pipeline configurations
- GET `/api/v1/m/{group}/routes` - Route configurations
- GET `/api/v1/m/{group}/outputs` - Destination configurations
- GET `/api/v1/metrics` - System metrics (CPU, memory, throughput)
- GET `/api/v1/license` - License consumption data

### Quickstart Guide Summary

See [quickstart.md](./quickstart.md) for complete setup and usage instructions.

**Installation**:
```bash
pip install cribl-health-check
cribl-hc --version
```

**First Run**:
```bash
# Configure credentials
cribl-hc config set-credentials --url https://cribl.example.com --token YOUR_API_TOKEN

# Run health check (MVP - Objective 1)
cribl-hc analyze --deployment prod

# View results
cribl-hc report --format markdown --output health-report.md
```

**Key Commands**:
- `cribl-hc analyze` - Run analysis (with objective selection)
- `cribl-hc report` - Generate reports in various formats
- `cribl-hc config` - Manage credentials and settings
- `cribl-hc history` - View historical trends

## Next Steps

1. **Phase 0 Complete**: All technology decisions documented in research.md
2. **Phase 1 Complete**: Data models, contracts, and quickstart guide created
3. **Ready for `/speckit.tasks`**: Generate actionable task breakdown organized by user story priority
4. **Implementation Order**: P1 (Health Assessment MVP) → P2 (Configuration Validation) → P3 (Optimization) → P4-P7

**Artifacts Created**:
- ✅ plan.md (this file)
- ✅ research.md (technology decisions)
- ✅ data-model.md (entity definitions)
- ✅ contracts/ (API specifications)
- ✅ quickstart.md (setup and usage guide)

**Branch**: `001-health-check-core`
**Status**: Planning complete, ready for task generation
