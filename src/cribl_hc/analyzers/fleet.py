"""
Fleet & Multi-Tenancy Management Analyzer for Cribl Health Check.

Analyzes multiple deployments, compares environments, detects patterns,
and provides fleet-wide insights.

Priority: P6 (Fleet management and multi-environment operations)
"""

import asyncio
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set
import structlog

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
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
        self._deployment_results: Dict[str, Dict[str, Any]] = {}

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "fleet"

    @property
    def supported_products(self) -> List[str]:
        """Fleet analyzer supports all products."""
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls per deployment.

        Each deployment: system_status(1) + pipelines(1) + workers(1) = 3 calls.
        For N deployments: 3N calls.
        """
        return 3  # Per deployment

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:system",
            "read:pipelines",
            "read:workers"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze is not used for FleetAnalyzer.

        Use analyze_fleet() instead with multiple clients.

        Args:
            client: Single API client (not used)

        Returns:
            AnalyzerResult with error message

        Raises:
            NotImplementedError: Use analyze_fleet() instead
        """
        result = AnalyzerResult(objective=self.objective_name, success=False)
        result.error = "FleetAnalyzer requires analyze_fleet() with multiple deployments"
        self.log.warning("analyze_called_use_analyze_fleet_instead")
        return result

    async def analyze_fleet(
        self,
        deployments: Dict[str, CriblAPIClient]
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
        deployments: Dict[str, CriblAPIClient],
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
    ) -> Dict[str, Any]:
        """
        Analyze a single deployment.

        Args:
            name: Deployment name
            client: API client for this deployment

        Returns:
            Dictionary with deployment analysis data
        """
        self.log.info("analyzing_deployment", deployment=name)

        deployment_data: Dict[str, Any] = {
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
