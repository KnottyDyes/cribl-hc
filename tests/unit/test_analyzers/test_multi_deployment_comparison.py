from unittest.mock import AsyncMock, MagicMock

import pytest

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.analyzers.multi_deployment_comparison import (
    DeploymentConfig,
    MultiDeploymentComparisonAnalyzer,
)


@pytest.fixture
def analyzer():
    return MultiDeploymentComparisonAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.capture_events = AsyncMock()
    return client


class TestMultiDeploymentComparisonAnalyzer:
    @pytest.mark.asyncio
    async def test_requires_multiple_deployments(self, analyzer, mock_client):
        """Test that analyzer requires at least 2 deployments."""
        # Mock single deployment configuration
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                )
            ]
        )

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "insufficient-deployments" in result.findings[0].id
        assert result.findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_compares_multiple_deployments(self, analyzer, mock_client):
        """Test comparison between multiple deployments."""
        # Mock multiple deployments
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                ),
                DeploymentConfig(
                    name="staging", host="staging.example.com", username="admin", password="pass"
                ),
            ]
        )

        # Mock analysis results
        mock_result_prod = MagicMock()
        mock_result_prod.findings = [
            MagicMock(severity="high", category="security"),
            MagicMock(severity="medium", category="config"),
        ]

        mock_result_staging = MagicMock()
        mock_result_staging.findings = [MagicMock(severity="low", category="config")]

        analyzer._run_parallel_analyses = AsyncMock(
            return_value={"prod": mock_result_prod, "staging": mock_result_staging}
        )

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) >= 1  # At least summary finding

        # Check metadata
        assert result.metadata["deployments_compared"] == 2
        assert result.metadata["comparisons_performed"] == 1  # prod vs staging
        assert result.metadata["total_findings_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_detects_finding_count_differences(self, analyzer, mock_client):
        """Test detection of significant differences in finding counts."""
        # Mock deployments with different finding counts
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                ),
                DeploymentConfig(
                    name="dev", host="dev.example.com", username="admin", password="pass"
                ),
            ]
        )

        # Create mock results with significant count difference
        mock_result_prod = MagicMock()
        mock_result_prod.findings = [MagicMock(severity="info")] * 50  # Many findings

        mock_result_dev = MagicMock()
        mock_result_dev.findings = [MagicMock(severity="info")] * 5  # Few findings

        analyzer._run_parallel_analyses = AsyncMock(
            return_value={"prod": mock_result_prod, "dev": mock_result_dev}
        )

        result = await analyzer.analyze(mock_client)

        # Should detect the significant difference (>50% difference threshold)
        difference_findings = [f for f in result.findings if "finding-count-difference" in f.id]
        assert len(difference_findings) >= 1
        assert difference_findings[0].severity in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_detects_severity_distribution_issues(self, analyzer, mock_client):
        """Test detection of severity distribution differences."""
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                ),
                DeploymentConfig(
                    name="dev", host="dev.example.com", username="admin", password="pass"
                ),
            ]
        )

        # Prod has many critical issues, dev has few
        mock_result_prod = MagicMock()
        mock_result_prod.findings = [MagicMock(severity="critical")] * 10 + [
            MagicMock(severity="info")
        ] * 10

        mock_result_dev = MagicMock()
        mock_result_dev.findings = [MagicMock(severity="info")] * 20

        analyzer._run_parallel_analyses = AsyncMock(
            return_value={"prod": mock_result_prod, "dev": mock_result_dev}
        )

        result = await analyzer.analyze(mock_client)

        # Should detect critical severity gap
        severity_findings = [f for f in result.findings if "critical-severity-gap" in f.id]
        assert len(severity_findings) >= 1
        assert severity_findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_detects_configuration_parity_issues(self, analyzer, mock_client):
        """Test detection of configuration parity issues."""
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                ),
                DeploymentConfig(
                    name="staging", host="staging.example.com", username="admin", password="pass"
                ),
            ]
        )

        # Prod has many config issues, staging has few
        mock_result_prod = MagicMock()
        mock_result_prod.findings = [
            MagicMock(severity="medium", category="config"),
            MagicMock(severity="medium", category="config"),
            MagicMock(severity="medium", category="config"),
            MagicMock(severity="medium", category="security"),
        ]

        mock_result_staging = MagicMock()
        mock_result_staging.findings = [
            MagicMock(severity="low", category="config"),
        ]

        analyzer._run_parallel_analyses = AsyncMock(
            return_value={"prod": mock_result_prod, "staging": mock_result_staging}
        )

        result = await analyzer.analyze(mock_client)

        # Should detect config parity issue
        parity_findings = [f for f in result.findings if "config-parity-issue" in f.id]
        assert len(parity_findings) >= 1
        assert parity_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_handles_analysis_failures(self, analyzer, mock_client):
        """Test handling of deployment analysis failures."""
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                ),
                DeploymentConfig(
                    name="failing", host="failing.example.com", username="admin", password="pass"
                ),
            ]
        )

        # Simulate one deployment succeeding, one failing
        successful_result = MagicMock()
        successful_result.findings = [MagicMock(severity="info")]
        successful_result.success = True

        failed_result = AnalyzerResult(objective="health", success=False, error="Connection failed")

        analyzer._run_parallel_analyses = AsyncMock(
            return_value={"prod": successful_result, "failing": failed_result}
        )

        result = await analyzer.analyze(mock_client)

        assert result.success is True  # Overall analysis still succeeds
        assert len(result.findings) >= 1

        # Check that failed deployments are noted
        assert result.metadata["failed_deployments"] == 1

    @pytest.mark.asyncio
    async def test_generates_comparison_summary(self, analyzer, mock_client):
        """Test generation of comparison summary findings."""
        analyzer._get_deployment_configs = MagicMock(
            return_value=[
                DeploymentConfig(
                    name="prod", host="prod.example.com", username="admin", password="pass"
                ),
                DeploymentConfig(
                    name="dev", host="dev.example.com", username="admin", password="pass"
                ),
            ]
        )

        mock_result_prod = MagicMock()
        mock_result_prod.findings = [MagicMock(severity="info")]

        mock_result_dev = MagicMock()
        mock_result_dev.findings = [MagicMock(severity="info")]

        analyzer._run_parallel_analyses = AsyncMock(
            return_value={"prod": mock_result_prod, "dev": mock_result_dev}
        )

        result = await analyzer.analyze(mock_client)

        # Should have summary finding
        summary_findings = [f for f in result.findings if "comparison-summary" in f.id]
        assert len(summary_findings) == 1
        assert summary_findings[0].severity == "info"

    def test_count_findings_by_severity(self, analyzer):
        """Test severity counting logic."""
        findings = [
            MagicMock(severity="critical"),
            MagicMock(severity="high"),
            MagicMock(severity="high"),
            MagicMock(severity="medium"),
            MagicMock(severity="low"),
            MagicMock(severity="info"),
            MagicMock(severity="info"),
            MagicMock(severity="info"),
            MagicMock(severity=None),  # Should handle None
        ]

        result = analyzer._count_findings_by_severity(findings)

        expected = {
            "critical": 1,
            "high": 2,
            "medium": 1,
            "low": 1,
            "info": 3,
        }
        assert result == expected

    def test_compare_two_deployments(self, analyzer):
        """Test comparison between two deployment results."""
        result_a = MagicMock()
        result_a.findings = [
            MagicMock(severity="critical"),
            MagicMock(severity="high"),
            MagicMock(severity="medium"),
        ]

        result_b = MagicMock()
        result_b.findings = [
            MagicMock(severity="low"),
            MagicMock(severity="info"),
        ]

        comparison = analyzer._compare_two_deployments("prod", "dev", result_a, result_b)

        assert comparison.deployment_a == "prod"
        assert comparison.deployment_b == "dev"
        assert comparison.total_findings_a == 3
        assert comparison.total_findings_b == 2
        assert comparison.severity_breakdown_a["critical"] == 1
        assert comparison.severity_breakdown_b["low"] == 1

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "multi_deployment_comparison"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        products = analyzer.supported_products
        assert "stream" in products
        assert "edge" in products
        assert "lake" in products
        assert "search" in products

    def test_description(self, analyzer):
        """Test analyzer description."""
        description = analyzer.get_description()
        assert "compare" in description.lower()
        assert "deployment" in description.lower()

    def test_required_permissions(self, analyzer):
        """Test required permissions."""
        permissions = analyzer.get_required_permissions()
        assert "read:system" in permissions
        assert "read:config" in permissions
        assert "read:health" in permissions

    def test_estimated_api_calls(self, analyzer):
        """Test estimated API calls."""
        calls = analyzer.get_estimated_api_calls()
        assert calls >= 0  # Should be a reasonable number
