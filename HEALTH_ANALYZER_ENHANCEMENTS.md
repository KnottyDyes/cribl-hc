# Health Analyzer Enhancements

## Overview
Expanded the health analyzer with additional checks to provide more comprehensive monitoring of Cribl Stream deployments.

## New Health Checks Added

### 1. Leader Health Monitoring
**Endpoint**: `/api/v1/health`

Monitors the health status of the leader node:
- Checks if leader reports "healthy" status
- Tracks leader role (primary/secondary)
- Generates **CRITICAL** finding if leader is unhealthy
- Adds leader status to analysis metadata

**Impact**: Leader issues can impact entire deployment coordination

**Example Finding**:
```
● CRITICAL
Leader Node Unhealthy
├── Leader node reports status 'degraded' (role: primary)
├── Components: leader
└── Impact: Leader issues can impact entire deployment coordination
```

### 2. Single Worker Deployment Detection
**Check**: Worker count validation

Detects deployments with only one worker node:
- Identifies lack of redundancy
- Generates **MEDIUM** severity finding
- Provides recommendations for adding workers

**Impact**: Single point of failure - if worker fails, all data processing stops

**Example Finding**:
```
● MEDIUM
Single Worker Deployment
├── Deployment has only 1 worker node, providing no redundancy or high availability
├── Components: architecture
└── Impact: Single point of failure - if worker fails, all data processing stops
```

**Remediation**:
- Add at least one additional worker for redundancy
- Configure worker group with minimum 2 workers
- Implement load balancing across multiple workers

### 3. Worker Process Count Validation
**Check**: Worker processes vs CPU count

Validates that workers are properly utilizing available CPU resources:
- Compares `workerProcesses` to available CPUs
- Recommended: `workerProcesses = CPUs - 1` (minimum 1)
- Generates **LOW** severity finding for suboptimal configurations
- Only flags healthy workers (avoids noise)

**Impact**: Underutilizing available CPU resources

**Example Finding**:
```
● LOW
Suboptimal Worker Process Count: worker-01
├── Worker worker-01 has 3 process(es) but has 8 CPUs available. Recommended: 7 processes
├── Components: worker-id-123
└── Impact: Underutilizing available CPU resources - could process 7x workload
```

**Remediation**:
- Increase worker processes to recommended count in worker group settings
- Monitor CPU utilization after change
- Adjust based on actual workload patterns

### 4. Memory Availability Check
**Check**: Total memory < 2GB

Detects workers with constrained memory:
- Checks `info.totalmem` field
- Flags workers with < 2GB total memory as warning
- Generates **MEDIUM** severity finding (warnings only)

**Impact**: Low memory can lead to performance issues and OOM kills

**Example Finding**:
```
● MEDIUM
Unhealthy Worker: worker-01
├── Worker worker-01 has 1 health concern(s): Low memory: 1.5GB
├── Components: worker-id-123
└── Impact: Worker performance degraded - Low memory: 1.5GB
```

### 5. Worker Uptime Monitoring
**Check**: Time since `firstMsgTime`

Detects recently restarted workers:
- Calculates uptime from `firstMsgTime` field
- Flags workers with < 5 minutes uptime as warning
- Generates **MEDIUM** severity finding (warnings only)

**Impact**: Frequent restarts indicate instability

**Example Finding**:
```
● MEDIUM
Unhealthy Worker: worker-01
├── Worker worker-01 has 1 health concern(s): Recently restarted: 2.3 min uptime
├── Components: worker-id-123
└── Impact: Worker performance degraded - Recently restarted: 2.3 min uptime
```

**Remediation**:
- Investigate recent restarts if applicable
- Check for crash loops or resource constraints
- Review worker logs for errors before restart

## Implementation Details

### Severity Levels
The analyzer uses a tiered severity system:

**Issues** (affect health score):
- Worker status != "healthy"
- Worker disconnected
- Disk usage > 90%

**Warnings** (don't affect health score):
- Low memory (< 2GB)
- Recent restart (< 5 minutes uptime)

**Severity Calculation**:
- **CRITICAL**: 2+ issues
- **HIGH**: 1 issue
- **MEDIUM**: Warnings only, or architectural concerns
- **LOW**: Optimization opportunities
- **INFO**: Informational findings

### Health Score Impact
- **100**: All workers healthy
- **90-99**: All workers healthy (perfect score)
- **70-89**: Degraded - some workers with issues
- **50-69**: Unhealthy - multiple workers require attention
- **0-49**: Critical - immediate action required

### API Calls Required
Total: **4 API calls**
1. `/api/v1/master/workers` - Worker data
2. `/api/v1/system/status` - System status (may 404 on Cribl Cloud)
3. `/api/v1/health` - Leader health
4. Internal processing (no additional API calls)

## Cribl Cloud Compatibility

All new checks work with Cribl Cloud's limited API:
- ✅ Leader health: `/api/v1/health` (available)
- ✅ Worker data: `/api/v1/master/workers` (available)
- ❌ Metrics: `/api/v1/metrics` (404 on Cribl Cloud)
- ❌ Routes: `/api/v1/master/routes` (404 on Cribl Cloud)
- ❌ PQ stats: `/api/v1/master/pq` (404 on Cribl Cloud)

## Testing

Tested against real Cribl Cloud deployment:
- Successfully detected unhealthy worker (status: shutting down)
- Correctly identified leader health
- Validated worker process counts
- No false positives for healthy workers

**Test Results**:
```
✓ Analysis completed
  Success: True
  Findings: 2
  Recommendations: 1

Metadata:
  worker_count: 3
  cribl_version: 4.15.0-f275b803
  leader_status: healthy
  leader_role: primary
  unhealthy_workers: 1
  health_score: 56.67
  health_status: unhealthy
```

## Future Enhancements

Potential additions (when API endpoints become available):

1. **Pipeline Error Monitoring**
   - Failed routes detection
   - Function execution errors
   - Parser failures

2. **Throughput Monitoring**
   - Events per second
   - Bytes per second
   - Backpressure indicators

3. **Persistent Queue Health**
   - PQ size monitoring
   - PQ age detection
   - Backlog warnings

4. **License Usage Tracking**
   - Daily volume trends
   - License limit warnings
   - Overage detection

5. **CPU/Memory Usage Metrics**
   - Real-time utilization (requires metrics endpoint)
   - Historical trends
   - Spike detection

## Documentation

Related Cribl documentation:
- [Distributed Deployment](https://docs.cribl.io/stream/deploy-distributed/)
- [High Availability](https://docs.cribl.io/stream/high-availability/)
- [Performance Tuning](https://docs.cribl.io/stream/performance-tuning/)
- [Scaling Workers](https://docs.cribl.io/stream/scaling/)
- [Monitoring](https://docs.cribl.io/stream/monitoring/)
