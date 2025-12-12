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

## Step 4: Store Your Credentials (RECOMMENDED!)

Instead of typing your URL and token every time, save them securely:

```bash
cribl-hc config set prod \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN
```

This encrypts and stores your credentials. Now you can use `--deployment prod` (or `-p prod`) instead of typing credentials!

**Alternative**: You can also use environment variables:
```bash
export CRIBL_URL=https://your-cribl-instance.com
export CRIBL_TOKEN=YOUR_API_TOKEN
```

Or provide credentials with each command using `--url` and `--token` flags.

See [CREDENTIAL_MANAGEMENT.md](CREDENTIAL_MANAGEMENT.md) for all options.

## Step 5: Test Connection (CRITICAL FIRST STEP!)

**Important**: This is the most important test. It validates that:
- Your URL is correct
- Your token works
- The Cribl API is reachable
- Network connectivity is good

**Using stored credentials** (recommended):
```bash
cribl-hc test-connection test --deployment prod
# or use the short form:
cribl-hc test-connection test -p prod
```

**Using environment variables**:
```bash
export CRIBL_URL=https://your-cribl-instance.com
export CRIBL_TOKEN=YOUR_API_TOKEN
cribl-hc test-connection test
```

**Or provide credentials directly**:
```bash
cribl-hc test-connection test \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN
# short form: -u and -t
cribl-hc test-connection test -u https://your-cribl-instance.com -t YOUR_API_TOKEN
```

**Expected output if successful**:
```
Using stored credentials for: prod
URL: https://your-cribl-instance.com

Testing connection to Cribl API...

✓ Connection Test Results

Status: SUCCESS
Response Time: 152ms
Cribl Version: 4.15.0
API Endpoint: https://your-cribl-instance.com/api/v1/health

Connection test passed successfully
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

## Step 6: Run Your First Analysis

Once connection test passes, run a full analysis:

**Using stored credentials** (recommended):
```bash
cribl-hc analyze run --deployment prod
# or use the short form:
cribl-hc analyze run -p prod
```

**Using environment variables**:
```bash
export CRIBL_URL=https://your-cribl-instance.com
export CRIBL_TOKEN=YOUR_API_TOKEN
cribl-hc analyze run
```

**Or provide credentials directly**:
```bash
cribl-hc analyze run \
  --url https://your-cribl-instance.com \
  --token YOUR_API_TOKEN
# short form:
cribl-hc analyze run -u https://your-cribl-instance.com -t YOUR_API_TOKEN
```

**Add verbose mode to see more details**:
```bash
cribl-hc analyze run -p prod --verbose
# or use short form:
cribl-hc analyze run -p prod -v
```

**Expected output**:
```
Using stored credentials for: prod
URL: https://your-cribl-instance.com


Cribl Stream Health Check
Target: https://your-cribl-instance.com
Deployment: default

Testing connection...
✓ Connected successfully (152ms)
Cribl version: 4.15.0

Running analysis...
  Analysis complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

         Analysis Summary
 Status                 COMPLETED
 Objectives Analyzed    health
 Total Findings         3
   Critical             0
   High                 1
   Medium               2
 Total Recommendations  2
 API Calls Used         4/100
 Duration               0.15s

╭──────────────────────────────────────────────────────────────────────────────╮
│ HEALTH Findings                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

● HIGH
System Health: Healthy
├── All 3 workers are operating normally with a health score of 100.0/100
├── Components: overall_health
└── Impact: Overall system health: 100.0/100

╭──────────────────────────────────────────────────────────────────────────────╮
│ Recommendations                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

▶ P2 PRIORITY

1. Optimize Worker Configuration
   [... details ...]

Analysis completed successfully
```

## Step 7: Run with Debug Mode (If You See Issues)

If you encounter any issues or want to see exactly what's happening:

```bash
cribl-hc analyze run --deployment prod --debug 2>&1 | tee debug.log
# or short form:
cribl-hc analyze run -p prod -d 2>&1 | tee debug.log
```

This will:
- Show extremely detailed output (including all API calls and responses)
- Save everything to `debug.log` file
- Help diagnose any issues

**Debug mode vs Verbose mode**:
- `--verbose` / `-v`: Shows informational messages (recommended for normal use)
- `--debug` / `-d`: Shows everything including detailed traces (for troubleshooting)

## Step 8: Generate Reports

```bash
cribl-hc analyze run \
  --deployment prod \
  --output my_first_report.json \
  --markdown

# or short form:
cribl-hc analyze run -p prod -o my_first_report.json -m
```

This creates:
- `my_first_report.json` - Machine-readable JSON
- `my_first_report.md` - Human-readable Markdown (when using `--markdown`)

**Report options**:
- `--output FILE` / `-o FILE`: Save JSON report to file
- `--markdown` / `-m`: Also generate Markdown report (FILE.md)

## Step 9: Validate Performance

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
  --deployment prod \
  --debug \
  --output feedback_report.json \
  --markdown \
  2>&1 | tee feedback_debug.log

# or short form:
cribl-hc analyze run -p prod -d -o feedback_report.json -m 2>&1 | tee feedback_debug.log

# or if using URL/token directly:
cribl-hc analyze run -u YOUR_URL -t YOUR_TOKEN -d -o feedback_report.json -m 2>&1 | tee feedback_debug.log
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
cribl-hc analyze run -p prod --debug
# or: cribl-hc analyze run -u URL -t TOKEN --debug

# Look for slow API responses in debug output:
# grep "api_response" debug.log
```

### Unexpected results
```bash
# Run with debug to see what data is being analyzed
cribl-hc analyze run -p prod --debug -o report.json

# Check the JSON report for raw data
cat report.json | jq .
```

## Managing Multiple Environments

You can store credentials for multiple Cribl instances:

```bash
# Store production credentials
cribl-hc config set prod --url https://prod.cribl.com --token PROD_TOKEN

# Store development credentials
cribl-hc config set dev --url https://dev.cribl.com --token DEV_TOKEN

# Store local credentials
cribl-hc config set local --url http://localhost:9000 --token LOCAL_TOKEN

# List all stored deployments
cribl-hc config list

# Now easily switch between them
cribl-hc analyze run -p prod -o prod-report.json
cribl-hc analyze run -p dev -o dev-report.json
cribl-hc analyze run -p local --verbose
```

For more details, see [CREDENTIAL_MANAGEMENT.md](CREDENTIAL_MANAGEMENT.md)

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
