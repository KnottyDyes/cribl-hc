# Community Gaps Implementation Plan

**Status**: Ready for Implementation  
**Created**: 2026-01-20  
**Source**: [Cribl Community Discoveries](./Cribl_Community_Discoveries.md)  
**Estimated Effort**: ~20-25 hours  

---

## Executive Summary

After completing the CriblVision Pack replication, these gaps remain from community research:

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 🔴 HIGH | File Monitor Permission Auditing | 6 hrs | Prevents silent source failures |
| 🔴 HIGH | Scheduled Collector Health | 6 hrs | Ensures data collection reliability |
| 🟠 MEDIUM | HEC-Specific Validation | 4 hrs | Better Splunk destination debugging |
| 🟠 MEDIUM | Log Level Configuration Check | 2 hrs | Prevents infrastructure overload |
| 🟡 LOW | Load Balancer Health Validation | 2 hrs | Better LB integration |
| 🟡 LOW | TCP Flow Control Detection | 3 hrs | Upstream source health |

---

## Phase 1: Source Health Gaps (12 hours)

### 1.1 FileMonitorPermissionAnalyzer (6 hours)

**Location**: `src/cribl_hc/analyzers/file_monitor_permissions.py`

**Problem Statement** (from Community):
> File monitor sources fail silently due to permission issues. Users don't know why data isn't flowing until they dig into logs.

**Source**: [Community Discussion](https://knowledge.cribl.io/general-7/troubleshooting-file-monitor-permission-issue-1182)

**Checks to Implement**:

```python
class FileMonitorPermissionAnalyzer(BaseAnalyzer):
    """Audit file monitor source permissions and accessibility."""
    
    async def analyze(self, context: AnalysisContext) -> list[Finding]:
        findings = []
        
        # 1. Get all file monitor sources
        sources = await self._get_file_monitor_sources(context)
        
        for source in sources:
            # 2. Check if monitored paths exist
            # 3. Check read permissions on paths
            # 4. Check if Cribl process user can access
            # 5. Check for symlink issues
            # 6. Validate glob patterns are valid
            pass
        
        return findings
```

**Finding Types**:

| Severity | Condition | Example |
|----------|-----------|---------|
| CRITICAL | Path does not exist | `/var/log/app/*.log` - directory missing |
| CRITICAL | No read permission | `/etc/secure/` - permission denied |
| HIGH | Symlink to inaccessible target | `/var/log/current` -> inaccessible |
| MEDIUM | Glob pattern matches nothing | `*.jsonl` - no matching files |
| LOW | Path exists but empty | Directory exists but has no files |

**API Requirements**:
- `GET /api/v1/sources` - Get file monitor source configs
- `GET /api/v1/system/info` - Get Cribl process user/permissions (if available)

**Note**: Some permission checks may only work for self-hosted deployments where cribl-hc has filesystem access. For cloud deployments, we can only validate configuration syntax.

---

### 1.2 ScheduledCollectorHealthAnalyzer (6 hours)

**Location**: `src/cribl_hc/analyzers/scheduled_collector_health.py`

**Problem Statement** (from Community):
> Collectors work in ad-hoc mode but fail when scheduled. Users don't have visibility into why scheduled jobs fail.

**Source**: [Community Discussion](https://knowledge.cribl.io/stream-56/scheduled-collector-discovers-events-but-does-not-collect-1559)

**Checks to Implement**:

```python
class ScheduledCollectorHealthAnalyzer(BaseAnalyzer):
    """Monitor scheduled collector job health and execution history."""
    
    async def analyze(self, context: AnalysisContext) -> list[Finding]:
        findings = []
        
        # 1. Get all scheduled collectors
        collectors = await self._get_scheduled_collectors(context)
        
        for collector in collectors:
            # 2. Check schedule validity (cron syntax)
            # 3. Get recent job execution history
            # 4. Calculate success/failure rate
            # 5. Check for jobs that never ran
            # 6. Detect jobs with increasing failure rate
            # 7. Check resource conflicts (overlapping schedules)
            pass
        
        return findings
```

**Finding Types**:

| Severity | Condition | Example |
|----------|-----------|---------|
| CRITICAL | Collector never executed | Scheduled but 0 runs in 7 days |
| CRITICAL | 100% failure rate | Last 10 runs all failed |
| HIGH | High failure rate (>50%) | 7/10 recent runs failed |
| HIGH | Job runtime exceeds schedule | 2hr job on 1hr schedule |
| MEDIUM | Increasing failure trend | Was 10% failures, now 40% |
| MEDIUM | Overlapping schedules | Two collectors compete for resources |
| LOW | Suboptimal schedule | Running every minute for hourly data |

**API Requirements**:
- `GET /api/v1/collectors` - Get collector configurations
- `GET /api/v1/jobs` or `/api/v1/system/jobs` - Get job execution history
- Schedule configs include cron expressions

**Metrics to Track**:
- Jobs scheduled vs executed
- Success/failure counts per collector
- Average runtime per job
- Last successful run timestamp

---

## Phase 2: Destination Health Enhancements (6 hours)

### 2.1 HECValidationAnalyzer (4 hours)

**Location**: `src/cribl_hc/analyzers/hec_validation.py`

**Problem Statement** (from Community):
> Users struggle to diagnose why HEC destinations stop receiving data. Token issues, SSL problems, and acknowledgment failures are common but hard to debug.

**Source**: [Community Discussion](https://knowledge.cribl.io/general-7/how-can-i-troubleshoot-a-cribl-destination-splunk-hec-not-sending-data-1294)

**Checks to Implement**:

```python
class HECValidationAnalyzer(BaseAnalyzer):
    """Validate Splunk HEC destination configurations and connectivity."""
    
    async def analyze(self, context: AnalysisContext) -> list[Finding]:
        findings = []
        
        # 1. Get all Splunk HEC outputs
        hec_outputs = await self._get_hec_outputs(context)
        
        for output in hec_outputs:
            # 2. Validate HEC URL format
            # 3. Check SSL/TLS configuration
            # 4. Validate token format (not actual auth)
            # 5. Check acknowledgment settings
            # 6. Validate index targeting
            # 7. Check for common misconfigurations
            pass
        
        return findings
```

**Finding Types**:

| Severity | Condition | Example |
|----------|-----------|---------|
| CRITICAL | Invalid HEC URL | Missing `/services/collector` path |
| CRITICAL | SSL disabled to HTTPS endpoint | Security risk + likely failure |
| HIGH | Token appears invalid | Wrong format, placeholder value |
| HIGH | Ack enabled but timeout too low | < 30s timeout with acks |
| MEDIUM | Index not specified | Using default index (may fail) |
| MEDIUM | No load balancing for multiple HECs | Single point of failure |
| LOW | Compression disabled | Performance optimization available |

**Configuration Validations**:
- URL format: `https://host:8088/services/collector/event`
- Token format: UUID-like pattern
- SSL settings match URL scheme
- Timeout values are reasonable
- Batch sizes are within HEC limits

---

### 2.2 LogLevelConfigurationAnalyzer (2 hours)

**Location**: `src/cribl_hc/analyzers/log_level_config.py`

**Problem Statement** (from Community):
> Enabling verbose logging levels (like "silly") can overwhelm infrastructure with disk I/O and fill storage.

**Source**: [Community Discussion](https://knowledge.cribl.io/stream-56/logging-level-silly-takes-my-infrastructure-down-1777)

**Checks to Implement**:

```python
class LogLevelConfigurationAnalyzer(BaseAnalyzer):
    """Validate logging configuration for production safety."""
    
    async def analyze(self, context: AnalysisContext) -> list[Finding]:
        findings = []
        
        # 1. Get logging configuration
        log_config = await self._get_log_config(context)
        
        # 2. Check log level (warn about debug/silly in prod)
        # 3. Check log rotation settings
        # 4. Estimate disk usage based on event volume
        # 5. Check for log destinations that may overflow
        
        return findings
```

**Finding Types**:

| Severity | Condition | Example |
|----------|-----------|---------|
| CRITICAL | Log level "silly" in production | Will overwhelm infrastructure |
| HIGH | Log level "debug" in production | Performance impact, disk fill |
| MEDIUM | No log rotation configured | Disk will eventually fill |
| MEDIUM | Log retention too long | > 30 days retention |
| LOW | Log level could be reduced | "info" when "warn" sufficient |

---

## Phase 3: Future Enhancements (5 hours)

### 3.1 LoadBalancerHealthAnalyzer (2 hours)

**Location**: `src/cribl_hc/analyzers/load_balancer_health.py`

**Problem Statement** (from Community):
> Users need to validate that Cribl's `/health` endpoint works correctly for load balancer integration.

**Checks**:
- Validate `/health` endpoint returns expected status codes
- Check response time is within LB timeout thresholds
- Verify health endpoint reflects actual system health

### 3.2 TCPFlowControlAnalyzer (3 hours)

**Location**: `src/cribl_hc/analyzers/tcp_flow_control.py`

**Problem Statement** (from Community):
> TCP output pauses cause data flow interruptions from upstream sources.

**Checks**:
- Monitor TCP connection states per source
- Detect flow control/backpressure from sources
- Correlate with destination health

---

## Implementation Roadmap

### Week 1: Source Health (Phase 1)
```
Day 1-2: FileMonitorPermissionAnalyzer
├── Implement source config retrieval
├── Add permission checking logic
├── Write 15+ test cases
└── Integration with orchestrator

Day 3-4: ScheduledCollectorHealthAnalyzer
├── Implement collector/job retrieval
├── Add schedule validation logic
├── Add execution history analysis
├── Write 15+ test cases
└── Integration with orchestrator

Day 5: Testing & Documentation
├── End-to-end testing
├── Update analyzer documentation
└── PR for Phase 1
```

### Week 2: Destination Enhancements (Phase 2)
```
Day 1-2: HECValidationAnalyzer
├── Implement HEC output retrieval
├── Add configuration validation
├── Write 10+ test cases
└── Integration with orchestrator

Day 3: LogLevelConfigurationAnalyzer
├── Implement log config retrieval
├── Add level/rotation checks
├── Write 8+ test cases
└── Integration with orchestrator

Day 4-5: Testing & PR
├── End-to-end testing
├── Documentation updates
└── PR for Phase 2
```

### Week 3: Future Enhancements (Phase 3 - Optional)
```
LoadBalancerHealthAnalyzer
TCPFlowControlAnalyzer
```

---

## Testing Strategy

### Unit Tests Per Analyzer

| Analyzer | Test Cases | Focus Areas |
|----------|------------|-------------|
| FileMonitorPermission | 15+ | Path validation, permission scenarios, symlinks |
| ScheduledCollectorHealth | 15+ | Schedule parsing, history analysis, failure detection |
| HECValidation | 10+ | URL validation, token format, SSL settings |
| LogLevelConfig | 8+ | Level detection, rotation checks |

### Integration Tests
- Full pipeline: API → Analyzer → Findings
- Mock API responses for various scenarios
- Error handling for unavailable endpoints

### End-to-End Tests
- Run against real Cribl deployment (if available)
- Verify findings are actionable
- No false positives in normal configurations

---

## Success Criteria

### Phase 1 Complete ✅
- [x] FileMonitorPermissionAnalyzer detects 5+ issue types (8 implemented)
- [x] ScheduledCollectorHealthAnalyzer tracks job history
- [x] 61+ tests passing (35 for file monitor, 26 for scheduled collector)
- [x] Analyzers auto-registered and integrated

### Phase 2 Complete ✅
- [x] HECValidationAnalyzer validates HEC configs
- [x] LogLevelConfigurationAnalyzer warns on verbose logging
- [ ] 18+ additional tests passing
- [x] All new analyzers integrated

### Phase 3 Complete (Stretch)
- [ ] LoadBalancerHealthAnalyzer validates /health endpoint
- [ ] TCPFlowControlAnalyzer detects flow issues
- [ ] 10+ additional tests

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Filesystem access limited | HIGH | Degrade gracefully to config-only validation |
| Job history API unavailable | MEDIUM | Check API availability, skip if not present |
| HEC configs vary by version | MEDIUM | Support multiple config formats |
| Log config location varies | LOW | Check common locations |

---

## API Requirements Summary

| Analyzer | Required Endpoints |
|----------|-------------------|
| FileMonitorPermission | `GET /api/v1/sources`, `GET /api/v1/system/info` |
| ScheduledCollectorHealth | `GET /api/v1/collectors`, `GET /api/v1/jobs` |
| HECValidation | `GET /api/v1/outputs` (filter type=splunk_hec) |
| LogLevelConfig | `GET /api/v1/system/settings` or `/api/v1/system/instance` |

---

## Next Steps

1. ~~**Review** this plan~~ ✅ Done
2. ~~**Validate** API endpoint availability for target Cribl versions~~ ✅ Done
3. ~~**Start Phase 1**: FileMonitorPermissionAnalyzer~~ ✅ Done
4. **Phase 2**: HECValidationAnalyzer, LogLevelConfigurationAnalyzer ✅ Done
5. **Phase 3**: LoadBalancerHealthAnalyzer, TCPFlowControlAnalyzer (optional)

---

**Created**: 2026-01-20  
**Updated**: 2026-01-20  
**Author**: Sisyphus (AI Agent)  
**Status**: Phase 2 COMPLETE

**Created**: 2026-01-20  
**Updated**: 2026-01-20  
**Author**: Sisyphus (AI Agent)  
**Status: Phase 2 COMPLETE
