# Quick Start Testing Guide

## Your First Test in 5 Minutes

This guide will help you test the cribl-hc tool with your Cribl Stream instance.

## Prerequisites

- Python 3.9+
- Access to a Cribl Stream instance
- API token for authentication

## Step 1: Install the Package

```bash
cd /Users/sarmstrong/Projects/cribl-hc
pip3 install -e .
```

**Expected output**:
```
Successfully installed cribl-hc
```

## Step 2: Test the Installation

```bash
cribl-hc version
```

**Expected output**:
```
cribl-hc version 0.1.0
```

## Step 3: Get Your Cribl API Token

1. Log into your Cribl Stream UI
2. Go to Settings → API Tokens
3. Create a new token or copy an existing one
4. Save it securely (you'll need it for testing)

## Step 4: Test Connection (CRITICAL FIRST STEP!)

**Important**: This is the most important test. It validates that:
- Your URL is correct
- Your token works
- The Cribl API is reachable
- Network connectivity is good

```bash
cribl-hc test-connection run \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN \
  --debug
```

**Expected output if successful**:
```
🐛 Debug mode enabled - detailed logging active

Testing Connection to Cribl Stream
Target: https://your-cribl-instance.com

[DEBUG] testing_connection url=https://your-cribl-instance.com
[DEBUG] api_request method=GET endpoint=/api/v1/health
[DEBUG] api_response status_code=200 response_time_ms=152.3

✓ Connection successful
   Response time: 152ms
   Cribl version: 4.0.0
   API endpoint: https://your-cribl-instance.com/api/v1/health

[DEBUG] connection_details response_time_ms=152.3 cribl_version=4.0.0
```

**If connection fails**, you'll see detailed error messages:

### Common Errors and Solutions

#### Error: "Connection refused"
```
✗ Connection failed: Connection refused
```
**Solution**: Check that the URL is correct and the Cribl instance is running

#### Error: "401 Unauthorized"
```
✗ Connection failed: 401 Unauthorized
```
**Solution**: Check that your API token is valid and has the right permissions

#### Error: "SSL Certificate verification failed"
```
✗ Connection failed: SSL verification error
```
**Solution**: Your Cribl instance may be using a self-signed certificate. This needs additional configuration.

#### Error: "Name or service not known"
```
✗ Connection failed: DNS lookup failed
```
**Solution**: Check the URL spelling and ensure the domain is reachable

## Step 5: Run Your First Analysis (Verbose Mode)

Once connection test passes, run a full analysis with verbose output:

```bash
cribl-hc analyze run \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN \
  --verbose
```

**Expected output**:
```
ℹ️  Verbose mode enabled

Cribl Stream Health Check
Target: https://your-cribl-instance.com
Deployment: default

Testing connection...
[INFO] testing_connection url=https://your-cribl-instance.com
✓ Connected successfully (152ms)
Cribl version: 4.0.0

[INFO] initializing_orchestrator max_api_calls=100 continue_on_error=True
Running analysis...
[Progress bar showing completion]
████████████████████ 100%

[INFO] displaying_results findings_count=3 recommendations_count=2

Analysis Summary
Status: COMPLETED
Objectives Analyzed: health
Total Findings: 3
  Critical: 0
  High: 1
  Medium: 2
Total Recommendations: 2
API Calls Used: 23/100

HEALTH Findings
...

Recommendations
...

Analysis completed successfully
```

## Step 6: Run with Debug Mode (If You See Issues)

If you encounter any issues or want to see exactly what's happening:

```bash
cribl-hc analyze run \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN \
  --debug \
  2>&1 | tee debug.log
```

This will:
- Show extremely detailed output
- Save everything to `debug.log` file
- Help diagnose any issues

## Step 7: Generate Reports

```bash
cribl-hc analyze run \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN \
  --output my_first_report.json \
  --markdown
```

This creates:
- `my_first_report.json` - Machine-readable JSON
- `my_first_report.md` - Human-readable Markdown

## Step 8: Validate Performance

```bash
python3 scripts/validate_performance.py my_first_report.json
```

**Expected output**:
```
============================================================
PERFORMANCE VALIDATION REPORT
============================================================

✓ PASS  Analysis Duration
   Target:  < 300.0s (5 minutes)
   Actual:  45.23s
   Margin:  254.77 (under budget)

✓ PASS  API Call Budget
   Target:  < 100 calls
   Actual:  23 calls
   Margin:  77 (under budget)

============================================================
OVERALL: ✓ ALL PERFORMANCE TARGETS MET
============================================================
```

## Providing Feedback

### What to Include

When providing feedback, please run this command and send me the output:

```bash
cribl-hc analyze run \
  --url YOUR_URL \
  --token YOUR_TOKEN \
  --debug \
  --output feedback_report.json \
  --markdown \
  2>&1 | tee feedback_debug.log
```

Then share:
1. `feedback_debug.log` - Full debug output
2. `feedback_report.json` - Analysis results
3. `feedback_report.md` - Readable report
4. Your observations:
   - What worked well
   - What didn't work
   - What was confusing
   - Any errors or unexpected behavior

### Masking Sensitive Data

Before sharing debug logs, you may want to mask:
- API tokens (replace with `<REDACTED>`)
- Internal URLs (replace with `https://cribl.example.com`)
- Worker hostnames (replace with `worker-XX`)

## Quick Troubleshooting

### "Module not found" errors
```bash
# Reinstall in development mode
pip3 install -e .
```

### "Command not found: cribl-hc"
```bash
# Check installation
pip3 show cribl-hc

# May need to add to PATH or use full path
python3 -m cribl_hc.cli.main --help
```

### Analysis hangs or is very slow
```bash
# Try with debug mode to see where it's stuck
cribl-hc analyze run -u URL -t TOKEN --debug

# Look for slow API responses:
# grep "response_time_ms" in debug output
```

### Unexpected results
```bash
# Run with debug to see what data is being analyzed
cribl-hc analyze run -u URL -t TOKEN --debug

# Check the JSON report for raw data
cat my_first_report.json | jq .
```

## Advanced: Using Environment Variables

To avoid typing URL and token every time:

```bash
# Set environment variables
export CRIBL_URL="https://your-cribl-instance.com"
export CRIBL_TOKEN="your-api-token-here"

# Now you can run without flags
cribl-hc analyze run --verbose

# Or store credentials
cribl-hc config set prod --url $CRIBL_URL --token $CRIBL_TOKEN

# Then use stored credentials (not yet implemented)
```

## Expected Timeline

- **Step 1-2** (Install): 1 minute
- **Step 3** (Get token): 2 minutes
- **Step 4** (Test connection): 30 seconds
- **Step 5** (First analysis): 30-120 seconds
- **Step 6-8** (Debug/reports): 2-3 minutes

**Total**: 5-10 minutes for complete testing

## Success Indicators

You'll know it's working if you see:

✅ Connection test passes
✅ Analysis completes without errors
✅ Findings are generated (assuming your deployment has issues)
✅ Recommendations are provided
✅ Performance targets met (< 5 min, < 100 API calls)
✅ Reports are generated successfully

## Next Steps After Testing

1. Review the findings - do they make sense?
2. Check recommendations - are they actionable?
3. Validate the health score - does it match your assessment?
4. Test with different deployments/environments
5. Share feedback for improvements

## Getting Help

If you encounter issues:

1. Check this guide first
2. Review `DEBUG_MODE_USAGE.md` for detailed debugging
3. Run with `--debug` and save the output
4. Share the debug log along with:
   - What you expected to happen
   - What actually happened
   - Your Cribl version
   - Deployment details (number of workers, etc.)

---

**Ready to start?** Begin with Step 1 and work your way through. The connection test (Step 4) is the most critical - everything else depends on that working!
