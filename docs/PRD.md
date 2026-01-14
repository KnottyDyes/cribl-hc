# Product Requirements Document: Cribl Health Check (cribl-hc)

**Version**: 1.0.0
**Last Updated**: 2026-01-13
**Status**: Active / In Development

## 1. Product Overview
**Cribl Health Check** is a comprehensive, read-only analysis tool designed to assess the health, configuration, security, and performance of Cribl deployments (Stream, Edge, Lake, Search). It provides actionable insights and remediation steps to ensuring operational excellence without risking production stability.

### 1.1 Value Proposition
- **Safety**: 100% read-only operations; never modifies state.
- **Speed**: Complete analysis in <5 minutes with <100 API calls.
- **Actionability**: Every finding comes with specific remediation steps.
- **Flexibility**: Works across Self-Hosted and Cloud, supports air-gapped environments.

---

## 2. Constitution & Core Principles
All development **MUST** adhere to the **13 Constitution Principles** (Source: `.specify/memory/constitution.md`):

1.  **Read-Only by Default**: GET requests only. Zero state modification.
2.  **Actionability First**: Findings must have clear remediation.
3.  **API-First Design**: CLI/GUI are thin wrappers around the Core API.
4.  **Minimal Data Collection**: Metrics only, no log content/PII.
5.  **Stateless Analysis**: Independent, reproducible runs.
6.  **Graceful Degradation**: Partial success > complete failure.
7.  **Performance Efficiency**: <5 min runtime, <100 API calls.
8.  **Pluggable Architecture**: Modular analyzer design.
9.  **Test-Driven Development**: 80%+ coverage, tests before code.
10. **Security by Design**: Encrypted credentials, no sensitive logs.
11. **Version Compatibility**: Support N through N-2 versions.
12. **Transparent Methodology**: Documented scoring logic.
13. **Safe Branch Management**: No blind deletions.

---

## 3. Functional Requirements

### 3.1 Interfaces
- **CLI**: Standard entry point for automation and quick checks (`cribl-hc analyze`).
- **TUI**: Interactive terminal UI for credential management and easy execution (`cribl-hc tui`).
- **Web GUI**: React-based dashboard for visual analysis, real-time progress, and reporting (Docker-based).

### 3.2 Core Capabilities (Analyzers)
The system is built on a modular "Analyzer" pattern.
**Implemented Analyzers (Phase 1-11 Completed):**
- **Health**: `HealthAnalyzer` (Status, Version)
- **Config**: `ConfigAnalyzer` (Syntax, Best Practices)
- **Resources**: `ResourceAnalyzer` (CPU/Mem/Disk), `StorageAnalyzer`
- **Security**: `SecurityAnalyzer` (TLS, RBAC, Secrets, Certificates)
- **Cost**: `CostAnalyzer` (License usage)
- **Fleet**: `FleetAnalyzer` (Drift detection)
- **Data Quality**: `LookupHealthAnalyzer`, `SchemaQualityAnalyzer`, `DataFlowTopologyAnalyzer`
- **Product-Specific**: `LakeHealthAnalyzer`, `SearchHealthAnalyzer`, `SearchPerformanceAnalyzer`
- **Runtime**: `BackpressureAnalyzer`, `PipelinePerformanceAnalyzer`

### 3.3 Reporting
- **Formats**: JSON (machine-readable), Markdown (human-readable), Interactive HTML (Web GUI).
- **Content**: Executive summary, scored findings (Critical/High/Med/Low), specific remediation steps.

---

## 4. Technical Architecture

### 4.1 Tech Stack
- **Backend/CLI**: Python 3.11+
  - **Frameworks**: `typer` (CLI), `FastAPI` (Web API)
  - **Networking**: `httpx` (Async HTTP)
  - **Data Models**: `pydantic`
  - **Formatting**: `rich`
- **Frontend**: React 19.2, TypeScript 5.7, TailwindCSS (Vite build)
- **Deployment**: Docker Compose

### 4.2 Data Flow
1.  **Input**: Credentials/Context -> **Orchestrator**
2.  **Process**: Orchestrator spawns parallel **Analyzers**
3.  **Fetch**: **CriblAPIClient** (Async, Rate-Limited) fetches data from Stream/Edge/Lake
4.  **Analyze**: Analyzers apply logic/rules to data -> **Findings**
5.  **Output**: **ReportGenerator** Formats findings -> JSON/MD/UI

### 4.3 Security
- Credentials stored encrypted via `fernet` (AES-128-CBC).
- Local key derivation (machine-specific).
- No sensitive data logging (filtered by `structlog`).

---

## 5. Roadmap & Priorities

### 5.1 Immediate Focus (P1 - "Quick Wins")
*Source: `docs/FUTURE_FEATURES.md`*
1.  **System Messages Surfacing**: Integrate `/system/messages` API to show internal Cribl warnings.
2.  **Worker Group Imbalance**: Detect traffic hotspots/idle nodes within groups.
3.  **API Key Usage Audit**: Identify stale/unused keys beyond just expiration.

### 5.2 Active Development: CriblVision Pack Replication
*Source: `IMPLEMENTATION_READY.md` & `docs/ANALYZER_GAPS_ROADMAP.md`*
Replicate functionality from the CriblVision pack into standalone analyzers.
- **Phase 1**: Pipeline Bottleneck Detection (`MetricsCollector`, `PipelineBottleneckAnalyzer`).
- **Phase 2**: Worker & Endpoint Health (`WorkerGroupBalanceAnalyzer`, `EndpointHealthAnalyzer`).
- **Phase 3**: Correlation & Polish (`MetricsCorrelationAnalyzer`).

### 5.3 Medium Term (P2)
1.  **Multi-Deployment Comparison**: Diff two environments (e.g., Prod vs. Dev).
2.  **Historical Persistence**: SQLite/JSON storage for trend analysis.
3.  **Scheduled Health Checks**: Cron/Daemon mode.

---

## 6. Developer Guidelines
- **Location**: `/Projects/cribl-hc`
- **Testing**: `pytest` required. Run `pytest` before commits. 80% coverage min.
- **Linting**: `ruff check .` and `black .`
- **New Analyzer Workflow**:
    1.  Create class in `src/cribl_hc/analyzers/` inheriting `BaseAnalyzer`.
    2.  Register in `src/cribl_hc/analyzers/__init__.py`.
    3.  Implement `analyze()` with `CriblAPIClient`.
    4.  Add unit/integration tests.
