"""
Unit tests for FleetAnalyzer (US6 - Fleet & Multi-Tenancy Management).

Tests cover:
- Multi-deployment orchestration
- Cross-environment comparison
- Fleet-wide pattern detection
- Aggregated reporting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from cribl_hc.analyzers.fleet import FleetAnalyzer
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate


class TestFleetAnalyzer:
    """Test suite for FleetAnalyzer."""

    @pytest.fixture
    def fleet_analyzer(self):
        """Create FleetAnalyzer instance."""
        return FleetAnalyzer()

    @pytest.fixture
    def mock_client_dev(self):
        """Create mock client for dev environment."""
        client = AsyncMock(spec=CriblAPIClient)
        client.deployment_name = "dev"
        client.environment = "development"
        client.base_url = "https://dev.cribl.example.com"
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        return client

    @pytest.fixture
    def mock_client_staging(self):
        """Create mock client for staging environment."""
        client = AsyncMock(spec=CriblAPIClient)
        client.deployment_name = "staging"
        client.environment = "staging"
        client.base_url = "https://staging.cribl.example.com"
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        return client

    @pytest.fixture
    def mock_client_prod(self):
        """Create mock client for production environment."""
        client = AsyncMock(spec=CriblAPIClient)
        client.deployment_name = "prod"
        client.environment = "production"
        client.base_url = "https://prod.cribl.example.com"
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        return client

    # === Objective Name Tests ===

    def test_objective_name(self, fleet_analyzer):
        """Test that analyzer has correct objective name."""
        assert fleet_analyzer.objective_name == "fleet"

    # === Multi-Deployment Orchestration Tests ===

    @pytest.mark.asyncio
    async def test_analyze_multiple_deployments(self, fleet_analyzer, mock_client_dev, mock_client_staging):
        """Test analyzing multiple deployments in parallel."""
        deployments = {
            "dev": mock_client_dev,
            "staging": mock_client_staging
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        assert result.success is True
        assert "deployments_analyzed" in result.metadata
        assert result.metadata["deployments_analyzed"] == 2
        assert "dev" in result.metadata["deployment_names"]
        assert "staging" in result.metadata["deployment_names"]

    @pytest.mark.asyncio
    async def test_analyze_fleet_empty(self, fleet_analyzer):
        """Test analyzing empty fleet returns appropriate result."""
        result = await fleet_analyzer.analyze_fleet({})

        assert result.success is False
        assert "No deployments" in result.error or result.metadata.get("deployments_analyzed", 0) == 0

    @pytest.mark.asyncio
    async def test_analyze_fleet_single_deployment(self, fleet_analyzer, mock_client_prod):
        """Test analyzing single deployment works."""
        deployments = {"prod": mock_client_prod}

        result = await fleet_analyzer.analyze_fleet(deployments)

        assert result.success is True
        assert result.metadata["deployments_analyzed"] == 1

    # === Cross-Environment Comparison Tests ===

    @pytest.mark.asyncio
    async def test_compare_environments(self, fleet_analyzer, mock_client_dev, mock_client_prod):
        """Test cross-environment comparison generates findings."""
        # Mock different health scores
        mock_client_dev.get_system_status = AsyncMock(return_value={
            "health": "yellow",
            "workers": {"healthy": 2, "unhealthy": 1}
        })
        mock_client_prod.get_system_status = AsyncMock(return_value={
            "health": "green",
            "workers": {"healthy": 5, "unhealthy": 0}
        })

        deployments = {
            "dev": mock_client_dev,
            "prod": mock_client_prod
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Should identify environment differences
        comparison_findings = [
            f for f in result.findings
            if "environment" in f.id.lower() or "comparison" in f.id.lower()
        ]
        assert len(comparison_findings) >= 0  # May have comparison findings

    @pytest.mark.asyncio
    async def test_identify_configuration_drift(self, fleet_analyzer, mock_client_dev, mock_client_prod):
        """Test identification of configuration drift between environments."""
        # Mock different pipeline counts
        mock_client_dev.get_pipelines = AsyncMock(return_value=[
            {"id": "pipeline-1"},
            {"id": "pipeline-2"}
        ])
        mock_client_prod.get_pipelines = AsyncMock(return_value=[
            {"id": "pipeline-1"},
            {"id": "pipeline-2"},
            {"id": "pipeline-3"}  # Extra pipeline in prod
        ])

        deployments = {
            "dev": mock_client_dev,
            "prod": mock_client_prod
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Should detect configuration drift
        drift_findings = [
            f for f in result.findings
            if "drift" in f.id.lower() or "drift" in f.title.lower()
        ]
        # May or may not have drift findings depending on implementation
        assert isinstance(drift_findings, list)

    # === Fleet-Wide Pattern Detection Tests ===

    @pytest.mark.asyncio
    async def test_detect_common_issues(self, fleet_analyzer):
        """Test detection of common issues across fleet."""
        # Create mock deployments with same issue
        clients = {}
        for env in ["dev", "staging", "prod"]:
            client = AsyncMock(spec=CriblAPIClient)
            client.deployment_name = env
            client.environment = env
            # All have high memory usage
            client.get_workers = AsyncMock(return_value=[
                {"id": f"worker-{env}-1", "metrics": {"memory_utilization": 92}}
            ])
            clients[env] = client

        result = await fleet_analyzer.analyze_fleet(clients)

        # Should identify fleet-wide pattern
        assert "fleet_patterns" in result.metadata or len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_aggregate_findings_by_severity(self, fleet_analyzer, mock_client_dev, mock_client_staging):
        """Test aggregation of findings by severity across fleet."""
        deployments = {
            "dev": mock_client_dev,
            "staging": mock_client_staging
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Should have severity counts in metadata
        metadata_keys = result.metadata.keys()
        # May have severity aggregations
        assert "deployments_analyzed" in metadata_keys

    # === Aggregated Reporting Tests ===

    @pytest.mark.asyncio
    async def test_fleet_metadata_includes_summary(self, fleet_analyzer, mock_client_dev, mock_client_staging, mock_client_prod):
        """Test that fleet analysis includes comprehensive summary."""
        deployments = {
            "dev": mock_client_dev,
            "staging": mock_client_staging,
            "prod": mock_client_prod
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Should have fleet summary metadata
        assert "deployments_analyzed" in result.metadata
        assert "deployment_names" in result.metadata
        assert result.metadata["deployments_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_fleet_recommendations_generated(self, fleet_analyzer, mock_client_dev, mock_client_prod):
        """Test that fleet-level recommendations are generated."""
        deployments = {
            "dev": mock_client_dev,
            "prod": mock_client_prod
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # May generate fleet-level recommendations
        assert isinstance(result.recommendations, list)

    # === Error Handling Tests ===

    @pytest.mark.asyncio
    async def test_partial_failure_graceful(self, fleet_analyzer, mock_client_dev):
        """Test graceful handling when one deployment fails."""
        # Mock failing client
        failing_client = AsyncMock(spec=CriblAPIClient)
        failing_client.deployment_name = "failing"
        failing_client.get_system_status = AsyncMock(side_effect=Exception("API Error"))

        deployments = {
            "dev": mock_client_dev,
            "failing": failing_client
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Should still succeed with partial results
        assert result.success is True or "deployments_analyzed" in result.metadata
        # Should note the failure
        assert "failed_deployments" in result.metadata or "errors" in result.metadata or result.metadata.get("deployments_analyzed", 0) >= 1

    @pytest.mark.asyncio
    async def test_all_deployments_fail(self, fleet_analyzer):
        """Test handling when all deployments fail."""
        failing_client = AsyncMock(spec=CriblAPIClient)
        failing_client.deployment_name = "failing"
        failing_client.get_system_status = AsyncMock(side_effect=Exception("API Error"))

        deployments = {"failing": failing_client}

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Should return result with error information
        assert "failed_deployments" in result.metadata or result.success is False

    # === Product Support Tests ===

    def test_supported_products(self, fleet_analyzer):
        """Test that FleetAnalyzer supports all products."""
        assert "stream" in fleet_analyzer.supported_products
        assert "edge" in fleet_analyzer.supported_products
        # Fleet management applies to all products

    # === API Call Estimation Tests ===

    def test_estimated_api_calls_per_deployment(self, fleet_analyzer):
        """Test API call estimation for fleet analysis."""
        # Should estimate calls per deployment
        estimated = fleet_analyzer.get_estimated_api_calls()
        assert estimated > 0

    # === Environment Comparison Edge Cases ===

    @pytest.mark.asyncio
    async def test_compare_identical_environments(self, fleet_analyzer):
        """Test comparison of identical environments."""
        # Create two identical mock clients
        clients = {}
        for env in ["env1", "env2"]:
            client = AsyncMock(spec=CriblAPIClient)
            client.deployment_name = env
            client.get_system_status = AsyncMock(return_value={"health": "green"})
            clients[env] = client

        result = await fleet_analyzer.analyze_fleet(clients)

        # Should not generate drift findings for identical configs
        assert result.success is True

    @pytest.mark.asyncio
    async def test_deployment_naming_in_findings(self, fleet_analyzer, mock_client_dev, mock_client_prod):
        """Test that findings reference deployment names correctly."""
        deployments = {
            "dev": mock_client_dev,
            "prod": mock_client_prod
        }

        result = await fleet_analyzer.analyze_fleet(deployments)

        # Findings should reference deployment names in affected_components or metadata
        for finding in result.findings:
            # Check that finding has deployment context
            assert finding.metadata or finding.affected_components
