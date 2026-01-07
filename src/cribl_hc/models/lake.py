"""
Cribl Lake data models.

This module defines Pydantic models for Cribl Lake resources including
datasets, lakehouses, and dataset statistics.
"""

from typing import Any

from pydantic import BaseModel, Field


class LakeDataset(BaseModel):
    """
    Represents a Cribl Lake dataset.

    Lake datasets store data in S3 buckets with configurable retention
    periods and formats (JSON or Parquet).
    """

    id: str = Field(..., description="Dataset ID (e.g., 'default_logs', 'cribl_metrics')")
    bucket_name: str = Field(..., alias="bucketName", description="S3 bucket name")
    description: str | None = Field(None, description="Human-readable description")
    retention_period_in_days: int = Field(
        ..., alias="retentionPeriodInDays", description="Retention period in days (e.g., 5-30)"
    )
    format: str = Field(..., description="Data format ('json' or 'parquet')")
    view_name: str = Field(..., alias="viewName", description="View name for querying")
    metrics: dict[str, Any] | None = Field(
        default=None, description="Dataset metrics (when includeMetrics=true)"
    )
    storage_location: str | None = Field(
        default=None,
        alias="storageLocation",
        description="Storage location ID where dataset is stored",
    )

    model_config = {"populate_by_name": True}


class Lakehouse(BaseModel):
    """
    Represents a Cribl Lakehouse.

    Lakehouses provide optimized search performance for datasets by
    maintaining an indexed view of the data.
    """

    id: str = Field(..., description="Lakehouse ID")
    name: str | None = Field(None, description="Lakehouse name")
    description: str | None = Field(None, description="Description")
    dataset_ids: list[str] | None = Field(
        default=None, alias="datasetIds", description="Associated dataset IDs"
    )
    status: str | None = Field(None, description="Lakehouse status")
    config: dict[str, Any] | None = Field(None, description="Lakehouse configuration")

    model_config = {"populate_by_name": True}


class DatasetStats(BaseModel):
    """
    Represents statistics for a Lake dataset.

    Dataset statistics include size, record count, and activity metrics.
    """

    dataset_id: str = Field(..., alias="datasetId", description="Dataset ID")
    size_bytes: int | None = Field(
        default=None, alias="sizeBytes", description="Dataset size in bytes"
    )
    record_count: int | None = Field(
        default=None, alias="recordCount", description="Number of records"
    )
    last_updated: int | None = Field(
        default=None, alias="lastUpdated", description="Last update timestamp (epoch ms)"
    )
    oldest_record: int | None = Field(
        default=None, alias="oldestRecord", description="Oldest record timestamp (epoch ms)"
    )
    newest_record: int | None = Field(
        default=None, alias="newestRecord", description="Newest record timestamp (epoch ms)"
    )

    model_config = {"populate_by_name": True}


class LakeDatasetList(BaseModel):
    """Response model for listing Lake datasets."""

    items: list[LakeDataset] = Field(default_factory=list, description="List of datasets")
    count: int = Field(..., description="Total number of datasets")


class LakehouseList(BaseModel):
    """Response model for listing Lakehouses."""

    items: list[Lakehouse] = Field(default_factory=list, description="List of lakehouses")
    count: int = Field(..., description="Total number of lakehouses")


class DatasetStatsList(BaseModel):
    """Response model for dataset statistics."""

    items: list[DatasetStats] = Field(default_factory=list, description="List of dataset stats")
    count: int = Field(..., description="Total number of stats entries")
