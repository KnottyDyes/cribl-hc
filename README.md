# Cribl Health Check

[![CI](https://github.com/yourusername/cribl-hc/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/cribl-hc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19.2-blue?logo=react)](https://react.dev/)

Comprehensive health checking tool for Cribl Stream deployments. Provides actionable insights across health assessment, configuration validation, performance optimization, security auditing, and cost management.

## Features

### CLI Features
- **Quick Health Assessment**: Overall health score (0-100) with prioritized critical issues
- **Configuration Validation**: Detect syntax errors, deprecated functions, and best practice violations
- **Performance Optimization**: Identify over/under-provisioned workers and optimization opportunities
- **Security Auditing**: Validate TLS configs, detect exposed secrets, assess RBAC
- **Cost Management**: Track license consumption and predict exhaustion timelines
- **Read-Only by Design**: All operations use read-only API access, zero risk to production
- **Fast Analysis**: Complete analysis in under 5 minutes using fewer than 100 API calls

### Web GUI Features (New!)
- **Interactive Dashboard**: Modern web interface for managing health checks
- **Real-time Updates**: Live progress tracking via WebSocket during analysis
- **Credential Management**: Add, edit, and test deployment credentials from the browser
- **Visual Results**: Interactive findings table with filtering and sorting
- **REST API**: Full API backend for programmatic access
- **Docker Support**: One-command deployment with Docker Compose

## Supported Products

**✅ Currently Supported:**
- **Cribl Stream (Self-Hosted)** - Full feature support including disk metrics
- **Cribl Stream (Cribl Cloud)** - Full feature support (disk metrics unavailable via API)

**✅ Edge Support (Partial - Phase 5B Complete):**
- **Cribl Edge (Health Monitoring)** - Edge Node health, Fleet support, unified API ✅
  - Phase 5C: Configuration validation and route analysis (planned)

**✅ Lake Support (Complete - Phase 7):**
- **Cribl Lake** - Dataset health, retention analysis, storage optimization ✅
  - LakeHealthAnalyzer: Dataset monitoring, retention policies, lakehouse availability
  - LakeStorageAnalyzer: JSON→Parquet recommendations, inactive dataset detection

**✅ Search Support (Complete - Phase 8):**
- **Cribl Search** - Query performance, job monitoring, cost analysis ✅
  - SearchHealthAnalyzer: Job monitoring, dataset availability, dashboard validation
  - SearchPerformanceAnalyzer: CPU cost analysis, query efficiency, optimization

This tool analyzes **all Cribl products** including:
- Worker/node health and capacity (Stream, Edge)
- Pipeline and route configurations (Stream, Edge)
- Resource utilization (CPU, memory, disk*)
- Configuration best practices and security posture
- Lookup table optimization and schema quality
- Data flow topology and route validation
- Lake dataset health and storage optimization
- Search job performance and cost analysis

_*Disk metrics available on self-hosted deployments only. Cribl Cloud does not expose disk metrics via API._

## Installation

### Prerequisites

- Python 3.11 or higher
- Cribl Stream API access token
- Network access to Cribl Stream API endpoints
- (Optional) Docker for containerized deployment
- (Optional) Node.js 18+ for frontend development

### Option 1: Docker (Recommended for Web GUI)

```bash
# Clone repository
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc

# Start web API
docker-compose up -d

# Access web interface
open http://localhost:8080/api/docs
```

### Option 2: Install from Source

```bash
# Clone repository
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc

# Install for CLI usage
pip install -e .

# OR install for web API
pip install -e .
python run_api.py  # Starts web server on port 8080
```

### Option 3: Install from PyPI (Coming Soon)

```bash
# Not yet available - package will be published to PyPI in the future
pip install cribl-health-check
```

> **Note**: The package is not yet published to PyPI. Currently, you must install from source using the method above.

## Quick Start

Choose your preferred interface:
- **Web GUI**: Modern browser-based interface (recommended for production use)
- **CLI**: Command-line interface for automation and scripting
- **TUI**: Interactive terminal interface for quick checks

### Web GUI Mode

```bash
# Start API server
python run_api.py

# OR with Docker
docker-compose up -d

# Access in browser
open http://localhost:8080/api/docs

# Interactive API documentation with "Try it out" buttons
# Add credentials, run analyses, view results - all from the browser
```

**Features**:
- Add/edit/test credentials via web interface
- Start analyses with real-time progress updates
- View findings in interactive table
- WebSocket live updates during analysis

**Documentation**: See [docs/WEB_GUI_QUICKSTART.md](docs/WEB_GUI_QUICKSTART.md)

### CLI Mode

#### 1. Configure Credentials

```bash
# Configure credentials for your Cribl Stream deployment

# For Cribl Cloud (format: https://<workspace>-<org-name>.cribl.cloud)
# Where <workspace> is your workspace ID (e.g., "main", "dev", "prod")
cribl-hc config set prod \
  --url https://main-myorg.cribl.cloud \
  --token YOUR_API_TOKEN

# For self-hosted Cribl Stream
cribl-hc config set prod \
  --url https://cribl.example.com \
  --token YOUR_API_TOKEN

# Short form:
cribl-hc config set prod -u https://main-myorg.cribl.cloud -t YOUR_API_TOKEN
```

**Alternative**: Use environment variables:
```bash
# Cribl Cloud (workspace can be "main", "dev", "prod", etc.)
export CRIBL_URL=https://main-myorg.cribl.cloud
export CRIBL_TOKEN=YOUR_API_TOKEN

# Self-hosted
export CRIBL_URL=https://cribl.example.com
export CRIBL_TOKEN=YOUR_API_TOKEN
```

### 2. Interactive TUI (Recommended for Getting Started)

```bash
# Launch the unified Terminal User Interface
cribl-hc tui
```

The TUI provides an interactive menu for:
- **Managing Deployments**: Add, edit, delete, and test deployment credentials
- **Running Health Checks**: Select a deployment and run analysis interactively
- **Viewing Results**: Browse analysis results with formatted output

**Features:**
- Easy credential management without command-line flags
- Interactive deployment selection (type number, name, or press Enter for default)
- Live progress tracking with status updates
- Formatted results display with color-coded health scores

### 3. Run Health Check (Command Line)

```bash
# Quick health assessment using stored credentials
cribl-hc analyze run --deployment prod

# Short form:
cribl-hc analyze run -p prod

# Output: Health score and critical findings
```

### 4. Generate Report

```bash
# Generate JSON and markdown reports
cribl-hc analyze run -p prod --output health-report.json --markdown

# Short form:
cribl-hc analyze run -p prod -f health-report.json -m

# This creates:
# - health-report.json (machine-readable)
# - health-report.md (human-readable)
```

## Usage

### Basic Analysis

```bash
# Analyze with default objectives (health only for MVP)
cribl-hc analyze run --deployment prod
# or short form:
cribl-hc analyze run -p prod

# Add verbose output
cribl-hc analyze run -p prod --verbose
# or short form:
cribl-hc analyze run -p prod -v

# Add debug mode for troubleshooting
cribl-hc analyze run -p prod --debug

# Analyze specific objectives (requires P2+ implementation)
cribl-hc analyze run -p prod --objective health --objective config --objective security
# or short form:
cribl-hc analyze run -p prod -o health -o config -o security
```

### Configuration Management

```bash
# Store credentials for Cribl Cloud deployment
cribl-hc config set prod --url https://main-myorg.cribl.cloud --token YOUR_TOKEN

# Store credentials for self-hosted deployment
cribl-hc config set onprem --url https://cribl.example.com --token YOUR_TOKEN

# List configured deployments
cribl-hc config list

# Show deployment details
cribl-hc config show prod

# Remove deployment
cribl-hc config remove staging

# Test connection
cribl-hc test-connection test --deployment prod
# or short form:
cribl-hc test-connection test -p prod
```

### Report Generation

Reports are generated during analysis using the `--output` and `--markdown` flags:

```bash
# Generate JSON report
cribl-hc analyze run -p prod --output report.json

# Generate both JSON and Markdown reports
cribl-hc analyze run -p prod --output report.json --markdown

# Short form:
cribl-hc analyze run -p prod -f report.json -m
```

## Python Library API

```python
from cribl_hc import analyze_deployment, Deployment, AnalysisRun

# Create deployment configuration for Cribl Cloud
deployment = Deployment(
    id="prod",
    name="Production Cribl Cloud",
    url="https://main-myorg.cribl.cloud",
    environment_type="cloud",
    auth_token="your-api-token"
)

# Or for self-hosted Cribl Stream
deployment = Deployment(
    id="onprem",
    name="On-Premises Cribl Cluster",
    url="https://cribl.example.com",
    environment_type="self-hosted",
    auth_token="your-api-token"
)

# Run analysis
result: AnalysisRun = await analyze_deployment(
    deployment,
    objectives=["health"]  # MVP: health only
)

# Access results
print(f"Health Score: {result.health_score.overall_score}")
print(f"Critical Findings: {len([f for f in result.findings if f.severity == 'critical'])}")

# Generate report
from cribl_hc.core.report_generator import generate_report
report = generate_report(result, format="markdown")
print(report)
```

## Architecture

- **API-First Design**: Core library with thin CLI wrapper
- **Stateless by Default**: Independent analysis runs, optional historical data
- **Read-Only Access**: All operations use GET requests only
- **Pluggable Analyzers**: Modular architecture for easy extension
- **Performance Optimized**: <5 min analysis, <100 API calls per run

## Constitution Principles

This project follows 12 core principles:

1. **Read-Only by Default**: Never modifies Cribl configurations
2. **Actionability First**: Clear remediation steps for all findings
3. **API-First Design**: Core library with thin CLI wrapper
4. **Minimal Data Collection**: Metrics-only, no log content extraction
5. **Stateless Analysis**: Independent runs, reproducible results
6. **Graceful Degradation**: Partial reports better than failures
7. **Performance Efficiency**: <5 min, <100 API calls
8. **Pluggable Architecture**: Module-based extensible design
9. **Test-Driven Development**: 80%+ code coverage
10. **Security by Design**: Encrypted credentials, no sensitive data in logs
11. **Version Compatibility**: Support Cribl Stream N through N-2
12. **Transparent Methodology**: Documented scoring and recommendations

See [.specify/memory/constitution.md](.specify/memory/constitution.md) for complete details.

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cribl_hc --cov-report=html

# Run specific test types
pytest -m unit
pytest -m integration
pytest -m contract
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff src/ tests/

# Type checking
mypy src/
```

## Requirements

### Runtime Dependencies

- httpx >= 0.25.0 (async HTTP client)
- pydantic >= 2.5.0 (data validation)
- typer >= 0.9.0 (CLI framework)
- rich >= 13.7.0 (terminal formatting)
- structlog >= 23.2.0 (structured logging)
- cryptography >= 41.0.0 (credential encryption)

### Development Dependencies

- pytest >= 7.4.0
- pytest-asyncio >= 0.21.0
- pytest-cov >= 4.1.0
- respx >= 0.20.0 (HTTP mocking)
- black >= 23.12.0 (code formatting)
- ruff >= 0.1.9 (linting)
- mypy >= 1.7.0 (type checking)

## Roadmap

### ✅ Phase 1-10: Core Analyzers (Complete)

**17 Analyzers Implemented:**

| Category | Analyzers | Products |
|----------|-----------|----------|
| **Health** | HealthAnalyzer | Stream, Edge |
| **Config** | ConfigAnalyzer | Stream, Edge |
| **Resources** | ResourceAnalyzer, StorageAnalyzer | Stream, Edge |
| **Security** | SecurityAnalyzer | Stream, Edge |
| **Cost** | CostAnalyzer | Stream |
| **Fleet** | FleetAnalyzer | All |
| **Predictive** | PredictiveAnalyzer | All |
| **Lake** | LakeHealthAnalyzer, LakeStorageAnalyzer | Lake |
| **Search** | SearchHealthAnalyzer, SearchPerformanceAnalyzer | Search |
| **Runtime** | BackpressureAnalyzer, PipelinePerformanceAnalyzer | Stream, Edge |
| **Data Quality** | LookupHealthAnalyzer, SchemaQualityAnalyzer, DataFlowTopologyAnalyzer | Stream, Edge |

### ✅ Phase 11: Polish & Integration (Complete)
- CLI refinement and report generation
- Integration testing (258+ tests passing)
- API alignment with Cribl v4.15.1 specs
- Documentation (ARCHITECTURE.md, API_REFERENCE.md, USER_GUIDE.md)

### 🔮 Future Phases
- Real-time monitoring mode
- Remediation automation
- Integration hooks (Jira, Slack, PagerDuty)
- Custom plugin architecture

## Contributing

Contributions are welcome! Please open an issue or pull request on [GitHub](https://github.com/KnottyDyes/cribl-hc).

## License

This project is provided as-is for use with Cribl Stream deployments.

## Documentation

- **[Getting Started Guide](docs/GETTING_STARTED.md)** - Quick start guide
- **[User Guide](docs/USER_GUIDE.md)** - Installation, usage, and troubleshooting
- **[Architecture](docs/ARCHITECTURE.md)** - System design and component overview
- **[API Reference](docs/API_REFERENCE.md)** - Python library and REST API documentation
- **[CLI Quick Reference](docs/CLI_QUICK_REFERENCE.md)** - Command cheat sheet
- **[Web GUI Quickstart](docs/WEB_GUI_QUICKSTART.md)** - Browser-based interface guide

## Support

- **Documentation**: [GitHub README](https://github.com/KnottyDyes/cribl-hc#readme)
- **Issues**: [GitHub Issues](https://github.com/KnottyDyes/cribl-hc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KnottyDyes/cribl-hc/discussions)

## Authors

Cribl Health Check Project
Sean Armstrong
Claude
---

**Status**: Production Ready - Phase 11 Complete
**Version**: 0.4.0
**Python**: 3.11+
**Cribl Stream**: 4.x (N through N-2 tested; older versions supported with best-effort compatibility)
**Tests**: 258+ passing (unit + integration)
