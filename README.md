# Cribl Health Check

Comprehensive health checking tool for Cribl Stream deployments. Provides actionable insights across health assessment, configuration validation, performance optimization, security auditing, and cost management.

## Features

- **Quick Health Assessment**: Overall health score (0-100) with prioritized critical issues
- **Configuration Validation**: Detect syntax errors, deprecated functions, and best practice violations
- **Performance Optimization**: Identify over/under-provisioned workers and optimization opportunities
- **Security Auditing**: Validate TLS configs, detect exposed secrets, assess RBAC
- **Cost Management**: Track license consumption and predict exhaustion timelines
- **Read-Only by Design**: All operations use read-only API access, zero risk to production
- **Fast Analysis**: Complete analysis in under 5 minutes using fewer than 100 API calls

## Supported Products

**✅ Currently Supported:**
- **Cribl Stream (Self-Hosted)** - Full feature support including disk metrics
- **Cribl Stream (Cribl Cloud)** - Full feature support (disk metrics unavailable via API)

**✅ Edge Support (Partial - Phase 5B Complete):**
- **Cribl Edge (Health Monitoring)** - Edge Node health, Fleet support, unified API ✅
  - Phase 5C: Configuration validation and route analysis (planned)

**🔮 Planned Support:**
- **Cribl Lake** - Storage utilization and performance monitoring (Phase 6)
- **Cribl Search** - Query performance and resource optimization (evaluating applicability)

This tool is specifically designed for **Cribl Stream** deployments and analyzes:
- Worker/node health and capacity
- Pipeline and route configurations
- Resource utilization (CPU, memory, disk*)
- Configuration best practices
- Security and compliance posture

_*Disk metrics available on self-hosted deployments only. Cribl Cloud does not expose disk metrics via API._

## Installation

### Prerequisites

- Python 3.11 or higher
- Cribl Stream API access token
- Network access to Cribl Stream API endpoints

### Install from Source (Current)

```bash
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc
pip install -e .
```

### Install from PyPI (Coming Soon)

```bash
# Not yet available - package will be published to PyPI in the future
pip install cribl-health-check
```

> **Note**: The package is not yet published to PyPI. Currently, you must install from source using the method above.

## Quick Start

### 1. Configure Credentials

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

### Phase 1: MVP (Current)
- ✅ Project setup
- ✅ P1: Quick Health Assessment
  - Overall health score (0-100)
  - Worker health monitoring
  - Critical issue identification
- ✅ Resource utilization monitoring
  - CPU and memory capacity planning
  - Disk metrics (self-hosted only)
  - Cloud vs self-hosted detection

### Phase 2: Configuration & Optimization
- ✅ **P2: Configuration Validation & Best Practices (Complete)**
  - ✅ Phase 2A: Rule-Based Architecture (24 rules, YAML-driven)
  - ✅ Phase 2B: Pipeline Efficiency Analysis (3 performance rules)
  - ✅ Phase 2C: Route Conflict Detection (2 reliability rules)
  - ✅ Phase 2D: Complexity Metrics (2 quality rules)
  - ✅ Phase 2E: Advanced Security (PII field masking)
  - 🔮 Phase 2F: RBAC/Teams Validation (Planned)
    - User role assignment validation
    - Team configuration checks (Enterprise)
    - Audit logging verification
    - Least privilege enforcement
- P3: Sizing & Performance Optimization
- P8: Interactive TUI (Terminal User Interface)

### Phase 3: Security & Cost
- P4: Security & Compliance Validation
- P5: Cost & License Management

### Phase 4: Advanced Features
- P6: Disaster Recovery Assessment
- P7: Fleet-Wide Analytics

### Phase 5: Cribl Edge Support
- ✅ **Phase 5A (Complete)**: Product detection foundation
  - Automatic Stream vs Edge vs Lake detection
  - Edge API endpoint mapping
  - Product-aware API client
- ✅ **Phase 5B (Complete)**: Edge Health Analyzer
  - Edge Node health monitoring
  - Edge Fleet support (nodes grouped by fleets)
  - Unified analyzer works for both Stream and Edge
  - Product-aware findings and messages
  - Zero breaking changes to Stream functionality
- 🔮 **Phase 5C (Planned)**: Edge Config & Resource Analyzers
  - Edge-specific configuration validation
  - Edge route and pipeline analysis
  - Edge resource utilization monitoring

### Phase 6: Cribl Lake Support
- Storage bucket utilization monitoring
- Data retention and lifecycle analysis
- Query performance metrics
- Cost optimization for storage
- Lake-specific health indicators

### Phase 7: Multi-Product Fleet Analytics
- Unified health dashboard across Stream/Edge/Lake
- Cross-product data flow visualization
- Holistic capacity planning
- Fleet-wide configuration compliance

## Contributing

Contributions are welcome! Please open an issue or pull request on [GitHub](https://github.com/KnottyDyes/cribl-hc).

## License

This project is provided as-is for use with Cribl Stream deployments.

## Documentation

- **[Getting Started Guide](docs/GETTING_STARTED.md)** - Quick start guide
- **[CLI Guide](docs/CLI_GUIDE.md)** - Complete CLI reference
- **[CLI Quick Reference](docs/CLI_QUICK_REFERENCE.md)** - Command cheat sheet
- **[Product Compatibility](docs/PRODUCT_COMPATIBILITY.md)** - Supported products and features
- **[Cribl Cloud API Notes](docs/cribl_cloud_api_notes.md)** - Cloud vs self-hosted differences

## Support

- **Documentation**: [GitHub README](https://github.com/KnottyDyes/cribl-hc#readme)
- **Issues**: [GitHub Issues](https://github.com/KnottyDyes/cribl-hc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KnottyDyes/cribl-hc/discussions)

## Authors

Cribl Health Check Project
Sean Armstrong
Claude
---

**Status**: Beta - MVP in development
**Version**: 1.0.0
**Python**: 3.11+
**Cribl Stream**: 4.x (N through N-2 tested; older versions supported with best-effort compatibility)
