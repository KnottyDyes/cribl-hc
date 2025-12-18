# cribl-hc CLI Guide

Complete guide to using the Cribl Health Check command-line interface.

## Overview

cribl-hc is designed specifically for **Cribl Stream** deployments and provides comprehensive health checking, configuration validation, and resource monitoring.

**Supported Deployments:**
- ✅ Cribl Stream Self-Hosted (all features)
- ✅ Cribl Stream Cribl Cloud (all features except disk metrics*)
- 🔮 Cribl Edge (planned - Phase 5)
- 🔮 Cribl Lake (planned - Phase 6)

_*Cribl Cloud does not expose disk metrics via API. CPU and memory monitoring fully supported._

## Installation

### Current Method (Install from Source)

```bash
git clone https://github.com/KnottyDyes/cribl-hc.git
cd cribl-hc
pip install -e .
```

### Future Method (PyPI - Not Yet Available)

```bash
# Not yet available - package will be published to PyPI in the future
pip install cribl-health-check
```

> **Note**: The package is not yet published to PyPI. Currently, you must install from source.

## Quick Start

### Option 1: Interactive TUI (Recommended for Getting Started)

```bash
# Launch the interactive Terminal User Interface
cribl-hc tui

# Follow the prompts to:
# 1. Add your deployment credentials
# 2. Run health checks interactively
# 3. View formatted results
```

### Option 2: Command Line

```bash
# Check version
cribl-hc version

# Configure credentials (one-time setup)
cribl-hc config set prod \
  --url https://main-myorg.cribl.cloud \
  --token your_bearer_token

# Run analysis
cribl-hc analyze run --deployment prod

# Or use environment variables
export CRIBL_URL=https://main-myorg.cribl.cloud
export CRIBL_TOKEN=your_bearer_token
cribl-hc analyze run

# Run specific analyzer
cribl-hc analyze run --objective health

# Save results to file
cribl-hc analyze run --output report.json
```

## Commands

### `cribl-hc tui`

Launch the interactive Terminal User Interface for managing credentials and running health checks.

**Usage:**

```bash
cribl-hc tui
```

**Features:**

The unified TUI provides a menu-driven interface with the following capabilities:

1. **Manage Deployments**
   - Add new deployment credentials (with automatic Cloud/Self-hosted detection)
   - Edit existing deployment credentials
   - Delete deployments
   - Test connections to verify credentials
   - View all configured deployments
   - View detailed deployment information

2. **Run Health Check**
   - Select from configured deployments
   - Flexible selection: type deployment number (1, 2, 3), name (prod, dev), or press Enter for default
   - Live progress tracking with status updates
   - Immediate results display with color-coded health scores
   - View findings and recommendations interactively

3. **View Recent Results** *(Coming soon)*
   - Browse previously saved analysis results
   - Compare historical health scores

4. **Settings** *(Coming soon)*
   - Configure default API call limits
   - Set default objectives to analyze
   - Customize output format preferences

**Navigation:**
- Main menu: Type option number (1-4) or 'q' to quit
- Deployment selection: Type number, deployment name, or press Enter for default
- Invalid input shows helpful error messages and re-prompts

**Example Session:**

```
╭─────────────────────────────────────────────────────╮
│           Cribl Health Check                        │
│         Interactive Terminal Interface              │
│                                                      │
│   Manage deployments, run analyses, and view results │
╰─────────────────────────────────────────────────────╯

╭─── Cribl Health Check ─────────────────────────────╮
│ Main Menu                                           │
│                                                      │
│ 1. Manage Deployments - Add, edit, delete, or test │
│ 2. Run Health Check - Analyze a Cribl deployment   │
│ 3. View Recent Results - Browse previous analyses  │
│ 4. Settings - Configure tool preferences            │
│                                                      │
│ Q. Quit                                             │
╰─────────────────────────────────────────────────────╯

Select an option [1]: 2

Available Deployments:
  1. dev - https://dev-myorg.cribl.cloud
  2. prod - https://prod-myorg.cribl.cloud

Select deployment (number or name) [dev]: 1

Starting health check for: dev
URL: https://dev-myorg.cribl.cloud

Testing connection...
✓ Connected successfully (145ms)
Cribl version: 4.8.2

Running analysis...
  Analyzing: health                          [████████████████] 100%

✓ Analysis completed
Findings: 2
Recommendations: 1
Health Score: 92

[Results displayed with color-coded findings and recommendations]

Press Enter to continue
```

**Benefits:**
- No need to remember command-line flags
- Visual feedback and progress indicators
- Error handling with helpful messages
- Credential management without editing config files
- Great for interactive use and getting started

### `cribl-hc version`

Show version information.

```bash
cribl-hc version
# Output: cribl-hc version 1.0.0
```

### `cribl-hc list`

List all available analyzers with their API call estimates and descriptions.

**Basic Usage:**

```bash
cribl-hc list
```

**Options:**

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--verbose` | `-v` | Show detailed information including permissions | `cribl-hc list -v` |

**Example Output:**

```
Available Analyzers (3 total)
┏━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Analyzer ┃ API Calls ┃ Description                               ┃
┡━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ config   │         5 │ Configuration validation & best practices │
│ health   │         3 │ Worker health & system status monitoring  │
│ resource │         3 │ CPU/memory/disk capacity planning         │
└──────────┴───────────┴───────────────────────────────────────────┘

Total API calls if all analyzers run: 11/100

Usage examples:
  cribl-hc analyze run                    # Run all analyzers
  cribl-hc analyze run -o health          # Run specific analyzer
```

**Verbose Mode:**

```bash
cribl-hc list --verbose
```

Shows additional permissions column listing the API permissions required by each analyzer.

### `cribl-hc analyze run`

Run health check analysis on a Cribl Stream deployment.

**Basic Usage:**

```bash
cribl-hc analyze run --url <URL> --token <TOKEN>
```

**Options:**

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--url` | `-u` | Cribl API URL | `https://main-myorg.cribl.cloud` or `https://cribl.example.com` |
| `--token` | `-t` | Bearer token | `eyJhbGc...` |
| `--objective` | `-o` | Analyzer to run (repeatable) | `-o health -o config` |
| `--output` | `-f` | Save JSON report to file | `--output report.json` |
| `--markdown` | `-m` | Generate Markdown report | `--markdown` |
| `--deployment` | `-p` | Use stored credentials | `--deployment prod` |
| `--deployment-id` | `-d` | Deployment identifier | `--deployment-id prod-us-east` |
| `--max-api-calls` | | API call budget | `--max-api-calls 100` |
| `--verbose` | `-v` | Verbose output | `-v` |
| `--debug` | | Debug logging | `--debug` |

## Available Analyzers

### 1. `health` - Worker Health & System Status

**Purpose:** Monitor worker node health, process status, and system stability

**API Calls:** 3
- `/api/v1/master/workers` - Worker status
- `/api/v1/system/status` - System health
- `/api/v1/metrics` - Performance metrics

**Permissions Required:**
- `read:workers`
- `read:system`
- `read:metrics`

**Detects:**
- Unhealthy workers
- Underprovisioned worker processes
- Version mismatches
- System health issues

**Example:**
```bash
cribl-hc analyze run --objective health
```

### 2. `config` - Configuration Validation

**Purpose:** Validate pipelines, routes, and configurations for errors and best practices

**API Calls:** 5
- `/api/v1/m/{group}/pipelines` - Pipeline configs
- `/api/v1/m/{group}/routes` - Route configs
- `/api/v1/m/{group}/inputs` - Input configs
- `/api/v1/m/{group}/outputs` - Output configs

**Permissions Required:**
- `read:pipelines`
- `read:routes`
- `read:inputs`
- `read:outputs`

**Detects:**
- Syntax errors in pipelines
- Deprecated functions
- Orphaned configurations
- Security misconfigurations (exposed credentials)
- Conflicting routes

**Example:**
```bash
cribl-hc analyze run --objective config
```

### 3. `resource` - Resource Utilization & Capacity Planning

**Purpose:** Monitor CPU, memory, and disk usage for capacity planning

**API Calls:** 3
- `/api/v1/master/workers` - Worker resources
- `/api/v1/metrics` - Resource metrics
- `/api/v1/system/status` - System status

**Permissions Required:**
- `read:workers`
- `read:metrics`
- `read:system`

**Detects:**
- High CPU utilization (>80% warning, >90% critical)
- Memory pressure (>85% warning, >95% critical)
- Disk space issues (>80% used, <10GB free)
- Resource imbalances across workers

**Example:**
```bash
cribl-hc analyze run --objective resource
```

## Usage Examples

### Example 1: Basic Analysis (Cribl Cloud)

Run all analyzers against a Cribl Cloud deployment:

```bash
# Cribl Cloud URL format: https://<workspace>-<org-name>.cribl.cloud
# "main" is the default workspace, but you can use "dev", "prod", etc.
export CRIBL_URL=https://main-myorg.cribl.cloud
export CRIBL_TOKEN=eyJhbGc...your-token-here

cribl-hc analyze run
```

**Output:**
```
Cribl Stream Health Check
Target: https://main-myorg.cribl.cloud
Deployment: default

Testing connection...
✓ Connected (92ms)

Running analysis...
  [1/3] health... ✓ (2.1s)
  [2/3] config... ✓ (1.8s)
  [3/3] resource... ✓ (1.5s)

Analysis complete!
API calls used: 11/100

=== Health Analysis ===
✓ Workers: 3/3 healthy
✓ Health Score: 95/100
✓ 0 critical findings

=== Config Analysis ===
✓ Pipelines: 20 validated
✓ Compliance Score: 87/100
⚠ 3 medium findings

=== Resource Analysis ===
✓ CPU: 45% average
✓ Memory: 62% average
✓ Health Score: 100/100
```

### Example 2: Single Analyzer (Self-Hosted)

Run only the health analyzer on self-hosted Cribl Stream:

```bash
cribl-hc analyze run \
    --url https://cribl.example.com \
    --token YOUR_TOKEN \
    --objective health
```

### Example 3: Multiple Specific Analyzers (Cribl Cloud)

Run health and config analyzers on Cribl Cloud:

```bash
# Example with "dev" workspace
cribl-hc analyze run \
    -u https://dev-acme-corp.cribl.cloud \
    -t YOUR_TOKEN \
    -o health \
    -o config
```

### Example 4: Save Results to File

Save JSON report:

```bash
cribl-hc analyze run \
    -u https://cribl.example.com \
    -t YOUR_TOKEN \
    --output /path/to/report.json
```

**Output File Structure:**
```json
{
  "deployment_id": "default",
  "timestamp": "2025-12-13T05:00:00Z",
  "cribl_version": "4.3.0",
  "analyzers_run": ["health", "config", "resource"],
  "api_calls_used": 11,
  "results": {
    "health": {
      "success": true,
      "findings": [...],
      "recommendations": [...],
      "metadata": {
        "health_score": 95
      }
    },
    ...
  }
}
```

### Example 5: Generate Markdown Report

Create both terminal and markdown reports:

```bash
cribl-hc analyze run \
    -u https://cribl.example.com \
    -t YOUR_TOKEN \
    --output report.json \
    --markdown
```

This creates:
- `report.json` - Machine-readable JSON
- `report.md` - Human-readable Markdown

### Example 6: Verbose Output

See detailed progress and API calls:

```bash
cribl-hc analyze run \
    -u https://cribl.example.com \
    -t YOUR_TOKEN \
    --verbose
```

**Output includes:**
```
{"event": "api_request", "method": "GET", "endpoint": "/api/v1/master/workers"}
{"event": "api_response", "status_code": 200}
{"event": "workers_fetched", "count": 3}
...
```

### Example 7: Debug Mode

Enable debug logging for troubleshooting:

```bash
cribl-hc analyze run \
    -u https://cribl.example.com \
    -t YOUR_TOKEN \
    --debug
```

### Example 8: Using Stored Credentials

First, store credentials:

```bash
cribl-hc config set prod \
    --url https://cribl.example.com \
    --token YOUR_TOKEN
```

Then use them:

```bash
cribl-hc analyze run --deployment prod
```

### Example 9: Custom API Budget

Limit API calls for testing:

```bash
cribl-hc analyze run \
    -u https://cribl.example.com \
    -t YOUR_TOKEN \
    --max-api-calls 20
```

### Example 10: Self-Hosted Cribl

Analyze self-hosted installation:

```bash
cribl-hc analyze run \
    --url https://cribl-leader.internal:9000 \
    --token YOUR_TOKEN \
    --deployment-id prod-datacenter-1
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CRIBL_URL` | Default Cribl API URL | `https://main-myorg.cribl.cloud` or `https://cribl.example.com` |
| `CRIBL_TOKEN` | Default bearer token | `eyJhbGc...` |

**Usage:**
```bash
# Cribl Cloud
export CRIBL_URL=https://main-myorg.cribl.cloud
export CRIBL_TOKEN=your_token_here

# Or self-hosted
export CRIBL_URL=https://cribl.example.com
export CRIBL_TOKEN=your_token_here

# No need to pass --url and --token
cribl-hc analyze run
```

## Output Formats

### Terminal Output (Default)

Rich, colored terminal output with progress indicators and summaries.

### JSON Output (`--output report.json`)

Machine-readable JSON with complete analysis results:

```json
{
  "deployment_id": "default",
  "timestamp": "2025-12-13T05:00:00Z",
  "cribl_version": "4.3.0",
  "deployment_type": "cloud",
  "worker_group": "default",
  "analyzers_run": ["health", "config", "resource"],
  "api_calls_used": 11,
  "api_calls_budget": 100,
  "execution_time_seconds": 5.4,
  "results": {
    "health": {
      "success": true,
      "objective": "health",
      "findings": [...],
      "recommendations": [...],
      "metadata": {...}
    }
  }
}
```

### Markdown Output (`--markdown`)

Human-readable markdown report suitable for documentation:

```markdown
# Cribl Health Check Report

**Deployment:** prod-us-east-1
**Timestamp:** 2025-12-13 05:00:00 UTC
**Cribl Version:** 4.3.0

## Summary

- ✅ Health Score: 95/100
- ✅ Config Compliance: 87/100
- ✅ Resource Health: 100/100
- 📊 Workers: 3/3 healthy
- 📊 API Calls: 11/100

## Findings

### CRITICAL (0)
No critical findings.

### HIGH (1)
...
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - no critical findings |
| 1 | Error - connection failed or invalid arguments |
| 2 | Critical findings detected |
| 3 | API budget exceeded |

## Best Practices

### 1. Use Environment Variables for Credentials

```bash
# In ~/.bashrc or ~/.zshrc
export CRIBL_URL=https://your-cribl.cloud
export CRIBL_TOKEN=your_token_here
```

### 2. Save Reports for Historical Tracking

```bash
# Create timestamped reports
cribl-hc analyze run \
    --output reports/cribl-hc-$(date +%Y%m%d-%H%M%S).json
```

### 3. Run Specific Analyzers for Focused Analysis

```bash
# Daily: Check worker health
cribl-hc analyze run -o health

# Weekly: Full config validation
cribl-hc analyze run -o config

# Monthly: Capacity planning
cribl-hc analyze run -o resource
```

### 4. Automate with Cron

```bash
# Run health check daily at 2 AM
0 2 * * * /usr/local/bin/cribl-hc analyze run -o health --output /var/log/cribl-hc/daily.json
```

### 5. Use Verbose Mode for CI/CD

```bash
# In CI pipeline
cribl-hc analyze run --verbose --output ci-report.json || exit 1
```

## Troubleshooting

### Connection Refused

```
✗ Connection failed: Connection error
```

**Solutions:**
- Verify `CRIBL_URL` is correct
- Check network connectivity
- Ensure Cribl API is accessible
- Check firewall rules

### 401 Unauthorized

```
✗ Connection failed: HTTP 401
```

**Solutions:**
- Verify bearer token is valid
- Check token hasn't expired
- Ensure token has required permissions

### 404 Not Found

```
✗ Endpoint not found: HTTP 404
```

**Solutions:**
- Cribl Cloud vs self-hosted endpoint differences
- Verify worker group name
- Check Cribl version compatibility

### API Budget Exceeded

```
✗ API budget exceeded: 100/100 calls used
```

**Solutions:**
- Increase budget: `--max-api-calls 200`
- Run fewer analyzers: `-o health`
- Wait for rate limit window to reset

## Advanced Usage

### Custom Deployment Identifier

Track different environments:

```bash
# Production
cribl-hc analyze run --deployment-id prod-us-east-1

# Staging
cribl-hc analyze run --deployment-id staging-us-west-2

# Development
cribl-hc analyze run --deployment-id dev-local
```

### Pipeline Integration

```bash
#!/bin/bash
# health-check-pipeline.sh

# Run analysis
cribl-hc analyze run \
    --output /tmp/report.json \
    --verbose

# Check exit code
if [ $? -eq 0 ]; then
    echo "✓ Health check passed"
    # Send success notification
    curl -X POST https://slack.com/webhook -d '{"text": "Cribl health check: PASS"}'
else
    echo "✗ Health check failed"
    # Send alert
    curl -X POST https://pagerduty.com/alert -d @/tmp/report.json
    exit 1
fi
```

## Further Reading

- [API Documentation](./API.md)
- [Analyzer Development Guide](./ANALYZERS.md)
- [Configuration Guide](./CONFIG.md)
- [Cribl Cloud API Notes](./cribl_cloud_api_notes.md)
