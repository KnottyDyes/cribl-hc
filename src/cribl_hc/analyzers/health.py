"""
Health analyzer for assessing overall system health and worker status.

This analyzer focuses on:
- Worker health monitoring (CPU, memory, disk usage)
- Critical issue identification
- Overall system health scoring
"""

from typing import Any, Dict, List, Optional

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

    @property
    def supported_products(self) -> List[str]:
        """Health analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Overall health assessment, worker monitoring, and critical issue identification"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls needed.

        - Stream: 5 (workers, system_status, health, system_messages, banners)
        - Edge: 5 (nodes, health, system_messages, banners)

        Note: Actual count may vary based on product detection.
        """
        return 5

    def get_required_permissions(self) -> List[str]:
        """List required API permissions."""
        return [
            "read:workers",
            "read:system",
            "read:metrics",
            "read:messages",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform health analysis on Cribl Stream or Edge deployment.

        Automatically adapts based on detected product type.

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

            # Fetch leader health
            leader_health = await self._fetch_leader_health(client)

            # Fetch system messages and banners from Core API
            system_messages = await self._fetch_system_messages(client)
            banners = await self._fetch_banners(client)

            # Get Cribl version from workers if system status not available
            if workers:
                cribl_version = workers[0].get("info", {}).get("cribl", {}).get("version", "unknown")
                result.metadata["cribl_version"] = cribl_version
            else:
                result.metadata["cribl_version"] = system_status.get("version", "unknown")

            # Check leader health
            self._check_leader_health(leader_health, result)

            # Surface system messages and banners from Core API
            self._surface_system_messages(system_messages, result)
            self._surface_banners(banners, result)
            result.metadata["system_messages_count"] = len(system_messages)
            result.metadata["active_banners_count"] = len([b for b in banners if b.get("enabled")])

            # Check deployment architecture
            self._check_deployment_architecture(workers, result)

            # Analyze worker health
            unhealthy_workers = self._analyze_worker_health(workers, result, client)
            result.metadata["unhealthy_workers"] = len(unhealthy_workers)

            # Calculate overall health score
            # For Cloud/Search-only deployments with no workers, use leader health
            if workers:
                health_score = self._calculate_health_score(workers, unhealthy_workers)
            else:
                # No workers available - use leader health as basis
                health_score = self._calculate_health_score_from_leader(leader_health)
                result.metadata["health_score_source"] = "leader_health"

            result.metadata["health_score"] = health_score
            result.metadata["health_status"] = self._get_health_status(health_score)

            # Add overall health finding
            self._add_overall_health_finding(result, health_score, len(workers), len(unhealthy_workers), leader_health)

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
        """
        Fetch worker/node data from API (works for both Stream and Edge).

        Note: Uses unified get_nodes() which automatically detects product type.
        """
        try:
            # Use unified method - works for both Stream and Edge
            nodes = await client.get_nodes()

            # Normalize Edge data if needed
            normalized_nodes = [
                client._normalize_node_data(node) for node in nodes
            ]

            # Log with product-aware message
            product = client.product_type or "stream"
            self.log.debug(
                "nodes_fetched",
                product=product,
                count=len(normalized_nodes)
            )
            return normalized_nodes
        except Exception as e:
            self.log.error("nodes_fetch_failed", error=str(e))
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

    async def _fetch_leader_health(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch leader health from API."""
        try:
            response = await client.get("/api/v1/health")
            data = response.json()
            self.log.debug("leader_health_fetched", status=data.get("status"))
            return data
        except Exception as e:
            self.log.error("leader_health_fetch_failed", error=str(e))
            return {}

    def _check_leader_health(self, leader_health: Dict[str, Any], result: AnalyzerResult) -> None:
        """Check leader health status."""
        if not leader_health:
            return

        status = leader_health.get("status", "unknown")
        role = leader_health.get("role", "unknown")

        result.metadata["leader_status"] = status
        result.metadata["leader_role"] = role

        if status != "healthy":
            result.add_finding(
                Finding(
                    id="health-leader-unhealthy",
                    title="Leader Node Unhealthy",
                    description=f"Leader node reports status '{status}' (role: {role})",
                    severity="critical",
                    category="health",
                    confidence_level="high",
                    affected_components=["leader"],
                    estimated_impact="Leader issues can impact entire deployment coordination",
                    remediation_steps=[
                        "Check leader node resources (CPU, memory, disk)",
                        "Review leader logs for errors",
                        "Verify leader connectivity to workers",
                        "Consider restarting leader if issues persist",
                    ],
                    metadata={"status": status, "role": role},
                )
            )

    def _check_deployment_architecture(self, workers: List[Dict[str, Any]], result: AnalyzerResult) -> None:
        """Check deployment architecture for best practices."""
        worker_count = len(workers)

        # Check for single worker deployments (lack of redundancy)
        if worker_count == 1:
            result.add_finding(
                Finding(
                    id="health-single-worker",
                    title="Single Worker Deployment",
                    description="Deployment has only 1 worker node, providing no redundancy or high availability",
                    severity="medium",
                    category="health",
                    confidence_level="high",
                    affected_components=["architecture"],
                    estimated_impact="Single point of failure - if worker fails, all data processing stops",
                    remediation_steps=[
                        "Add at least one additional worker for redundancy",
                        "Configure worker group with minimum 2 workers",
                        "Implement load balancing across multiple workers",
                        "Document disaster recovery procedures",
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/deploy-distributed/",
                        "https://docs.cribl.io/stream/high-availability/",
                    ],
                    metadata={"worker_count": worker_count},
                )
            )

        # Check for workers with low process counts
        for worker in workers:
            worker_id = worker.get("id", "unknown")
            worker_processes = worker.get("workerProcesses", 0)
            info = worker.get("info", {})
            hostname = info.get("hostname", "unknown")
            total_cpus = info.get("cpus", 0)

            if worker_processes > 0 and total_cpus > 0:
                # Cribl default recommendation is -2 (CPUs - 2)
                # This leaves 2 CPUs for OS and Cribl management tasks
                recommended_processes = max(1, total_cpus - 2)

                # Only flag if significantly under-configured (more than 3 below optimal)
                # Worker at n-2 is optimal, n-3 or less is suboptimal
                if worker_processes < (recommended_processes - 1) and worker.get("status") == "healthy":
                    result.add_finding(
                        Finding(
                            id=f"health-worker-processes-{worker_id}",
                            title=f"Suboptimal Worker Process Count: {hostname}",
                            description=f"Worker {hostname} has {worker_processes} process(es) but has {total_cpus} CPUs available. "
                                      f"Recommended: {recommended_processes} processes",
                            severity="low",
                            category="health",
                            confidence_level="medium",
                            affected_components=[worker_id],
                            estimated_impact=f"Underutilizing available CPU resources - could process {recommended_processes}x workload",
                            remediation_steps=[
                                f"Increase worker processes to {recommended_processes} in worker group settings",
                                "Monitor CPU utilization after change",
                                "Adjust based on actual workload patterns",
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/performance-tuning/",
                            ],
                            metadata={
                                "worker_id": worker_id,
                                "hostname": hostname,
                                "current_processes": worker_processes,
                                "recommended_processes": recommended_processes,
                                "total_cpus": total_cpus,
                            },
                        )
                    )

    def _analyze_worker_health(
        self,
        workers: List[Dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient
    ) -> List[Dict[str, Any]]:
        """
        Analyze worker/node health and generate findings (Stream and Edge).

        A worker/node is considered unhealthy if:
        - Status is not "healthy"
        - Disk usage > 90%
        - Worker/node is disconnected
        - Memory appears constrained (< 2GB total)
        - Worker recently restarted (< 5 minutes uptime)

        Returns:
            List of unhealthy workers
        """
        unhealthy_workers = []
        import time

        current_time = int(time.time() * 1000)  # Current time in milliseconds

        for worker in workers:
            worker_id = worker.get("id", "unknown")
            issues = []
            warnings = []

            # Check worker status
            status = worker.get("status", "unknown")
            if status != "healthy":
                issues.append(f"Status: {status}")

            # Check if disconnected
            if worker.get("disconnected", False):
                issues.append("Disconnected")

            # Get worker info
            info = worker.get("info", {})
            hostname = info.get("hostname", "unknown")

            # Calculate disk usage from available data
            total_disk = info.get("totalDiskSpace", 0)
            free_disk = info.get("freeDiskSpace", 0)
            disk_usage_percent = 0

            if total_disk > 0:
                used_disk = total_disk - free_disk
                disk_usage_percent = (used_disk / total_disk) * 100

                if disk_usage_percent > 90:
                    issues.append(f"Disk: {disk_usage_percent:.1f}%")

            # Check memory availability
            total_mem = info.get("totalmem", 0)
            total_mem_gb = total_mem / (1024**3) if total_mem > 0 else 0

            if total_mem_gb > 0 and total_mem_gb < 2:
                warnings.append(f"Low memory: {total_mem_gb:.1f}GB")

            # Check worker uptime (time since firstMsgTime)
            first_msg_time = worker.get("firstMsgTime", 0)
            if first_msg_time > 0:
                uptime_ms = current_time - first_msg_time
                uptime_minutes = uptime_ms / (1000 * 60)

                # Flag workers that recently restarted (< 5 minutes)
                if uptime_minutes < 5:
                    warnings.append(f"Recently restarted: {uptime_minutes:.1f} min uptime")

            # If worker has issues or warnings, create finding
            if issues or warnings:
                unhealthy_workers.append(worker)

                # Determine severity based on issues vs warnings
                if len(issues) >= 2:
                    severity = "critical"
                elif len(issues) >= 1:
                    severity = "high"
                else:
                    severity = "medium"  # Only warnings

                worker_group = worker.get("group", "default")

                # Product-aware naming
                product_name = "Edge Node" if client.is_edge else "Worker"

                all_concerns = issues + warnings
                description = f"{product_name} {hostname} (group: {worker_group}) has {len(all_concerns)} health concern(s): {', '.join(all_concerns)}"

                result.add_finding(
                    Finding(
                        id=f"health-worker-{worker_id}",
                        title=f"Unhealthy {product_name}: {hostname}",
                        description=description,
                        severity=severity,
                        category="health",
                        confidence_level="high",
                        affected_components=[worker_id],
                        estimated_impact=f"{product_name} performance degraded - {', '.join(all_concerns)}",
                        remediation_steps=[
                            "Review worker status and logs",
                            "Check worker connectivity to leader",
                            "Monitor resource usage (disk, memory)",
                            "Investigate recent restarts if applicable",
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
                            "memory_total_gb": total_mem_gb if total_mem_gb > 0 else None,
                            "uptime_minutes": uptime_minutes if first_msg_time > 0 else None,
                            "issues": issues,
                            "warnings": warnings,
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
        Calculate overall health score (0-100) based on worker health.

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

    def _calculate_health_score_from_leader(
        self,
        leader_health: Dict[str, Any]
    ) -> float:
        """
        Calculate health score based on leader health endpoint.

        Used for Cloud/Search-only deployments where worker metrics
        are not available.

        Scoring:
        - 100: Leader status is "healthy"
        - 50: Leader status is unknown or other
        - 0: Leader is unhealthy or no data

        Returns:
            Health score between 0 and 100
        """
        if not leader_health:
            return 50.0  # Unknown - can't determine health

        status = leader_health.get("status", "").lower()

        if status == "healthy":
            return 100.0
        elif status in ("degraded", "warning"):
            return 70.0
        elif status in ("unhealthy", "critical", "error"):
            return 30.0
        else:
            # Unknown status - return moderate score
            return 50.0

    def _count_worker_issues(self, worker: Dict[str, Any]) -> int:
        """Count number of issues for a worker (not warnings)."""
        import time
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

        # Note: Memory and uptime are warnings, not issues
        # They don't count toward critical severity calculation

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
        leader_health: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add overall health summary finding."""
        status = self._get_health_status(health_score)

        # Check if this is a Cloud/Search deployment without workers
        is_managed_deployment = total_workers == 0 and leader_health

        if is_managed_deployment:
            # Cloud/Search-only deployment - use leader-based messaging
            leader_status = leader_health.get("status", "unknown")
            if status == "healthy":
                severity = "info"
                title = "System Health: Good"
                description = f"Managed deployment is operating normally (leader status: {leader_status}, health score: {health_score}/100)"
                remediation_steps = []
            elif status == "degraded":
                severity = "medium"
                title = "System Health: Degraded"
                description = f"Managed deployment shows degraded health (leader status: {leader_status}, health score: {health_score}/100)"
                remediation_steps = [
                    "Review system logs for warnings",
                    "Check for recent configuration changes",
                    "Monitor system performance",
                ]
            else:
                severity = "high"
                title = "System Health: Needs Attention"
                description = f"Managed deployment may need attention (leader status: {leader_status}, health score: {health_score}/100)"
                remediation_steps = [
                    "Review system health in Cribl UI",
                    "Check for error messages in logs",
                    "Contact Cribl support if issues persist",
                ]
        else:
            # Traditional worker-based deployment
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
                    "is_managed_deployment": is_managed_deployment,
                    "leader_status": leader_health.get("status") if leader_health else None,
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

    # === Core API: System Messages & Banners ===

    async def _fetch_system_messages(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """
        Fetch system messages from Core API.

        System messages are generated by Cribl to surface important
        operational information like warnings and errors.
        """
        try:
            return await client.get_system_messages() or []
        except Exception as e:
            self.log.warning("failed_to_fetch_system_messages", error=str(e))
            return []

    async def _fetch_banners(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """
        Fetch system banners from Core API.

        Banners are user-configurable messages (e.g., maintenance notices)
        that appear in the Cribl UI.
        """
        try:
            return await client.get_banners() or []
        except Exception as e:
            self.log.warning("failed_to_fetch_banners", error=str(e))
            return []

    def _surface_system_messages(
        self,
        messages: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Surface system messages as findings.

        Cribl generates system messages for operational issues like
        disk space warnings, connection problems, etc.

        Args:
            messages: List of system messages from API
            result: AnalyzerResult to add findings to
        """
        if not messages:
            return

        # Map Cribl severity to our severity levels
        severity_map = {
            "error": "high",
            "critical": "critical",
            "warn": "medium",
            "warning": "medium",
            "info": "low",
        }

        for msg in messages:
            msg_id = msg.get("id", "unknown")
            msg_severity = msg.get("severity", "info").lower()
            msg_title = msg.get("title") or msg.get("message", "System Message")
            msg_text = msg.get("message") or msg.get("description", "")
            msg_channel = msg.get("channel", "system")

            # Map severity
            our_severity = severity_map.get(msg_severity, "low")

            # Only surface warnings and above
            if our_severity in ("low",) and msg_severity == "info":
                continue

            result.add_finding(Finding(
                id=f"health-system-message-{msg_id}",
                category="health",
                severity=our_severity,
                title=f"System Message: {msg_title[:50]}",
                description=(
                    f"Cribl system message ({msg_channel}): {msg_text}"
                ),
                confidence_level="high",
                remediation_steps=[
                    "Review the system message in Cribl UI for full context",
                    "Address the underlying issue described in the message",
                    "Clear the message after resolution"
                ],
                metadata={
                    "message_id": msg_id,
                    "severity": msg_severity,
                    "channel": msg_channel,
                    "full_message": msg_text
                }
            ))

    def _surface_banners(
        self,
        banners: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Surface active system banners as informational findings.

        Banners are typically maintenance notices or operational messages
        configured by administrators.

        Args:
            banners: List of banner configurations from API
            result: AnalyzerResult to add findings to
        """
        if not banners:
            return

        for banner in banners:
            banner_id = banner.get("id", "unknown")
            enabled = banner.get("enabled", False)
            banner_type = banner.get("type", "info")
            message = banner.get("message", "")

            # Only report enabled banners
            if not enabled:
                continue

            # Determine severity based on banner type
            if banner_type in ("error", "critical"):
                severity = "high"
            elif banner_type in ("warning", "warn"):
                severity = "medium"
            else:
                severity = "low"

            result.add_finding(Finding(
                id=f"health-banner-{banner_id}",
                category="health",
                severity=severity,
                title=f"Active Banner: {message[:40]}..." if len(message) > 40 else f"Active Banner: {message}",
                description=(
                    f"An active system banner is configured: {message}"
                ),
                confidence_level="high",
                remediation_steps=[
                    "Review if the banner is still relevant",
                    "Disable banner after the event/maintenance is complete"
                ],
                metadata={
                    "banner_id": banner_id,
                    "type": banner_type,
                    "message": message
                }
            ))
