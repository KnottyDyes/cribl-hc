"""
Unit tests for Cribl Lake data models.

Tests use real data from sandbox API discovery to validate model parsing.
"""

import pytest

from cribl_hc.models.lake import (
    DatasetStats,
    DatasetStatsList,
    LakeDataset,
    LakeDatasetList,
    Lakehouse,
    LakehouseList,
)


class TestLakeDataset:
    """Tests for LakeDataset model."""

    def test_parse_dataset_from_sandbox(self):
        """Test parsing a real dataset from sandbox API."""
        # Real data from sandbox: default_logs dataset
        data = {
            "id": "default_logs",
            "bucketName": "lake-sandboxdev-serene-lovelace-dd6mau4",
            "description": "Default dataset for capturing logs from multiple sources",
            "retentionPeriodInDays": 30,
            "format": "json",
            "viewName": "default_logs-read-view"
        }

        dataset = LakeDataset(**data)

        assert dataset.id == "default_logs"
        assert dataset.bucket_name == "lake-sandboxdev-serene-lovelace-dd6mau4"
        assert dataset.description == "Default dataset for capturing logs from multiple sources"
        assert dataset.retention_period_in_days == 30
        assert dataset.format == "json"
        assert dataset.view_name == "default_logs-read-view"
        assert dataset.metrics is None

    def test_parse_dataset_with_metrics(self):
        """Test parsing dataset with metrics."""
        data = {
            "id": "default_events",
            "bucketName": "lake-sandboxdev-serene-lovelace-dd6mau4",
            "description": "Think events from Kubernetes or a 3rd party API",
            "retentionPeriodInDays": 30,
            "format": "json",
            "viewName": "default_events-read-view",
            "metrics": {}
        }

        dataset = LakeDataset(**data)

        assert dataset.id == "default_events"
        assert dataset.metrics == {}

    def test_parse_cribl_internal_dataset(self):
        """Test parsing Cribl internal dataset (cribl_logs)."""
        data = {
            "id": "cribl_logs",
            "bucketName": "internal-sandboxdev-serene-lovelace-dd6mau4",
            "description": "Internal logs from Cribl deployments",
            "retentionPeriodInDays": 30,
            "format": "json",
            "viewName": "cribl_logs-read-view",
            "metrics": {}
        }

        dataset = LakeDataset(**data)

        assert dataset.id == "cribl_logs"
        assert dataset.bucket_name == "internal-sandboxdev-serene-lovelace-dd6mau4"
        assert "Internal logs" in dataset.description

    def test_parse_short_retention_dataset(self):
        """Test parsing dataset with short retention (storage_test)."""
        data = {
            "retentionPeriodInDays": 5,
            "format": "json",
            "id": "storage_test",
            "bucketName": "lake-sandboxdev-serene-lovelace-dd6mau4",
            "viewName": "storage_test-read-view",
            "metrics": {}
        }

        dataset = LakeDataset(**data)

        assert dataset.id == "storage_test"
        assert dataset.retention_period_in_days == 5
        assert dataset.description is None  # No description in this dataset

    def test_parquet_format_dataset(self):
        """Test parsing dataset with Parquet format."""
        data = {
            "id": "test_parquet",
            "bucketName": "test-bucket",
            "retentionPeriodInDays": 10,
            "format": "parquet",
            "viewName": "test_parquet-view"
        }

        dataset = LakeDataset(**data)

        assert dataset.format == "parquet"


class TestLakeDatasetList:
    """Tests for LakeDatasetList model."""

    def test_parse_dataset_list_from_sandbox(self):
        """Test parsing real dataset list from sandbox."""
        # Real response from GET /api/v1/products/lake/lakes/default/datasets
        data = {
            "items": [
                {
                    "id": "default_events",
                    "bucketName": "lake-sandboxdev-serene-lovelace-dd6mau4",
                    "description": "Think events from Kubernetes or a 3rd party API",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "default_events-read-view"
                },
                {
                    "id": "default_logs",
                    "bucketName": "lake-sandboxdev-serene-lovelace-dd6mau4",
                    "description": "Default dataset for capturing logs",
                    "retentionPeriodInDays": 30,
                    "format": "json",
                    "viewName": "default_logs-read-view"
                }
            ],
            "count": 2
        }

        dataset_list = LakeDatasetList(**data)

        assert dataset_list.count == 2
        assert len(dataset_list.items) == 2
        assert dataset_list.items[0].id == "default_events"
        assert dataset_list.items[1].id == "default_logs"

    def test_parse_empty_dataset_list(self):
        """Test parsing empty dataset list."""
        data = {
            "items": [],
            "count": 0
        }

        dataset_list = LakeDatasetList(**data)

        assert dataset_list.count == 0
        assert len(dataset_list.items) == 0


class TestLakehouse:
    """Tests for Lakehouse model."""

    def test_parse_minimal_lakehouse(self):
        """Test parsing lakehouse with minimal fields."""
        data = {
            "id": "lakehouse-001"
        }

        lakehouse = Lakehouse(**data)

        assert lakehouse.id == "lakehouse-001"
        assert lakehouse.name is None
        assert lakehouse.status is None

    def test_parse_full_lakehouse(self):
        """Test parsing lakehouse with all fields."""
        data = {
            "id": "lakehouse-001",
            "name": "Primary Lakehouse",
            "description": "Main lakehouse for analytics",
            "datasetIds": ["default_logs", "default_metrics"],
            "status": "active",
            "config": {
                "indexingEnabled": True,
                "compressionLevel": "high"
            }
        }

        lakehouse = Lakehouse(**data)

        assert lakehouse.id == "lakehouse-001"
        assert lakehouse.name == "Primary Lakehouse"
        assert lakehouse.description == "Main lakehouse for analytics"
        assert lakehouse.dataset_ids == ["default_logs", "default_metrics"]
        assert lakehouse.status == "active"
        assert lakehouse.config["indexingEnabled"] is True


class TestLakehouseList:
    """Tests for LakehouseList model."""

    def test_parse_empty_lakehouse_list_from_sandbox(self):
        """Test parsing empty lakehouse list from sandbox."""
        # Real response from sandbox
        data = {
            "items": [],
            "count": 0
        }

        lakehouse_list = LakehouseList(**data)

        assert lakehouse_list.count == 0
        assert len(lakehouse_list.items) == 0


class TestDatasetStats:
    """Tests for DatasetStats model."""

    def test_parse_minimal_stats(self):
        """Test parsing minimal dataset stats."""
        data = {
            "datasetId": "default_logs"
        }

        stats = DatasetStats(**data)

        assert stats.dataset_id == "default_logs"
        assert stats.size_bytes is None
        assert stats.record_count is None

    def test_parse_full_stats(self):
        """Test parsing complete dataset stats."""
        data = {
            "datasetId": "default_logs",
            "sizeBytes": 1073741824,  # 1GB
            "recordCount": 1000000,
            "lastUpdated": 1766939703882,
            "oldestRecord": 1766000000000,
            "newestRecord": 1766939703882
        }

        stats = DatasetStats(**data)

        assert stats.dataset_id == "default_logs"
        assert stats.size_bytes == 1073741824
        assert stats.record_count == 1000000
        assert stats.last_updated == 1766939703882
        assert stats.oldest_record == 1766000000000
        assert stats.newest_record == 1766939703882


class TestDatasetStatsList:
    """Tests for DatasetStatsList model."""

    def test_parse_empty_stats_list_from_sandbox(self):
        """Test parsing empty stats list from sandbox."""
        # Real response from sandbox
        data = {
            "items": [],
            "count": 0
        }

        stats_list = DatasetStatsList(**data)

        assert stats_list.count == 0
        assert len(stats_list.items) == 0

    def test_parse_stats_list_with_items(self):
        """Test parsing stats list with multiple datasets."""
        data = {
            "items": [
                {
                    "datasetId": "default_logs",
                    "sizeBytes": 1073741824,
                    "recordCount": 1000000
                },
                {
                    "datasetId": "default_metrics",
                    "sizeBytes": 536870912,
                    "recordCount": 500000
                }
            ],
            "count": 2
        }

        stats_list = DatasetStatsList(**data)

        assert stats_list.count == 2
        assert len(stats_list.items) == 2
        assert stats_list.items[0].dataset_id == "default_logs"
        assert stats_list.items[1].dataset_id == "default_metrics"
