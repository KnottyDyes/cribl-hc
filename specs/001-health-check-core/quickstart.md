# Quickstart Guide: Cribl Health Check Core

**Feature**: 001-health-check-core
**Target Time**: First analysis in < 30 minutes from installation

## Prerequisites

- Python 3.11 or newer
- pip or uv package manager
- Cribl Stream deployment with API access (Cloud or self-hosted)
- API token with read-only permissions

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install cribl-health-check

# Verify installation
cribl-hc --version
# Output: cribl-health-check version 1.0.0
```

### Option 2: Install from Source

```bash
git clone https://github.com/cribl/health-check.git
cd health-check
pip install -e .

# Verify
cribl-hc --version
```

### Option 3: Standalone Executable (No Python Required)

```bash
# Download for your platform
curl -L https://github.com/cribl/health-check/releases/latest/download/cribl-hc-linux -o cribl-hc
chmod +x cribl-hc

# Run directly
./cribl-hc --version
```

## Quick Start (5 Minutes to First Report)

### Step 1: Configure Credentials (2 minutes)

```bash
# Interactive configuration
cribl-hc config init

# You'll be prompted for:
# - Deployment ID (e.g., "prod", "staging")
# - Deployment Name (e.g., "Production Cribl Cluster")
# - Cribl URL (e.g., "https://cribl.example.com" or "https://org.cribl.cloud")
# - API Token (will be encrypted and stored securely)
# - Environment Type (cloud / self-hosted)
```

**Alternative: Non-Interactive Configuration**

```bash
cribl-hc config set-credentials \
  --id prod \
  --name "Production Cluster" \
  --url https://cribl.example.com \
  --token YOUR_API_TOKEN_HERE \
  --environment self-hosted
```

**Credentials Storage**: Encrypted in `~/.cribl-hc/credentials.enc` (Constitution Principle X - Security by Design)

### Step 2: Run Your First Health Check (3 minutes)

```bash
# Run health assessment (MVP - Objective 1)
cribl-hc analyze --deployment prod

# Output:
# ✓ Connecting to Cribl API...
# ✓ Analyzing worker health...
# ✓ Calculating health score...
# ✓ Generating findings...
#
# Health Score: 78/100 (Good)
#
# Critical Issues: 0
# High Priority: 2
# Medium Priority: 5
# Low Priority: 3
#
# Analysis complete in 2m 15s (87 API calls used)
```

### Step 3: View the Report

```bash
# Generate human-readable markdown report
cribl-hc report --format markdown --output health-report.md

# Open in browser (HTML format)
cribl-hc report --format html --output health-report.html --open

# Export for automation (JSON)
cribl-hc report --format json --output health-report.json
```

**Example Report Snippet**:
```markdown
# Health Check Report: Production Cluster
Generated: 2025-12-10 14:05:00
Overall Score: 78/100 (Good)

## Critical Issues
None found.

## High Priority Issues
1. **Worker Memory Exhaustion Risk**
   - Severity: High
   - Affected: worker-01
   - Impact: High risk of worker crash and data loss
   - Remediation:
     1. Increase worker memory allocation from 16GB to 24GB
     2. Review memory-intensive pipelines
     3. Check for memory leaks in custom functions
   - Documentation: https://docs.cribl.io/stream/sizing-workers
```

## Common Usage Patterns

### Run Specific Objectives Only

```bash
# Health assessment only (fastest)
cribl-hc analyze --deployment prod --objectives health

# Health + Configuration validation
cribl-hc analyze --deployment prod --objectives health,config

# All objectives (comprehensive analysis, ~5 minutes)
cribl-hc analyze --deployment prod --objectives all
```

**Available Objectives**:
- `health` - Worker health and system resources (P1 MVP)
- `config` - Configuration auditing and best practices (P2)
- `sizing` - Sizing and scaling analysis (P3)
- `security` - Security and compliance (P4)
- `cost` - License and cost management (P5)
- `fleet` - Multi-deployment analysis (P6)
- `predictive` - Predictive analytics (P7)

### Run Against Multiple Deployments

```bash
# Configure multiple deployments
cribl-hc config set-credentials --id staging --url https://staging.cribl.example.com --token TOKEN1
cribl-hc config set-credentials --id prod --url https://prod.cribl.example.com --token TOKEN2

# Analyze both
cribl-hc analyze --deployment staging
cribl-hc analyze --deployment prod

# Fleet comparison (Objective 15)
cribl-hc fleet analyze --deployments staging,prod
cribl-hc fleet report --format html --output fleet-comparison.html
```

### View Historical Trends

```bash
# Enable historical tracking (optional, Constitution Principle V - Stateless by default)
cribl-hc config set history-enabled true

# Run analyses over time...
# (analyses automatically record historical data when enabled)

# View trends
cribl-hc history show --deployment prod --metric health_score --days 30

# Output:
# Health Score Trend (Last 30 Days)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 90┤                              ╭─
# 85┤                          ╭───╯
# 80┤                   ╭──────╯
# 75┤            ╭──────╯
# 70┤  ──────────╯
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#    Dec 1              Dec 15         Dec 30
#
# Trend: Improving (+18 points)
# Forecast: 92 (next analysis)
```

## Advanced Configuration

### Custom Analysis Schedules

```bash
# Run via cron (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/cribl-hc analyze --deployment prod --quiet" | crontab -

# Output to log file
cribl-hc analyze --deployment prod --log-file /var/log/cribl-hc/analysis.log
```

### CI/CD Integration

```yaml
# GitHub Actions example
name: Daily Cribl Health Check
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Install cribl-health-check
        run: pip install cribl-health-check

      - name: Configure credentials
        run: |
          cribl-hc config set-credentials \
            --id prod \
            --url ${{ secrets.CRIBL_URL }} \
            --token ${{ secrets.CRIBL_TOKEN }} \
            --environment self-hosted

      - name: Run analysis
        run: cribl-hc analyze --deployment prod

      - name: Generate report
        run: cribl-hc report --format html --output health-report.html

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: health-report
          path: health-report.html
```

### Air-Gapped Environments

```bash
# Download standalone executable to air-gapped environment
# (no network access required after installation)

# Configure with local Cribl instance
cribl-hc config set-credentials \
  --id local \
  --url https://10.0.1.100:9000 \
  --token TOKEN \
  --environment self-hosted

# Run analysis (no external data transmission - Constitution Principle IV)
cribl-hc analyze --deployment local

# Export report for transfer
cribl-hc report --format json --output /mnt/usb/health-report.json
```

## Troubleshooting

### Issue: "Connection refused" or "API unreachable"

**Solution**:
```bash
# Test connectivity
curl -k https://cribl.example.com/api/v1/system/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check URL and token
cribl-hc config show --deployment prod

# Update if needed
cribl-hc config set-credentials --id prod --url CORRECT_URL --token NEW_TOKEN
```

### Issue: "API rate limit exceeded"

**Solution**:
```bash
# The tool respects rate limits automatically with backoff
# If you see this error, wait 60 seconds and retry

# Or reduce objectives to use fewer API calls
cribl-hc analyze --deployment prod --objectives health
# (Uses ~15 API calls vs 87 for all objectives)
```

### Issue: "Partial analysis completed with errors"

**Solution**:
```bash
# This is expected behavior (Constitution Principle VI - Graceful Degradation)
# The tool produces partial reports when some data unavailable

# View the report to see what completed successfully
cribl-hc report --format markdown

# Check logs for details
cribl-hc logs show --last 50
```

### Issue: "Invalid credentials" or "403 Forbidden"

**Solution**:
```bash
# Verify API token has read-only access
# Required permissions:
# - Read system status
# - Read worker information
# - Read configurations
# - Read metrics

# Generate new token in Cribl UI:
# Settings → API Tokens → Create New Token
# Permissions: Select "Read-Only" role

# Update credentials
cribl-hc config set-credentials --id prod --token NEW_TOKEN
```

## Command Reference

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `cribl-hc analyze` | Run health check analysis | `cribl-hc analyze --deployment prod` |
| `cribl-hc report` | Generate formatted report | `cribl-hc report --format html` |
| `cribl-hc config` | Manage credentials and settings | `cribl-hc config init` |
| `cribl-hc history` | View historical trends | `cribl-hc history show --metric health_score` |
| `cribl-hc fleet` | Analyze multiple deployments | `cribl-hc fleet analyze --deployments prod,staging` |
| `cribl-hc validate` | Test credentials and connectivity | `cribl-hc validate --deployment prod` |

### Global Options

| Option | Description | Example |
|--------|-------------|---------|
| `--quiet` | Suppress output | `cribl-hc analyze --quiet` |
| `--verbose` | Detailed output | `cribl-hc analyze --verbose` |
| `--log-level` | Set log level | `--log-level debug` |
| `--no-color` | Disable colored output | `cribl-hc report --no-color` |
| `--version` | Show version | `cribl-hc --version` |
| `--help` | Show help | `cribl-hc --help` |

## Performance Tips

1. **Run Specific Objectives**: Use `--objectives health` for faster 2-minute checks
2. **Parallel Fleet Analysis**: Deployments analyzed in parallel for fleet operations
3. **Scheduled Analysis**: Run during off-peak hours to minimize impact
4. **Historical Data**: Disable if not needed (`config set history-enabled false`)

## Security Best Practices

1. **Rotate API Tokens**: Rotate Cribl API tokens quarterly
2. **Read-Only Tokens**: ONLY use read-only API tokens (Constitution Principle I)
3. **Secure Storage**: Credentials encrypted at rest in `~/.cribl-hc/credentials.enc`
4. **Audit Logs**: Review audit logs regularly: `cribl-hc logs show`
5. **No Secrets in CI**: Use secrets management (GitHub Secrets, HashiCorp Vault)

## Getting Help

- **Command Help**: `cribl-hc COMMAND --help`
- **Documentation**: https://github.com/cribl/health-check/docs
- **Issues**: https://github.com/cribl/health-check/issues
- **Cribl Docs**: https://docs.cribl.io/stream

## Next Steps

After your first health check:

1. ✅ Review findings and prioritize P0/P1 recommendations
2. ✅ Run configuration validation: `cribl-hc analyze --objectives config`
3. ✅ Set up scheduled analysis via cron or CI/CD
4. ✅ Enable historical tracking to monitor trends
5. ✅ Explore fleet management for multiple environments

**Target Met**: 30 minutes from installation to first actionable report! 🎉
