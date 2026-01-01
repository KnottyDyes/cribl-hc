"""
Fleet & Multi-Tenancy Management Analyzer for Cribl Health Check.

Analyzes multiple deployments, compares environments, detects patterns,
and provides fleet-wide insights.

Priority: P6 (Fleet management and multi-environment operations)
"""

import asyncio
from collections import Counter, defaultdict
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class FleetAnalyzer(BaseAnalyzer):
    """
    Analyzer for fleet and multi-tenancy management.

    Identifies:
    - Configuration drift across environments
    - Common issues affecting multiple deployments
    - Environment-specific problems
    - Fleet-wide patterns and trends
    - Cross-deployment best practices violations

    Priority: P6 (Fleet management - valuable for enterprises with multiple environments)

    Example:
        >>> deployments = {
        ...     "dev": CriblAPIClient("https://dev.example.com", "token1"),
        ...     "staging": CriblAPIClient("https://staging.example.com", "token2"),
        ...     "prod": CriblAPIClient("https://prod.example.com", "token3")
        ... }
        >>> analyzer = FleetAnalyzer()
        >>> result = await analyzer.analyze_fleet(deployments)
        >>> print(f"Analyzed {result.metadata['deployments_analyzed']} deployments")
    """

    def __init__(self):
        """Initialize FleetAnalyzer."""
        super().__init__()
        self._deployment_results: dict[str, dict[str, Any]] = {}

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "fleet"

    @property
    def supported_products(self) -> list[str]:
        """Fleet analyzer supports all products."""
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls per deployment.

        Single deployment: system_status(1) + pipelines(1) + workers(1) +
                          worker_groups(1) + master_summary(1) = 5 calls.
        For N deployments: 5N calls.
        """
        return 5  # Per deployment

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return [
            "read:system",
            "read:pipelines",
            "read:workers",
            "read:master"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze single deployment for fleet health and config drift.

        Checks worker groups for configuration version mismatches,
        deployment status, and fleet-wide health metrics.

        Args:
            client: API client for the deployment

        Returns:
            AnalyzerResult with fleet health findings

        Note:
            For multi-deployment comparison, use analyze_fleet() instead.
        """
        result = AnalyzerResult(objective=self.objective_name)
        self.log.info("fleet_single_deployment_analysis_started")

        try:
            # Fetch worker groups and master summary using Core API
            worker_groups = await client.get_worker_groups()
            master_summary = await client.get_master_summary()
            workers = await client.get_workers()

            result.metadata["worker_group_count"] = len(worker_groups)
            result.metadata["total_workers"] = len(workers)
            result.metadata["master_summary"] = master_summary

            # Analyze config drift within worker groups
            await self._analyze_config_drift(client, worker_groups, workers, result)

            # Analyze worker group health
            self._analyze_worker_group_health(worker_groups, master_summary, result)

            # Analyze fleet-wide patterns
            self._analyze_single_deployment_patterns(workers, result)

            result.success = True

        except Exception as e:
            self.log.error("fleet_analysis_failed", error=str(e))
            result.error = f"Fleet analysis failed: {str(e)}"
            result.success = False

        return result

    async def _analyze_config_drift(
        self,
        client: CriblAPIClient,
        worker_groups: list[dict[str, Any]],
        workers: list[dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze configuration drift between worker groups and workers.

        Detects:
        - Workers running different config versions than their group
        - Worker groups with deployments in progress
        - Workers that haven't received latest config

        Args:
            client: API client for fetching group summaries
            worker_groups: List of worker group configurations
            workers: List of worker nodes
            result: AnalyzerResult to add findings to
        """
        if not worker_groups:
            self.log.info("no_worker_groups_found_skipping_drift_check")
            return

        # Build lookup of expected config versions by group
        group_config_versions: dict[str, str] = {}
        groups_deploying: list[dict[str, Any]] = []

        for group in worker_groups:
            group_id = group.get("id", "unknown")
            config_version = group.get("configVersion", "unknown")
            deploying_count = group.get("deployingWorkerCount", 0)

            group_config_versions[group_id] = config_version

            # Check for deployments in progress
            if deploying_count > 0:
                groups_deploying.append({
                    "group": group_id,
                    "deploying_count": deploying_count,
                    "config_version": config_version
                })

        # Report deployments in progress
        if groups_deploying:
            for deploying in groups_deploying:
                result.add_finding(Finding(
                    id=f"fleet-deployment-in-progress-{deploying['group']}",
                    category="fleet",
                    severity="low",
                    title=f"Config Deployment In Progress: {deploying['group']}",
                    description=(
                        f"Worker group '{deploying['group']}' has {deploying['deploying_count']} "
                        f"worker(s) still deploying config version {deploying['config_version']}. "
                        f"This is normal during deployments but should complete within minutes."
                    ),
                    confidence_level="high",
                    remediation_steps=[
                        "Monitor deployment progress in Cribl UI",
                        "If stuck for >10 minutes, check worker connectivity",
                        "Review worker logs for deployment errors"
                    ],
                    metadata=deploying
                ))

        # Check individual workers for config drift
        workers_with_drift: list[dict[str, Any]] = []
        workers_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for worker in workers:
            worker_id = worker.get("id", "unknown")
            worker_group = worker.get("group", "default")
            worker_config = worker.get("configVersion", "unknown")

            workers_by_group[worker_group].append(worker)

            expected_version = group_config_versions.get(worker_group)
            if expected_version and worker_config != expected_version:
                workers_with_drift.append({
                    "worker_id": worker_id,
                    "group": worker_group,
                    "worker_version": worker_config,
                    "expected_version": expected_version,
                    "status": worker.get("status", "unknown")
                })

        # Report config drift
        if workers_with_drift:
            # Group by worker group for better reporting
            drift_by_group: dict[str, list[str]] = defaultdict(list)
            for drift in workers_with_drift:
                drift_by_group[drift["group"]].append(drift["worker_id"])

            for group_id, drifted_workers in drift_by_group.items():
                expected = group_config_versions.get(group_id, "unknown")
                result.add_finding(Finding(
                    id=f"fleet-config-drift-{group_id}",
                    category="fleet",
                    severity="medium",
                    title=f"Config Version Drift in Worker Group: {group_id}",
                    description=(
                        f"{len(drifted_workers)} worker(s) in group '{group_id}' are running "
                        f"a different config version than expected ({expected}). "
                        f"This may indicate failed deployments or connectivity issues."
                    ),
                    confidence_level="high",
                    estimated_impact="Workers may process data with outdated configurations",
                    remediation_steps=[
                        f"Review worker status for group '{group_id}' in Cribl UI",
                        "Check worker connectivity to leader node",
                        "Attempt manual config deployment to affected workers",
                        "Review worker logs for deployment errors",
                        "Consider restarting affected workers if deployment is stuck"
                    ],
                    affected_components=drifted_workers,
                    documentation_links=[
                        "https://docs.cribl.io/stream/manage-workers/"
                    ],
                    metadata={
                        "group": group_id,
                        "expected_version": expected,
                        "drifted_worker_count": len(drifted_workers),
                        "drifted_workers": workers_with_drift
                    }
                ))

        # Store drift summary in metadata
        result.metadata["config_drift"] = {
            "groups_deploying": len(groups_deploying),
            "workers_with_drift": len(workers_with_drift),
            "group_config_versions": group_config_versions
        }

    def _analyze_worker_group_health(
        self,
        worker_groups: list[dict[str, Any]],
        master_summary: dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze health metrics across worker groups.

        Args:
            worker_groups: List of worker group configurations
            master_summary: Master summary with fleet-wide metrics
            result: AnalyzerResult to add findings to
        """
        if not master_summary:
            return

        # Extract fleet-wide metrics
        total_workers = master_summary.get("workerCount", 0)
        healthy_workers = master_summary.get("healthyWorkerCount", 0)
        unhealthy_workers = total_workers - healthy_workers

        result.metadata["fleet_health"] = {
            "total_workers": total_workers,
            "healthy_workers": healthy_workers,
            "unhealthy_workers": unhealthy_workers,
            "health_pct": round((healthy_workers / total_workers * 100), 1) if total_workers > 0 else 0
        }

        # Alert if significant portion of fleet is unhealthy
        if total_workers > 0:
            unhealthy_pct = (unhealthy_workers / total_workers) * 100

            if unhealthy_pct >= 25:
                result.add_finding(Finding(
                    id="fleet-health-critical",
                    category="fleet",
                    severity="critical",
                    title="Critical Fleet Health Issue",
                    description=(
                        f"{unhealthy_workers} of {total_workers} workers ({unhealthy_pct:.0f}%) "
                        f"are unhealthy. This represents a significant portion of your fleet."
                    ),
                    confidence_level="high",
                    estimated_impact="Significant risk of data processing interruption",
                    remediation_steps=[
                        "Immediately investigate unhealthy workers in Cribl UI",
                        "Check leader node health and connectivity",
                        "Review infrastructure (CPU, memory, disk, network)",
                        "Consider scaling or replacing unhealthy workers"
                    ],
                    metadata={
                        "unhealthy_count": unhealthy_workers,
                        "total_count": total_workers,
                        "unhealthy_pct": round(unhealthy_pct, 1)
                    }
                ))
            elif unhealthy_pct >= 10:
                result.add_finding(Finding(
                    id="fleet-health-warning",
                    category="fleet",
                    severity="medium",
                    title="Fleet Health Degraded",
                    description=(
                        f"{unhealthy_workers} of {total_workers} workers ({unhealthy_pct:.0f}%) "
                        f"are unhealthy. Monitor closely and investigate."
                    ),
                    confidence_level="high",
                    remediation_steps=[
                        "Review unhealthy workers in Cribl UI",
                        "Check for common issues (connectivity, resources)",
                        "Schedule maintenance if needed"
                    ],
                    metadata={
                        "unhealthy_count": unhealthy_workers,
                        "total_count": total_workers,
                        "unhealthy_pct": round(unhealthy_pct, 1)
                    }
                ))

    def _analyze_single_deployment_patterns(
        self,
        workers: list[dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze patterns in a single deployment.

        Args:
            workers: List of worker nodes
            result: AnalyzerResult to add findings to
        """
        if not workers:
            return

        # Group workers by status
        status_counts: dict[str, int] = Counter()
        for worker in workers:
            status = worker.get("status", "unknown")
            status_counts[status] += 1

        result.metadata["worker_status_distribution"] = dict(status_counts)

        # Check for workers with unknown status
        unknown_count = status_counts.get("unknown", 0)
        if unknown_count > 0:
            result.add_finding(Finding(
                id="fleet-workers-unknown-status",
                category="fleet",
                severity="low",
                title="Workers with Unknown Status",
                description=(
                    f"{unknown_count} worker(s) are reporting unknown status. "
                    f"This may indicate monitoring issues or workers that haven't checked in."
                ),
                confidence_level="medium",
                remediation_steps=[
                    "Check worker connectivity to leader",
                    "Review worker heartbeat settings",
                    "Verify network path between workers and leader"
                ],
                metadata={"unknown_count": unknown_count}
            ))

    async def analyze_fleet(
        self,
        deployments: dict[str, CriblAPIClient]
    ) -> AnalyzerResult:
        """
        Analyze multiple deployments and generate fleet-wide insights.

        Args:
            deployments: Dictionary mapping deployment names to API clients
                Example: {"dev": client1, "staging": client2, "prod": client3}

        Returns:
            AnalyzerResult with fleet-wide findings and recommendations

        Example:
            >>> deployments = {
            ...     "dev": dev_client,
            ...     "prod": prod_client
            ... }
            >>> result = await analyzer.analyze_fleet(deployments)
            >>> drift_findings = [f for f in result.findings if "drift" in f.id]
        """
        result = AnalyzerResult(objective=self.objective_name)

        # Validate input
        if not deployments:
            result.success = False
            result.error = "No deployments provided for fleet analysis"
            self.log.error("no_deployments_provided")
            return result

        self.log.info("fleet_analysis_started", deployment_count=len(deployments))

        # Initialize metadata
        deployment_names = list(deployments.keys())
        result.metadata.update({
            "deployment_names": deployment_names,
            "deployments_analyzed": 0,
            "failed_deployments": [],
            "successful_deployments": []
        })

        # Step 1: Analyze each deployment in parallel
        await self._analyze_all_deployments(deployments, result)

        # Step 2: Compare environments
        self._compare_environments(result)

        # Step 3: Detect fleet-wide patterns
        self._detect_fleet_patterns(result)

        # Step 4: Generate fleet-level recommendations
        self._generate_fleet_recommendations(result)

        # Mark as successful if at least one deployment analyzed
        result.success = result.metadata["deployments_analyzed"] > 0

        self.log.info(
            "fleet_analysis_completed",
            deployments_analyzed=result.metadata["deployments_analyzed"],
            findings_count=len(result.findings),
            recommendations_count=len(result.recommendations)
        )

        return result

    async def _analyze_all_deployments(
        self,
        deployments: dict[str, CriblAPIClient],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze all deployments in parallel.

        Args:
            deployments: Dictionary of deployment name to API client
            result: AnalyzerResult to populate with metadata
        """
        tasks = []
        for name, client in deployments.items():
            tasks.append(self._analyze_single_deployment(name, client))

        # Execute in parallel
        deployment_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for name, deployment_data in zip(deployments.keys(), deployment_results):
            if isinstance(deployment_data, Exception):
                self.log.error(
                    "deployment_analysis_failed",
                    deployment=name,
                    error=str(deployment_data)
                )
                result.metadata["failed_deployments"].append(name)
            else:
                self._deployment_results[name] = deployment_data
                result.metadata["successful_deployments"].append(name)
                result.metadata["deployments_analyzed"] += 1

    async def _analyze_single_deployment(
        self,
        name: str,
        client: CriblAPIClient
    ) -> dict[str, Any]:
        """
        Analyze a single deployment.

        Args:
            name: Deployment name
            client: API client for this deployment

        Returns:
            Dictionary with deployment analysis data
        """
        self.log.info("analyzing_deployment", deployment=name)

        deployment_data: dict[str, Any] = {
            "name": name,
            "environment": getattr(client, "environment", "unknown"),
            "base_url": getattr(client, "base_url", ""),
            "product_type": getattr(client, "product_type", "stream")
        }

        try:
            # Fetch system status
            deployment_data["system_status"] = await client.get_system_status()
        except Exception as e:
            self.log.warning("failed_to_get_system_status", deployment=name, error=str(e))
            deployment_data["system_status"] = {}

        try:
            # Fetch pipelines
            deployment_data["pipelines"] = await client.get_pipelines()
            deployment_data["pipeline_count"] = len(deployment_data["pipelines"])
        except Exception as e:
            self.log.warning("failed_to_get_pipelines", deployment=name, error=str(e))
            deployment_data["pipelines"] = []
            deployment_data["pipeline_count"] = 0

        try:
            # Fetch workers
            deployment_data["workers"] = await client.get_workers()
            deployment_data["worker_count"] = len(deployment_data["workers"])
        except Exception as e:
            self.log.warning("failed_to_get_workers", deployment=name, error=str(e))
            deployment_data["workers"] = []
            deployment_data["worker_count"] = 0

        return deployment_data

    def _compare_environments(self, result: AnalyzerResult) -> None:
        """
        Compare deployments and identify configuration drift.

        Args:
            result: AnalyzerResult to add findings to
        """
        if len(self._deployment_results) < 2:
            return  # Need at least 2 deployments to compare

        # Compare pipeline counts
        pipeline_counts = {
            name: data.get("pipeline_count", 0)
            for name, data in self._deployment_results.items()
        }

        # Check for significant differences
        if len(set(pipeline_counts.values())) > 1:
            min_count = min(pipeline_counts.values())
            max_count = max(pipeline_counts.values())
            min_env = [k for k, v in pipeline_counts.items() if v == min_count][0]
            max_env = [k for k, v in pipeline_counts.items() if v == max_count][0]

            # Only flag if difference is significant (>20%)
            if max_count > 0 and (max_count - min_count) / max_count > 0.2:
                result.add_finding(Finding(
                    id="fleet-config-drift-pipelines",
                    category="fleet",
                    severity="medium",
                    title="Pipeline Count Drift Across Environments",
                    description=(
                        f"Significant difference in pipeline counts detected: "
                        f"{min_env} has {min_count} pipelines while {max_env} has {max_count} pipelines. "
                        f"This may indicate configuration drift or missing deployments."
                    ),
                    confidence_level="high",
                    remediation_steps=[
                        "Review pipeline configurations across all environments",
                        "Ensure production-critical pipelines are deployed consistently",
                        "Consider using GitOps workflow for configuration management",
                        "Document intentional environment-specific configurations"
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/deploy-git"
                    ],
                    metadata={
                        "pipeline_counts": pipeline_counts,
                        "min_env": min_env,
                        "max_env": max_env,
                        "difference_pct": round(((max_count - min_count) / max_count) * 100, 1)
                    }
                ))

        # Compare worker counts
        worker_counts = {
            name: data.get("worker_count", 0)
            for name, data in self._deployment_results.items()
        }

        if len(set(worker_counts.values())) > 1:
            # Log worker count differences (informational)
            result.metadata["worker_count_by_env"] = worker_counts

    def _detect_fleet_patterns(self, result: AnalyzerResult) -> None:
        """
        Detect patterns affecting multiple deployments.

        Args:
            result: AnalyzerResult to add findings to
        """
        if not self._deployment_results:
            return

        # Collect health statuses
        health_statuses = defaultdict(list)
        for name, data in self._deployment_results.items():
            status = data.get("system_status", {}).get("health", "unknown")
            health_statuses[status].append(name)

        # Check if multiple deployments are unhealthy
        unhealthy_envs = health_statuses.get("yellow", []) + health_statuses.get("red", [])

        if len(unhealthy_envs) >= 2:
            result.add_finding(Finding(
                id="fleet-pattern-multiple-unhealthy",
                category="fleet",
                severity="high",
                title="Multiple Deployments Unhealthy",
                description=(
                    f"Multiple deployments ({', '.join(unhealthy_envs)}) are reporting unhealthy status. "
                    f"This may indicate a systemic issue affecting your fleet."
                ),
                confidence_level="high",
                estimated_impact="Potential service degradation across multiple environments",
                remediation_steps=[
                    "Investigate common issues across affected deployments",
                    "Check for infrastructure problems (network, storage, compute)",
                    "Review recent configuration changes",
                    "Escalate to Cribl support if pattern persists"
                ],
                affected_components=unhealthy_envs,
                metadata={
                    "unhealthy_deployments": unhealthy_envs,
                    "unhealthy_count": len(unhealthy_envs),
                    "health_statuses": dict(health_statuses)
                }
            ))

        # Store fleet patterns in metadata
        result.metadata["fleet_patterns"] = {
            "health_distribution": dict(health_statuses),
            "total_pipelines": sum(
                data.get("pipeline_count", 0)
                for data in self._deployment_results.values()
            ),
            "total_workers": sum(
                data.get("worker_count", 0)
                for data in self._deployment_results.values()
            )
        }

    def _generate_fleet_recommendations(self, result: AnalyzerResult) -> None:
        """
        Generate fleet-level recommendations.

        Args:
            result: AnalyzerResult to add recommendations to
        """
        if len(self._deployment_results) < 2:
            return

        # Recommend GitOps if seeing configuration drift
        drift_findings = [f for f in result.findings if "drift" in f.id.lower()]
        if drift_findings:
            result.add_recommendation(Recommendation(
                id="fleet-rec-gitops",
                type="fleet",
                priority="p1",
                title="Implement GitOps for Configuration Management",
                description=(
                    "Configuration drift detected across environments. "
                    "Implement GitOps workflow to ensure consistent deployments."
                ),
                rationale=(
                    "GitOps ensures configuration consistency, provides audit trail, "
                    "and enables automated deployment workflows"
                ),
                implementation_steps=[
                    "Set up Git repository for Cribl configurations",
                    "Configure Git integration in all deployments",
                    "Define deployment workflows (dev → staging → prod)",
                    "Implement automated testing in CI/CD pipeline",
                    "Document configuration promotion process"
                ],
                before_state=f"Configuration managed manually across {len(self._deployment_results)} environments",
                after_state="Automated GitOps workflow with version control",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Reduces configuration errors and deployment time by 60%"
                ),
                implementation_effort="medium",
                related_findings=[f.id for f in drift_findings],
                documentation_links=[
                    "https://docs.cribl.io/stream/deploy-git"
                ]
            ))

        # Recommend fleet monitoring if multiple deployments
        if len(self._deployment_results) >= 3:
            result.add_recommendation(Recommendation(
                id="fleet-rec-centralized-monitoring",
                type="fleet",
                priority="p2",
                title="Implement Centralized Fleet Monitoring",
                description=(
                    f"With {len(self._deployment_results)} deployments, centralized monitoring "
                    f"would improve visibility and incident response"
                ),
                rationale="Centralized monitoring enables faster problem detection and resolution across the fleet",
                implementation_steps=[
                    "Deploy metrics aggregation solution (e.g., Prometheus, Cribl Search)",
                    "Configure all deployments to send metrics to central location",
                    "Create fleet-wide dashboards",
                    "Set up cross-deployment alerting",
                    "Document monitoring runbooks"
                ],
                impact_estimate=ImpactEstimate(
                    performance_improvement="Reduces mean time to detect (MTTD) by 70%"
                ),
                implementation_effort="high",
                documentation_links=[
                    "https://docs.cribl.io/stream/monitoring"
                ]
            ))
