# Debug Mode Usage Guide

This guide explains how to use the debug and verbose modes in cribl-hc for troubleshooting and testing.

## Quick Reference

```bash
# Normal mode (minimal output)
cribl-hc analyze run --url https://cribl.example.com --token YOUR_TOKEN

# Verbose mode (INFO level logging)
cribl-hc analyze run -u https://cribl.example.com -t YOUR_TOKEN --verbose

# Debug mode (DEBUG level logging with detailed traces)
cribl-hc analyze run -u https://cribl.example.com -t YOUR_TOKEN --debug
```

## Logging Levels

### Normal Mode (Default)
- Minimal console output
- Only shows critical information and results
- No detailed logging to console
- **Use for**: Production runs, clean reports

### Verbose Mode (`--verbose` or `-v`)
- INFO level logging enabled
- Shows connection status, progress updates, and major operations
- Structured logs with key metrics
- **Use for**: Initial testing, understanding workflow

Example output:
```
ℹ️  Verbose mode enabled
Cribl Stream Health Check
Target: https://cribl.example.com
Deployment: production

Testing connection...
✓ Connected successfully (152ms)
Cribl version: 4.0.0

Running analysis...
[Progress bar with detailed status]

Analysis complete
```

### Debug Mode (`--debug`)
- DEBUG level logging enabled
- Extremely detailed output including:
  - All API requests and responses
  - Internal state transitions
  - Progress tracking details
  - File I/O operations
  - Rate limiting decisions
- **Use for**: Troubleshooting issues, development, understanding failures

Example output:
```
🐛 Debug mode enabled - detailed logging active
Cribl Stream Health Check
Target: https://cribl.example.com
Deployment: production

Debug: Max API calls: 100
Debug: Objectives: ['health']

Testing connection...
[timestamp] [DEBUG] testing_connection url=https://cribl.example.com
✓ Connected successfully (152ms)
Cribl version: 4.0.0
[timestamp] [DEBUG] connection_successful response_time_ms=152.0 cribl_version=4.0.0

[timestamp] [DEBUG] initializing_orchestrator max_api_calls=100 continue_on_error=True

Running analysis...
[timestamp] [DEBUG] analysis_progress current_objective=health completed_objectives=0 total_objectives=1 percentage=0.0
[timestamp] [DEBUG] api_request method=GET endpoint=/api/v1/system/workers
[timestamp] [DEBUG] api_response status_code=200 response_time_ms=145.3
[timestamp] [DEBUG] analysis_progress current_objective=health completed_objectives=1 total_objectives=1 percentage=100.0

[timestamp] [DEBUG] analysis_complete deployment_id=production status=completed findings_count=3 recommendations_count=2 api_calls_used=15 duration_seconds=5.2
```

## Common Testing Scenarios

### 1. Test Connection Only
```bash
cribl-hc test-connection run --url https://cribl.example.com --token YOUR_TOKEN --verbose
```

### 2. Test with Invalid Credentials (Debug)
```bash
# Use debug mode to see exactly where authentication fails
cribl-hc analyze run -u https://cribl.example.com -t INVALID_TOKEN --debug
```

Expected debug output:
```
🐛 Debug mode enabled - detailed logging active
...
Testing connection...
[DEBUG] testing_connection url=https://cribl.example.com
[DEBUG] api_request method=GET endpoint=/api/v1/health
[ERROR] connection_failed error="401 Unauthorized" url=https://cribl.example.com
✗ Connection failed: 401 Unauthorized
```

### 3. Test API Call Budgeting (Debug)
```bash
# Set low API limit to test budget enforcement
cribl-hc analyze run -u URL -t TOKEN --max-api-calls 10 --debug
```

Watch for debug logs showing:
```
[DEBUG] rate_limiter_check calls_used=9 calls_remaining=1
[WARN] api_budget_approaching calls_used=10 max_calls=10
```

### 4. Test Specific Objectives (Verbose)
```bash
cribl-hc analyze run -u URL -t TOKEN -o health -o config --verbose
```

### 5. Generate Reports with Debug Info
```bash
# Save both JSON and Markdown with debug logging
cribl-hc analyze run -u URL -t TOKEN --output report.json --markdown --debug
```

Debug output will show:
```
[DEBUG] saving_json_report output_file=/path/to/report.json
✓ JSON report saved to: /path/to/report.json
[DEBUG] saving_markdown_report output_file=/path/to/report.md
✓ Markdown report saved to: /path/to/report.md
```

## Troubleshooting Guide

### Issue: No output at all
**Solution**: Enable verbose mode to see what's happening
```bash
cribl-hc analyze run -u URL -t TOKEN --verbose
```

### Issue: Connection fails with no details
**Solution**: Enable debug mode to see full HTTP traces
```bash
cribl-hc analyze run -u URL -t TOKEN --debug
```

Look for:
- SSL/TLS errors
- Network timeout errors
- DNS resolution issues
- HTTP error codes (401, 403, 404, 500)

### Issue: Analysis hangs or runs slowly
**Solution**: Use debug mode to see where it's stuck
```bash
cribl-hc analyze run -u URL -t TOKEN --debug
```

Look for:
- Which objective is currently running
- API call patterns
- Rate limiter backoff messages

### Issue: Unexpected results or missing data
**Solution**: Verbose mode shows what was analyzed
```bash
cribl-hc analyze run -u URL -t TOKEN --verbose
```

Check:
- Which objectives were actually run
- API call count (should be < 100)
- Findings and recommendations count

## Log Output Format

Debug/verbose logs use structured logging with key-value pairs:

```
[timestamp] [LEVEL] event_name key1=value1 key2=value2
```

Example:
```
[2025-12-11 14:32:15] [DEBUG] api_request method=GET endpoint=/api/v1/system/workers
[2025-12-11 14:32:15] [DEBUG] api_response status_code=200 response_time_ms=145.3
[2025-12-11 14:32:15] [INFO] displaying_results findings_count=3 recommendations_count=2
```

## Saving Debug Logs to File

To save debug output to a file for sharing:

```bash
# Redirect both stdout and stderr
cribl-hc analyze run -u URL -t TOKEN --debug 2>&1 | tee debug.log
```

This creates a `debug.log` file with all debug output while still showing it on screen.

## Environment Variables

You can also set credentials via environment variables for easier testing:

```bash
export CRIBL_URL="https://cribl.example.com"
export CRIBL_TOKEN="your-token-here"

# Now run with just debug flag
cribl-hc analyze run --debug
```

## Testing Checklist

When reporting issues, please run with `--debug` and provide:

- [ ] Full debug output (or attach debug.log file)
- [ ] Cribl Stream version (shown in connection test)
- [ ] Command used (mask sensitive tokens)
- [ ] Expected vs actual behavior
- [ ] Any error messages or stack traces

## Performance Impact

- **Normal mode**: Fastest, minimal overhead
- **Verbose mode**: ~5% overhead from INFO logging
- **Debug mode**: ~15-20% overhead from detailed logging

Debug mode is safe to use but may slow down analysis slightly. Use normal mode for production runs.

## Next Steps

After successful testing with debug mode:

1. Review the logs to understand the analysis flow
2. Check API call usage (should be well under 100)
3. Verify findings and recommendations match expectations
4. Test with production credentials (start with verbose mode)
5. Run full analysis and generate reports

## Getting Help

If you encounter issues:

1. Run with `--debug` flag
2. Save complete debug output: `cribl-hc analyze run --debug 2>&1 > debug.log`
3. Share the debug.log file along with your question
4. Include Cribl version and deployment details

The debug output provides all the context needed to diagnose issues.
