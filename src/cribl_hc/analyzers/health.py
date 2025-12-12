"""
Health analyzer for assessing overall system health and worker status.

This analyzer focuses on:
- Worker health monitoring (CPU, memory, disk usage)
- Critical issue identification
- Overall system health scoring
"""

from typing import Any, Dict, List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class HealthAnalyzer(BaseAnalyzer):
    """
    Analyzer for overall health assessment and worker monitoring.

    Evaluates:
    - Worker health (CPU, memory, disk)
    - System availability
    - Critical issues requiring immediate attention

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = HealthAnalyzer()
        ...     result = await analyzer.analyze(client)
        ...     print(f"Health score: {result.metadata['health_score']}")
    """

    @property
    def objective_name(self) -> str:
        """Return 'health' as the objective name."""
        return "health"

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Overall health assessment, worker monitoring, and critical issue identification"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls needed."""
        return 3  # workers, system status, metrics

    def get_required_permissions(self) -> List[str]:
        """List required API permissions."""
        return [
            "read:workers",
            "read:system",
            "read:metrics",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform health analysis on Cribl Stream deployment.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with health findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            self.log.info("health_analysis_started")

            # Fetch worker data
            workers = await self._fetch_workers(client)
            result.metadata["worker_count"] = len(workers)

            # Fetch system status (may not be available on Cribl Cloud)
            system_status = await self._fetch_system_status(client)

            # Get Cribl version from workers if system status not available
            if workers:
                cribl_version = workers[0].get("info", {}).get("cribl", {}).get("version", "unknown")
                result.metadata["cribl_version"] = cribl_version
            else:
                result.metadata["cribl_version"] = system_status.get("version", "unknown")

            # Analyze worker health
            unhealthy_workers = self._analyze_worker_health(workers, result)
            result.metadata["unhealthy_workers"] = len(unhealthy_workers)

            # Calculate overall health score
            health_score = self._calculate_health_score(workers, unhealthy_workers)
            result.metadata["health_score"] = health_score
            result.metadata["health_status"] = self._get_health_status(health_score)

            # Add overall health finding
            self._add_overall_health_finding(result, health_score, len(workers), len(unhealthy_workers))

            # Generate recommendations for unhealthy workers
            if unhealthy_workers:
                self._generate_worker_recommendations(result, unhealthy_workers)

            self.log.info(
                "health_analysis_completed",
                health_score=health_score,
                workers=len(workers),
                unhealthy=len(unhealthy_workers),
                findings=len(result.findings),
            )

        except Exception as e:
            self.log.error("health_analysis_failed", error=str(e))
            result.success = False
            result.error = f"Health analysis failed: {str(e)}"

            # Add error finding
            result.add_finding(
                Finding(
                    id="health-analysis-error",
                    title="Health Analysis Failed",
                    description=f"Unable to complete health analysis: {str(e)}",
                    severity="high",
                    category="health",
                    confidence_level="high",
                    affected_components=["health_analyzer"],
                    estimated_impact="Unable to assess system health",
                    remediation_steps=[
                        "Check API connectivity",
                        "Verify authentication token is valid",
                        "Review error logs for details",
                    ],
                    metadata={"error": str(e)},
                )
            )

        return result

    async def _fetch_workers(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch worker data from API."""
        try:
            workers = await client.get_workers()
            self.log.debug("workers_fetched", count=len(workers))
            return workers
        except Exception as e:
            self.log.error("workers_fetch_failed", error=str(e))
            return []

    async def _fetch_system_status(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch system status from API."""
        try:
            status = await client.get_system_status()
            self.log.debug("system_status_fetched")
            return status
        except Exception as e:
            self.log.error("system_status_fetch_failed", error=str(e))
            return {}

    def _analyze_worker_health(
        self,
        workers: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> List[Dict[str, Any]]:
        """
        Analyze worker health and generate findings.

        A worker is considered unhealthy if:
        - Status is not "healthy"
        - Disk usage > 90%
        - Worker is disconnected

        Returns:
            List of unhealthy workers
        """
        unhealthy_workers = []

        for worker in workers:
            worker_id = worker.get("id", "unknown")
            issues = []

            # Check worker status
            status = worker.get("status", "unknown")
            if status != "healthy":
                issues.append(f"Status: {status}")

            # Check if disconnected
            if worker.get("disconnected", False):
                issues.append("Disconnected")

            # Calculate disk usage from available data
            info = worker.get("info", {})
            total_disk = info.get("totalDiskSpace", 0)
            free_disk = info.get("freeDiskSpace", 0)

            if total_disk > 0:
                used_disk = total_disk - free_disk
                disk_usage_percent = (used_disk / total_disk) * 100

                if disk_usage_percent > 90:
                    issues.append(f"Disk: {disk_usage_percent:.1f}%")
            else:
                # No disk data available
                disk_usage_percent = 0

            # If worker has issues, create finding
            if issues:
                unhealthy_workers.append(worker)

                severity = "critical" if len(issues) >= 2 else "high"

                # Get worker info for metadata
                hostname = info.get("hostname", "unknown")
                worker_group = worker.get("group", "default")

                result.add_finding(
                    Finding(
                        id=f"health-worker-{worker_id}",
                        title=f"Unhealthy Worker: {hostname}",
                        description=f"Worker {hostname} (group: {worker_group}) has {len(issues)} health issue(s): {', '.join(issues)}",
                        severity=severity,
                        category="health",
                        confidence_level="high",
                        affected_components=[worker_id],
                        estimated_impact=f"Worker performance degraded - {', '.join(issues)}",
                        remediation_steps=[
                            "Review worker status and logs",
                            "Check worker connectivity to leader",
                            "Monitor disk space usage",
                        ],
                        metadata={
                            "worker_id": worker_id,
                            "hostname": hostname,
                            "group": worker_group,
                            "status": status,
                            "disconnected": worker.get("disconnected", False),
                            "disk_usage_percent": disk_usage_percent if total_disk > 0 else None,
                            "disk_total_gb": total_disk / (1024**3) if total_disk > 0 else None,
                            "disk_free_gb": free_disk / (1024**3) if free_disk > 0 else None,
                            "issues": issues,
                        },
                    )
                )

        return unhealthy_workers

    def _calculate_health_score(
        self,
        workers: List[Dict[str, Any]],
        unhealthy_workers: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate overall health score (0-100).

        Scoring:
        - 100: All workers healthy
        - 75-99: Some workers with single issues
        - 50-74: Multiple workers with issues
        - 0-49: Critical - multiple workers with multiple issues

        Returns:
            Health score between 0 and 100
        """
        if not workers:
            return 0.0

        healthy_ratio = (len(workers) - len(unhealthy_workers)) / len(workers)

        # Base score from healthy ratio
        base_score = healthy_ratio * 100

        # Penalty for severity of issues
        if unhealthy_workers:
            critical_count = sum(
                1 for w in unhealthy_workers
                if self._count_worker_issues(w) >= 2
            )

            # Deduct points for critical workers
            penalty = (critical_count / len(workers)) * 30
            base_score = max(0, base_score - penalty)

        return round(base_score, 2)

    def _count_worker_issues(self, worker: Dict[str, Any]) -> int:
        """Count number of issues for a worker."""
        issues = 0

        # Check status
        if worker.get("status") != "healthy":
            issues += 1

        # Check if disconnected
        if worker.get("disconnected", False):
            issues += 1

        # Check disk usage
        info = worker.get("info", {})
        total_disk = info.get("totalDiskSpace", 0)
        free_disk = info.get("freeDiskSpace", 0)

        if total_disk > 0:
            used_disk = total_disk - free_disk
            disk_usage_percent = (used_disk / total_disk) * 100
            if disk_usage_percent > 90:
                issues += 1

        return issues

    def _get_health_status(self, score: float) -> str:
        """Convert health score to status string."""
        if score >= 90:
            return "healthy"
        elif score >= 70:
            return "degraded"
        elif score >= 50:
            return "unhealthy"
        else:
            return "critical"

    def _add_overall_health_finding(
        self,
        result: AnalyzerResult,
        health_score: float,
        total_workers: int,
        unhealthy_count: int,
    ) -> None:
        """Add overall health summary finding."""
        status = self._get_health_status(health_score)

        if status == "healthy":
            severity = "info"
            title = "System Health: Good"
            description = f"All {total_workers} workers are operating normally with a health score of {health_score}/100"
            remediation_steps = []
        elif status == "degraded":
            severity = "medium"
            title = "System Health: Degraded"
            description = f"{unhealthy_count}/{total_workers} workers have health issues (health score: {health_score}/100)"
            remediation_steps = [
                "Review worker health findings below",
                "Address resource constraints on affected workers",
                "Monitor system performance trends",
            ]
        elif status == "unhealthy":
            severity = "high"
            title = "System Health: Unhealthy"
            description = f"{unhealthy_count}/{total_workers} workers require attention (health score: {health_score}/100)"
            remediation_steps = [
                "Immediately review worker health findings",
                "Scale worker resources or add capacity",
                "Investigate root cause of resource pressure",
            ]
        else:  # critical
            severity = "critical"
            title = "System Health: Critical"
            description = f"{unhealthy_count}/{total_workers} workers in critical state (health score: {health_score}/100)"
            remediation_steps = [
                "Urgent: Review all worker health findings",
                "Immediate action required to prevent service degradation",
                "Consider emergency scaling or traffic reduction",
            ]

        result.add_finding(
            Finding(
                id=f"health-overall-{status}",
                title=title,
                description=description,
                severity=severity,
                category="health",
                confidence_level="high",
                affected_components=["overall_health"],
                estimated_impact=f"Overall system health: {health_score}/100",
                remediation_steps=remediation_steps,
                metadata={
                    "health_score": health_score,
                    "total_workers": total_workers,
                    "unhealthy_workers": unhealthy_count,
                    "status": status,
                },
            )
        )

    def _generate_worker_recommendations(
        self,
        result: AnalyzerResult,
        unhealthy_workers: List[Dict[str, Any]],
    ) -> None:
        """Generate recommendations for unhealthy workers."""
        for worker in unhealthy_workers:
            worker_id = worker.get("id", "unknown")
            info = worker.get("info", {})
            hostname = info.get("hostname", "unknown")
            status = worker.get("status", "unknown")
            disconnected = worker.get("disconnected", False)

            steps = []

            # Status recommendations
            if status != "healthy":
                steps.append(f"Investigate why worker status is '{status}'")
                steps.append("Review worker logs for errors or warnings")
                steps.append("Check worker connectivity to leader")

            # Disconnection recommendations
            if disconnected:
                steps.append("Verify network connectivity between worker and leader")
                steps.append("Check worker process health")
                steps.append("Review firewall rules and network configuration")

            # Disk recommendations
            total_disk = info.get("totalDiskSpace", 0)
            free_disk = info.get("freeDiskSpace", 0)

            if total_disk > 0:
                used_disk = total_disk - free_disk
                disk_usage_percent = (used_disk / total_disk) * 100

                if disk_usage_percent > 90:
                    steps.append("Clean up old persistent queues and logs")
                    steps.append("Review disk space allocation for worker node")
                    steps.append("Configure log rotation and retention policies")
                    steps.append(f"Current disk usage: {disk_usage_percent:.1f}%")

            # Convert priority to p0/p1/p2/p3 format
            priority_level = "p1" if self._count_worker_issues(worker) >= 2 else "p2"

            result.add_recommendation(
                Recommendation(
                    id=f"rec-health-worker-{worker_id}",
                    type="worker_health",
                    priority=priority_level,
                    title=f"Remediate Worker Health: {worker_id}",
                    description=f"Address health issues on worker {worker_id}",
                    rationale=f"Worker has resource constraints that may impact performance",
                    implementation_steps=steps,
                    before_state=f"Worker experiencing resource constraints",
                    after_state="Worker operating within normal resource limits",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Improved worker stability and throughput"
                    ),
                    implementation_effort="medium",
                    related_findings=[f"health-worker-{worker_id}"],
                    documentation_links=[
                        "https://docs.cribl.io/stream/scaling/",
                        "https://docs.cribl.io/stream/monitoring/",
                    ],
                )
            )
