"""
Resource Utilization Analyzer for Cribl Health Check.

Monitors CPU, memory, and disk usage across worker nodes to detect capacity
issues and provide optimization recommendations.

Priority: P1 (Critical for preventing outages)
"""

from datetime import datetime
from typing import Any, Dict, List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class ResourceAnalyzer(BaseAnalyzer):
    """
    Analyzer for resource utilization and capacity planning.

    Monitors CPU, memory, and disk usage across worker nodes to detect:
    - High CPU utilization (>80% avg, >90% peak)
    - Memory pressure (>85% usage, potential OOM)
    - Disk space constraints (<20% free, <10GB available) - Self-hosted only
    - Imbalanced resource distribution
    - Capacity planning needs

    Note: Disk metrics are only available for self-hosted deployments.
    Cribl Cloud deployments skip disk analysis as these metrics are not
    exposed via the API.

    Priority: P1 (Critical for preventing outages)

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = ResourceAnalyzer()
        ...     result = await analyzer.analyze(client)
        ...     print(f"Resource Health: {result.metadata['resource_health_score']}/100")
    """

    # Resource thresholds
    CPU_WARNING_THRESHOLD = 0.80  # 80% average CPU
    CPU_CRITICAL_THRESHOLD = 0.90  # 90% peak CPU
    MEMORY_WARNING_THRESHOLD = 0.85  # 85% memory usage
    MEMORY_CRITICAL_THRESHOLD = 0.95  # 95% memory usage
    DISK_WARNING_THRESHOLD = 0.80  # 80% disk usage
    DISK_CRITICAL_THRESHOLD = 0.90  # 90% disk usage
    DISK_MIN_FREE_GB = 10.0  # Minimum 10GB free space

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "resource"

    @property
    def supported_products(self) -> List[str]:
        """Resource analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: workers(1) + metrics(1) + system(1) = 3."""
        return 3

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return ["read:workers", "read:metrics", "read:system"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze resource utilization across worker fleet or Edge nodes.

        Automatically adapts based on detected product type (Stream or Edge).

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with resource findings and capacity recommendations
        """
        result = AnalyzerResult(objective="resource")

        try:
            # Detect product type
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            self.log.info("resource_analysis_started", product=client.product_type, product_name=product_name)

            # 1. Fetch resource data (unified API works for both Stream and Edge)
            workers = await self._fetch_workers(client)
            metrics = await self._fetch_metrics(client)
            system_status = await self._fetch_system_status(client)

            result.metadata["worker_count"] = len(workers)
            result.metadata["analysis_timestamp"] = datetime.utcnow().isoformat()
            result.metadata["product_type"] = client.product_type

            # 2. Analyze resource utilization
            self._analyze_cpu_utilization(workers, metrics, result)
            self._analyze_memory_utilization(workers, metrics, result)

            # Disk metrics are not available in Cribl Cloud
            if not client.is_cloud:
                self._analyze_disk_utilization(workers, metrics, result)
            else:
                self.log.debug("skipping_disk_metrics", reason="not_available_in_cribl_cloud")
                result.metadata["disk_metrics_skipped"] = True
                result.metadata["disk_metrics_skip_reason"] = "Disk metrics not available in Cribl Cloud"

            # 3. Detect imbalances and bottlenecks
            self._detect_resource_imbalances(workers, result)

            # 4. Calculate resource health score
            resource_score = self._calculate_resource_health_score(result)
            result.metadata["resource_health_score"] = resource_score

            # 5. Generate capacity planning recommendations
            self._generate_capacity_recommendations(workers, metrics, result)

            # 6. Add summary statistics
            self._add_resource_summary(workers, metrics, result)

            self.log.info(
                "resource_analysis_completed",
                product=client.product_type,
                findings=len(result.findings),
                recommendations=len(result.recommendations),
                health_score=resource_score,
            )

        except Exception as e:
            self.log.error("resource_analysis_failed", product=client.product_type, error=str(e))
            result.success = True  # Graceful degradation
            result.metadata["product_type"] = client.product_type

            # Product-aware error messages
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"

            result.add_finding(
                Finding(
                    id="resource-analysis-error",
                    category="resource",
                    severity="medium",
                    title=f"Resource Analysis Incomplete ({product_name})",
                    description=f"Analysis failed on {product_name}: {str(e)}",
                    affected_components=["resource-analyzer"],
                    remediation_steps=["Check API connectivity", "Verify permissions", f"Review {product_name} API access"],
                    confidence_level="high",
                    metadata={"product_type": client.product_type, "error": str(e)},
                )
            )

        return result

    async def _fetch_workers(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch worker node data from API."""
        try:
            workers = await client.get_workers()
            self.log.debug("workers_fetched", count=len(workers))
            return workers
        except Exception as e:
            self.log.error("workers_fetch_failed", error=str(e))
            return []

    async def _fetch_metrics(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch system metrics from API."""
        try:
            metrics = await client.get_metrics(time_range="1h")
            self.log.debug("metrics_fetched")
            return metrics
        except Exception as e:
            self.log.error("metrics_fetch_failed", error=str(e))
            return {}

    async def _fetch_system_status(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch system status from API."""
        try:
            status = await client.get_system_status()
            self.log.debug("system_status_fetched")
            return status
        except Exception as e:
            self.log.warning("system_status_fetch_failed", error=str(e))
            return {}  # Optional - graceful degradation

    def _analyze_cpu_utilization(
        self,
        workers: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
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
                            "Consider upgrading to larger instance type",
                        ],
                        estimated_impact="Risk of dropped events and processing delays",
                        confidence_level="high",
                        metadata={
                            "cpu_utilization": cpu_perc,
                            "total_cpus": total_cpus,
                            "load_average": load_avg,
                        },
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
                            "Review and optimize resource-intensive pipelines",
                        ],
                        estimated_impact="Approaching capacity limits",
                        confidence_level="high",
                        metadata={"cpu_utilization": cpu_perc, "total_cpus": total_cpus},
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
                            "Review I/O-bound operations",
                        ],
                        confidence_level="medium",
                    )
                )

    def _analyze_memory_utilization(
        self,
        workers: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
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
                            "Review memory leaks in custom functions",
                        ],
                        estimated_impact="Imminent risk of process termination and data loss",
                        confidence_level="high",
                        metadata={
                            "memory_utilization": memory_perc,
                            "used_gb": round(used_gb, 2),
                            "total_gb": round(total_gb, 2),
                            "free_gb": round(free_gb, 2),
                        },
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
                            "Consider adding worker nodes",
                        ],
                        estimated_impact="Approaching memory limits, risk of OOM",
                        confidence_level="high",
                        metadata={
                            "memory_utilization": memory_perc,
                            "used_gb": round(used_gb, 2),
                            "total_gb": round(total_gb, 2),
                        },
                    )
                )

    def _analyze_disk_utilization(
        self,
        workers: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """
        Analyze disk utilization from metrics (self-hosted only).

        Note: This method is only called for self-hosted deployments.
        Cribl Cloud deployments do not expose disk metrics via the API.

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
                            "Enable log rotation if not configured",
                        ],
                        estimated_impact="Risk of disk full errors causing data loss",
                        confidence_level="high",
                        metadata={
                            "free_gb": round(free_gb, 2),
                            "total_gb": round(total_gb, 2),
                            "used_perc": round(disk_perc * 100, 1),
                        },
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
                            "Review persistent queue configuration",
                        ],
                        estimated_impact="Risk of disk full errors",
                        confidence_level="high",
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
                            "Review data retention policies",
                        ],
                        estimated_impact="Approaching disk capacity limits",
                        confidence_level="medium",
                    )
                )

    def _detect_resource_imbalances(
        self, workers: List[Dict[str, Any]], result: AnalyzerResult
    ) -> None:
        """
        Detect imbalanced resource distribution across workers.

        Identifies scenarios where some workers are overloaded while others
        are underutilized.
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
            cpu_variance = (
                sum((x - cpu_avg) ** 2 for x in cpu_utilizations)
                / len(cpu_utilizations)
            )
            cpu_stddev = cpu_variance**0.5

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
                            "Consider adjusting routing rules",
                        ],
                        estimated_impact="Inefficient resource utilization",
                        confidence_level="medium",
                        metadata={
                            "cpu_stddev": round(cpu_stddev, 3),
                            "cpu_avg": round(cpu_avg, 3),
                            "worker_count": len(workers),
                        },
                    )
                )

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

    def _generate_capacity_recommendations(
        self,
        workers: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Generate capacity planning recommendations based on resource findings."""

        # Check if we have high-severity resource findings
        high_cpu_findings = [
            f
            for f in result.findings
            if "cpu" in f.id and f.severity in ["high", "critical"]
        ]
        high_memory_findings = [
            f
            for f in result.findings
            if "memory" in f.id and f.severity in ["high", "critical"]
        ]
        high_disk_findings = [
            f
            for f in result.findings
            if "disk" in f.id and f.severity in ["high", "critical"]
        ]

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
                        "Deploy additional capacity during low-traffic window",
                    ],
                    before_state=f"{len(high_cpu_findings)} workers experiencing high CPU utilization",
                    after_state="All workers below 70% CPU utilization with capacity for growth",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Reduced event processing latency, eliminated drop risk",
                        cost_impact="Additional worker nodes or larger instances",
                        time_to_implement="2-4 hours",
                    ),
                    implementation_effort="medium",
                    related_findings=[f.id for f in high_cpu_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/scaling-worker-processes/",
                        "https://docs.cribl.io/stream/capacity-planning/",
                    ],
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
                        "Review memory-intensive pipeline functions",
                    ],
                    before_state=f"{len(high_memory_findings)} workers experiencing memory pressure",
                    after_state="All workers below 75% memory utilization",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Eliminated OOM risk, stable processing",
                        cost_impact="Larger instance types with more RAM",
                        time_to_implement="1-2 hours",
                    ),
                    implementation_effort="medium",
                    related_findings=[f.id for f in high_memory_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/memory-management/"
                    ],
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
                        "Implement disk space monitoring alerts",
                    ],
                    before_state=f"{len(high_disk_findings)} workers with disk space concerns",
                    after_state="All workers with >30% free disk space",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Eliminated disk full risk",
                        cost_impact="Additional storage volumes",
                        time_to_implement="30 minutes - 1 hour",
                    ),
                    implementation_effort="low",
                    related_findings=[f.id for f in high_disk_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/persistent-queues/"
                    ],
                )
            )

    def _add_resource_summary(
        self,
        workers: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
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

        result.metadata.update(
            {
                "total_cpus": total_cpus,
                "total_memory_gb": round(total_memory_gb, 2),
                "avg_cpu_utilization": round(avg_cpu * 100, 1),
                "avg_memory_utilization": round(avg_memory * 100, 1),
                "critical_findings": len(
                    [f for f in result.findings if f.severity == "critical"]
                ),
                "high_findings": len(
                    [f for f in result.findings if f.severity == "high"]
                ),
                "medium_findings": len(
                    [f for f in result.findings if f.severity == "medium"]
                ),
                "low_findings": len([f for f in result.findings if f.severity == "low"]),
            }
        )
