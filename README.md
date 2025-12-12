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

## Installation

### Prerequisites

- Python 3.11 or higher
- Cribl Stream API access token
- Network access to Cribl Stream API endpoints

### Install from PyPI

```bash
pip install cribl-health-check
```

### Install from Source

```bash
git clone https://github.com/cribl/health-check.git
cd health-check
pip install -e .
```

## Quick Start

### 1. Configure Credentials

```bash
# Configure credentials for your Cribl Stream deployment
cribl-hc config set prod \
  --url https://cribl.example.com \
  --token YOUR_API_TOKEN

# Short form:
cribl-hc config set prod -u https://cribl.example.com -t YOUR_API_TOKEN
```

**Alternative**: Use environment variables:
```bash
export CRIBL_URL=https://cribl.example.com
export CRIBL_TOKEN=YOUR_API_TOKEN
```

### 2. Run Health Check (MVP)

```bash
# Quick health assessment
cribl-hc analyze run --deployment prod

# Short form:
cribl-hc analyze run -p prod

# Output: Health score and critical findings
```

### 3. Generate Report

```bash
# Generate JSON and markdown reports
cribl-hc analyze run -p prod --output health-report.json --markdown

# Short form:
cribl-hc analyze run -p prod -o health-report.json -m

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
# or short form:
cribl-hc analyze run -p prod -d

# Analyze specific objectives (requires P2+ implementation)
cribl-hc analyze run -p prod --objectives health,config,security
# or short form:
cribl-hc analyze run -p prod -o health,config,security
```

### Configuration Management

```bash
# Store credentials for a deployment
cribl-hc config set prod --url https://cribl.example.com --token YOUR_TOKEN

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
cribl-hc analyze run -p prod -o report.json -m
```

## Python Library API

```python
from cribl_hc import analyze_deployment, Deployment, AnalysisRun

# Create deployment configuration
deployment = Deployment(
    id="prod",
    name="Production Cribl Cluster",
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
git clone https://github.com/cribl/health-check.git
cd health-check

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
- 🚧 P1: Quick Health Assessment
  - Overall health score (0-100)
  - Worker health monitoring
  - Critical issue identification

### Phase 2: Configuration & Optimization
- P2: Configuration Validation & Best Practices
- P3: Sizing & Performance Optimization

### Phase 3: Security & Cost
- P4: Security & Compliance Validation
- P5: Cost & License Management

### Phase 4: Advanced Features
- P6: Disaster Recovery Assessment
- P7: Fleet-Wide Analytics

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [GitHub README](https://github.com/cribl/health-check#readme)
- **Issues**: [GitHub Issues](https://github.com/cribl/health-check/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cribl/health-check/discussions)

## Authors

Cribl Health Check Project

---

**Status**: Beta - MVP in development
**Version**: 1.0.0
**Python**: 3.11+
**Cribl Stream**: 4.x (N through N-2 supported)
