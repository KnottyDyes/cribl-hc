# Cribl Health Check - User Guide

## Introduction

Cribl Health Check is a comprehensive analysis tool that provides actionable insights for your Cribl deployments. It supports:

- **Cribl Stream** (Self-hosted and Cloud)
- **Cribl Edge**
- **Cribl Lake**
- **Cribl Search**

## Installation

### Prerequisites

- Python 3.11 or higher
- Cribl API access token with read permissions
- Network access to Cribl API endpoints

### Install from Source

```bash
# Clone repository
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .
```

### Docker Installation

```bash
# Clone and start
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc
docker-compose up -d

# Access web interface
open http://localhost:8080/api/docs
```

## Quick Start

### 1. Configure Your First Deployment

```bash
# For Cribl Cloud
cribl-hc config set prod \
  --url https://main-myorg.cribl.cloud \
  --token YOUR_API_TOKEN

# For self-hosted Cribl Stream
cribl-hc config set prod \
  --url https://cribl.example.com \
  --token YOUR_API_TOKEN
```

### 2. Test the Connection

```bash
cribl-hc test-connection test --deployment prod
```

### 3. Run Your First Analysis

```bash
cribl-hc analyze run --deployment prod
```

### 4. Generate a Report

```bash
cribl-hc analyze run -p prod --output report.json --markdown
```

This creates:
- `report.json` - Machine-readable results
- `report.md` - Human-readable report

## Using the CLI

### Interactive TUI Mode

The Terminal User Interface provides an interactive experience:

```bash
cribl-hc tui
```

Features:
- Visual deployment selection
- Real-time analysis progress
- Formatted results display
- Color-coded health scores

### Command Reference

#### Configuration Management

```bash
# Add/update deployment
cribl-hc config set <name> --url <url> --token <token>

# List deployments
cribl-hc config list

# Show deployment details
cribl-hc config show <name>

# Remove deployment
cribl-hc config remove <name>

# Test connection
cribl-hc test-connection test -p <name>
```

#### Analysis Commands

```bash
# Run analysis with default objectives
cribl-hc analyze run -p <deployment>

# Run specific objectives
cribl-hc analyze run -p <deployment> -o health -o config -o security

# Verbose output
cribl-hc analyze run -p <deployment> --verbose

# Debug mode
cribl-hc analyze run -p <deployment> --debug

# Generate reports
cribl-hc analyze run -p <deployment> -f report.json -m
```

## Using the Web API

### Start the API Server

```bash
python run_api.py
```

### Access the Documentation

Open http://localhost:8080/api/docs for interactive Swagger documentation.

### Example: Run Analysis via API

```bash
# Store credentials
curl -X POST http://localhost:8080/api/v1/credentials \
  -H "Content-Type: application/json" \
  -d '{"id": "prod", "name": "Production", "url": "https://cribl.example.com", "auth_token": "token"}'

# Run analysis
curl -X POST http://localhost:8080/api/v1/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"deployment_id": "prod", "objectives": ["health", "config"]}'
```

## Understanding Results

### Health Score

The health score (0-100) is calculated from:

| Component | Weight | Factors |
|-----------|--------|---------|
| Workers | 40% | CPU, memory, disk usage, status |
| Pipelines | 30% | Syntax errors, best practices |
| Connectivity | 20% | API availability, response times |
| Security | 10% | TLS, credential exposure |

**Score Ranges:**
- 90-100: Excellent
- 80-89: Good
- 70-79: Fair
- 60-69: Needs Attention
- <60: Critical

### Finding Severities

| Severity | Color | Action |
|----------|-------|--------|
| Critical | Red | Immediate attention required |
| High | Orange | Address soon |
| Medium | Yellow | Plan to address |
| Low | Blue | Consider addressing |
| Info | Gray | Informational |

### Common Findings

#### Health Category
- **Worker CPU High** - CPU usage above 90%
- **Worker Memory High** - Memory usage above 90%
- **Worker Disk High** - Disk usage above 90%
- **Worker Unhealthy** - Worker reporting unhealthy status

#### Configuration Category
- **Pipeline Syntax Error** - Invalid pipeline configuration
- **Orphaned Pipeline** - Pipeline not referenced by any route
- **Missing Output** - Route references non-existent output
- **Catch-all Route Not Last** - Catch-all route before specific routes

#### Security Category
- **Hardcoded Credential** - Password/token in configuration
- **Unencrypted Connection** - Non-TLS output connection
- **Exposed Secret** - Secret visible in config

#### Performance Category
- **Backpressure Detected** - Destination experiencing backpressure
- **Queue Nearly Full** - Persistent queue above threshold
- **Slow Function** - Pipeline function taking >5ms average

## Analysis Objectives

### Core Objectives

| Objective | Description | Products |
|-----------|-------------|----------|
| `health` | Overall health assessment | Stream, Edge |
| `config` | Configuration validation | Stream, Edge |
| `resource` | Resource/capacity analysis | Stream, Edge |
| `storage` | Storage optimization | Stream, Edge |
| `security` | Security posture | Stream, Edge |
| `cost` | License and cost tracking | Stream |

### Advanced Objectives

| Objective | Description | Products |
|-----------|-------------|----------|
| `fleet` | Multi-deployment analysis | All |
| `predictive` | Forecasting and predictions | All |
| `backpressure` | Queue and backpressure monitoring | Stream, Edge |
| `pipeline_performance` | Function-level analysis | Stream, Edge |
| `lookup_health` | Lookup table optimization | Stream, Edge |
| `schema_quality` | Parser and schema analysis | Stream, Edge |
| `dataflow_topology` | Route topology validation | Stream, Edge |

### Product-Specific Objectives

| Objective | Description | Products |
|-----------|-------------|----------|
| `lake_health` | Dataset health monitoring | Lake |
| `lake_storage` | Storage optimization | Lake |
| `search_health` | Job monitoring | Search |
| `search_performance` | Query performance | Search |

## Best Practices

### API Token Permissions

Create a token with these minimal permissions:
- `read:workers`
- `read:pipelines`
- `read:routes`
- `read:inputs`
- `read:outputs`
- `read:system`

### Regular Analysis Schedule

Recommended analysis frequency:
- **Daily**: Health objective
- **Weekly**: Full analysis (all objectives)
- **After Changes**: Config and security objectives

### Acting on Findings

1. **Critical**: Address within 24 hours
2. **High**: Address within 1 week
3. **Medium**: Address within 1 month
4. **Low**: Address when convenient

### Exporting Results

```bash
# JSON for automation
cribl-hc analyze run -p prod -f results.json

# Markdown for documentation
cribl-hc analyze run -p prod -f results.json -m

# Both formats
cribl-hc analyze run -p prod -f results.json --markdown
```

## Troubleshooting

### Connection Issues

**Problem**: `Connection refused`
```bash
# Check URL accessibility
curl -I https://cribl.example.com/api/v1/version

# Verify token
cribl-hc test-connection test -p <deployment>
```

**Problem**: `401 Unauthorized`
- Verify API token is correct
- Check token hasn't expired
- Ensure token has required permissions

**Problem**: `SSL Certificate Error`
- For self-signed certs, the tool may need configuration
- Verify certificate chain is complete

### Analysis Issues

**Problem**: Analysis times out
- Check network connectivity
- Verify API rate limits aren't being hit
- Try running individual objectives

**Problem**: Zero findings
- Verify correct deployment URL
- Check API token permissions
- Run with `--debug` flag for more info

### Getting Help

- **Documentation**: [GitHub README](https://github.com/KnottyDyes/cribl-hc#readme)
- **Issues**: [GitHub Issues](https://github.com/KnottyDyes/cribl-hc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KnottyDyes/cribl-hc/discussions)

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CRIBL_URL` | Default Cribl URL | `https://cribl.example.com` |
| `CRIBL_TOKEN` | Default API token | `your-token` |
| `CRIBL_HC_DEBUG` | Enable debug mode | `true` |
| `CRIBL_HC_CONFIG_DIR` | Config directory | `~/.cribl-hc` |

## Examples

### Example 1: Daily Health Check Script

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cribl-hc analyze run -p prod -o health -f "health-$DATE.json" -m

# Check for critical issues
if grep -q '"severity": "critical"' "health-$DATE.json"; then
  echo "CRITICAL issues found!"
  exit 1
fi
```

### Example 2: Full Weekly Report

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
cribl-hc analyze run -p prod \
  -o health -o config -o security -o resource \
  -f "weekly-report-$DATE.json" -m

# Email report
mail -s "Weekly Cribl Health Report" team@example.com < "weekly-report-$DATE.md"
```

### Example 3: Multi-Environment Analysis

```bash
# Configure all environments
cribl-hc config set dev --url https://dev.cribl.example.com --token $DEV_TOKEN
cribl-hc config set staging --url https://staging.cribl.example.com --token $STAGING_TOKEN
cribl-hc config set prod --url https://prod.cribl.example.com --token $PROD_TOKEN

# Analyze all
for env in dev staging prod; do
  cribl-hc analyze run -p $env -f "${env}-health.json"
done
```
