# cribl-hc CLI Quick Reference

## Installation

```bash
pip install -e .
```

## Common Commands

```bash
# Show version
cribl-hc version

# Run all analyzers
cribl-hc analyze run

# Run specific analyzer
cribl-hc analyze run -o health
cribl-hc analyze run -o config
cribl-hc analyze run -o resource

# Save to file
cribl-hc analyze run --output report.json

# With verbose output
cribl-hc analyze run -v

# Test connection
cribl-hc test-connection
```

## Credentials

```bash
# Environment variables
export CRIBL_URL=https://your-cribl.cloud
export CRIBL_TOKEN=your_bearer_token

# Command line
cribl-hc analyze run --url https://cribl.cloud --token TOKEN

# Stored credentials
cribl-hc config set prod --url URL --token TOKEN
cribl-hc analyze run --deployment prod
```

## Analyzers

| Analyzer | Purpose | API Calls |
|----------|---------|-----------|
| `health` | Worker health & system status | 3 |
| `config` | Configuration validation | 5 |
| `resource` | CPU/memory/disk capacity | 3 |

## Output Formats

```bash
# Terminal (default)
cribl-hc analyze run

# JSON file
cribl-hc analyze run --output report.json

# Markdown report
cribl-hc analyze run --markdown
```

## Options Cheat Sheet

```
-u, --url          Cribl API URL
-t, --token        Bearer token
-o, --objective    Analyzer to run (repeatable)
-f, --output       Save JSON to file
-m, --markdown     Generate markdown report
-v, --verbose      Verbose output
--debug            Debug mode
-p, --deployment   Use stored credentials
```

## Examples

```bash
# Basic
cribl-hc analyze run -u https://cribl.cloud -t TOKEN

# Specific analyzers
cribl-hc analyze run -o health -o config

# Save results
cribl-hc analyze run --output ~/reports/$(date +%Y%m%d).json

# CI/CD integration
cribl-hc analyze run -v --output ci-report.json || exit 1
```

## Exit Codes

- `0` - Success
- `1` - Error (connection/args)
- `2` - Critical findings
- `3` - API budget exceeded

## Get Help

```bash
cribl-hc --help
cribl-hc analyze --help
cribl-hc analyze run --help
```

## Documentation

- Full CLI Guide: [CLI_GUIDE.md](./CLI_GUIDE.md)
- Cribl Cloud Notes: [cribl_cloud_api_notes.md](./cribl_cloud_api_notes.md)
