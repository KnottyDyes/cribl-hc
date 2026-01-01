# Performance Validation Guide

## Performance Targets

The cribl-hc tool has two primary performance targets defined in the Constitution:

1. **Duration**: Analysis completes in < 5 minutes (300 seconds)
2. **API Calls**: Uses < 100 API calls per analysis run

## Automatic Performance Monitoring

The tool automatically monitors and reports performance metrics during every run.

### Normal Output
Performance warnings are displayed if targets are exceeded:

```bash
cribl-hc analyze run -u URL -t TOKEN

# If duration exceeds 5 minutes:
⚠ Performance Warning: Analysis took 320.5s (target: <300s)

# If API calls exceed 100:
⚠ Performance Warning: Used 105 API calls (budget: 100)
```

### Verbose Output
In verbose or debug mode, performance metrics are shown even when targets are met:

```bash
cribl-hc analyze run -u URL -t TOKEN --verbose

# Output:
ℹ Performance: Analysis took 45.2s (15% of 5-minute target)
ℹ Performance: Used 23/100 API calls (23% of budget)
```

## Manual Performance Validation

### Option 1: Using the Validation Script

Run analysis and save JSON report, then validate:

```bash
# Run analysis and save results
cribl-hc analyze run -u URL -t TOKEN --output report.json

# Validate performance
python3 scripts/validate_performance.py report.json
```

**Expected Output**:
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

✓ PASS  API Call Efficiency
   Target:  N/A
   Actual:  0.51 calls/second
   Margin:  None

============================================================
OVERALL: ✓ ALL PERFORMANCE TARGETS MET
============================================================
```

### Option 2: Using Debug Mode

```bash
cribl-hc analyze run -u URL -t TOKEN --debug
```

Look for the `performance_metrics` log entry at the end:

```
[INFO] performance_metrics duration_seconds=45.2 duration_target=300.0 duration_ok=True api_calls_used=23 api_call_target=100 api_calls_ok=True
```

## Performance Testing Scenarios

### 1. Minimal Analysis (Quick Test)
```bash
# Test with single objective
cribl-hc analyze run -u URL -t TOKEN -o health --verbose
```

**Expected Results**:
- Duration: 5-30 seconds
- API calls: 5-15 calls
- Status: ✓ Well under targets

### 2. Full Analysis (All Objectives)
```bash
# Test with all objectives
cribl-hc analyze run -u URL -t TOKEN --verbose
```

**Expected Results**:
- Duration: 30-120 seconds (depending on deployment size)
- API calls: 20-60 calls
- Status: ✓ Within targets

### 3. Large Deployment Test
```bash
# Test with large deployment (many workers)
cribl-hc analyze run -u LARGE_URL -t TOKEN --verbose --output large_deployment.json
```

**Expected Results**:
- Duration: 60-180 seconds
- API calls: 40-80 calls
- Status: ✓ Should still be within targets

### 4. Stress Test (Max API Calls)
```bash
# Artificially lower API budget to test enforcement
cribl-hc analyze run -u URL -t TOKEN --max-api-calls 20 --debug
```

**Expected Behavior**:
- Analysis stops when API budget is reached
- Partial completion status
- Clear warning about API budget exceeded

## Performance Metrics Explained

### Duration
- **Measured from**: Analysis start to completion
- **Includes**: Connection testing, all analyzer runs, result aggregation
- **Excludes**: Report file I/O
- **Target**: < 300 seconds (5 minutes)
- **Typical**: 30-120 seconds for most deployments

### API Call Count
- **Measured**: Total HTTP requests to Cribl API
- **Tracked by**: RateLimiter with automatic counting
- **Enforced**: Hard limit at max_api_calls (default: 100)
- **Target**: < 100 calls per analysis
- **Typical**: 20-60 calls depending on objectives

### API Call Efficiency
- **Calculated**: api_calls_used / duration_seconds
- **Unit**: calls per second
- **Typical**: 0.3-1.5 calls/second
- **Informational**: Not a hard target, but useful for optimization

## Troubleshooting Performance Issues

### Issue: Duration Exceeds 5 Minutes

**Possible Causes**:
1. Large number of workers (50+)
2. Slow network connection to Cribl API
3. Cribl API responding slowly
4. Multiple objectives being analyzed

**Solutions**:
```bash
# Test with fewer objectives
cribl-hc analyze run -u URL -t TOKEN -o health --debug

# Check API response times in debug output
# Look for: api_response response_time_ms=XXXX
```

**Diagnosis**:
- If individual API calls > 2000ms: Network or Cribl API issue
- If total API calls > 60: May need to optimize analyzers
- If many retries: Check Cribl API health

### Issue: API Calls Exceed 100

**Possible Causes**:
1. Inefficient analyzer implementation
2. Large number of workers requiring pagination
3. Retries due to failed API calls

**Solutions**:
```bash
# Enable debug mode to see all API calls
cribl-hc analyze run -u URL -t TOKEN --debug 2>&1 | grep "api_request"

# Count API calls:
cribl-hc analyze run -u URL -t TOKEN --debug 2>&1 | grep -c "api_request"
```

**Diagnosis**:
- Count calls per analyzer
- Identify which endpoints are called most frequently
- Check for unnecessary duplicate calls

## Performance Benchmarks

### Small Deployment (< 10 workers)
- **Duration**: 10-30 seconds
- **API Calls**: 10-25 calls
- **Typical Findings**: 0-5
- **Typical Recommendations**: 0-3

### Medium Deployment (10-50 workers)
- **Duration**: 30-90 seconds
- **API Calls**: 25-50 calls
- **Typical Findings**: 5-15
- **Typical Recommendations**: 3-10

### Large Deployment (50+ workers)
- **Duration**: 90-180 seconds
- **API Calls**: 50-80 calls
- **Typical Findings**: 15-30
- **Typical Recommendations**: 10-20

## CI/CD Integration

### Automated Performance Testing

```bash
#!/bin/bash
# performance_test.sh

# Run analysis
cribl-hc analyze run \
  --url "$CRIBL_URL" \
  --token "$CRIBL_TOKEN" \
  --output test_report.json

# Validate performance
python3 scripts/validate_performance.py test_report.json

# Exit code 0 if passed, 1 if failed
exit $?
```

### GitHub Actions Example

```yaml
name: Performance Test

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -e .

      - name: Run performance test
        env:
          CRIBL_URL: ${{ secrets.CRIBL_URL }}
          CRIBL_TOKEN: ${{ secrets.CRIBL_TOKEN }}
        run: |
          cribl-hc analyze run --output report.json
          python3 scripts/validate_performance.py report.json
```

## Performance Optimization Tips

### For Faster Analysis:
1. Analyze specific objectives only: `--objective health`
2. Use local/nearby Cribl instances when possible
3. Ensure stable network connection
4. Run during off-peak hours for faster API responses

### For Reducing API Calls:
1. Implement response caching (future enhancement)
2. Batch API requests where possible (future enhancement)
3. Limit objectives to what you actually need
4. Use appropriate max-api-calls budget

## Reporting Performance Issues

When reporting performance issues, include:

1. **Command used**: Full cribl-hc command with flags
2. **Debug output**: Run with `--debug 2>&1 | tee debug.log`
3. **Deployment size**: Number of workers, pipelines, etc.
4. **Network details**: Geographic location, network latency
5. **Validation report**: Output from `validate_performance.py`
6. **Expected vs Actual**: What you expected vs what you got

## Future Performance Enhancements

Planned optimizations to improve performance:

1. **Parallel Analyzer Execution**: Run multiple analyzers concurrently
2. **Response Caching**: Cache frequently accessed data
3. **Batch API Requests**: Combine multiple requests where possible
4. **Progressive Analysis**: Stream results as they become available
5. **Smart Pagination**: Optimize pagination for large datasets

## Performance SLA

**Current Targets** (as defined in Constitution):
- Duration: < 5 minutes (300 seconds)
- API Calls: < 100 calls

**Typical Performance** (observed in testing):
- Duration: 30-120 seconds (10-40% of target)
- API Calls: 20-60 calls (20-60% of budget)

**Performance Guarantees**:
- ✓ Analysis will never exceed 100 API calls (hard limit enforced)
- ✓ Analysis will warn if duration exceeds 5 minutes
- ✓ Performance metrics logged for every run
- ✓ Validation tools provided for automated testing
