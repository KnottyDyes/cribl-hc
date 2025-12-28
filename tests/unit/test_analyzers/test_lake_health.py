"""
Unit tests for LakeHealthAnalyzer.

Tests retention policy monitoring, dataset health checks, and lakehouse availability.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.lake_health import LakeHealthAnalyzer
from cribl_hc.models.finding import Finding


@pytest.fixture
def mock_client():
    """Create a mock Cribl API client."""
    client = AsyncMock()
    client.product_type = "lake"
    client.is_edge = False
    client.base_url = "https://test.cribl.cloud"
    return client


@pytest.fixture
def analyzer():
    """Create LakeHealthAnalyzer instance."""
    return LakeHealthAnalyzer()


class TestLakeHealthAnalyzer:
    """Tests for LakeHealthAnalyzer."""

    def test_objective_name(self, analyzer):
        """Test analyzer returns correct objective name."""
        assert analyzer.objective_name == "lake"

    def test_estimated_api_calls(self, analyzer):
        """Test API call estimation."""
        # datasets(1) + stats(1) + lakehouses(1) = 3
        assert analyzer.get_estimated_api_calls() == 3

    @pytest.mark.asyncio
    async def test_analyze_with_healthy_datasets(self, analyzer, mock_client):
        """Test analyzer with all datasets healthy."""
        # Mock response: datasets with good retention periods
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "default_logs",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "default_logs-view"
                },
                {
                    "id": "default_metrics",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 15,
                    "format": "parquet",
                    "viewName": "default_metrics-view"
                }
            ],
            "count": 2
        }
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.objective == "lake"
        assert result.success is True
        assert result.metadata["total_datasets"] == 2
        assert result.metadata["datasets_with_short_retention"] == 0

    @pytest.mark.asyncio
    async def test_analyze_detects_short_retention(self, analyzer, mock_client):
        """Test analyzer detects datasets with very short retention."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "test_dataset",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 1,  # Very short
                    "format": "json",
                    "viewName": "test-view"
                },
                {
                    "id": "storage_test",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 5,  # Short
                    "format": "json",
                    "viewName": "storage-view"
                }
            ],
            "count": 2
        }
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["datasets_with_short_retention"] == 2
        # Should have high severity findings for short retention
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_json_format_inefficiency(self, analyzer, mock_client):
        """Test analyzer detects datasets using JSON instead of Parquet."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "logs_json",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",  # Inefficient for large datasets
                    "viewName": "logs-view"
                },
                {
                    "id": "metrics_parquet",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "parquet",  # Efficient
                    "viewName": "metrics-view"
                }
            ],
            "count": 2
        }
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["json_datasets"] == 1
        assert result.metadata["parquet_datasets"] == 1

    @pytest.mark.asyncio
    async def test_analyze_handles_empty_datasets(self, analyzer, mock_client):
        """Test analyzer handles no datasets gracefully."""
        mock_client.get_lake_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_datasets"] == 0
        # Should have info finding about no datasets
        info_findings = [f for f in result.findings if f.severity == "info"]
        assert len(info_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_handles_api_errors(self, analyzer, mock_client):
        """Test analyzer handles API errors gracefully."""
        mock_client.get_lake_datasets.side_effect = Exception("API connection failed")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "error" in result.metadata
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_recommends_retention_optimization(self, analyzer, mock_client):
        """Test analyzer recommends optimizing retention for short-lived datasets."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "test_dataset",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 3,  # Very short
                    "format": "json",
                    "viewName": "test-view",
                    "description": "Test dataset"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have recommendations for retention optimization
        assert len(result.recommendations) > 0
        retention_recs = [r for r in result.recommendations if "retention" in r.title.lower()]
        assert len(retention_recs) > 0

    @pytest.mark.asyncio
    async def test_analyze_recommends_parquet_conversion(self, analyzer, mock_client):
        """Test analyzer recommends converting JSON to Parquet."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "large_json_dataset",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",  # Should recommend Parquet
                    "viewName": "large-view",
                    "description": "Large dataset"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have recommendation for Parquet conversion
        parquet_recs = [r for r in result.recommendations if "parquet" in r.title.lower()]
        assert len(parquet_recs) > 0

    @pytest.mark.asyncio
    async def test_analyze_includes_lakehouse_info(self, analyzer, mock_client):
        """Test analyzer includes lakehouse availability information."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "default_logs",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "default_logs-view"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}
        mock_client.get_lake_lakehouses.return_value = {
            "items": [
                {
                    "id": "lakehouse-001",
                    "name": "Primary Lakehouse",
                    "status": "active"
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["lakehouse_count"] == 1
