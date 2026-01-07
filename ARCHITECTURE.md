# Cribl Health Check - Architecture Documentation

## Overview

Cribl Health Check is a comprehensive analysis tool for Cribl deployments (Stream, Edge, Lake, Search). It follows an API-first, modular architecture designed for extensibility and maintainability.

## Core Principles

The architecture adheres to the project's 12 Constitution Principles:

1. **Read-Only by Default** - All API operations are GET requests only
2. **Actionability First** - Every finding includes remediation steps
3. **API-First Design** - Core library with thin CLI wrapper
4. **Minimal Data Collection** - Metrics only, no log content extraction
5. **Stateless Analysis** - Independent runs, reproducible results
6. **Graceful Degradation** - Partial reports better than failures
7. **Performance Efficiency** - <5 min analysis, <100 API calls
8. **Pluggable Architecture** - Module-based extensible design
9. **Test-Driven Development** - 80%+ code coverage target
10. **Security by Design** - Encrypted credentials, no sensitive data in logs
11. **Version Compatibility** - Support Cribl Stream N through N-2
12. **Transparent Methodology** - Documented scoring and recommendations

## Directory Structure

```
src/cribl_hc/
├── __init__.py              # Package initialization
├── analyzers/               # Analysis modules (17 analyzers)
│   ├── __init__.py          # Analyzer registry
│   ├── base.py              # BaseAnalyzer abstract class
│   ├── health.py            # HealthAnalyzer
│   ├── config.py            # ConfigAnalyzer
│   ├── resource.py          # ResourceAnalyzer
│   ├── storage.py           # StorageAnalyzer
│   ├── security.py          # SecurityAnalyzer
│   ├── cost.py              # CostAnalyzer
│   ├── fleet.py             # FleetAnalyzer
│   ├── predictive.py        # PredictiveAnalyzer
│   ├── backpressure.py      # BackpressureAnalyzer
│   ├── pipeline_performance.py  # PipelinePerformanceAnalyzer
│   ├── lookup_health.py     # LookupHealthAnalyzer
│   ├── schema_quality.py    # SchemaQualityAnalyzer
│   ├── dataflow_topology.py # DataFlowTopologyAnalyzer
│   ├── lake_health.py       # LakeHealthAnalyzer
│   ├── lake_storage.py      # LakeStorageAnalyzer
│   ├── search_health.py     # SearchHealthAnalyzer
│   └── search_performance.py # SearchPerformanceAnalyzer
├── api/                     # Web API (FastAPI)
│   ├── __init__.py
│   ├── app.py               # FastAPI application
│   └── routers/             # API route handlers
│       ├── analysis.py      # Analysis endpoints
│       ├── analyzers.py     # Analyzer metadata endpoints
│       ├── credentials.py   # Credential management
│       └── system.py        # System info endpoints
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── main.py              # CLI entry point (typer)
│   ├── commands/            # CLI commands
│   │   ├── analyze.py       # analyze command
│   │   └── config.py        # config command
│   ├── output.py            # Rich terminal output
│   ├── tui.py               # Terminal UI
│   ├── unified_tui.py       # Unified TUI experience
│   └── modern_tui.py        # Modern TUI implementation
├── core/                    # Core functionality
│   ├── __init__.py
│   ├── api_client.py        # Cribl API client (httpx)
│   ├── health_scorer.py     # Health score calculation
│   ├── orchestrator.py      # Analysis orchestration
│   └── report_generator.py  # Report generation (JSON, Markdown)
├── models/                  # Pydantic data models
│   ├── __init__.py
│   ├── analysis.py          # AnalysisRun, AnalysisResult
│   ├── config.py            # Configuration models
│   ├── deployment.py        # Deployment model
│   ├── finding.py           # Finding model
│   ├── health.py            # HealthScore model
│   ├── lake.py              # Lake-specific models
│   ├── recommendation.py    # Recommendation model
│   ├── rule.py              # Rule model
│   ├── search.py            # Search-specific models
│   ├── trend.py             # HistoricalTrend model
│   └── worker.py            # Worker model
├── rules/                   # Best practice rules
│   ├── __init__.py
│   ├── loader.py            # YAML rule loader
│   └── cribl_rules.yaml     # Rule definitions
└── utils/                   # Utilities
    ├── __init__.py
    ├── crypto.py            # Fernet encryption
    ├── logger.py            # Structured logging (structlog)
    ├── rate_limiter.py      # Rate limiting with backoff
    └── version.py           # Cribl version detection
```

## Component Architecture

### 1. Analyzer Registry Pattern

All analyzers register with a global registry, enabling dynamic discovery and extensibility:

```python
from cribl_hc.analyzers import register_analyzer, get_analyzer

# Registration happens at import time
register_analyzer(HealthAnalyzer)
register_analyzer(ConfigAnalyzer)
# ... etc

# Retrieval by objective name
analyzer = get_analyzer("health")
result = await analyzer.analyze(client)
```

### 2. BaseAnalyzer Abstract Class

All analyzers inherit from `BaseAnalyzer`:

```python
class BaseAnalyzer(ABC):
    @property
    @abstractmethod
    def objective_name(self) -> str:
        """Return unique objective identifier."""

    @abstractmethod
    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """Perform analysis and return results."""

    def get_estimated_api_calls(self) -> int:
        """Return estimated API calls for budgeting."""

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
```

### 3. API Client Architecture

The `CriblAPIClient` handles all Cribl API communication:

- **Auto-detection**: Detects product type (Stream, Edge, Lake, Search)
- **Cloud/Self-hosted**: Automatically uses correct endpoint patterns
- **Rate limiting**: Built-in rate limiting with exponential backoff
- **Error handling**: Graceful handling of API errors

```python
async with CriblAPIClient(
    base_url="https://cribl.example.com",
    auth_token="token"
) as client:
    # Auto-detects product type
    workers = await client.get_workers()
    pipelines = await client.get_pipelines()
    routes = await client.get_routes()
```

### 4. Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CLI/API   │────▶│ Orchestrator │────▶│  Analyzers  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           │                    ▼
                           │             ┌─────────────┐
                           │             │ API Client  │
                           │             └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Report    │     │  Cribl API  │
                    │  Generator  │     └─────────────┘
                    └─────────────┘
```

## Analyzer Categories

| Category | Analyzers | Purpose |
|----------|-----------|---------|
| **Core Health** | Health, Resource | Worker health, capacity |
| **Configuration** | Config, Security | Pipeline/route validation, security posture |
| **Operations** | Backpressure, PipelinePerformance | Runtime health, queue monitoring |
| **Data Quality** | Lookup, Schema, DataFlow | Lookup tables, parsers, topology |
| **Cost** | Cost, Storage | License tracking, storage optimization |
| **Multi-Deployment** | Fleet, Predictive | Cross-environment, forecasting |
| **Product-Specific** | Lake*, Search* | Lake datasets, Search jobs |

## API Endpoint Patterns

### Stream/Edge (Config Endpoints)
```
Self-hosted: /api/v1/master/{resource}
Cloud:       /api/v1/m/{group}/{resource}
```

### Lake (Product-Scoped)
```
/api/v1/products/lake/lakes/{lakeId}/datasets
/api/v1/products/lake/lakehouses
```

### Search (Workspace-Scoped)
```
/api/v1/m/{workspace}/search/jobs
/api/v1/m/{workspace}/search/datasets
/api/v1/m/{workspace}/search/dashboards
```

## Security Architecture

### Credential Storage
- Credentials encrypted using Fernet (AES-128-CBC)
- Stored in `~/.cribl-hc/credentials.enc`
- Key derived from machine-specific data

### API Security
- Bearer token authentication
- Optional OAuth client credentials
- No sensitive data in logs (structlog filtering)

## Extension Points

### Adding a New Analyzer

1. Create analyzer class in `src/cribl_hc/analyzers/`:
```python
class MyAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "my_objective"

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()
        # ... analysis logic
        return result
```

2. Register in `analyzers/__init__.py`:
```python
from cribl_hc.analyzers.my_analyzer import MyAnalyzer
register_analyzer(MyAnalyzer)
```

### Adding API Endpoints

Add routes in `src/cribl_hc/api/routers/`:
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"status": "ok"}
```

## Testing Strategy

```
tests/
├── unit/           # Unit tests (fast, isolated)
│   ├── test_analyzers/
│   ├── test_core/
│   ├── test_models/
│   └── test_utils/
├── integration/    # Integration tests (mock APIs)
│   ├── test_api_client.py
│   └── test_*_analyzer.py
└── contract/       # Contract tests (API schema)
    └── test_cribl_api.py
```

Run tests: `pytest tests/`

## Performance Considerations

- **Async I/O**: All API calls use `httpx.AsyncClient`
- **Parallel Analysis**: Multiple analyzers can run concurrently
- **Rate Limiting**: Respects Cribl API rate limits
- **API Budget**: Total calls tracked to stay under 100/analysis

## Dependencies

| Package | Purpose |
|---------|---------|
| httpx | Async HTTP client |
| pydantic | Data validation |
| typer | CLI framework |
| rich | Terminal formatting |
| structlog | Structured logging |
| cryptography | Credential encryption |
| fastapi | Web API |
| pytest | Testing |
