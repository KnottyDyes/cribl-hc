"""
Unit tests for LakeStorageAnalyzer.

Tests storage optimization analysis including format efficiency,
dataset activity monitoring, and cost savings calculations.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from cribl_hc.analyzers.lake_storage import LakeStorageAnalyzer


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
    """Create LakeStorageAnalyzer instance."""
    return LakeStorageAnalyzer()


class TestLakeStorageAnalyzer:
    """Tests for LakeStorageAnalyzer."""

    def test_objective_name(self, analyzer):
        """Test analyzer returns correct objective name."""
        assert analyzer.objective_name == "lake"

    def test_estimated_api_calls(self, analyzer):
        """Test API call estimation."""
        # datasets(1) + stats(1) = 2
        assert analyzer.get_estimated_api_calls() == 2

    @pytest.mark.asyncio
    async def test_analyze_with_efficient_datasets(self, analyzer, mock_client):
        """Test analyzer with all datasets already optimized."""
        # Mock response: datasets with Parquet format (efficient)
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "efficient_logs",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "parquet",
                    "viewName": "efficient_logs-view"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {
            "items": [
                {
                    "datasetId": "efficient_logs",
                    "sizeBytes": 10737418240,  # 10GB
                    "recordCount": 1000000,
                    "lastUpdated": int(datetime.utcnow().timestamp() * 1000)
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.objective == "lake"
        assert result.success is True
        assert result.metadata["total_datasets"] == 1
        assert result.metadata["parquet_datasets"] == 1
        assert result.metadata["potential_savings_gb"] == 0

    @pytest.mark.asyncio
    async def test_analyze_detects_large_json_dataset(self, analyzer, mock_client):
        """Test analyzer detects large JSON datasets for optimization."""
        # 50GB JSON dataset - should trigger optimization finding
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "large_json_logs",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "large_json_logs-view"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {
            "items": [
                {
                    "datasetId": "large_json_logs",
                    "sizeBytes": 53687091200,  # 50GB
                    "recordCount": 5000000,
                    "lastUpdated": int(datetime.utcnow().timestamp() * 1000)
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["json_datasets"] == 1
        assert result.metadata["potential_savings_gb"] > 0
        # Should have medium severity finding for large JSON dataset
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) > 0
        # Should have optimization recommendation
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_ignores_small_json_datasets(self, analyzer, mock_client):
        """Test analyzer ignores small JSON datasets (< 10GB)."""
        # 5GB JSON dataset - too small to optimize
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "small_json_logs",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "small_json_logs-view"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {
            "items": [
                {
                    "datasetId": "small_json_logs",
                    "sizeBytes": 5368709120,  # 5GB
                    "recordCount": 500000,
                    "lastUpdated": int(datetime.utcnow().timestamp() * 1000)
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should not flag small JSON datasets
        storage_findings = [f for f in result.findings if "json" in f.id.lower()]
        assert len(storage_findings) == 0
        assert result.metadata["potential_savings_gb"] == 0

    @pytest.mark.asyncio
    async def test_analyze_detects_inactive_datasets(self, analyzer, mock_client):
        """Test analyzer detects inactive datasets (30+ days)."""
        # Dataset last updated 45 days ago
        last_update = datetime.utcnow() - timedelta(days=45)
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "old_dataset",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "parquet",
                    "viewName": "old_dataset-view"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {
            "items": [
                {
                    "datasetId": "old_dataset",
                    "sizeBytes": 1073741824,  # 1GB
                    "recordCount": 100000,
                    "lastUpdated": int(last_update.timestamp() * 1000)
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have low severity finding for inactive dataset
        low_findings = [f for f in result.findings if f.severity == "low"]
        assert len(low_findings) > 0
        assert any("inactive" in f.title.lower() for f in low_findings)

    @pytest.mark.asyncio
    async def test_analyze_handles_datasets_without_stats(self, analyzer, mock_client):
        """Test analyzer handles datasets without statistics gracefully."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "no_stats_dataset",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "no_stats_dataset-view"
                }
            ],
            "count": 1
        }
        # No stats available for this dataset
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_datasets"] == 1
        assert result.metadata["datasets_with_stats"] == 0
        # Cannot optimize without size data
        assert result.metadata["potential_savings_gb"] == 0

    @pytest.mark.asyncio
    async def test_analyze_handles_empty_datasets(self, analyzer, mock_client):
        """Test analyzer handles no datasets gracefully."""
        mock_client.get_lake_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_lake_dataset_stats.return_value = {"items": [], "count": 0}

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
        # Should have critical error finding
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_calculates_total_storage(self, analyzer, mock_client):
        """Test analyzer calculates total storage across datasets."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "dataset1",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "parquet",
                    "viewName": "dataset1-view"
                },
                {
                    "id": "dataset2",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "dataset2-view"
                }
            ],
            "count": 2
        }
        mock_client.get_lake_dataset_stats.return_value = {
            "items": [
                {
                    "datasetId": "dataset1",
                    "sizeBytes": 10737418240,  # 10GB
                    "recordCount": 1000000
                },
                {
                    "datasetId": "dataset2",
                    "sizeBytes": 21474836480,  # 20GB
                    "recordCount": 2000000
                }
            ],
            "count": 2
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_storage_gb"] == 30.0
        assert result.metadata["datasets_with_stats"] == 2

    @pytest.mark.asyncio
    async def test_analyze_recommends_parquet_conversion(self, analyzer, mock_client):
        """Test analyzer recommends Parquet conversion for large JSON datasets."""
        mock_client.get_lake_datasets.return_value = {
            "items": [
                {
                    "id": "big_json_dataset",
                    "bucketName": "lake-test",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "big_json_dataset-view"
                }
            ],
            "count": 1
        }
        mock_client.get_lake_dataset_stats.return_value = {
            "items": [
                {
                    "datasetId": "big_json_dataset",
                    "sizeBytes": 107374182400,  # 100GB
                    "recordCount": 10000000,
                    "lastUpdated": int(datetime.utcnow().timestamp() * 1000)
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have optimization recommendation
        assert len(result.recommendations) > 0
        parquet_recs = [r for r in result.recommendations if "parquet" in r.title.lower()]
        assert len(parquet_recs) > 0
        # Check recommendation has proper impact estimate
        rec = parquet_recs[0]
        assert rec.impact_estimate.storage_reduction_gb is not None
        assert rec.impact_estimate.storage_reduction_gb > 0
