# Data Model: Cribl Health Check Core

**Feature**: 001-health-check-core
**Date**: 2025-12-10
**Status**: Complete

## Overview

This document defines all data entities for the Cribl Health Check Core tool. All entities are implemented as Pydantic models for strong type validation, automatic JSON serialization, and clear data contracts.

## Entity Relationship Diagram

```text
┌─────────────────┐
│   Deployment    │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐         ┌──────────────────┐
│   AnalysisRun   │────────▶│   HealthScore    │
└────────┬────────┘ 1:1     └──────────────────┘
         │
         │ 1:N              ┌──────────────────┐
         ├─────────────────▶│     Finding      │
         │                  └──────────────────┘
         │
         │ 1:N              ┌──────────────────┐
         ├─────────────────▶│  Recommendation  │
         │                  └──────────────────┘
         │
         │ 1:N              ┌──────────────────┐
         └─────────────────▶│   WorkerNode     │
                            └──────────────────┘

┌─────────────────┐
│ HistoricalTrend │ (Optional, linked by deployment_id)
└─────────────────┘

┌─────────────────┐
│ConfigurationElem│ (Referenced by Finding)
└─────────────────┘

┌─────────────────┐
│BestPracticeRule │ (Configuration-driven, loaded at startup)
└─────────────────┘
```

## Core Entities

### 1. Deployment

Represents a Cribl Stream environment (Cloud or self-hosted) with API credentials and metadata.

**Attributes**:
```python
class Deployment(BaseModel):
    id: str  # Unique identifier (user-defined, e.g., "prod", "staging")
    name: str  # Human-readable name
    url: str  # Base URL (e.g., "https://cribl.example.com")
    environment_type: Literal["cloud", "self-hosted"]
    auth_token: SecretStr  # API token (encrypted in storage)
    cribl_version: Optional[str] = None  # Detected version (e.g., "4.5.2")
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}  # Custom key-value pairs
```

**Validation Rules**:
- `url` must be valid HTTP/HTTPS URL
- `id` must be lowercase alphanumeric + hyphens
- `auth_token` is SecretStr (not logged or displayed)
- `cribl_version` validated against N through N-2 support

**Relationships**:
- Has many `AnalysisRun` instances
- Has many `WorkerNode` instances

**Example**:
```json
{
  "id": "prod-cribl",
  "name": "Production Cribl Cluster",
  "url": "https://cribl.example.com",
  "environment_type": "self-hosted",
  "auth_token": "**SECRET**",
  "cribl_version": "4.5.2",
  "created_at": "2025-12-10T10:00:00Z",
  "updated_at": "2025-12-10T10:00:00Z",
  "metadata": {
    "region": "us-east-1",
    "team": "platform"
  }
}
```

---

### 2. AnalysisRun

Single execution of health check analysis with metadata and results.

**Attributes**:
```python
class AnalysisRun(BaseModel):
    id: str  # UUID for this run
    deployment_id: str  # Reference to Deployment
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: Literal["running", "completed", "partial", "failed"]
    objectives_analyzed: List[str]  # e.g., ["health", "config", "security"]
    api_calls_used: int  # Count of Cribl API calls made
    health_score: Optional[HealthScore] = None
    findings: List[Finding] = []
    recommendations: List[Recommendation] = []
    worker_nodes: List[WorkerNode] = []
    errors: List[str] = []  # Errors encountered during analysis
    partial_completion: bool = False  # True if some objectives failed
```

**Validation Rules**:
- `api_calls_used` must be ≤ 100 (enforced limit)
- `duration_seconds` must be ≤ 300 (5 minutes target)
- `status` derived from completion state and errors
- `objectives_analyzed` validated against known objective names

**State Transitions**:
```text
running → completed (all objectives succeeded)
running → partial (some objectives failed but results available)
running → failed (critical failure, no results)
```

**Example**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "deployment_id": "prod-cribl",
  "started_at": "2025-12-10T14:00:00Z",
  "completed_at": "2025-12-10T14:03:45Z",
  "duration_seconds": 225.3,
  "status": "completed",
  "objectives_analyzed": ["health", "config", "security"],
  "api_calls_used": 87,
  "health_score": { ... },
  "findings": [ ... ],
  "recommendations": [ ... ],
  "errors": [],
  "partial_completion": false
}
```

---

### 3. HealthScore

Numeric representation (0-100) of deployment health calculated from multiple metrics.

**Attributes**:
```python
class ComponentScore(BaseModel):
    name: str
    score: int  # 0-100
    weight: float  # Weight in overall score calculation
    details: str  # Explanation of score

class HealthScore(BaseModel):
    overall_score: int  # 0-100 (weighted average of components)
    components: Dict[str, ComponentScore]  # Component breakdown
    timestamp: datetime
    trend_direction: Optional[Literal["improving", "stable", "declining"]] = None
    previous_score: Optional[int] = None  # For trend calculation
```

**Component Scores**:
- `workers`: Worker node health (CPU, memory, disk, connectivity)
- `configuration`: Configuration validity and best practices
- `security`: Security posture and compliance
- `performance`: Performance efficiency and optimization
- `reliability`: HA, backups, disaster recovery
- `cost_efficiency`: License utilization and cost optimization

**Calculation Formula**:
```python
overall_score = sum(component.score * component.weight for component in components.values())
```

**Default Weights**:
```python
{
    "workers": 0.25,
    "configuration": 0.20,
    "security": 0.20,
    "performance": 0.15,
    "reliability": 0.15,
    "cost_efficiency": 0.05
}
```

**Validation Rules**:
- All scores must be 0-100 inclusive
- Weights must sum to 1.0
- `trend_direction` requires `previous_score`

**Example**:
```json
{
  "overall_score": 78,
  "components": {
    "workers": {
      "name": "Worker Health",
      "score": 85,
      "weight": 0.25,
      "details": "3 of 5 workers healthy, 2 with high memory usage"
    },
    "configuration": {
      "name": "Configuration Quality",
      "score": 72,
      "weight": 0.20,
      "details": "4 syntax errors, 2 deprecated functions found"
    }
  },
  "timestamp": "2025-12-10T14:03:45Z",
  "trend_direction": "improving",
  "previous_score": 74
}
```

---

### 4. Finding

Identified problem or improvement opportunity with severity, remediation, and documentation links.

**Attributes**:
```python
class Finding(BaseModel):
    id: str  # Unique identifier for this finding
    category: str  # Objective category (e.g., "health", "config", "security")
    severity: Literal["critical", "high", "medium", "low", "info"]
    title: str  # Brief title (e.g., "Worker node memory exhaustion")
    description: str  # Detailed description of the issue
    affected_components: List[str]  # e.g., ["worker-01", "pipeline-logs"]
    remediation_steps: List[str]  # Step-by-step fix instructions
    documentation_links: List[str]  # URLs to Cribl docs
    estimated_impact: str  # Impact description (e.g., "High risk of data loss")
    confidence_level: Literal["high", "medium", "low"]
    detected_at: datetime
    metadata: Dict[str, Any] = {}  # Additional context
```

**Severity Definitions**:
- **critical**: Immediate action required, service at risk
- **high**: Significant issue, should address within 24 hours
- **medium**: Notable issue, address within 1 week
- **low**: Minor issue, address when convenient
- **info**: Informational, no action required

**Validation Rules**:
- `remediation_steps` must have at least 1 step for critical/high/medium
- `documentation_links` must be valid URLs to docs.cribl.io domain
- `estimated_impact` required for critical and high severity

**Example**:
```json
{
  "id": "finding-mem-001",
  "category": "health",
  "severity": "high",
  "title": "Worker node approaching memory exhaustion",
  "description": "Worker worker-01 is using 92% of allocated memory (14.7GB of 16GB). Persistent high memory usage may lead to OOM kills and data loss.",
  "affected_components": ["worker-01"],
  "remediation_steps": [
    "Review worker memory allocation in worker group settings",
    "Consider vertical scaling: increase worker memory to 24GB",
    "Investigate memory-intensive pipelines on this worker",
    "Check for memory leaks in custom functions"
  ],
  "documentation_links": [
    "https://docs.cribl.io/stream/sizing-workers",
    "https://docs.cribl.io/stream/monitoring#memory"
  ],
  "estimated_impact": "High risk of worker crash and data loss if memory exhaustion occurs",
  "confidence_level": "high",
  "detected_at": "2025-12-10T14:01:23Z",
  "metadata": {
    "current_memory_gb": 14.7,
    "allocated_memory_gb": 16,
    "utilization_percent": 92
  }
}
```

---

### 5. Recommendation

Actionable suggestion for improvement with impact estimates and priorities.

**Attributes**:
```python
class ImpactEstimate(BaseModel):
    cost_savings_annual: Optional[float] = None  # Dollars saved per year
    performance_improvement: Optional[str] = None  # e.g., "20% throughput increase"
    storage_reduction_gb: Optional[float] = None  # GB saved
    time_to_implement: Optional[str] = None  # e.g., "30 minutes"

class Recommendation(BaseModel):
    id: str
    type: str  # e.g., "scaling", "optimization", "security", "cost"
    priority: Literal["p0", "p1", "p2", "p3"]
    title: str
    description: str
    rationale: str  # Why this recommendation is made
    implementation_steps: List[str]
    before_state: str  # Current state description
    after_state: str  # Expected state after implementation
    impact_estimate: ImpactEstimate
    implementation_effort: Literal["low", "medium", "high"]
    related_findings: List[str] = []  # Finding IDs this addresses
    documentation_links: List[str] = []
    created_at: datetime
```

**Priority Definitions**:
- **p0**: Critical, implement immediately (< 24 hours)
- **p1**: High priority, implement soon (< 1 week)
- **p2**: Medium priority, plan for next sprint
- **p3**: Low priority, nice-to-have improvement

**Validation Rules**:
- `impact_estimate` should have at least one metric for p0/p1
- `before_state` and `after_state` required for optimization recommendations
- `implementation_steps` must have at least 1 step

**Example**:
```json
{
  "id": "rec-storage-001",
  "type": "optimization",
  "priority": "p1",
  "title": "Implement sampling for high-volume debug logs",
  "description": "Reduce storage costs by 35% by sampling debug-level logs at 10:1 ratio before forwarding to Splunk",
  "rationale": "Debug logs represent 60% of total volume but are rarely queried. Sampling maintains statistical significance while reducing costs.",
  "implementation_steps": [
    "Add eval function to 'debug-logs' pipeline: sample rate=0.1",
    "Test sampling logic with known debug volume",
    "Monitor Splunk for adequate debug log coverage",
    "Adjust sample rate if needed (recommend 0.05-0.2 range)"
  ],
  "before_state": "Sending 2.4TB/day of debug logs to Splunk at full volume",
  "after_state": "Send 240GB/day of sampled debug logs (10% sample), maintain full volume for error/warn logs",
  "impact_estimate": {
    "cost_savings_annual": 18720.0,
    "storage_reduction_gb": 788.4,
    "performance_improvement": "15% reduction in Splunk indexer load",
    "time_to_implement": "45 minutes"
  },
  "implementation_effort": "low",
  "related_findings": ["finding-storage-003"],
  "documentation_links": [
    "https://docs.cribl.io/stream/sampling-function"
  ],
  "created_at": "2025-12-10T14:02:15Z"
}
```

---

### 6. WorkerNode

Individual Cribl worker instance with resource utilization and health status.

**Attributes**:
```python
class ResourceUtilization(BaseModel):
    cpu_percent: float  # 0-100
    memory_used_gb: float
    memory_total_gb: float
    memory_percent: float  # 0-100
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float  # 0-100

class WorkerNode(BaseModel):
    id: str  # Worker ID from Cribl API
    name: str  # Human-readable name
    group_id: str  # Worker group membership
    host: str  # Hostname or IP
    version: str  # Cribl version running on this worker
    health_status: Literal["healthy", "degraded", "unhealthy", "unreachable"]
    resource_utilization: ResourceUtilization
    connectivity_status: Literal["connected", "disconnected", "unknown"]
    last_seen: datetime
    uptime_seconds: Optional[int] = None
    metadata: Dict[str, Any] = {}
```

**Health Status Determination**:
```python
def determine_health_status(worker: WorkerNode) -> str:
    if worker.connectivity_status != "connected":
        return "unreachable"
    if worker.resource_utilization.cpu_percent > 90 or \
       worker.resource_utilization.memory_percent > 90 or \
       worker.resource_utilization.disk_percent > 90:
        return "unhealthy"
    if worker.resource_utilization.cpu_percent > 75 or \
       worker.resource_utilization.memory_percent > 75 or \
       worker.resource_utilization.disk_percent > 80:
        return "degraded"
    return "healthy"
```

**Example**:
```json
{
  "id": "wrkr-abc123",
  "name": "worker-01",
  "group_id": "default",
  "host": "10.0.1.45",
  "version": "4.5.2",
  "health_status": "degraded",
  "resource_utilization": {
    "cpu_percent": 68.5,
    "memory_used_gb": 14.7,
    "memory_total_gb": 16.0,
    "memory_percent": 91.9,
    "disk_used_gb": 45.2,
    "disk_total_gb": 100.0,
    "disk_percent": 45.2
  },
  "connectivity_status": "connected",
  "last_seen": "2025-12-10T14:03:30Z",
  "uptime_seconds": 2592000,
  "metadata": {
    "instance_type": "m5.xlarge",
    "az": "us-east-1a"
  }
}
```

---

### 7. ConfigurationElement

Pipeline, route, function, destination, or other configurable component.

**Attributes**:
```python
class ConfigurationElement(BaseModel):
    id: str
    type: Literal["pipeline", "route", "function", "destination", "input", "lookup"]
    name: str
    group_id: str  # Worker group this config belongs to
    definition: Dict[str, Any]  # Raw configuration JSON
    usage_status: Literal["active", "unused", "orphaned"]
    validation_status: Literal["valid", "syntax_error", "logic_error", "warning"]
    best_practice_compliance: float  # 0-1 score
    validation_errors: List[str] = []
    validation_warnings: List[str] = []
    last_modified: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
```

**Usage Status Definitions**:
- **active**: Referenced by routes and actively processing data
- **unused**: Defined but not referenced by any routes
- **orphaned**: References non-existent components (broken dependencies)

**Example**:
```json
{
  "id": "pipeline-logs-processing",
  "type": "pipeline",
  "name": "logs-processing",
  "group_id": "default",
  "definition": {
    "id": "logs-processing",
    "functions": [
      {"id": "eval", "filter": "true", "add": [{"name": "_processed", "value": "true"}]}
    ]
  },
  "usage_status": "active",
  "validation_status": "warning",
  "best_practice_compliance": 0.85,
  "validation_errors": [],
  "validation_warnings": [
    "Pipeline uses deprecated 'eval' function syntax, migrate to 'c.Set' method"
  ],
  "last_modified": "2025-11-15T08:30:00Z",
  "metadata": {
    "routes_using": ["route-splunk", "route-s3"]
  }
}
```

---

### 8. HistoricalTrend

Time-series data for tracking changes over multiple analysis runs (optional).

**Attributes**:
```python
class DataPoint(BaseModel):
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = {}

class HistoricalTrend(BaseModel):
    deployment_id: str
    metric_name: str  # e.g., "health_score", "api_calls_used", "finding_count"
    data_points: List[DataPoint]
    trend_direction: Literal["improving", "stable", "declining", "volatile"]
    anomalies_detected: List[DataPoint] = []  # Points flagged as anomalous
    forecast_next: Optional[float] = None  # Predicted next value
    created_at: datetime
    updated_at: datetime
```

**Trend Direction Calculation**:
```python
def calculate_trend(data_points: List[DataPoint]) -> str:
    if len(data_points) < 3:
        return "stable"
    recent = [p.value for p in data_points[-5:]]
    slope = linear_regression_slope(recent)
    variance = standard_deviation(recent) / mean(recent)

    if variance > 0.2:
        return "volatile"
    elif slope > 0.1:
        return "improving"
    elif slope < -0.1:
        return "declining"
    return "stable"
```

**Example**:
```json
{
  "deployment_id": "prod-cribl",
  "metric_name": "health_score",
  "data_points": [
    {"timestamp": "2025-12-01T00:00:00Z", "value": 72.0},
    {"timestamp": "2025-12-02T00:00:00Z", "value": 74.0},
    {"timestamp": "2025-12-03T00:00:00Z", "value": 76.0},
    {"timestamp": "2025-12-10T14:03:45Z", "value": 78.0}
  ],
  "trend_direction": "improving",
  "anomalies_detected": [],
  "forecast_next": 80.0,
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2025-12-10T14:03:45Z"
}
```

---

### 9. BestPracticeRule

Validation rule derived from Cribl documentation (configuration-driven).

**Attributes**:
```python
class BestPracticeRule(BaseModel):
    id: str
    name: str
    category: str  # e.g., "performance", "security", "reliability"
    description: str
    rationale: str
    check_type: Literal["config_pattern", "metric_threshold", "relationship"]
    validation_logic: str  # Python expression or JSONPath query
    severity_if_violated: Literal["critical", "high", "medium", "low"]
    documentation_link: str
    cribl_version_min: Optional[str] = None  # Minimum Cribl version this applies to
    cribl_version_max: Optional[str] = None  # Maximum version (for deprecated rules)
    enabled: bool = True
```

**Example**:
```json
{
  "id": "rule-bp-001",
  "name": "Pipeline functions ordered for efficiency",
  "category": "performance",
  "description": "Filtering functions should appear early in pipelines to reduce data volume processed by downstream functions",
  "rationale": "Processing fewer events through expensive operations (regex, lookups) improves throughput and reduces CPU usage",
  "check_type": "config_pattern",
  "validation_logic": "functions[0].id in ['drop', 'sampling', 'eval'] and 'filter' in functions[0]",
  "severity_if_violated": "medium",
  "documentation_link": "https://docs.cribl.io/stream/pipeline-best-practices#ordering",
  "cribl_version_min": "4.0.0",
  "enabled": true
}
```

---

## Data Validation Rules

### Cross-Entity Validation

1. **AnalysisRun.deployment_id** must reference existing Deployment
2. **Finding.affected_components** should reference WorkerNode IDs or ConfigurationElement names
3. **Recommendation.related_findings** must reference valid Finding IDs
4. **HealthScore.timestamp** must match AnalysisRun.completed_at

### Business Logic Validation

1. **Health scores**: All component scores must be 0-100, overall score derived from components
2. **API call budget**: AnalysisRun.api_calls_used must be ≤ 100
3. **Duration limit**: AnalysisRun.duration_seconds should be ≤ 300 (5 minutes)
4. **Severity mapping**: Critical findings should generate p0/p1 recommendations

### Data Integrity Rules

1. **Immutable IDs**: Entity IDs are immutable once created
2. **Timestamp ordering**: created_at ≤ updated_at for all entities with both
3. **Status consistency**: AnalysisRun status must match presence of completed_at and errors

## Storage Schema

### JSON File Storage (Optional Historical Data)

```text
~/.cribl-hc/
├── deployments/
│   ├── prod-cribl.json           # Deployment metadata
│   └── staging-cribl.json
├── analysis-runs/
│   ├── prod-cribl/
│   │   ├── 2025-12-10_140000.json  # AnalysisRun with all nested entities
│   │   └── 2025-12-09_140000.json
│   └── staging-cribl/
│       └── 2025-12-10_100000.json
└── trends/
    ├── prod-cribl_health_score.json  # HistoricalTrend
    ├── prod-cribl_api_calls.json
    └── staging-cribl_health_score.json
```

### File Format Example

```json
{
  "schema_version": "1.0",
  "entity_type": "AnalysisRun",
  "data": {
    "id": "...",
    "deployment_id": "...",
    ...
  }
}
```

## Migration Strategy

### Version 1.0 → 1.1 (Example)

If fields are added to entities:
- Use Pydantic default values for backward compatibility
- Old JSON files load successfully with new fields set to defaults
- New JSON files include new fields

If fields are removed:
- Mark as deprecated in v1.0, remove in v2.0
- Provide migration script to transform old JSON to new format

## Summary

- **9 core entities** fully defined with Pydantic models
- **Strong validation** at model and business logic levels
- **Clear relationships** between entities
- **JSON serialization** automatic via Pydantic
- **Backward compatibility** strategy for future changes
- **Constitution aligned**: No sensitive data in models, graceful degradation support, transparent methodology
