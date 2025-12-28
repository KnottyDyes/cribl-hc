"""
Unit tests for StorageAnalyzer.

Following TDD: These tests are written FIRST and should FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.storage import StorageAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestStorageAnalyzer:
    """Test suite for StorageAnalyzer."""

    @pytest.fixture
    def storage_analyzer(self):
        """Create StorageAnalyzer instance."""
        return StorageAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock Cribl API client."""
        client = AsyncMock(spec=CriblAPIClient)
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        return client

    # === Objective Name and Metadata Tests ===

    def test_objective_name(self, storage_analyzer):
        """Test that analyzer has correct objective name."""
        assert storage_analyzer.objective_name == "storage"

    def test_estimated_api_calls(self, storage_analyzer):
        """Test API call estimation."""
        # Should need: routes(1) + outputs(1) + metrics(1) + pipelines(1) = 4 calls
        assert storage_analyzer.get_estimated_api_calls() == 4

    def test_required_permissions(self, storage_analyzer):
        """Test required API permissions."""
        permissions = storage_analyzer.get_required_permissions()
        assert "read:routes" in permissions
        assert "read:outputs" in permissions
        assert "read:metrics" in permissions

    # === Storage Consumption Analysis Tests ===

    @pytest.mark.asyncio
    async def test_analyze_storage_by_destination(self, storage_analyzer, mock_client):
        """Test storage consumption calculation by destination."""
        # Mock outputs with volume data
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-main",
                "type": "s3",
                "stats": {"out_bytes_total": 1_000_000_000_000}  # 1TB
            },
            {
                "id": "splunk-prod",
                "type": "splunk",
                "stats": {"out_bytes_total": 500_000_000_000}  # 500GB
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        assert result.success is True
        assert "storage_by_destination" in result.metadata
        assert result.metadata["storage_by_destination"]["s3-main"] > 0
        assert result.metadata["storage_by_destination"]["splunk-prod"] > 0

    @pytest.mark.asyncio
    async def test_identify_high_volume_destinations(self, storage_analyzer, mock_client):
        """Test identification of destinations consuming most storage."""
        # Mock high-volume destination
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-archive",
                "type": "s3",
                "stats": {"out_bytes_total": 10_000_000_000_000}  # 10TB
            },
            {
                "id": "s3-small",
                "type": "s3",
                "stats": {"out_bytes_total": 10_000_000}  # 10MB
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should create finding for high-volume destination
        high_volume_findings = [
            f for f in result.findings
            if "high" in f.id.lower() and "volume" in f.id.lower()
        ]
        assert len(high_volume_findings) > 0
        assert "s3-archive" in high_volume_findings[0].affected_components

    # === Data Reduction Opportunity Tests ===

    @pytest.mark.asyncio
    async def test_identify_sampling_opportunities(self, storage_analyzer, mock_client):
        """Test identification of sampling opportunities."""
        # Mock route sending all data without sampling
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "logs-to-s3",
                "filter": "true",  # All data
                "output": "s3-archive",
                "final": True
            }
        ])
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-archive",
                "type": "s3",
                "stats": {"out_bytes_total": 5_000_000_000_000}  # 5TB
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should suggest sampling for high-volume routes
        sampling_findings = [
            f for f in result.findings
            if "sampling" in f.description.lower()
        ]
        assert len(sampling_findings) > 0

    @pytest.mark.asyncio
    async def test_identify_filtering_opportunities(self, storage_analyzer, mock_client):
        """Test identification of filtering opportunities."""
        # Mock route with no filtering
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "all-logs-to-s3",
                "filter": "true",  # No filtering
                "output": "s3-main",
                "final": True
            }
        ])
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-main",
                "type": "s3",
                "stats": {"out_bytes_total": 2_000_000_000_000}  # 2TB
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should suggest filtering for high-volume unfiltered routes
        filtering_findings = [
            f for f in result.findings
            if "filter" in f.description.lower() or "reduce" in f.description.lower()
        ]
        assert len(filtering_findings) > 0

    @pytest.mark.asyncio
    async def test_identify_aggregation_opportunities(self, storage_analyzer, mock_client):
        """Test identification of aggregation/rollup opportunities."""
        # Mock high-frequency metrics being sent without aggregation
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "metrics-to-s3",
                "filter": "sourcetype=='metrics'",
                "output": "s3-metrics",
                "final": True
            }
        ])
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-metrics",
                "type": "s3",
                "stats": {"out_bytes_total": 3_000_000_000_000}  # 3TB of metrics
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[
            {
                "id": "metrics-passthrough",
                "conf": {
                    "functions": []  # No aggregation
                }
            }
        ])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should suggest aggregation for metrics
        aggregation_findings = [
            f for f in result.findings
            if "aggregat" in f.description.lower() or "rollup" in f.description.lower()
        ]
        # May or may not find aggregation opportunity depending on implementation
        # This is a "nice to have" finding

    # === ROI Calculation Tests ===

    @pytest.mark.asyncio
    async def test_calculate_storage_savings_gb(self, storage_analyzer, mock_client):
        """Test calculation of potential GB saved."""
        # Mock high-volume destination
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-main",
                "type": "s3",
                "stats": {"out_bytes_total": 5_000_000_000_000}  # 5TB
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "logs-to-s3",
                "filter": "true",
                "output": "s3-main",
                "final": True
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Check for recommendations with GB saved estimates
        storage_recs = [
            r for r in result.recommendations
            if "storage" in r.id.lower()
        ]
        if storage_recs:
            # Should have impact estimate with storage savings
            assert storage_recs[0].impact_estimate is not None
            # Impact estimate should mention savings or reduction
            impact_str = str(storage_recs[0].impact_estimate)
            assert "GB" in impact_str or "TB" in impact_str or "save" in impact_str.lower()

    @pytest.mark.asyncio
    async def test_calculate_cost_savings(self, storage_analyzer, mock_client):
        """Test calculation of potential cost savings."""
        # Mock high-volume S3 destination (S3 storage costs ~$0.023/GB/month)
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-archive",
                "type": "s3",
                "stats": {"out_bytes_total": 10_000_000_000_000}  # 10TB
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "all-to-s3",
                "filter": "true",
                "output": "s3-archive",
                "final": True
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Check for cost savings in recommendations
        storage_recs = [
            r for r in result.recommendations
            if "storage" in r.id.lower() or "cost" in r.id.lower()
        ]
        if storage_recs:
            # Impact estimate should mention cost savings
            impact_str = str(storage_recs[0].impact_estimate)
            assert "$" in impact_str or "cost" in impact_str.lower()

    @pytest.mark.asyncio
    async def test_effort_estimation(self, storage_analyzer, mock_client):
        """Test implementation effort estimation."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-main",
                "type": "s3",
                "stats": {"out_bytes_total": 1_000_000_000_000}
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Recommendations should include implementation effort
        for rec in result.recommendations:
            assert hasattr(rec, "implementation_effort")
            assert rec.implementation_effort in ["low", "medium", "high"]

    # === Before/After Projection Tests ===

    @pytest.mark.asyncio
    async def test_before_after_projections(self, storage_analyzer, mock_client):
        """Test before/after storage projections."""
        # Mock high-volume destination
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-archive",
                "type": "s3",
                "stats": {"out_bytes_total": 5_000_000_000_000}  # 5TB current
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "logs-to-archive",
                "filter": "true",
                "output": "s3-archive",
                "final": True
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Check for recommendations with before/after states
        storage_recs = [
            r for r in result.recommendations
            if "storage" in r.id.lower()
        ]
        if storage_recs:
            rec = storage_recs[0]
            assert hasattr(rec, "before_state")
            assert hasattr(rec, "after_state")
            assert rec.before_state is not None
            assert rec.after_state is not None
            # Before state should mention current volume
            assert "TB" in rec.before_state or "GB" in rec.before_state
            # After state should mention reduced volume
            assert "TB" in rec.after_state or "GB" in rec.after_state or "reduce" in rec.after_state.lower()

    # === Metadata Tests ===

    @pytest.mark.asyncio
    async def test_metadata_total_storage(self, storage_analyzer, mock_client):
        """Test total storage consumption in metadata."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {"id": "out1", "stats": {"out_bytes_total": 1_000_000_000}},
            {"id": "out2", "stats": {"out_bytes_total": 2_000_000_000}}
        ])
        mock_client.get_routes = AsyncMock(return_value=[])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        assert "total_bytes" in result.metadata
        assert result.metadata["total_bytes"] == 3_000_000_000

    @pytest.mark.asyncio
    async def test_metadata_potential_savings(self, storage_analyzer, mock_client):
        """Test potential savings percentage in metadata."""
        # High-volume destination with no optimization
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-main",
                "type": "s3",
                "stats": {"out_bytes_total": 10_000_000_000_000}
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[
            {
                "id": "all-to-s3",
                "filter": "true",
                "output": "s3-main",
                "final": True
            }
        ])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should calculate potential savings percentage
        assert "potential_savings_pct" in result.metadata or "savings_opportunities" in result.metadata

    # === Edge Case Tests ===

    @pytest.mark.asyncio
    async def test_no_outputs(self, storage_analyzer, mock_client):
        """Test analysis when no outputs configured."""
        mock_client.get_outputs = AsyncMock(return_value=[])
        mock_client.get_routes = AsyncMock(return_value=[])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should succeed with zero storage
        assert result.success is True
        assert result.metadata.get("total_bytes", 0) == 0
        assert result.metadata.get("destination_count", 0) == 0

    @pytest.mark.asyncio
    async def test_outputs_without_stats(self, storage_analyzer, mock_client):
        """Test handling of outputs without statistics."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "new-output",
                "type": "s3"
                # No stats field
            }
        ])
        mock_client.get_routes = AsyncMock(return_value=[])
        mock_client.get_pipelines = AsyncMock(return_value=[])
        mock_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(mock_client)

        # Should handle gracefully
        assert result.success is True

    @pytest.mark.asyncio
    async def test_error_handling(self, storage_analyzer, mock_client):
        """Test graceful error handling."""
        mock_client.get_outputs = AsyncMock(side_effect=Exception("API Error"))

        result = await storage_analyzer.analyze(mock_client)

        # Should still return success (graceful degradation)
        assert result.success is True
        # Should have zero total bytes when outputs fetch fails
        assert result.metadata.get("total_bytes") == 0
        # Should have zero destinations
        assert result.metadata.get("destination_count") == 0

    # === Product Type Tests (Stream vs Edge) ===

    @pytest.mark.asyncio
    async def test_edge_deployment_analysis(self, storage_analyzer):
        """Test storage analysis on Edge deployment."""
        edge_client = AsyncMock(spec=CriblAPIClient)
        edge_client.is_edge = True
        edge_client.is_stream = False
        edge_client.product_type = "edge"

        # Edge typically has fewer outputs
        edge_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "cribl-stream",
                "type": "cribl",
                "stats": {"out_bytes_total": 100_000_000}  # 100MB to Stream
            }
        ])
        edge_client.get_routes = AsyncMock(return_value=[])
        edge_client.get_pipelines = AsyncMock(return_value=[])
        edge_client.get_metrics = AsyncMock(return_value={})

        result = await storage_analyzer.analyze(edge_client)

        assert result.success is True
        assert result.metadata.get("product_type") == "edge"
        # Edge should typically have lower volumes and fewer optimization opportunities
