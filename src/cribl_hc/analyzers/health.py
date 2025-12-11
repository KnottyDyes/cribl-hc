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
from cribl_hc.models.recommendation import Recommendation
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

            # Fetch system status
            system_status = await self._fetch_system_status(client)
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
                    title="Health Analysis Failed",
                    description=f"Unable to complete health analysis: {str(e)}",
                    severity="high",
                    category="system",
                    affected_component="health_analyzer",
                    evidence={"error": str(e)},
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
        - CPU usage > 90%
        - Memory usage > 90%
        - Disk usage > 90%

        Returns:
            List of unhealthy workers
        """
        unhealthy_workers = []

        for worker in workers:
            worker_id = worker.get("id", "unknown")
            issues = []

            # Check CPU usage
            cpu_usage = worker.get("metrics", {}).get("cpu_usage", 0)
            if cpu_usage > 90:
                issues.append(f"CPU: {cpu_usage:.1f}%")

            # Check memory usage
            memory_usage = worker.get("metrics", {}).get("memory_usage", 0)
            if memory_usage > 90:
                issues.append(f"Memory: {memory_usage:.1f}%")

            # Check disk usage
            disk_usage = worker.get("metrics", {}).get("disk_usage", 0)
            if disk_usage > 90:
                issues.append(f"Disk: {disk_usage:.1f}%")

            # If worker has issues, create finding
            if issues:
                unhealthy_workers.append(worker)

                severity = "critical" if len(issues) >= 2 else "high"

                result.add_finding(
                    Finding(
                        title=f"Unhealthy Worker: {worker_id}",
                        description=f"Worker {worker_id} has {len(issues)} health issue(s): {', '.join(issues)}",
                        severity=severity,
                        category="worker_health",
                        affected_component=worker_id,
                        evidence={
                            "worker_id": worker_id,
                            "cpu_usage": cpu_usage,
                            "memory_usage": memory_usage,
                            "disk_usage": disk_usage,
                            "issues": issues,
                        },
                        impact_summary=f"Worker performance degraded - {', '.join(issues)}",
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
        metrics = worker.get("metrics", {})

        if metrics.get("cpu_usage", 0) > 90:
            issues += 1
        if metrics.get("memory_usage", 0) > 90:
            issues += 1
        if metrics.get("disk_usage", 0) > 90:
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
            description = f"All {total_workers} workers are operating normally"
        elif status == "degraded":
            severity = "medium"
            title = "System Health: Degraded"
            description = f"{unhealthy_count}/{total_workers} workers have health issues"
        elif status == "unhealthy":
            severity = "high"
            title = "System Health: Unhealthy"
            description = f"{unhealthy_count}/{total_workers} workers require attention"
        else:  # critical
            severity = "critical"
            title = "System Health: Critical"
            description = f"{unhealthy_count}/{total_workers} workers in critical state"

        result.add_finding(
            Finding(
                title=title,
                description=description,
                severity=severity,
                category="system",
                affected_component="overall_health",
                evidence={
                    "health_score": health_score,
                    "total_workers": total_workers,
                    "unhealthy_workers": unhealthy_count,
                    "status": status,
                },
                impact_summary=f"Overall system health: {health_score}/100",
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
            metrics = worker.get("metrics", {})

            steps = []

            # CPU recommendations
            if metrics.get("cpu_usage", 0) > 90:
                steps.append("Review pipeline complexity and reduce CPU-intensive functions")
                steps.append("Consider scaling horizontally by adding more workers")
                steps.append("Check for inefficient regex patterns or complex expressions")

            # Memory recommendations
            if metrics.get("memory_usage", 0) > 90:
                steps.append("Review memory-intensive functions (aggregation, lookups)")
                steps.append("Reduce lookup table sizes or use Redis for large lookups")
                steps.append("Consider increasing worker memory allocation")

            # Disk recommendations
            if metrics.get("disk_usage", 0) > 90:
                steps.append("Clean up old persistent queues and logs")
                steps.append("Review disk space allocation for worker node")
                steps.append("Configure log rotation and retention policies")

            result.add_recommendation(
                Recommendation(
                    title=f"Remediate Worker Health: {worker_id}",
                    description=f"Address health issues on worker {worker_id}",
                    priority="high" if self._count_worker_issues(worker) >= 2 else "medium",
                    category="worker_health",
                    affected_component=worker_id,
                    remediation_steps=steps,
                    estimated_effort_minutes=30,
                    references=[
                        "https://docs.cribl.io/stream/scaling/",
                        "https://docs.cribl.io/stream/monitoring/",
                    ],
                )
            )
