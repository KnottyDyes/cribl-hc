"""
Multi-Deployment Comparison Analyzer for Cribl Health Check.

Compares health analysis results across multiple deployments (prod vs dev, etc.)
to identify configuration parity issues and environmental differences.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger


@dataclass
class DeploymentConfig:
    """Configuration for a single deployment."""

    name: str
    host: str
    username: str
    password: str
    worker_groups: Optional[list[str]] = None
    tags: Optional[dict[str, str]] = None


@dataclass
class ComparisonResult:
    """Result of comparing two deployments."""

    deployment_a: str
    deployment_b: str
    total_findings_a: int
    total_findings_b: int
    severity_breakdown_a: dict[str, int]
    severity_breakdown_b: dict[str, int]
    unique_findings_a: int
    unique_findings_b: int
    common_findings: int
    analysis_timestamp: datetime


class MultiDeploymentComparisonAnalyzer(BaseAnalyzer):
    """
    Analyzer for comparing health analysis results across multiple deployments.

    Phase 13 - Enterprise Operations

    Compares prod vs dev, staging vs prod, etc. to identify:
    - Configuration parity issues
    - Environmental differences
    - Missing configurations in lower environments
    - Inconsistent security settings
    """

    # Comparison thresholds
    FINDING_COUNT_DIFFERENCE_THRESHOLD = 0.5  # 50% difference in total findings
    CRITICAL_FINDING_RATIO_THRESHOLD = 0.2  # 20% of findings are critical

    def __init__(self) -> None:
        """Initialize the multi-deployment comparison analyzer."""
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        """
        Return the objective name for this analyzer.
        """
        return "multi_deployment_comparison"

    @property
    def category(self) -> str:
        """
        Return the category this analyzer belongs to.
        """
        return "enterprise"

    @property
    def supported_products(self) -> list[str]:
        """Multi-deployment comparison applies to all products."""
        return ["stream", "edge", "lake", "search"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Compares health analysis results across multiple deployments"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: multiplied by number of deployments."""
        return 50  # Base estimate - scales with deployment count

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:system", "read:config", "read:health"]

    async def post_analyze_cleanup(self) -> None:
        """Optional cleanup after analysis completes."""
        pass

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform multi-deployment comparison analysis.

        This analyzer is special - it doesn't analyze a single deployment,
        but compares multiple deployments. The client parameter is used
        as a template for creating clients for other deployments.
        """
        result = self.create_result()

        try:
            # Get deployment configurations from environment/analysis context
            deployments = self._get_deployment_configs()

            if len(deployments) < 2:
                result.add_finding(
                    self.create_finding(
                        id="multi-deployment-insufficient-deployments",
                        title="Insufficient Deployments for Comparison",
                        description=f"Only {len(deployments)} deployment(s) configured. Need at least 2 for meaningful comparison.",
                        severity="info",
                        category="deployment",
                        confidence_level="high",
                        affected_components=["deployment:comparison"],
                        remediation_steps=[
                            "Configure multiple deployment endpoints in the analysis configuration",
                            "Ensure all target deployments are accessible",
                            "Verify authentication credentials for each deployment",
                        ],
                        metadata={"configured_deployments": len(deployments)},
                    )
                )
                return result

            # Run analysis on all deployments in parallel
            analysis_results = await self._run_parallel_analyses(deployments)

            # Compare results between deployments
            comparisons = self._compare_deployments(analysis_results)

            # Generate comparison findings
            for comparison in comparisons:
                findings = self._generate_comparison_findings(comparison, analysis_results)
                for finding in findings:
                    result.add_finding(finding)

            # Add summary findings
            summary_findings = self._generate_summary_findings(comparisons, deployments)
            for finding in summary_findings:
                result.add_finding(finding)

            result.metadata.update(
                {
                    "deployments_compared": len(deployments),
                    "comparisons_performed": len(comparisons),
                    "total_findings_analyzed": sum(
                        len(results.findings) for results in analysis_results.values()
                    ),
                }
            )

        except Exception as e:
            self.log.error("multi_deployment_comparison_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _get_deployment_configs(self) -> list[DeploymentConfig]:
        """
        Get deployment configurations.

        In a real implementation, this would read from:
        - Configuration file
        - Environment variables
        - Analysis parameters
        - Database/registry
        """
        # For now, return mock configurations
        # In production, this would be configurable
        return [
            DeploymentConfig(
                name="production",
                host="prod.cribl.example.com",
                username="admin",
                password="${PROD_PASSWORD}",
                tags={"environment": "prod", "criticality": "high"},
            ),
            DeploymentConfig(
                name="staging",
                host="staging.cribl.example.com",
                username="admin",
                password="${STAGING_PASSWORD}",
                tags={"environment": "staging", "criticality": "medium"},
            ),
            DeploymentConfig(
                name="development",
                host="dev.cribl.example.com",
                username="admin",
                password="${DEV_PASSWORD}",
                tags={"environment": "dev", "criticality": "low"},
            ),
        ]

    async def _run_parallel_analyses(
        self, deployments: list[DeploymentConfig]
    ) -> dict[str, AnalyzerResult]:
        """
        Run health analysis on all deployments in parallel.

        Returns a dict mapping deployment names to their analysis results.
        """

        async def analyze_deployment(deployment: DeploymentConfig) -> tuple[str, AnalyzerResult]:
            """Analyze a single deployment."""
            try:
                # Create client for this deployment
                self._create_client_for_deployment(deployment)

                # For now, create a mock analysis result
                # In a real implementation, this would run all analyzers
                result = self._create_mock_analysis_result(deployment.name)

                return deployment.name, result

            except Exception as e:
                self.log.error(f"analysis_failed_for_{deployment.name}", error=str(e))
                # Return error result
                error_result = AnalyzerResult(
                    objective="health", success=False, error=f"Analysis failed: {str(e)}"
                )
                return deployment.name, error_result

        # Run all analyses in parallel
        tasks = [analyze_deployment(deployment) for deployment in deployments]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        analysis_results = {}
        for result in results:
            if isinstance(result, BaseException):
                self.log.error("parallel_analysis_exception", error=str(result))
                continue

            deployment_name, analysis_result = result
            analysis_results[deployment_name] = analysis_result

        return analysis_results

    def _create_client_for_deployment(self, deployment: DeploymentConfig) -> CriblAPIClient:
        """
        Create a CriblAPIClient for the given deployment.

        In a real implementation, this would create authenticated clients
        for each deployment endpoint.
        """
        # This is a simplified version - in production, this would:
        # - Resolve environment variables for passwords
        # - Handle authentication methods (API keys, certificates, etc.)
        # - Configure timeouts and retry logic
        # - Set up proper TLS validation

        # For now, return a mock client with a placeholder token
        # Real implementation would create actual CriblAPIClient instances
        return CriblAPIClient(
            base_url=f"https://{deployment.host}:9000",
            auth_token=f"token_for_{deployment.name}",
            timeout=30,
        )

    def _create_mock_analysis_result(self, deployment_name: str) -> AnalyzerResult:
        """
        Create a mock analysis result for testing.

        In a real implementation, this would run all analyzers against the deployment.
        """
        result = AnalyzerResult(objective="health", success=True)

        # Add some mock findings based on deployment type
        # This simulates different health states for different environments
        if "prod" in deployment_name.lower():
            # Production has more security findings
            result.add_finding(
                self.create_finding(
                    id=f"mock-security-{deployment_name}",
                    title="Security Configuration Check",
                    description="Security settings verified",
                    severity="info",
                    category="security",
                    confidence_level="high",
                    affected_components=[f"deployment:{deployment_name}"],
                )
            )
        elif "dev" in deployment_name.lower():
            # Development has more config issues
            result.add_finding(
                self.create_finding(
                    id=f"mock-config-{deployment_name}",
                    title="Configuration Validation",
                    description="Pipeline configuration needs review",
                    severity="medium",
                    category="config",
                    confidence_level="medium",
                    affected_components=[f"deployment:{deployment_name}"],
                )
            )

        return result

    def _compare_deployments(
        self, analysis_results: dict[str, AnalyzerResult]
    ) -> list[ComparisonResult]:
        """
        Compare analysis results between deployments.

        Generates ComparisonResult objects for each pair of deployments.
        """
        comparisons = []
        deployment_names = list(analysis_results.keys())

        # Compare each deployment against every other deployment
        for i, name_a in enumerate(deployment_names):
            for name_b in deployment_names[i + 1 :]:
                comparison = self._compare_two_deployments(
                    name_a, name_b, analysis_results[name_a], analysis_results[name_b]
                )
                comparisons.append(comparison)

        return comparisons

    def _compare_two_deployments(
        self, name_a: str, name_b: str, result_a: AnalyzerResult, result_b: AnalyzerResult
    ) -> ComparisonResult:
        """Compare two specific deployment results."""
        # Count total findings
        total_a = len(result_a.findings)
        total_b = len(result_b.findings)

        # Count findings by severity
        severity_a = self._count_findings_by_severity(result_a.findings)
        severity_b = self._count_findings_by_severity(result_b.findings)

        # Find unique and common findings
        # This is a simplified comparison - real implementation would
        # use finding IDs, titles, and content similarity
        unique_a = total_a  # Simplified
        unique_b = total_b  # Simplified
        common = 0  # Simplified

        return ComparisonResult(
            deployment_a=name_a,
            deployment_b=name_b,
            total_findings_a=total_a,
            total_findings_b=total_b,
            severity_breakdown_a=severity_a,
            severity_breakdown_b=severity_b,
            unique_findings_a=unique_a,
            unique_findings_b=unique_b,
            common_findings=common,
            analysis_timestamp=datetime.now(),
        )

    def _count_findings_by_severity(self, findings: list[Any]) -> dict[str, int]:
        """Count findings by severity level."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for finding in findings:
            severity = getattr(finding, "severity", "info")
            if severity in severity_counts:
                severity_counts[severity] += 1

        return severity_counts

    def _generate_comparison_findings(
        self, comparison: ComparisonResult, analysis_results: dict[str, AnalyzerResult]
    ) -> list[Any]:
        """Generate findings based on deployment comparison."""
        findings = []

        # Check for significant finding count differences
        findings.extend(self._check_finding_count_differences(comparison))

        # Check for severity distribution differences
        findings.extend(self._check_severity_distribution_differences(comparison))

        # Check for missing configurations in lower environments
        findings.extend(self._check_configuration_parity(comparison, analysis_results))

        return findings

    def _check_finding_count_differences(self, comparison: ComparisonResult) -> list[Any]:
        """Check for significant differences in total finding counts."""
        findings = []

        # Calculate percentage difference
        if comparison.total_findings_a > 0 and comparison.total_findings_b > 0:
            ratio = abs(comparison.total_findings_a - comparison.total_findings_b) / max(
                comparison.total_findings_a, comparison.total_findings_b
            )

            if ratio > self.FINDING_COUNT_DIFFERENCE_THRESHOLD:
                severity = "high" if ratio > 0.8 else "medium"

                findings.append(
                    self.create_finding(
                        id=f"comparison-finding-count-difference-{comparison.deployment_a}-{comparison.deployment_b}",
                        title=f"Significant Finding Count Difference: {comparison.deployment_a} vs {comparison.deployment_b}",
                        description=f"Deployment '{comparison.deployment_a}' has {comparison.total_findings_a} findings "
                        f"vs '{comparison.deployment_b}' with {comparison.total_findings_b} findings "
                        f"({ratio:.1%} difference). This may indicate configuration inconsistencies.",
                        severity=severity,
                        category="deployment",
                        confidence_level="medium",
                        estimated_impact="Configuration inconsistencies between environments may lead to unexpected behavior and troubleshooting difficulties",
                        affected_components=[
                            f"deployment:{comparison.deployment_a}",
                            f"deployment:{comparison.deployment_b}",
                        ],
                        remediation_steps=[
                            f"Compare configurations between {comparison.deployment_a} and {comparison.deployment_b}",
                            "Check if lower environments are missing security configurations",
                            "Verify that development environments have appropriate test data",
                            "Review deployment pipelines for configuration drift",
                        ],
                        metadata={
                            "deployment_a": comparison.deployment_a,
                            "deployment_b": comparison.deployment_b,
                            "findings_a": comparison.total_findings_a,
                            "findings_b": comparison.total_findings_b,
                            "difference_ratio": round(ratio, 3),
                        },
                    )
                )

        return findings

    def _check_severity_distribution_differences(self, comparison: ComparisonResult) -> list[Any]:
        """Check for significant differences in severity distributions."""
        findings = []

        # Check critical finding ratios
        critical_ratio_a = comparison.severity_breakdown_a["critical"] / max(
            1, comparison.total_findings_a
        )
        critical_ratio_b = comparison.severity_breakdown_b["critical"] / max(
            1, comparison.total_findings_b
        )

        if (
            critical_ratio_a > self.CRITICAL_FINDING_RATIO_THRESHOLD
            and critical_ratio_b < self.CRITICAL_FINDING_RATIO_THRESHOLD * 0.5
        ):
            findings.append(
                self.create_finding(
                    id=f"comparison-critical-severity-gap-{comparison.deployment_a}-{comparison.deployment_b}",
                    title=f"Critical Issue Gap: {comparison.deployment_a} vs {comparison.deployment_b}",
                    description=f"Deployment '{comparison.deployment_a}' has {critical_ratio_a:.1%} critical findings "
                    f"while '{comparison.deployment_b}' has only {critical_ratio_b:.1%} critical findings. "
                    f"This may indicate serious issues in {comparison.deployment_a}.",
                    severity="critical",
                    category="deployment",
                    confidence_level="high",
                    estimated_impact="Critical issues in one environment may indicate systemic problems or incomplete deployments",
                    affected_components=[f"deployment:{comparison.deployment_a}"],
                    remediation_steps=[
                        f"Investigate critical issues in {comparison.deployment_a}",
                        f"Check if {comparison.deployment_b} has been recently patched or configured",
                        "Review deployment procedures for consistency",
                        "Consider promoting fixes from lower to higher environments",
                    ],
                    metadata={
                        "deployment_a": comparison.deployment_a,
                        "deployment_b": comparison.deployment_b,
                        "critical_ratio_a": round(critical_ratio_a, 3),
                        "critical_ratio_b": round(critical_ratio_b, 3),
                    },
                )
            )

        return findings

    def _check_configuration_parity(
        self, comparison: ComparisonResult, analysis_results: dict[str, AnalyzerResult]
    ) -> list[Any]:
        """Check for configuration parity issues between environments."""
        findings = []

        # This is a simplified check - real implementation would:
        # - Compare specific configuration-related findings
        # - Check for security settings differences
        # - Validate resource allocation consistency
        # - Compare version differences

        # For now, just check if one environment has many more config-related findings
        result_a = analysis_results[comparison.deployment_a]
        result_b = analysis_results[comparison.deployment_b]

        config_findings_a = len(
            [f for f in result_a.findings if getattr(f, "category", "") == "config"]
        )
        config_findings_b = len(
            [f for f in result_b.findings if getattr(f, "category", "") == "config"]
        )

        if config_findings_a > config_findings_b * 2 and config_findings_a > 5:
            findings.append(
                self.create_finding(
                    id=f"comparison-config-parity-issue-{comparison.deployment_a}-{comparison.deployment_b}",
                    title=f"Configuration Parity Issue: {comparison.deployment_a} vs {comparison.deployment_b}",
                    description=f"Deployment '{comparison.deployment_a}' has {config_findings_a} configuration issues "
                    f"compared to {config_findings_b} in '{comparison.deployment_b}'. "
                    f"This suggests configuration inconsistencies between environments.",
                    severity="medium",
                    category="config",
                    confidence_level="medium",
                    estimated_impact="Configuration differences may cause inconsistent behavior and make troubleshooting more difficult",
                    affected_components=[
                        f"deployment:{comparison.deployment_a}",
                        f"deployment:{comparison.deployment_b}",
                    ],
                    remediation_steps=[
                        "Compare pipeline configurations between environments",
                        "Check if development environments are missing route configurations",
                        "Validate that staging has production-like settings",
                        "Review deployment automation for configuration consistency",
                    ],
                    metadata={
                        "deployment_a": comparison.deployment_a,
                        "deployment_b": comparison.deployment_b,
                        "config_findings_a": config_findings_a,
                        "config_findings_b": config_findings_b,
                    },
                )
            )

        return findings

    def _generate_summary_findings(
        self, comparisons: list[ComparisonResult], deployments: list[DeploymentConfig]
    ) -> list[Any]:
        """Generate summary findings for the overall comparison."""
        findings = []

        if not comparisons:
            return findings

        # Calculate overall statistics
        total_deployments = len(deployments)
        successful_comparisons = len(comparisons)
        failed_deployments = total_deployments - len(
            {comp.deployment_a for comp in comparisons}.union(
                {comp.deployment_b for comp in comparisons}
            )
        )

        # Summary finding
        findings.append(
            self.create_finding(
                id="multi-deployment-comparison-summary",
                title=f"Multi-Deployment Comparison Summary: {successful_comparisons} Comparisons Completed",
                description=f"Successfully compared {total_deployments} deployments with {successful_comparisons} pairwise comparisons. "
                f"{'All deployments analyzed successfully.' if failed_deployments == 0 else f'{failed_deployments} deployment(s) had analysis failures.'}",
                severity="info" if failed_deployments == 0 else "warning",
                category="deployment",
                confidence_level="high",
                affected_components=[f"deployment:{d.name}" for d in deployments],
                metadata={
                    "total_deployments": total_deployments,
                    "successful_comparisons": successful_comparisons,
                    "failed_deployments": failed_deployments,
                    "deployment_names": [d.name for d in deployments],
                },
            )
        )

        return findings
