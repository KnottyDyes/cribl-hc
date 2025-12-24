# Connection Testing

The Cribl Health Check tool includes a comprehensive connection testing feature that allows you to verify connectivity to your Cribl Stream deployment before running full health checks.

## Overview

Connection testing verifies:
- ✓ Cribl leader URL is reachable
- ✓ Authentication token is valid
- ✓ API is responding correctly
- ✓ Cribl version can be detected

## CLI Usage

### Interactive Mode

The simplest way to test your connection is using interactive mode, which will prompt you for credentials:

```bash
cribl-hc test-connection
```

You'll be prompted for:
- **Cribl Leader URL**: Your Cribl leader URL (e.g., `https://cribl.example.com`)
- **Bearer Token**: Your authentication token (input will be hidden)

### Command-Line Arguments

You can also provide credentials directly:

```bash
cribl-hc test-connection \
  --url https://cribl.example.com \
  --token YOUR_BEARER_TOKEN
```

### Custom Timeout

Specify a custom timeout (default is 30 seconds):

```bash
cribl-hc test-connection \
  --url https://cribl.example.com \
  --token YOUR_BEARER_TOKEN \
  --timeout 60
```

## Output Examples

### Successful Connection

```
Testing connection to Cribl API...

╭─ Connection Test: SUCCESS ─────────────────╮
│  Status          ✓ Connected                │
│  Cribl Version   4.5.2                      │
│  Response Time   125ms                      │
│  API URL         https://cribl.example.com/api/v1/version │
╰─────────────────────────────────────────────╯

Connection test passed! You can now run health checks.
```

### Failed Connection - Invalid Token

```
Testing connection to Cribl API...

╭─ Connection Test: FAILED ──────────────────╮
│  Status          ✗ Failed                   │
│  Message         Authentication failed - invalid bearer token │
│  Response Time   42ms                       │
│  API URL         https://cribl.example.com/api/v1/version │
│  Error Details   HTTP 401: Unauthorized     │
╰─────────────────────────────────────────────╯

Connection test failed. Please verify your URL and token.
```

### Failed Connection - Network Error

```
Testing connection to Cribl API...

╭─ Connection Test: FAILED ──────────────────╮
│  Status          ✗ Failed                   │
│  Message         Cannot connect to Cribl API - check URL and network │
│  Response Time   5001ms                     │
│  API URL         https://unreachable.example.com/api/v1/version │
│  Error Details   Connection error: Connection refused │
╰─────────────────────────────────────────────╯

Connection test failed. Please verify your URL and token.
```

## Programmatic Usage

You can also use the connection testing functionality programmatically in your Python code:

```python
from cribl_hc.cli.test_connection import run_connection_test

# Test connection with output displayed
result = run_connection_test(
    url="https://cribl.example.com",
    token="your-bearer-token",
    show_output=True  # Shows rich formatted output
)

if result.success:
    print(f"Connected to Cribl {result.cribl_version}")
    print(f"Response time: {result.response_time_ms}ms")
else:
    print(f"Connection failed: {result.error}")
```

### Using the API Client Directly

For more control, you can use the `CriblAPIClient` directly:

```python
import asyncio
from cribl_hc.core.api_client import CriblAPIClient

async def test_connection():
    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="your-bearer-token",
        timeout=30.0
    ) as client:
        result = await client.test_connection()

        if result.success:
            print(f"✓ Connected to Cribl {result.cribl_version}")
            print(f"  Response time: {result.response_time_ms}ms")
        else:
            print(f"✗ Connection failed: {result.message}")
            if result.error:
                print(f"  Error: {result.error}")

# Run the async function
asyncio.run(test_connection())
```

## Exit Codes

The CLI command uses standard exit codes:
- **0**: Connection test passed
- **1**: Connection test failed

This makes it easy to integrate into scripts and CI/CD pipelines:

```bash
#!/bin/bash

if cribl-hc test-connection --url "$CRIBL_URL" --token "$CRIBL_TOKEN"; then
    echo "Connection OK - proceeding with health check"
    cribl-hc analyze --objectives health
else
    echo "Connection failed - aborting"
    exit 1
fi
```

## Troubleshooting

### Authentication Errors (HTTP 401)

**Problem**: `Authentication failed - invalid bearer token`

**Solutions**:
1. Verify your bearer token is correct
2. Check token hasn't expired
3. Ensure token has appropriate permissions
4. Regenerate token in Cribl UI if needed

### Connection Errors

**Problem**: `Cannot connect to Cribl API - check URL and network`

**Solutions**:
1. Verify the URL is correct (including protocol: `https://`)
2. Check network connectivity to the Cribl leader
3. Verify firewall rules allow outbound connections
4. Test URL in browser or with `curl`

### Timeout Errors

**Problem**: `Connection timeout after 30s`

**Solutions**:
1. Increase timeout with `--timeout 60`
2. Check network latency to Cribl leader
3. Verify Cribl leader is responding (not overloaded)

### Endpoint Not Found (HTTP 404)

**Problem**: `API endpoint not found - verify URL and Cribl version`

**Solutions**:
1. Check that URL points to Cribl leader (not worker node)
2. Verify Cribl version is N, N-1, or N-2 (supported versions)
3. Ensure URL doesn't include API path (use `https://cribl.example.com`, not `https://cribl.example.com/api/v1`)

## Security Best Practices

1. **Never commit bearer tokens** to version control
2. **Use environment variables** for tokens in scripts:
   ```bash
   export CRIBL_TOKEN="your-token"
   cribl-hc test-connection --url https://cribl.example.com --token "$CRIBL_TOKEN"
   ```
3. **Rotate tokens regularly** in production environments
4. **Use dedicated tokens** for health checking with minimal required permissions

## Next Steps

Once your connection test passes:

1. **Run a quick health check**:
   ```bash
   cribl-hc analyze --objectives health
   ```

2. **Configure persistent credentials** (optional):
   ```bash
   cribl-hc config add-deployment \
     --id prod \
     --url https://cribl.example.com \
     --token YOUR_TOKEN
   ```

3. **Schedule regular health checks**:
   ```bash
   # Add to crontab for daily health checks
   0 2 * * * cribl-hc analyze --deployment prod --objectives health,config
   ```
