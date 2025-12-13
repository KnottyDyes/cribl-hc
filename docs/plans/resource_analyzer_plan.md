# ResourceAnalyzer Implementation Plan

## Overview
Implement ResourceAnalyzer for P1 priority: Resource Utilization & Capacity Planning. This analyzer will monitor CPU, memory, and disk usage across worker nodes to detect capacity issues and provide optimization recommendations.

## User Story (P1)
As a Cribl administrator, I need to monitor resource utilization across my worker fleet and receive early warnings about capacity constraints, so I can prevent outages and optimize infrastructure costs.

## Acceptance Criteria
1. Detect CPU usage exceeding safe thresholds (>80% avg, >90% peak)
2. Identify memory pressure and potential OOM risks (>85% usage)
3. Flag disk space issues (>80% used, <10GB free)
4. Provide capacity planning recommendations based on growth trends
5. Detect imbalanced resource distribution across workers
6. Generate actionable remediation steps with cost estimates

## Architecture Pattern (Based on HealthAnalyzer & ConfigAnalyzer)

### File Structure
```
src/cribl_hc/analyzers/
├── resource.py            (NEW - ResourceAnalyzer implementation)
└── __init__.py            (UPDATE - register ResourceAnalyzer)

tests/unit/test_analyzers/
└── test_resource.py       (NEW - ResourceAnalyzer tests)

tests/integration/
└── test_resource_analyzer.py  (NEW - Integration tests)
```

### Class Structure
```python
class ResourceAnalyzer(BaseAnalyzer):
    @property
    def objective_name() -> str: return "resource"

    def get_estimated_api_calls() -> int: return 3

    def get_required_permissions() -> List[str]:
        return ["read:workers", "read:metrics", "read:system"]

    async def analyze(client: CriblAPIClient) -> AnalyzerResult:
        # Main analysis orchestration
        # Returns AnalyzerResult with findings and recommendations
```

## Data Sources

### 1. Worker Node Data (`/api/v1/master/workers`)
```json
{
  "id": "worker-01",
  "status": "healthy",
  "info": {
    "hostname": "worker-01.example.com",
    "cpus": 8,
    "totalMemory": 34359738368,  // bytes
    "freeMemory": 8589934592,
    "arch": "x64",
    "platform": "linux"
  },
  "metrics": {
    "cpu": {
      "perc": 0.45,  // 45% utilization
      "loadAverage": [2.1, 1.8, 1.5]
    },
    "memory": {
      "rss": 4294967296,  // bytes
      "heapUsed": 2147483648
    }
  },
  "workerProcesses": 4
}
```

### 2. System Metrics (`/api/v1/metrics`)
```json
{
  "throughput": {
    "bytes_in": 1073741824,  // bytes/sec
    "bytes_out": 536870912,
    "events_in": 10000,
    "events_out": 10000
  },
  "workers": {
    "worker-01": {
      "cpu": {"perc": 0.45},
      "memory": {"rss": 4294967296, "total": 34359738368},
      "disk": {
        "used": 107374182400,  // 100GB
        "total": 536870912000,  // 500GB
        "free": 429496729600    // 400GB
      }
    }
  }
}
```

### 3. System Status (`/api/v1/system/status`)
```json
{
  "health": "healthy",
  "version": "4.3.0",
  "uptime": 86400
}
```

## Implementation Steps

### Step 1: Create ResourceAnalyzer Base Structure
**File:** `src/cribl_hc/analyzers/resource.py`

#### 1.1 Define ResourceAnalyzer Class
```python
from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger
from typing import Any, Dict, List

log = get_logger(__name__)

class ResourceAnalyzer(BaseAnalyzer):
    """
    Analyzer for resource utilization and capacity planning.

    Monitors CPU, memory, and disk usage across worker nodes to detect:
    - High CPU utilization (>80% avg, >90% peak)
    - Memory pressure (>85% usage, potential OOM)
    - Disk space constraints (<20% free, <10GB available)
    - Imbalanced resource distribution
    - Capacity planning needs

    Priority: P1 (Critical for preventing outages)
    """

    # Resource thresholds
    CPU_WARNING_THRESHOLD = 0.80    # 80% average CPU
    CPU_CRITICAL_THRESHOLD = 0.90   # 90% peak CPU
    MEMORY_WARNING_THRESHOLD = 0.85 # 85% memory usage
    MEMORY_CRITICAL_THRESHOLD = 0.95 # 95% memory usage
    DISK_WARNING_THRESHOLD = 0.80   # 80% disk usage
    DISK_CRITICAL_THRESHOLD = 0.90  # 90% disk usage
    DISK_MIN_FREE_GB = 10.0         # Minimum 10GB free space

    @property
    def objective_name(self) -> str:
        return "resource"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: workers(1) + metrics(1) + system(1) = 3"""
        return 3

    def get_required_permissions(self) -> List[str]:
        return ["read:workers", "read:metrics", "read:system"]
```

#### 1.2 Implement Main analyze() Method
```python
async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
    """
    Analyze resource utilization across worker fleet.

    Args:
        client: Authenticated Cribl API client

    Returns:
        AnalyzerResult with resource findings and capacity recommendations
    """
    result = AnalyzerResult(objective="resource")

    try:
        self.log.info("resource_analysis_started")

        # 1. Fetch resource data
        workers = await self._fetch_workers(client)
        metrics = await self._fetch_metrics(client)
        system_status = await self._fetch_system_status(client)

        result.metadata["worker_count"] = len(workers)
        result.metadata["analysis_timestamp"] = datetime.utcnow().isoformat()

        # 2. Analyze resource utilization
        self._analyze_cpu_utilization(workers, metrics, result)
        self._analyze_memory_utilization(workers, metrics, result)
        self._analyze_disk_utilization(workers, metrics, result)

        # 3. Detect imbalances and bottlenecks
        self._detect_resource_imbalances(workers, result)

        # 4. Calculate resource health score
        resource_score = self._calculate_resource_health_score(result)
        result.metadata["resource_health_score"] = resource_score

        # 5. Generate capacity planning recommendations
        self._generate_capacity_recommendations(workers, metrics, result)

        # 6. Add summary statistics
        self._add_resource_summary(workers, metrics, result)

        self.log.info("resource_analysis_completed",
                     findings=len(result.findings),
                     recommendations=len(result.recommendations),
                     health_score=resource_score)

    except Exception as e:
        self.log.error("resource_analysis_failed", error=str(e))
        result.success = True  # Graceful degradation
        result.add_finding(
            Finding(
                id="resource-analysis-error",
                category="resource",
                severity="medium",
                title="Resource Analysis Incomplete",
                description=f"Analysis failed: {str(e)}",
                affected_components=["resource-analyzer"],
                remediation_steps=["Check API connectivity", "Verify permissions"],
                confidence_level="high"
            )
        )

    return result
```

### Step 2: Implement Data Fetching Methods

#### 2.1 _fetch_workers()
```python
async def _fetch_workers(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
    """Fetch worker node data from API."""
    try:
        workers = await client.get_workers()
        self.log.debug("workers_fetched", count=len(workers))
        return workers
    except Exception as e:
        self.log.error("workers_fetch_failed", error=str(e))
        return []
```

#### 2.2 _fetch_metrics()
```python
async def _fetch_metrics(self, client: CriblAPIClient) -> Dict[str, Any]:
    """Fetch system metrics from API."""
    try:
        metrics = await client.get_metrics(time_range="1h")
        self.log.debug("metrics_fetched")
        return metrics
    except Exception as e:
        self.log.error("metrics_fetch_failed", error=str(e))
        return {}
```

#### 2.3 _fetch_system_status()
```python
async def _fetch_system_status(self, client: CriblAPIClient) -> Dict[str, Any]:
    """Fetch system status from API."""
    try:
        status = await client.get_system_status()
        self.log.debug("system_status_fetched")
        return status
    except Exception as e:
        self.log.warning("system_status_fetch_failed", error=str(e))
        return {}  # Optional - graceful degradation
```

### Step 3: Implement Resource Analysis Methods

#### 3.1 _analyze_cpu_utilization()
```python
def _analyze_cpu_utilization(
    self,
    workers: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result: AnalyzerResult
) -> None:
    """
    Analyze CPU utilization across workers.

    Detects:
    - High average CPU (>80%)
    - Peak CPU spikes (>90%)
    - Load average concerns
    """
    for worker in workers:
        worker_id = worker.get("id", "unknown")
        metrics_data = worker.get("metrics", {})
        cpu_data = metrics_data.get("cpu", {})

        cpu_perc = cpu_data.get("perc", 0)
        load_avg = cpu_data.get("loadAverage", [0, 0, 0])

        info = worker.get("info", {})
        total_cpus = info.get("cpus", 1)

        # Check CPU percentage
        if cpu_perc >= self.CPU_CRITICAL_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"resource-cpu-critical-{worker_id}",
                    category="resource",
                    severity="high",
                    title=f"Critical CPU Utilization: {worker_id}",
                    description=f"Worker '{worker_id}' CPU at {cpu_perc*100:.1f}% (critical threshold: {self.CPU_CRITICAL_THRESHOLD*100:.0f}%)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "Add more worker processes if CPU count allows",
                        "Scale horizontally by adding worker nodes",
                        "Review pipeline complexity and optimize",
                        "Consider upgrading to larger instance type"
                    ],
                    estimated_impact="Risk of dropped events and processing delays",
                    confidence_level="high",
                    metadata={
                        "cpu_utilization": cpu_perc,
                        "total_cpus": total_cpus,
                        "load_average": load_avg
                    }
                )
            )
        elif cpu_perc >= self.CPU_WARNING_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"resource-cpu-warning-{worker_id}",
                    category="resource",
                    severity="medium",
                    title=f"High CPU Utilization: {worker_id}",
                    description=f"Worker '{worker_id}' CPU at {cpu_perc*100:.1f}% (warning threshold: {self.CPU_WARNING_THRESHOLD*100:.0f}%)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "Monitor CPU trends over time",
                        "Plan capacity expansion if trend continues",
                        "Review and optimize resource-intensive pipelines"
                    ],
                    estimated_impact="Approaching capacity limits",
                    confidence_level="high",
                    metadata={
                        "cpu_utilization": cpu_perc,
                        "total_cpus": total_cpus
                    }
                )
            )

        # Check load average vs CPU count
        if load_avg and load_avg[0] > total_cpus * 2:
            result.add_finding(
                Finding(
                    id=f"resource-cpu-load-{worker_id}",
                    category="resource",
                    severity="medium",
                    title=f"High Load Average: {worker_id}",
                    description=f"Load average ({load_avg[0]:.2f}) exceeds 2x CPU count ({total_cpus})",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "Investigate processes causing high load",
                        "Consider increasing worker processes",
                        "Review I/O-bound operations"
                    ],
                    confidence_level="medium"
                )
            )
```

#### 3.2 _analyze_memory_utilization()
```python
def _analyze_memory_utilization(
    self,
    workers: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result: AnalyzerResult
) -> None:
    """
    Analyze memory utilization across workers.

    Detects:
    - High memory usage (>85%)
    - Critical memory pressure (>95%)
    - Potential OOM risks
    """
    for worker in workers:
        worker_id = worker.get("id", "unknown")
        info = worker.get("info", {})

        total_memory = info.get("totalMemory", 0)
        free_memory = info.get("freeMemory", 0)

        if total_memory == 0:
            continue

        used_memory = total_memory - free_memory
        memory_perc = used_memory / total_memory

        # Convert to GB for human-readable messages
        total_gb = total_memory / (1024**3)
        used_gb = used_memory / (1024**3)
        free_gb = free_memory / (1024**3)

        if memory_perc >= self.MEMORY_CRITICAL_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"resource-memory-critical-{worker_id}",
                    category="resource",
                    severity="critical",
                    title=f"Critical Memory Pressure: {worker_id}",
                    description=f"Worker '{worker_id}' memory at {memory_perc*100:.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB used)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "URGENT: Risk of OOM killer terminating processes",
                        "Add more worker nodes immediately",
                        "Upgrade instance to larger memory size",
                        "Review memory leaks in custom functions"
                    ],
                    estimated_impact="Imminent risk of process termination and data loss",
                    confidence_level="high",
                    metadata={
                        "memory_utilization": memory_perc,
                        "used_gb": round(used_gb, 2),
                        "total_gb": round(total_gb, 2),
                        "free_gb": round(free_gb, 2)
                    }
                )
            )
        elif memory_perc >= self.MEMORY_WARNING_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"resource-memory-warning-{worker_id}",
                    category="resource",
                    severity="high",
                    title=f"High Memory Utilization: {worker_id}",
                    description=f"Worker '{worker_id}' memory at {memory_perc*100:.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB used)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "Plan memory capacity expansion",
                        "Monitor memory trends closely",
                        "Review memory-intensive pipeline operations",
                        "Consider adding worker nodes"
                    ],
                    estimated_impact="Approaching memory limits, risk of OOM",
                    confidence_level="high",
                    metadata={
                        "memory_utilization": memory_perc,
                        "used_gb": round(used_gb, 2),
                        "total_gb": round(total_gb, 2)
                    }
                )
            )
```

#### 3.3 _analyze_disk_utilization()
```python
def _analyze_disk_utilization(
    self,
    workers: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result: AnalyzerResult
) -> None:
    """
    Analyze disk utilization from metrics.

    Detects:
    - High disk usage (>80%)
    - Critical disk space (<10GB free)
    - Risk of disk full errors
    """
    # Disk metrics are typically in the metrics response
    worker_metrics = metrics.get("workers", {})

    for worker_id, worker_data in worker_metrics.items():
        disk_data = worker_data.get("disk", {})

        total_bytes = disk_data.get("total", 0)
        used_bytes = disk_data.get("used", 0)
        free_bytes = disk_data.get("free", 0)

        if total_bytes == 0:
            continue

        disk_perc = used_bytes / total_bytes
        free_gb = free_bytes / (1024**3)
        total_gb = total_bytes / (1024**3)
        used_gb = used_bytes / (1024**3)

        # Check critical free space
        if free_gb < self.DISK_MIN_FREE_GB:
            result.add_finding(
                Finding(
                    id=f"resource-disk-critical-{worker_id}",
                    category="resource",
                    severity="critical",
                    title=f"Critical Disk Space: {worker_id}",
                    description=f"Worker '{worker_id}' has only {free_gb:.1f}GB free (minimum: {self.DISK_MIN_FREE_GB}GB)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "URGENT: Add disk capacity immediately",
                        "Clean up old logs and temporary files",
                        "Review persistent queue sizes",
                        "Enable log rotation if not configured"
                    ],
                    estimated_impact="Risk of disk full errors causing data loss",
                    confidence_level="high",
                    metadata={
                        "free_gb": round(free_gb, 2),
                        "total_gb": round(total_gb, 2),
                        "used_perc": round(disk_perc * 100, 1)
                    }
                )
            )
        elif disk_perc >= self.DISK_CRITICAL_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"resource-disk-critical-perc-{worker_id}",
                    category="resource",
                    severity="high",
                    title=f"Critical Disk Utilization: {worker_id}",
                    description=f"Worker '{worker_id}' disk at {disk_perc*100:.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB used)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "Expand disk capacity",
                        "Archive or delete old data",
                        "Review persistent queue configuration"
                    ],
                    estimated_impact="Risk of disk full errors",
                    confidence_level="high"
                )
            )
        elif disk_perc >= self.DISK_WARNING_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"resource-disk-warning-{worker_id}",
                    category="resource",
                    severity="medium",
                    title=f"High Disk Utilization: {worker_id}",
                    description=f"Worker '{worker_id}' disk at {disk_perc*100:.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB used)",
                    affected_components=[f"worker-{worker_id}"],
                    remediation_steps=[
                        "Plan disk capacity expansion",
                        "Monitor disk growth trends",
                        "Review data retention policies"
                    ],
                    estimated_impact="Approaching disk capacity limits",
                    confidence_level="medium"
                )
            )
```

#### 3.4 _detect_resource_imbalances()
```python
def _detect_resource_imbalances(
    self,
    workers: List[Dict[str, Any]],
    result: AnalyzerResult
) -> None:
    """
    Detect imbalanced resource distribution across workers.

    Identifies scenarios where some workers are overloaded while others are underutilized.
    """
    if len(workers) < 2:
        return  # Need at least 2 workers to detect imbalance

    cpu_utilizations = []
    memory_utilizations = []

    for worker in workers:
        metrics_data = worker.get("metrics", {})
        cpu_data = metrics_data.get("cpu", {})
        cpu_perc = cpu_data.get("perc", 0)

        info = worker.get("info", {})
        total_memory = info.get("totalMemory", 0)
        free_memory = info.get("freeMemory", 0)

        if total_memory > 0:
            memory_perc = (total_memory - free_memory) / total_memory
            memory_utilizations.append(memory_perc)

        cpu_utilizations.append(cpu_perc)

    # Calculate standard deviation
    if cpu_utilizations:
        cpu_avg = sum(cpu_utilizations) / len(cpu_utilizations)
        cpu_variance = sum((x - cpu_avg) ** 2 for x in cpu_utilizations) / len(cpu_utilizations)
        cpu_stddev = cpu_variance ** 0.5

        # If standard deviation > 0.2 (20%), there's significant imbalance
        if cpu_stddev > 0.2:
            result.add_finding(
                Finding(
                    id="resource-cpu-imbalance",
                    category="resource",
                    severity="medium",
                    title="Imbalanced CPU Distribution Across Workers",
                    description=f"CPU utilization varies significantly across workers (stddev: {cpu_stddev*100:.1f}%)",
                    affected_components=["worker-fleet"],
                    remediation_steps=[
                        "Review load balancing configuration",
                        "Check if specific routes are sending to specific workers",
                        "Ensure workers have similar capacity",
                        "Consider adjusting routing rules"
                    ],
                    estimated_impact="Inefficient resource utilization",
                    confidence_level="medium",
                    metadata={
                        "cpu_stddev": round(cpu_stddev, 3),
                        "cpu_avg": round(cpu_avg, 3),
                        "worker_count": len(workers)
                    }
                )
            )
```

#### 3.5 _calculate_resource_health_score()
```python
def _calculate_resource_health_score(self, result: AnalyzerResult) -> float:
    """
    Calculate resource health score (0-100).

    Higher score = better resource health.
    Deductions based on severity of resource findings.
    """
    base_score = 100.0

    for finding in result.findings:
        if finding.category != "resource":
            continue

        if finding.severity == "critical":
            base_score -= 25
        elif finding.severity == "high":
            base_score -= 15
        elif finding.severity == "medium":
            base_score -= 8
        elif finding.severity == "low":
            base_score -= 3

    return max(0.0, round(base_score, 2))
```

#### 3.6 _generate_capacity_recommendations()
```python
def _generate_capacity_recommendations(
    self,
    workers: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result: AnalyzerResult
) -> None:
    """Generate capacity planning recommendations based on resource findings."""

    # Check if we have high-severity resource findings
    high_cpu_findings = [f for f in result.findings if "cpu" in f.id and f.severity in ["high", "critical"]]
    high_memory_findings = [f for f in result.findings if "memory" in f.id and f.severity in ["high", "critical"]]
    high_disk_findings = [f for f in result.findings if "disk" in f.id and f.severity in ["high", "critical"]]

    # CPU capacity recommendation
    if high_cpu_findings:
        result.add_recommendation(
            Recommendation(
                id="rec-resource-cpu-capacity",
                type="capacity",
                priority="p1",
                title="Expand CPU Capacity",
                description=f"Add worker nodes or increase CPU allocation to address {len(high_cpu_findings)} worker(s) with high CPU utilization",
                rationale="High CPU utilization increases risk of dropped events and processing delays",
                implementation_steps=[
                    "Review current worker CPU utilization trends",
                    "Calculate required additional capacity (recommend 20% headroom)",
                    "Choose scaling approach: horizontal (add nodes) or vertical (larger instances)",
                    "Test with additional worker node in non-production",
                    "Deploy additional capacity during low-traffic window"
                ],
                before_state=f"{len(high_cpu_findings)} workers experiencing high CPU utilization",
                after_state="All workers below 70% CPU utilization with capacity for growth",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Reduced event processing latency, eliminated drop risk",
                    cost_impact="Estimated $X/month for additional worker nodes",
                    time_to_implement="2-4 hours"
                ),
                implementation_effort="medium",
                related_findings=[f.id for f in high_cpu_findings],
                documentation_links=[
                    "https://docs.cribl.io/stream/scaling-worker-processes/",
                    "https://docs.cribl.io/stream/capacity-planning/"
                ]
            )
        )

    # Memory capacity recommendation
    if high_memory_findings:
        result.add_recommendation(
            Recommendation(
                id="rec-resource-memory-capacity",
                type="capacity",
                priority="p1",
                title="Expand Memory Capacity",
                description=f"Increase memory allocation to address {len(high_memory_findings)} worker(s) with high memory utilization",
                rationale="High memory utilization increases risk of OOM killer terminating processes",
                implementation_steps=[
                    "Identify workers approaching memory limits",
                    "Upgrade to instance types with more RAM",
                    "Distribute load across more worker nodes",
                    "Review memory-intensive pipeline functions"
                ],
                before_state=f"{len(high_memory_findings)} workers experiencing memory pressure",
                after_state="All workers below 75% memory utilization",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Eliminated OOM risk, stable processing",
                    cost_impact="Estimated $Y/month for larger instances",
                    time_to_implement="1-2 hours"
                ),
                implementation_effort="medium",
                related_findings=[f.id for f in high_memory_findings],
                documentation_links=["https://docs.cribl.io/stream/memory-management/"]
            )
        )

    # Disk capacity recommendation
    if high_disk_findings:
        result.add_recommendation(
            Recommendation(
                id="rec-resource-disk-capacity",
                type="capacity",
                priority="p1",
                title="Expand Disk Capacity",
                description=f"Add disk space to {len(high_disk_findings)} worker(s) approaching disk limits",
                rationale="Full disks cause data loss and processing failures",
                implementation_steps=[
                    "Expand disk volumes for affected workers",
                    "Enable log rotation and cleanup policies",
                    "Review persistent queue sizes",
                    "Implement disk space monitoring alerts"
                ],
                before_state=f"{len(high_disk_findings)} workers with disk space concerns",
                after_state="All workers with >30% free disk space",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Eliminated disk full risk",
                    cost_impact="Estimated $Z/month for additional storage",
                    time_to_implement="30 minutes - 1 hour"
                ),
                implementation_effort="low",
                related_findings=[f.id for f in high_disk_findings],
                documentation_links=["https://docs.cribl.io/stream/persistent-queues/"]
            )
        )
```

#### 3.7 _add_resource_summary()
```python
def _add_resource_summary(
    self,
    workers: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    result: AnalyzerResult
) -> None:
    """Add summary statistics to metadata."""

    total_cpus = 0
    total_memory_gb = 0
    avg_cpu = 0
    avg_memory = 0

    for worker in workers:
        info = worker.get("info", {})
        total_cpus += info.get("cpus", 0)
        total_memory_gb += info.get("totalMemory", 0) / (1024**3)

        metrics_data = worker.get("metrics", {})
        cpu_data = metrics_data.get("cpu", {})
        avg_cpu += cpu_data.get("perc", 0)

        total_mem = info.get("totalMemory", 0)
        free_mem = info.get("freeMemory", 0)
        if total_mem > 0:
            avg_memory += (total_mem - free_mem) / total_mem

    worker_count = len(workers)
    if worker_count > 0:
        avg_cpu /= worker_count
        avg_memory /= worker_count

    result.metadata.update({
        "total_cpus": total_cpus,
        "total_memory_gb": round(total_memory_gb, 2),
        "avg_cpu_utilization": round(avg_cpu * 100, 1),
        "avg_memory_utilization": round(avg_memory * 100, 1),
        "critical_findings": len([f for f in result.findings if f.severity == "critical"]),
        "high_findings": len([f for f in result.findings if f.severity == "high"]),
        "medium_findings": len([f for f in result.findings if f.severity == "medium"]),
        "low_findings": len([f for f in result.findings if f.severity == "low"])
    })
```

### Step 4: Register Analyzer

**File:** `src/cribl_hc/analyzers/__init__.py`

```python
from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.analyzers.config import ConfigAnalyzer
from cribl_hc.analyzers.resource import ResourceAnalyzer  # NEW

# Register analyzers
register_analyzer(HealthAnalyzer)
register_analyzer(ConfigAnalyzer)
register_analyzer(ResourceAnalyzer)  # NEW
```

## API Calls Budget

**Estimated API Calls:** 3
1. `client.get_workers()` - 1 call (worker node data with CPU/memory)
2. `client.get_metrics(time_range="1h")` - 1 call (detailed metrics including disk)
3. `client.get_system_status()` - 1 call (optional system health)

**Total:** 3 calls (3% of 100-call budget)

## Threshold Reference

| Resource | Warning | Critical | Rationale |
|----------|---------|----------|-----------|
| CPU | >80% avg | >90% peak | Processing delays, event drops |
| Memory | >85% | >95% | OOM killer risk |
| Disk Usage | >80% | >90% | Disk full errors |
| Disk Free | <20GB | <10GB | Minimum for ops |
| Load Avg | >1.5x CPUs | >2x CPUs | Queue buildup |

## Severity Mapping

| Issue Type | Severity | Rationale |
|-----------|----------|-----------|
| Memory >95% | CRITICAL | Imminent OOM risk |
| Disk <10GB free | CRITICAL | Imminent disk full |
| CPU >90% | HIGH | Drop risk |
| Memory >85% | HIGH | OOM risk |
| Disk >90% | HIGH | Disk full risk |
| CPU >80% | MEDIUM | Capacity planning needed |
| Imbalanced distribution | MEDIUM | Inefficiency |
| Disk >80% | MEDIUM | Monitor trends |

## Success Criteria

- [ ] ResourceAnalyzer registered and accessible
- [ ] All 6 acceptance criteria met
- [ ] Unit tests pass (15+ tests)
- [ ] Integration tests pass
- [ ] Real deployment test shows actionable findings
- [ ] API calls ≤3
- [ ] Follows HealthAnalyzer/ConfigAnalyzer patterns
- [ ] Graceful degradation on errors

## Implementation Order

1. ✅ Create implementation plan
2. Create ResourceAnalyzer skeleton
3. Implement data fetching methods
4. Implement CPU analysis
5. Implement memory analysis
6. Implement disk analysis
7. Implement imbalance detection
8. Implement scoring and recommendations
9. Register analyzer
10. Write unit tests
11. Write integration tests
12. Test against real deployment

## Estimated Effort

- **Implementation:** 2-3 hours
- **Testing:** 1 hour
- **Integration validation:** 30 minutes
- **Total:** 3.5-4.5 hours
