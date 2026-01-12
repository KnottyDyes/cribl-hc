# Analyzer Gaps & Expansion Roadmap

**Generated**: 2025-01-10  
**Status**: Analysis Complete - Ready for Implementation  
**Total Gap Coverage**: 10 new analyzers (56 hours effort)

---

## Executive Summary

Current state: **21 analyzers implemented**, excellent API coverage  
Gap analysis: **10 critical analyzer gaps identified**  
Coverage improvement: **Current 75% → 95% after Phase 1-3 (20 hours)**

### High-Level Roadmap

| Phase | Analyzers | Hours | Focus |
|-------|-----------|-------|-------|
| **Phase 1** | 3 | 20 | 🔴 Critical Input/Output/Route Coverage |
| **Phase 2** | 2 | 11 | 🟠 Quality & Reliability |
| **Phase 3** | 3 | 16 | 🟡 Organization & Optimization |
| **Phase 4** | 2 | 9 | 🟢 Search & Licensing (Nice-to-have) |
| **Total** | **10** | **56** | **~7 business days** |

---

## Phase 1: Critical Input/Output/Route Coverage (20 hours)

### PRIORITY 1: InputSourceAnalyzer (6 hours)

**Location**: `src/cribl_hc/analyzers/input_health.py`

**Objective**: Monitor input source health and connectivity

**APIs Used**:
- `get_inputs()` - List all input sources
- `get_system_status()` - Get input status metrics
- `get_metrics()` - Get performance metrics

**Checks to Implement**:

1. **Input Connectivity Status**
   - Flag inputs that are disconnected or experiencing errors
   - Severity: CRITICAL for disconnected, HIGH for frequent errors
   - Impact: No data flowing from source

2. **Data Lag/Freshness**
   - Track time since last event received
   - Flag inputs with no data for >5 minutes
   - Severity: HIGH (stale data detection)

3. **Error Rate Trends**
   - Calculate error rate per input
   - Flag if error rate >5% over last hour
   - Severity: MEDIUM-HIGH

4. **Input Queue Depth**
   - Monitor queue backlog
   - Flag if queue growing (downstream bottleneck)
   - Severity: MEDIUM

5. **Sample Event Validation**
   - Validate recent events for format/quality
   - Flag malformed or unexpected data patterns
   - Severity: MEDIUM

**Example Findings**:
```
🔴 CRITICAL: Input 'syslog' disconnected
   Last event: 45 minutes ago
   Status: Connection timeout
   Recommendation: Check network connectivity and firewall rules

🟠 HIGH: Input 'api_logs' error rate spike
   Error rate: 12% (threshold: 5%)
   Errors: 234 in last hour
   Recommendation: Review API configuration and error logs
```

**Test Coverage**: 8+ test cases covering all check types

**Estimated PR Size**: 200-250 lines (implementation) + 150-200 lines (tests)

---

### PRIORITY 2: OutputDestinationAnalyzer (6 hours)

**Location**: `src/cribl_hc/analyzers/output_health.py`

**Objective**: Validate output connectivity and configuration

**APIs Used**:
- `get_outputs()` - List all outputs
- `get_system_status()` - Get output status
- `get_notifications()` - Track delivery confirmations

**Checks to Implement**:

1. **Destination Connectivity**
   - Verify output connections are healthy
   - Flag unreachable or misconfigured destinations
   - Severity: CRITICAL (data loss risk)

2. **Configuration Validation**
   - Validate authentication credentials (non-decrypted)
   - Check required fields are populated
   - Flag deprecated endpoints
   - Severity: HIGH

3. **Error Rate Tracking**
   - Monitor delivery failures per output
   - Flag outputs with >5% failure rate
   - Severity: HIGH

4. **Buffer/Queue Status**
   - Monitor output queue depth
   - Flag if queue backing up
   - Severity: MEDIUM (indicates downstream issues)

5. **Delivery Confirmation**
   - Verify acknowledgments are being received
   - Flag if confirmation disabled on critical outputs
   - Severity: MEDIUM

**Example Findings**:
```
🔴 CRITICAL: Output 'aws-s3' cannot connect
   Status: Connection refused
   Last successful: 2 hours ago
   Events queued: 1.2M (risk of loss)
   Recommendation: Check AWS credentials and S3 bucket permissions

🟠 HIGH: Output 'splunk' delivery failure rate
   Failure rate: 8% (threshold: 5%)
   Failed events: 456 in last hour
   Recommendation: Check Splunk HEC token and network connectivity
```

**Test Coverage**: 8+ test cases covering all check types

**Estimated PR Size**: 200-250 lines (implementation) + 150-200 lines (tests)

---

### PRIORITY 3: RoutePerformanceAnalyzer (8 hours)

**Location**: `src/cribl_hc/analyzers/route_performance.py`

**Objective**: Analyze route throughput and load distribution

**APIs Used**:
- `get_routes()` - List all routes
- `get_metrics()` - Get performance metrics
- `get_pipelines()` - Link routes to pipelines

**Checks to Implement**:

1. **Route Throughput Per Second**
   - Calculate events/second for each route
   - Flag routes with zero throughput
   - Flag routes with unusual spikes/dips
   - Severity: MEDIUM

2. **Latency Percentiles (p50, p95, p99)**
   - Track processing latency distribution
   - Flag if p99 > 5s (configurable)
   - Severity: MEDIUM-HIGH (performance impact)

3. **Error Rates by Route**
   - Calculate error rate per route
   - Flag routes with errors >5%
   - Severity: HIGH

4. **Pipeline Overload Detection**
   - Flag if pipeline receiving >threshold events/sec
   - Recommend load balancing or pipeline split
   - Severity: MEDIUM

5. **Route Balance Analysis**
   - Analyze if traffic distributed evenly across routes
   - Flag imbalanced routing (indicates misconfiguration)
   - Severity: MEDIUM

**Example Findings**:
```
🟠 HIGH: Route 'prod-route' latency degradation
   Current p99: 8.2s (threshold: 5s)
   Increase: 45% in last 2 hours
   Affected pipelines: 3
   Recommendation: Check downstream pipeline performance or scale up resources

🟡 MEDIUM: Route 'analytics' very low throughput
   Events/sec: 0.3 (average: 15)
   Status: Healthy but underutilized
   Recommendation: Consider consolidating with other routes
```

**Test Coverage**: 10+ test cases covering all check types and edge cases

**Estimated PR Size**: 250-300 lines (implementation) + 200-250 lines (tests)

---

## Phase 2: Quality & Reliability (11 hours)

### PRIORITY 4: ParserQualityAnalyzer (6 hours)

**Location**: `src/cribl_hc/analyzers/parser_quality.py`

**APIs Used**: `get_parsers()`, `get_metrics()`, `get_pipelines()`

**Key Checks**:
- Parser error rate analysis
- Unused parser detection
- Complex/risky regex pattern detection
- Parser function usage analysis
- Field extraction quality metrics

---

### PRIORITY 5: NotificationDeliveryAnalyzer (5 hours)

**Location**: `src/cribl_hc/analyzers/notification_delivery.py`

**APIs Used**: `get_notifications()`, `get_notification_targets()`

**Key Checks**:
- Delivery success rate tracking
- Failed notification analysis
- Target availability validation
- Alert routing verification
- Escalation path health

---

## Phase 3: Organization & Optimization (16 hours)

### PRIORITY 6: EnhancedTeamPermissionsAnalyzer (4 hours)

Focus: Team structure analysis, permission overlap detection

### PRIORITY 7: WorkerGroupOptimizationAnalyzer (7 hours)

Focus: CPU/memory utilization, scaling recommendations, cost analysis

### PRIORITY 8: LibraryAndResourceAnalyzer (5 hours)

Focus: Unused library detection, dependency analysis, reuse optimization

---

## Phase 4: Search & Licensing (9 hours)

### PRIORITY 9: SearchWorkspaceOptimizationAnalyzer (4 hours)

Focus: Workspace organization, saved search usage, dashboard health

### PRIORITY 10: LicenseOptimizationAnalyzer (5 hours)

Focus: License consumption trends, cost optimization, drop rule opportunities

---

## Implementation Guidelines

### Code Structure Pattern

All analyzers should follow this structure:

```python
from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)

class YourAnalyzer(BaseAnalyzer):
    """
    Analyzer for [specific domain].
    
    Checks:
    - Check 1 description
    - Check 2 description
    """
    
    THRESHOLD_CRITICAL = 90
    THRESHOLD_HIGH = 75
    THRESHOLD_MEDIUM = 50
    
    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """Execute analysis."""
        result = AnalyzerResult(objective=self.objective_name)
        
        try:
            # Fetch data
            data = await client.get_XXX()
            
            # Perform checks
            for item in data:
                if not self._validate_item(item):
                    result.add_finding(
                        self.create_finding(
                            id="check-id",
                            title="Finding title",
                            description="Detailed description",
                            severity="high",  # critical, high, medium, low
                            category="category",
                            affected_components=[f"item:{item.id}"],
                            metadata={"key": "value"},
                        )
                    )
            
            # Add metadata
            result.metadata["items_analyzed"] = len(data)
            result.metadata["findings"] = len(result.findings)
            result.success = True
            
        except Exception as e:
            log.error(f"Analysis failed: {e}")
            result.success = False
        
        return result
```

### Testing Pattern

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestYourAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return YourAnalyzer()
    
    @pytest.mark.asyncio
    async def test_critical_condition_detected(self, analyzer):
        """Test detection of critical conditions."""
        client = AsyncMock()
        client.get_XXX.return_value = [
            {"id": "item1", "status": "error"}
        ]
        
        result = await analyzer.analyze(client)
        
        assert result.success
        assert len(result.findings) >= 1
        assert result.findings[0].severity == "critical"
```

---

## Integration Checklist

For each new analyzer, ensure:

- [ ] File created in `src/cribl_hc/analyzers/`
- [ ] Class inherits from `BaseAnalyzer`
- [ ] Objective name defined (`self.objective_name = "..."`
- [ ] `async def analyze(client)` implemented
- [ ] All checks documented with clear severity levels
- [ ] Metadata populated appropriately
- [ ] Error handling for missing/incomplete data
- [ ] Test file created in `tests/unit/test_analyzers/`
- [ ] 8+ test cases covering normal/edge/error cases
- [ ] Analyzer registered in `src/cribl_hc/analyzers/__init__.py`
- [ ] Documentation added to README
- [ ] PR created with clear description

---

## Success Criteria

### Phase 1 Completion (20 hours)
- ✅ InputSourceAnalyzer 100% complete
- ✅ OutputDestinationAnalyzer 100% complete  
- ✅ RoutePerformanceAnalyzer 100% complete
- ✅ All tests passing
- ✅ Documentation complete
- ✅ PR #45-47 merged to main

### Phase 2 Completion (11 hours)
- ✅ ParserQualityAnalyzer 100% complete
- ✅ NotificationDeliveryAnalyzer 100% complete
- ✅ All tests passing
- ✅ PR #48-49 merged

### Post-Implementation

**Coverage Statistics**:
- Before: 21 analyzers (75% coverage)
- After Phase 1: 24 analyzers (82% coverage)
- After Phase 2: 26 analyzers (88% coverage)
- After Phase 3: 29 analyzers (95% coverage)
- After Phase 4: 31 analyzers (100% coverage)

**API Endpoint Utilization**:
- Before: 34 APIs, 80% utilized
- After Phase 1-2: 34 APIs, 95% utilized
- After Phase 3-4: 34 APIs, 100% utilized

---

## Next Steps

1. **Immediate** (This week):
   - Review and approve Phase 1 specification
   - Set up branch for Phase 1 implementation
   - Begin InputSourceAnalyzer implementation

2. **Short-term** (Next 2 weeks):
   - Complete Phase 1 (3 analyzers)
   - Create PR for Phase 1 with comprehensive tests
   - Begin Phase 2 planning

3. **Medium-term** (Following month):
   - Complete Phase 2 & Phase 3
   - Begin Phase 4 if resources available
   - Update documentation with new coverage stats

---

## References

- API Reference: `/Projects/cribl-hc/cribl_api_reference/`
- Existing Analyzers: `src/cribl_hc/analyzers/`
- Test Examples: `tests/unit/test_analyzers/test_health.py`
- Base Classes: `src/cribl_hc/analyzers/base.py`
