# CriblVision Pack Replication Plan

**Status**: Research Phase Complete → Ready for Implementation  
**Created**: 2026-01-11  
**Branch Target**: `feature/criblvision-pack-replication`  
**Effort**: ~40-50 hours across 3 phases  

---

## Executive Summary

This plan outlines how to replicate **CriblVision Pack** monitoring capabilities within cribl-hc, focusing on four core problem areas:

1. **Throughput Bottlenecks** - Identify pipelines where input < output (with filters accounted for)
2. **Worker Group Imbalance** - Detect uneven load distribution (80/20 split is a red flag)
3. **Backpressure Monitoring** - Track destination pushback and queue buildup
4. **Endpoint Health** - Monitor request failure counts and latency spikes

### Why This Matters

- **Operational Visibility**: Users can spot data flow issues before they cascade
- **Cost Optimization**: Identify underutilized workers and right-size deployments
- **Performance Tuning**: Data-driven decisions on pipeline routing and worker scaling
- **Proactive Alerting**: Detect trends that lead to outages (growing queue depth, increasing errors)

### Current State

✅ **Already Implemented:**
- BackpressureAnalyzer (destination queue depth, persistent queues, HTTP retries)
- RoutePerformanceAnalyzer (throughput per route, latency, error rates, traffic balance)
- ResourceAnalyzer (worker CPU/memory utilization)
- MetricsAPI integration (`/api/v1/system/metrics`)

❌ **Gaps:**
- Worker group load distribution analysis (which worker group handles what % of traffic)
- Pipeline-level throughput analysis (in_events vs out_events ratio detection)
- Fine-grained endpoint health tracking per destination
- Correlation between metrics (queue depth + latency + error rate = root cause)
- Time-series trend analysis for predictive insights

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│            CriblVision Pack Replication Layer               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   MetricsCollector (new utility)                     │  │
│  │   - Normalize metric format from API                 │  │
│  │   - Calculate event ratios (in/out/drop)             │  │
│  │   - Smooth data (MA, trend detection)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ▲                                     │
│            ┌────────────┼────────────┐                       │
│            │            │            │                       │
│  ┌─────────────────┐ ┌──────────────────────┐               │
│  │ Bottleneck      │ │ WorkerGroup          │               │
│  │ Analyzer        │ │ BalanceAnalyzer      │               │
│  │ (Enhanced)      │ │ (NEW)                │               │
│  └─────────────────┘ └──────────────────────┘               │
│            │            │            │                       │
│  ┌─────────────────┐ ┌──────────────────────┐               │
│  │ Backpressure    │ │ EndpointHealth       │               │
│  │ Analyzer        │ │ Analyzer             │               │
│  │ (Enhanced)      │ │ (NEW)                │               │
│  └─────────────────┘ └──────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                         ▲
                         │
              ┌──────────┴──────────┐
              │                     │
         ┌────────────┐       ┌──────────────┐
         │ Metrics    │       │ Worker/Route │
         │ API        │       │ Configs      │
         └────────────┘       └──────────────┘
```

---

## Phase 1: Metrics Collection & Pipeline Bottleneck Detection (15 hours)

### 1.1 MetricsCollector Utility (4 hours)

**Location**: `src/cribl_hc/core/metrics_collector.py` (new)

**Purpose**: Normalize and enrich metrics data from the API

**Core Functionality**:

```python
class MetricsCollector:
    """Collect, normalize, and enrich metrics from Cribl API."""
    
    def normalize_metrics(self, raw_metrics: dict) -> dict:
        """
        Convert raw API metrics to standard format.
        
        Returns:
        {
            'pipelines': {
                'pipeline-id': {
                    'in_events': int,
                    'out_events': int,
                    'drop_events': int,
                    'error_events': int,
                    'processing_time_ms': float,
                }
            },
            'routes': {
                'route-id': {
                    'throughput': float,  # events/sec
                    'latency_p50_ms': float,
                    'latency_p99_ms': float,
                    'error_rate_percent': float,
                }
            },
            'workers': {
                'worker-id': {
                    'cpu_percent': float,
                    'memory_percent': float,
                    'events_per_sec': float,
                    'queue_depth': int,
                }
            },
            'outputs': {
                'output-id': {
                    'backpressure_time_ms': float,
                    'backpressure_percent': float,
                    'queue_depth': int,
                    'queue_depth_percent': float,
                }
            }
        }
        """
    
    def calculate_event_ratios(self, metrics: dict) -> dict:
        """Calculate in/out/drop ratios per pipeline."""
        return {
            'pipeline-id': {
                'drop_ratio': drop_events / in_events,
                'retention_ratio': out_events / in_events,
                'error_ratio': error_events / in_events,
            }
        }
    
    def detect_trends(self, 
                     current: dict,
                     historical: list[dict],
                     window_hours: int = 24) -> dict:
        """
        Detect trends in metrics over time.
        Returns dict of trend analysis per metric.
        """
        # Simple linear regression on historical data
        # Return: slope, r_squared, forecast_next_hour
```

**Tests**:
- Test metric normalization across different API versions
- Test ratio calculations with edge cases (0 events, divide-by-zero)
- Test trend detection with various data patterns (flat, increasing, spike)

### 1.2 Enhanced PipelineBottleneckAnalyzer (11 hours)

**Location**: `src/cribl_hc/analyzers/pipeline_bottleneck.py` (new)

**Objective**: Identify pipelines where throughput doesn't match input

**Checks to Implement**:

#### 1.2.1 Intentional Filtering Detection (HIGH priority)
```
Problem: Pipeline receives 1M events, outputs 900K (dropping 100K)
Question: Is this intentional (filters) or a bug?

Solution:
1. Compare metrics to configured filters/functions
2. Estimate expected drop rate based on config
3. Flag if actual drop > expected by 20%

Severity: MEDIUM (expected) or HIGH (unexpected)
```

#### 1.2.2 Silent Failure Detection
```
Problem: Pipeline receives events but produces nothing
Root causes: Null pipeline, disabled, error in parsing, etc.

Check:
- in_events > 0 but out_events = 0
- Check if pipeline is enabled/healthy
- Check error rate

Severity: CRITICAL
```

#### 1.2.3 Throughput Cliff Detection
```
Problem: One pipeline handles 95% of traffic, others 5%
This indicates possible misconfiguration or hot-spotting

Check:
- Calculate relative throughput per pipeline
- Flag if max > mean by 3x standard deviation

Severity: MEDIUM (performance issue)
```

#### 1.2.4 Processing Time Anomalies
```
Problem: Pipeline taking 10x longer to process events
May indicate: downstream backpressure, CPU saturation, GC pauses

Check:
- Track average processing time per event
- Compare to baseline (first hour of deployment)
- Flag if > baseline by 50%

Severity: MEDIUM-HIGH
```

**Metrics Required**:
- Pipeline metrics (in_events, out_events, error_events, drop_events, processing_time_ms)
- Pipeline configuration (enabled, filters, functions)
- Historical baseline data

**Example Findings**:

```
🔴 CRITICAL: Pipeline 'data_loss_detector' producing zero events
   Input: 50,000 events/hour
   Output: 0 events/hour
   Status: Configured filters may be blocking all data
   Root Cause: Check filter rules and test data

🟠 HIGH: Pipeline 'cloud_sync' has unexpected drop rate
   Expected drop: 5% (via config filters)
   Actual drop: 22%
   Root Cause: Check error logs for parsing failures

🟡 MEDIUM: Pipeline throughput imbalance detected
   - main_pipeline: 80% of total throughput
   - backup_pipeline: 20% of total throughput
   Recommendation: Review route configurations for balance
```

---

## Phase 2: Worker Group Load Balancing & Endpoint Health (18 hours)

### 2.1 WorkerGroupBalanceAnalyzer (9 hours)

**Location**: `src/cribl_hc/analyzers/worker_group_balance.py` (new)

**Objective**: Detect uneven load distribution across worker groups

**Checks to Implement**:

#### 2.1.1 Load Distribution Analysis
```
Problem: Worker Group A processes 80% of traffic, Group B handles 20%
Impact: Uneven resource utilization, potential bottleneck in A

Check:
- Get worker group list and their capabilities
- Analyze metrics per worker group
- Calculate % traffic per group
- Flag if Gini coefficient > 0.4 (high inequality)
- Compare against router configuration (intentional vs accidental)

Severity: MEDIUM (optimization opportunity)
```

#### 2.1.2 Worker Utilization Variance
```
Problem: Worker A in group handling 10 routes, Worker B handling 1 route
Impact: Uneven CPU/memory burden, hot-spot risk

Check:
- Get worker list and their assigned routes/pipelines
- Calculate metrics per worker
- Flag if one worker >> others

Severity: MEDIUM-HIGH
```

#### 2.1.3 Capacity Planning Detection
```
Problem: All workers in group at 85%+ CPU, no headroom for spikes
Impact: Any traffic spike → cascading failures

Check:
- Monitor worker group capacity trends
- Predict when headroom exhausted (linear regression)
- Flag if exhaustion likely within 48 hours

Severity: MEDIUM (planning issue)
```

**Metrics Required**:
- Worker group configs (membership, roles)
- Worker metrics (CPU, memory, queues per worker)
- Route-to-worker-group assignments

**Example Findings**:

```
🟠 HIGH: Uneven load distribution across worker groups
   Worker Group 'prod': 78% of total CPU utilization
   Worker Group 'backup': 22% of total CPU utilization
   Recommendation: Review route filters and rebalance if not intentional

🟡 MEDIUM: Capacity exhaustion predicted in 36 hours
   Current: 87% CPU average across 'prod' group
   Trend: +2% per day
   Recommendation: Plan scaling before headroom exhausted
```

### 2.2 EndpointHealthAnalyzer (9 hours)

**Location**: `src/cribl_hc/analyzers/endpoint_health.py` (new)

**Objective**: Track per-destination health metrics (requests, failures, latency)

**Checks to Implement**:

#### 2.2.1 Request Failure Rate Tracking
```
Problem: Destination receiving 1000 requests/sec, 50 failing per sec (5%)
Impact: Data loss, incomplete delivery, retry storms

Check:
- Aggregate failure metrics per destination
- Flag if failure rate > 2% (warning) or > 5% (critical)
- Differentiate: DNS errors vs connection timeouts vs HTTP 5xx

Severity: HIGH (data reliability)
```

#### 2.2.2 Latency Spike Detection
```
Problem: Destination normally responds in 100ms, now seeing p99 = 5000ms
Impact: Backpressure, queue buildup, cascade failures

Check:
- Track latency percentiles per destination
- Compare p50, p99, p999 to baseline
- Flag if p99 > baseline * 2

Severity: MEDIUM (performance)
```

#### 2.2.3 Circuit Breaker State
```
Problem: Destination is circuit-broken (all requests failing fast)
Impact: No traffic reaching destination, data queuing

Check:
- Query circuit breaker status per output
- Determine time-to-recovery estimate
- Flag with recovery timeline

Severity: CRITICAL (data flow broken)
```

#### 2.2.4 Destination Availability Ratio
```
Problem: Destination up/down intermittently (flaky)
Impact: Unpredictable delivery, hard to debug

Check:
- Calculate uptime ratio per destination
- Flag if < 99.9% over last 24 hours
- Track mean time between failures (MTBF)

Severity: MEDIUM (reliability)
```

**Metrics Required**:
- HTTP request counts (success, fail) per destination
- Latency metrics (p50, p99, p999) per destination
- Circuit breaker state per output
- Destination connectivity status

**Example Findings**:

```
🔴 CRITICAL: Destination 'splunk_prod' failure rate spike
   Failure rate: 8.5% (threshold: 5%)
   Requests/sec: 2000
   Failed: 170/sec
   p99 latency: 12000ms (baseline: 500ms)
   Root cause: Splunk instance may be down or overloaded
   Recommendation: Check Splunk HEC endpoint, increase indexer count

🟠 HIGH: Destination 'es_cluster' intermittent failures
   Uptime: 94.2% (threshold: 99.9%)
   Failures: 12 outages in 24 hours
   MTBF: 2 hours
   Recommendation: Check Elasticsearch cluster health and network stability

🟡 MEDIUM: Destination 'kafka_backup' latency degradation
   p99 latency: 2500ms (was 400ms baseline)
   Trend: +50% over last 6 hours
   Recommendation: Check Kafka broker health, consumer lag
```

---

## Phase 3: Integration & Correlation (17 hours)

### 3.1 Enhanced BackpressureAnalyzer Integration (6 hours)

**Current State**: Monitors queue depth, persistent queues, HTTP retries

**Enhancements**:
- Correlate endpoint failures with backpressure (are failures causing queues?)
- Link slow endpoints to queue buildup
- Predict queue exhaustion with improved trend analysis
- Add endpoint-specific backpressure recommendations

### 3.2 MetricsCorrelationAnalyzer (6 hours)

**Location**: `src/cribl_hc/analyzers/metrics_correlation.py` (new)

**Purpose**: Connect disparate metrics to identify root causes

**Example Correlations**:

```
1. High latency + high queue depth + low CPU
   → Destination bottleneck, not local resource issue
   
2. High drop rate + low error rate + specific pipeline
   → Intentional filtering or known data quality issue
   
3. Growing queue + increasing failure rate + high CPU
   → Cascading failure pattern (needs immediate action)
   
4. Imbalanced worker group + high latency in one group
   → Hot-spot causing contention
```

**Implementation**:
- Score correlations based on time alignment
- Produce composite findings (e.g., "Destination X failure causing Y queue buildup")
- Recommend priority actions (fix destination first, then monitor queue)

### 3.3 HealthScorer Updates (5 hours)

**Current State**: Calculates overall health from individual analyzer scores

**Enhancements**:
- Weight backpressure + bottleneck detection higher (critical path impact)
- Penalize worker group imbalance (missed optimization)
- Reward endpoint health (proactive monitoring)
- Add trending component (is health improving or degrading?)

---

## Implementation Roadmap

### Phased Rollout (3 Phases)

```
Phase 1 (Week 1): Throughput Bottleneck Detection
├─ MetricsCollector utility
├─ PipelineBottleneckAnalyzer
├─ Tests: 25+ test cases
└─ Integration: Route in orchestrator

Phase 2 (Week 2-3): Worker & Endpoint Health
├─ WorkerGroupBalanceAnalyzer
├─ EndpointHealthAnalyzer
├─ Tests: 30+ test cases
└─ Integration: Route in orchestrator

Phase 3 (Week 3-4): Correlation & Polish
├─ MetricsCorrelationAnalyzer
├─ BackpressureAnalyzer enhancements
├─ HealthScorer updates
├─ End-to-end testing
├─ Documentation
└─ PR review & merge
```

### Branch Structure

```
feature/criblvision-pack-replication
├── phase/1-metrics-collection
│   ├── src/cribl_hc/core/metrics_collector.py
│   └── src/cribl_hc/analyzers/pipeline_bottleneck.py
├── phase/2-worker-endpoint
│   ├── src/cribl_hc/analyzers/worker_group_balance.py
│   └── src/cribl_hc/analyzers/endpoint_health.py
└── phase/3-correlation
    ├── src/cribl_hc/analyzers/metrics_correlation.py
    ├── src/cribl_hc/analyzers/backpressure.py (enhanced)
    └── src/cribl_hc/core/health_scorer.py (enhanced)
```

---

## API Requirements

### Metrics Endpoint
```
GET /api/v1/system/metrics

Response:
{
  "pipelines": {
    "pipeline-id": {
      "in_events": int,
      "out_events": int,
      "drop_events": int,
      "error_events": int,
      "processing_time_ms": float
    }
  },
  "routes": {
    "route-id": {
      "throughput": float,
      "latency_p50": float,
      "latency_p99": float,
      "error_rate": float
    }
  },
  "workers": {
    "worker-id": {
      "cpu": float,
      "memory": float,
      "queue_depth": int
    }
  },
  "outputs": {
    "output-id": {
      "backpressure_ms": float,
      "request_count": int,
      "failure_count": int,
      "latency_p99": float
    }
  }
}
```

### Configuration Endpoints (Already Available)
- `GET /api/v1/pipelines` - Pipeline configs and filter rules
- `GET /api/v1/routes` - Route assignments to pipelines/outputs
- `GET /api/v1/workers` - Worker list and group membership
- `GET /api/v1/outputs` - Output destination configs

---

## Success Criteria

### Phase 1
- [ ] MetricsCollector normalizes metrics from multiple API versions
- [ ] PipelineBottleneckAnalyzer detects 4+ bottleneck types
- [ ] 25+ tests, all passing
- [ ] Example dashboard/report showing bottleneck detection

### Phase 2
- [ ] WorkerGroupBalanceAnalyzer ranks worker groups by load
- [ ] EndpointHealthAnalyzer tracks failure rate per destination
- [ ] 30+ tests, all passing
- [ ] Integration with BackpressureAnalyzer (no duplication)

### Phase 3
- [ ] MetricsCorrelationAnalyzer produces 3+ correlation types
- [ ] HealthScorer reflects overall system health accurately
- [ ] 100+ tests total, all passing
- [ ] Documentation complete (README, examples, troubleshooting)
- [ ] PR merged and deployed

---

## Testing Strategy

### Unit Tests
- Metrics normalization edge cases
- Ratio calculations (zero events, division by zero)
- Trend detection (flat, increasing, spike, decay)
- Threshold logic (CRITICAL vs HIGH vs MEDIUM)

### Integration Tests
- Full pipeline: Metrics API → Analyzers → Findings
- Multiple worker groups simultaneously
- Endpoint failure scenarios
- Historical data correlation

### End-to-End Tests
- Run analysis on production-like deployment
- Verify all findings are actionable
- Check that recommendations match findings

---

## Documentation

### User-Facing
- README with examples of each analyzer
- Troubleshooting guide (how to read findings, common false positives)
- Best practices for interpreting results

### Developer-Facing
- Architecture doc explaining metric flows
- API spec for metrics endpoint
- Testing guide (how to mock metrics for development)

---

## Risk Mitigation

### Risk: Metrics API not available or incomplete
**Mitigation**: 
- MetricsCollector returns empty dict gracefully
- Analyzers check for None/empty data before processing
- Findings include metadata explaining what data was unavailable

### Risk: False positives in bottleneck detection
**Mitigation**:
- Use configurable thresholds (allow customization)
- Document expected drops per pipeline
- Correlate with error rates to reduce FP

### Risk: Performance impact of trend analysis
**Mitigation**:
- Limit historical window to 24 hours (not unbounded)
- Cache trend results (update once per hour)
- Use simple linear regression (not complex ML)

---

## References

- **Backpressure Analyzer**: `src/cribl_hc/analyzers/backpressure.py` (already handles queue depth)
- **Route Performance**: `src/cribl_hc/analyzers/route_performance.py` (already handles throughput)
- **Resource Analyzer**: `src/cribl_hc/analyzers/resource.py` (already handles worker CPU/memory)
- **Metrics API**: `src/cribl_hc/core/api_client.py` → `get_metrics()`
- **Test Template**: `tests/unit/test_analyzers/test_alerting.py`

---

## Questions for Stakeholders

1. Should we support historical metric storage (24h window is in-memory only)?
2. Are there specific Cribl Enterprise metrics we should prioritize?
3. Should "worker group balance" account for intentional asymmetric routing?
4. What's the max acceptable latency for correlation analysis?
5. Should we generate alerts or just findings?

---

## Next Steps

1. **Review this plan** with technical stakeholders
2. **Validate Phase 1** with metrics endpoint availability check
3. **Create branch**: `feature/criblvision-pack-replication`
4. **Start Phase 1**: MetricsCollector + PipelineBottleneckAnalyzer
5. **Set up continuous integration** for new analyzers

---

**Created**: 2026-01-11  
**Author**: Sisyphus (AI Agent)  
**Status**: Ready for Review & Implementation
