"""
Unit tests for LakeHealthAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.lake_health import LakeHealthAnalyzer


@pytest.fixture
def mock_client():
    """Create a mock Cribl API client."""
    client = AsyncMock()
    client.product_type = "lake"
    client.is_edge = False
    client.base_url = "https://test.cribl.cloud"

    async def _mock_get_lake_datasets(*args, **kwargs):
        return {"items": [], "count": 0}

    async def _mock_get_lake_lakehouses(*args, **kwargs):
        return {"items": [], "count": 0}

    async def _mock_get_lake_storage_locations(*args, **kwargs):
        return {"items": [], "count": 0}

    client.get_lake_datasets = _mock_get_lake_datasets
    client.get_lake_lakehouses = _mock_get_lake_lakehouses
    client.get_lake_storage_locations = _mock_get_lake_storage_locations

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
        assert analyzer.get_estimated_api_calls() == 4

    @pytest.mark.asyncio
    async def test_analyze_with_healthy_datasets(self, analyzer, mock_client):
        """Test analyzer with all datasets healthy."""

        async def _mock_get_lake_datasets(*args, **kwargs):
            return {
                "items": [
                    {
                        "id": "default_logs",
                        "bucketName": "b",
                        "viewName": "v",
                        "retentionPeriodInDays": 30,
                        "format": "json",
                    },
                    {
                        "id": "default_metrics",
                        "bucketName": "b",
                        "viewName": "v",
                        "retentionPeriodInDays": 15,
                        "format": "parquet",
                    },
                ],
                "count": 2,
            }

        mock_client.get_lake_datasets = _mock_get_lake_datasets

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_datasets"] == 2
        assert len(result.findings) == 1  # one for json format

    @pytest.mark.asyncio
    async def test_analyze_detects_short_retention(self, analyzer, mock_client):
        """Test analyzer detects datasets with very short retention."""

        async def _mock_get_lake_datasets(*args, **kwargs):
            return {
                "items": [
                    {
                        "id": "test_dataset",
                        "bucketName": "b",
                        "viewName": "v",
                        "retentionPeriodInDays": 1,
                        "format": "json",
                    },
                    {
                        "id": "storage_test",
                        "bucketName": "b",
                        "viewName": "v",
                        "retentionPeriodInDays": 5,
                        "format": "json",
                    },
                ],
                "count": 2,
            }

        mock_client.get_lake_datasets = _mock_get_lake_datasets

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["datasets_with_very_short_retention"] == 2
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) == 2

    @pytest.mark.asyncio
    async def test_analyze_handles_api_errors(self, analyzer, mock_client):
        """Test analyzer handles API errors gracefully."""

        async def _mock_get_lake_datasets(*args, **kwargs):
            raise Exception("API connection failed")

        mock_client.get_lake_datasets = _mock_get_lake_datasets

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "error" in result.metadata
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_no_datasets(self, analyzer, mock_client):
        """Test analyzer with an empty list of datasets from the API."""
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_datasets"] == 0
        assert len(result.findings) == 1
        assert result.findings[0].severity == "info"
        assert "No Lake Datasets Found" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_with_malformed_datasets(self, analyzer, mock_client):
        """Test analyzer handles datasets with missing required fields."""

        async def _mock_get_lake_datasets(*args, **kwargs):
            return {
                "items": [
                    {
                        "id": "test_dataset",
                        "bucketName": "b",
                        "viewName": "v",
                        "retentionPeriodInDays": 1,
                    }
                    # Missing 'format'
                ],
                "count": 1,
            }

        mock_client.get_lake_datasets = _mock_get_lake_datasets

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "error" in result.metadata
        assert "validation error" in result.metadata["error"].lower()
