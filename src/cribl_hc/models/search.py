"""
Cribl Search data models.

This module defines Pydantic models for Cribl Search resources including
search jobs, datasets, dashboards, and saved searches.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CPUMetrics(BaseModel):
    """
    Represents CPU metrics for a search job.

    Tracks total, billable, and executor CPU usage for cost analysis.
    """

    total_cpu_seconds: Optional[float] = Field(
        default=None,
        alias="totalCPUSeconds",
        description="Total CPU seconds consumed"
    )
    billable_cpu_seconds: Optional[float] = Field(
        default=None,
        alias="billableCPUSeconds",
        description="Billable CPU seconds (for cost calculation)"
    )
    executors_cpu_seconds: Optional[float] = Field(
        default=None,
        alias="executorsCPUSeconds",
        description="CPU seconds consumed by executors"
    )

    class Config:
        populate_by_name = True


class SearchJobMetadata(BaseModel):
    """
    Represents metadata for a search job.

    Contains information about datasets, providers, and operators used.
    """

    datasets: Optional[List[str]] = Field(
        default=None,
        description="Datasets queried by this job"
    )
    providers: Optional[List[str]] = Field(
        default=None,
        description="Data providers used"
    )
    operators: Optional[List[str]] = Field(
        default=None,
        description="Query operators used"
    )

    class Config:
        populate_by_name = True


class SearchJob(BaseModel):
    """
    Represents a Cribl Search job.

    Search jobs track query execution including status, performance metrics,
    and resource consumption.
    """

    id: str = Field(..., description="Job ID (e.g., '1766939703881.P0akH8')")
    query: Optional[str] = Field(None, description="KQL query string")
    earliest: Optional[str] = Field(None, description="Search time range start")
    latest: Optional[str] = Field(None, description="Search time range end")
    status: Optional[str] = Field(
        None,
        description="Job status ('running', 'completed', 'failed', 'cancelled')"
    )
    user: Optional[str] = Field(None, description="User ID who created the job")
    display_username: Optional[str] = Field(
        None,
        alias="displayUsername",
        description="Display name of user"
    )
    stages: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Query execution stages"
    )
    cpu_metrics: Optional[CPUMetrics] = Field(
        default=None,
        alias="cpuMetrics",
        description="CPU usage metrics"
    )
    metadata: Optional[SearchJobMetadata] = Field(
        default=None,
        description="Job metadata (datasets, providers, operators)"
    )
    time_created: Optional[int] = Field(
        default=None,
        alias="timeCreated",
        description="Job creation timestamp (epoch ms)"
    )
    time_started: Optional[int] = Field(
        default=None,
        alias="timeStarted",
        description="Job start timestamp (epoch ms)"
    )
    time_completed: Optional[int] = Field(
        default=None,
        alias="timeCompleted",
        description="Job completion timestamp (epoch ms)"
    )
    error: Optional[str] = Field(None, description="Error message if job failed")
    result_count: Optional[int] = Field(
        default=None,
        alias="resultCount",
        description="Number of results returned"
    )

    class Config:
        populate_by_name = True


class SearchDataset(BaseModel):
    """
    Represents a Cribl Search dataset.

    Search datasets define data sources that can be queried, including
    Lake datasets, S3 buckets, and external providers.
    """

    id: str = Field(..., description="Dataset ID (e.g., 'cribl_edge_appscope_events')")
    provider: Optional[str] = Field(
        None,
        description="Provider name (e.g., 'cribl_edge', 's3', 'cribl_lake')"
    )
    type: Optional[str] = Field(
        None,
        description="Dataset type (e.g., 'cribl_edge', 's3')"
    )
    description: Optional[str] = Field(None, description="Human-readable description")
    fleets: Optional[List[str]] = Field(
        default=None,
        description="Associated fleets (e.g., ['*'] for all)"
    )
    path: Optional[str] = Field(None, description="Data path pattern")
    filter: Optional[str] = Field(None, description="Filter expression")
    enabled: Optional[bool] = Field(default=True, description="Whether dataset is enabled")
    schema_fields: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        alias="schemaFields",
        description="Dataset schema definition"
    )

    class Config:
        populate_by_name = True


class DashboardElement(BaseModel):
    """
    Represents an element/widget on a Search dashboard.
    """

    id: Optional[str] = Field(None, description="Element ID")
    type: Optional[str] = Field(None, description="Element type (chart, table, etc.)")
    query: Optional[str] = Field(None, description="Query for this element")
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Element configuration"
    )

    class Config:
        populate_by_name = True


class DashboardSchedule(BaseModel):
    """
    Represents a schedule for dashboard refresh.
    """

    enabled: Optional[bool] = Field(default=False, description="Whether schedule is enabled")
    cron: Optional[str] = Field(None, description="Cron expression for schedule")
    timezone: Optional[str] = Field(None, description="Timezone for schedule")

    class Config:
        populate_by_name = True


class Dashboard(BaseModel):
    """
    Represents a Cribl Search dashboard.

    Dashboards provide visualizations for search results with
    configurable elements, schedules, and access groups.
    """

    id: str = Field(..., description="Dashboard ID")
    name: Optional[str] = Field(None, description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    category: Optional[str] = Field(None, description="Dashboard category")
    elements: Optional[List[DashboardElement]] = Field(
        default=None,
        description="Dashboard elements/widgets"
    )
    schedule: Optional[DashboardSchedule] = Field(
        default=None,
        description="Refresh schedule configuration"
    )
    groups: Optional[List[str]] = Field(
        default=None,
        description="Access groups for this dashboard"
    )
    created_by: Optional[str] = Field(
        default=None,
        alias="createdBy",
        description="User who created the dashboard"
    )
    modified_by: Optional[str] = Field(
        default=None,
        alias="modifiedBy",
        description="User who last modified the dashboard"
    )
    created: Optional[int] = Field(
        default=None,
        description="Creation timestamp (epoch ms)"
    )
    modified: Optional[int] = Field(
        default=None,
        description="Last modification timestamp (epoch ms)"
    )

    class Config:
        populate_by_name = True


class SavedSearch(BaseModel):
    """
    Represents a Cribl Search saved search.

    Saved searches store reusable query definitions with
    default time ranges for quick execution.
    """

    id: str = Field(..., description="Saved search ID")
    name: Optional[str] = Field(None, description="Saved search name")
    description: Optional[str] = Field(None, description="Description")
    query: Optional[str] = Field(None, description="KQL query string")
    earliest: Optional[str] = Field(None, description="Default time range start")
    latest: Optional[str] = Field(None, description="Default time range end")
    lib: Optional[str] = Field(None, description="Library/folder path")
    groups: Optional[List[str]] = Field(
        default=None,
        description="Access groups"
    )
    created_by: Optional[str] = Field(
        default=None,
        alias="createdBy",
        description="User who created the saved search"
    )
    modified_by: Optional[str] = Field(
        default=None,
        alias="modifiedBy",
        description="User who last modified"
    )
    created: Optional[int] = Field(
        default=None,
        description="Creation timestamp (epoch ms)"
    )
    modified: Optional[int] = Field(
        default=None,
        description="Last modification timestamp (epoch ms)"
    )

    class Config:
        populate_by_name = True


class SearchJobList(BaseModel):
    """Response model for listing Search jobs."""

    items: List[SearchJob] = Field(default_factory=list, description="List of search jobs")
    count: int = Field(..., description="Total number of jobs")


class SearchDatasetList(BaseModel):
    """Response model for listing Search datasets."""

    items: List[SearchDataset] = Field(default_factory=list, description="List of datasets")
    count: int = Field(..., description="Total number of datasets")


class DashboardList(BaseModel):
    """Response model for listing dashboards."""

    items: List[Dashboard] = Field(default_factory=list, description="List of dashboards")
    count: int = Field(..., description="Total number of dashboards")


class SavedSearchList(BaseModel):
    """Response model for listing saved searches."""

    items: List[SavedSearch] = Field(default_factory=list, description="List of saved searches")
    count: int = Field(..., description="Total number of saved searches")
