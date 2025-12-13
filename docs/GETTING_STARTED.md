# Getting Started with cribl-hc

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/cribl-hc.git
cd cribl-hc

# Install with pip (creates cribl-hc command)
pip install -e .

# Verify installation
cribl-hc version
```

## Quick Start

### 1. Set Your Credentials

```bash
# For Cribl Cloud (format: https://<workspace>-<org-name>.cribl.cloud)
# Where <workspace> is your workspace ID (e.g., "main", "dev", "prod")
export CRIBL_URL=https://main-myorg.cribl.cloud
export CRIBL_TOKEN=your_bearer_token

# Or for self-hosted Cribl Stream
export CRIBL_URL=https://cribl.example.com
export CRIBL_TOKEN=your_bearer_token
```

### 2. Run Your First Health Check

```bash
# Run all analyzers
cribl-hc analyze run

# Or run a specific analyzer
cribl-hc analyze run --objective health
```

### 3. View the Results

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

## Common Commands

```bash
# Show version
cribl-hc version

# List available analyzers
cribl-hc list
cribl-hc list --verbose

# Get help
cribl-hc --help
cribl-hc analyze --help
cribl-hc analyze run --help

# Run specific analyzers
cribl-hc analyze run --objective health
cribl-hc analyze run --objective config
cribl-hc analyze run --objective resource

# Run multiple specific analyzers
cribl-hc analyze run -o health -o config

# Save results to JSON file
cribl-hc analyze run --output report.json

# Generate markdown report
cribl-hc analyze run --markdown

# Verbose mode (show API calls)
cribl-hc analyze run --verbose

# Debug mode (detailed logging)
cribl-hc analyze run --debug
```

## Available Analyzers

| Analyzer | Purpose | API Calls | Permissions |
|----------|---------|-----------|-------------|
| `health` | Worker health & system status | 3 | read:workers, read:system, read:metrics |
| `config` | Configuration validation | 5 | read:pipelines, read:routes, read:inputs, read:outputs |
| `resource` | CPU/memory/disk capacity planning | 3 | read:workers, read:metrics, read:system |

## Next Steps

- **[CLI Guide](./CLI_GUIDE.md)** - Comprehensive command reference
- **[Quick Reference](./CLI_QUICK_REFERENCE.md)** - Cheat sheet
- **[Cribl Cloud Notes](./cribl_cloud_api_notes.md)** - API differences

## Examples

### Example 1: Daily Health Check

```bash
#!/bin/bash
# daily-health-check.sh

cribl-hc analyze run --objective health \
    --output ~/reports/health-$(date +%Y%m%d).json
```

### Example 2: Weekly Full Analysis

```bash
#!/bin/bash
# weekly-analysis.sh

cribl-hc analyze run \
    --output ~/reports/weekly-$(date +%Y%m%d).json \
    --markdown \
    --verbose
```

### Example 3: CI/CD Integration

```bash
#!/bin/bash
# ci-health-check.sh

# Run health check
cribl-hc analyze run --objective config --output ci-report.json

# Check exit code
if [ $? -ne 0 ]; then
    echo "❌ Health check failed"
    exit 1
else
    echo "✅ Health check passed"
fi
```

## Troubleshooting

### Command Not Found: `cribl-hc`

If you get `command not found`, you need to install the package:

```bash
pip install -e .
```

The installation creates the `cribl-hc` command entry point.

### Connection Failed

```bash
# Verify your credentials
echo $CRIBL_URL
echo $CRIBL_TOKEN

# Test connection explicitly
cribl-hc test-connection
```

### Token Expired (401 Unauthorized)

Generate a new bearer token from your Cribl deployment and update:

```bash
export CRIBL_TOKEN=new_token_here
```

## Support

- Issues: https://github.com/your-org/cribl-hc/issues
- Documentation: [docs/](.)
