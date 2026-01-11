"""
Cribl Search data models.

This module defines Pydantic models for Cribl Search resources including
search jobs, datasets, dashboards, and saved searches.
"""

from typing import Any

from pydantic import BaseModel, Field


class CPUMetrics(BaseModel):
    """
    Represents CPU metrics for a search job.

    Tracks total, billable, and executor CPU usage for cost analysis.
    """

    total_cpu_seconds: float | None = Field(
        default=None, alias="totalCPUSeconds", description="Total CPU seconds consumed"
    )
    billable_cpu_seconds: float | None = Field(
        default=None,
        alias="billableCPUSeconds",
        description="Billable CPU seconds (for cost calculation)",
    )
    executors_cpu_seconds: float | None = Field(
        default=None, alias="executorsCPUSeconds", description="CPU seconds consumed by executors"
    )

    model_config = {"populate_by_name": True}


class SearchJobMetadata(BaseModel):
    """
    Represents metadata for a search job.

    Contains information about datasets, providers, and operators used.
    """

    datasets: list[str] | None = Field(default=None, description="Datasets queried by this job")
    providers: list[str] | None = Field(default=None, description="Data providers used")
    operators: list[str] | None = Field(default=None, description="Query operators used")

    model_config = {"populate_by_name": True}


class SearchJob(BaseModel):
    """
    Represents a Cribl Search job.

    Search jobs track query execution including status, performance metrics,
    and resource consumption.
    """

    id: str = Field(..., description="Job ID (e.g., '1766939703881.P0akH8')")
    query: str | None = Field(None, description="KQL query string")
    earliest: str | None = Field(None, description="Search time range start")
    latest: str | None = Field(None, description="Search time range end")
    status: str | None = Field(
        None, description="Job status ('running', 'completed', 'failed', 'cancelled')"
    )
    user: str | None = Field(None, description="User ID who created the job")
    display_username: str | None = Field(
        None, alias="displayUsername", description="Display name of user"
    )
    stages: list[dict[str, Any]] | None = Field(default=None, description="Query execution stages")
    cpu_metrics: CPUMetrics | None = Field(
        default=None, alias="cpuMetrics", description="CPU usage metrics"
    )
    metadata: SearchJobMetadata | None = Field(
        default=None, description="Job metadata (datasets, providers, operators)"
    )
    time_created: int | None = Field(
        default=None, alias="timeCreated", description="Job creation timestamp (epoch ms)"
    )
    time_started: int | None = Field(
        default=None, alias="timeStarted", description="Job start timestamp (epoch ms)"
    )
    time_completed: int | None = Field(
        default=None, alias="timeCompleted", description="Job completion timestamp (epoch ms)"
    )
    error: str | None = Field(None, description="Error message if job failed")
    result_count: int | None = Field(
        default=None, alias="resultCount", description="Number of results returned"
    )

    model_config = {"populate_by_name": True}


class SearchDataset(BaseModel):
    """
    Represents a Cribl Search dataset.

    Search datasets define data sources that can be queried, including
    Lake datasets, S3 buckets, and external providers.
    """

    id: str = Field(..., description="Dataset ID (e.g., 'cribl_edge_appscope_events')")
    provider: str | None = Field(
        None, description="Provider name (e.g., 'cribl_edge', 's3', 'cribl_lake')"
    )
    type: str | None = Field(None, description="Dataset type (e.g., 'cribl_edge', 's3')")
    description: str | None = Field(None, description="Human-readable description")
    fleets: list[str] | None = Field(
        default=None, description="Associated fleets (e.g., ['*'] for all)"
    )
    path: str | None = Field(None, description="Data path pattern")
    filter: str | None = Field(None, description="Filter expression")
    enabled: bool | None = Field(default=True, description="Whether dataset is enabled")
    schema_fields: list[dict[str, Any]] | None = Field(
        default=None, alias="schemaFields", description="Dataset schema definition"
    )

    model_config = {"populate_by_name": True}


class DashboardElement(BaseModel):
    """
    Represents an element/widget on a Search dashboard.
    """

    id: str | None = Field(None, description="Element ID")
    type: str | None = Field(None, description="Element type (chart, table, etc.)")
    query: str | None = Field(None, description="Query for this element")
    config: dict[str, Any] | None = Field(default=None, description="Element configuration")

    model_config = {"populate_by_name": True}


class DashboardSchedule(BaseModel):
    """
    Represents a schedule for dashboard refresh.
    """

    enabled: bool | None = Field(default=False, description="Whether schedule is enabled")
    cron: str | None = Field(None, description="Cron expression for schedule")
    timezone: str | None = Field(None, description="Timezone for schedule")

    model_config = {"populate_by_name": True}


class Dashboard(BaseModel):
    """
    Represents a Cribl Search dashboard.

    Dashboards provide visualizations for search results with
    configurable elements, schedules, and access groups.
    """

    id: str = Field(..., description="Dashboard ID")
    name: str | None = Field(None, description="Dashboard name")
    description: str | None = Field(None, description="Dashboard description")
    category: str | None = Field(None, description="Dashboard category")
    elements: list[DashboardElement] | None = Field(
        default=None, description="Dashboard elements/widgets"
    )
    schedule: DashboardSchedule | None = Field(
        default=None, description="Refresh schedule configuration"
    )
    groups: list[str] | None = Field(default=None, description="Access groups for this dashboard")
    created_by: str | None = Field(
        default=None, alias="createdBy", description="User who created the dashboard"
    )
    modified_by: str | None = Field(
        default=None, alias="modifiedBy", description="User who last modified the dashboard"
    )
    created: int | None = Field(default=None, description="Creation timestamp (epoch ms)")
    modified: int | None = Field(default=None, description="Last modification timestamp (epoch ms)")

    model_config = {"populate_by_name": True}


class SearchGroup(BaseModel):
    """
    Represents a Cribl Search group.

    Search groups organize datasets and dashboards for access control.
    """

    id: str = Field(..., description="Group ID")
    name: str | None = Field(None, description="Group name")
    description: str | None = Field(None, description="Group description")
    datasets: list[str] | None = Field(default=None, description="Associated dataset IDs")
    dashboards: list[str] | None = Field(default=None, description="Associated dashboard IDs")
    created_by: str | None = Field(
        default=None, alias="createdBy", description="User who created group"
    )

    model_config = {"populate_by_name": True}


class SavedSearch(BaseModel):
    """
    Represents a Cribl Search saved search.

    Saved searches store reusable query definitions with
    default time ranges for quick execution.
    """

    id: str = Field(..., description="Saved search ID")
    name: str | None = Field(None, description="Saved search name")
    description: str | None = Field(None, description="Description")
    query: str | None = Field(None, description="KQL query string")
    earliest: str | None = Field(None, description="Default time range start")
    latest: str | None = Field(None, description="Default time range end")
    lib: str | None = Field(None, description="Library/folder path")
    groups: list[str] | None = Field(default=None, description="Access groups")
    created_by: str | None = Field(
        default=None, alias="createdBy", description="User who created saved search"
    )
    modified_by: str | None = Field(
        default=None, alias="modifiedBy", description="User who last modified"
    )
    created: int | None = Field(default=None, description="Creation timestamp (epoch ms)")
    modified: int | None = Field(default=None, description="Last modification timestamp (epoch ms)")

    model_config = {"populate_by_name": True}


class SearchCost(BaseModel):
    """
    Represents cost data for Search queries.

    Tracks CPU consumption, storage usage, and estimated costs
    for Search operations over a time period.
    """

    total_cost_usd: float | None = Field(
        default=None, alias="totalCost", description="Total cost in USD for analyzed period"
    )
    total_cpu_seconds: float | None = Field(
        default=None, alias="totalCPUSeconds", description="Total CPU seconds consumed"
    )
    total_scanned_gb: float | None = Field(
        default=None, alias="totalScannedGb", description="Total data scanned in GB"
    )
    storage_cost_usd: float | None = Field(
        default=None, alias="storageCost", description="Storage cost in USD"
    )
    time_period_days: int = Field(..., alias="timePeriodDays", description="Time period analyzed")
    breakdown_by_dataset: dict[str, dict[str, float]] | None = Field(
        default=None, alias="breakdownByDataset", description="Cost breakdown by dataset ID"
    )
    breakdown_by_query_type: dict[str, dict[str, float]] | None = Field(
        default=None, alias="breakdownByQueryType", description="Cost breakdown by query type"
    )

    model_config = {"populate_by_name": True}


class SearchHealthCheckStatus(BaseModel):
    status: str = Field(..., description="Health status (green/red)")
    reported_at: int = Field(..., alias="reported_at", description="Reported timestamp (epoch ms)")
    reason: str | None = Field(None, description="Failure reason if status is red")

    model_config = {"populate_by_name": True}


class SearchHealthCheckList(BaseModel):
    items: list[SearchHealthCheckStatus] = Field(
        default_factory=list, description="List of healthcheck statuses"
    )
    count: int = Field(..., description="Total number of statuses")


class TimeSeriesPoint(BaseModel):
    start_time: int = Field(..., alias="startTime", description="Start time (epoch ms)")
    end_time: int = Field(..., alias="endTime", description="End time (epoch ms)")
    value: float = Field(..., description="Metric value")

    model_config = {"populate_by_name": True}


class DatasetStatsResponse(BaseModel):
    byte_counts: list[TimeSeriesPoint] = Field(
        default_factory=list, alias="byteCounts", description="Byte counts over time"
    )
    event_counts: list[TimeSeriesPoint] = Field(
        default_factory=list, alias="eventCounts", description="Event counts over time"
    )
    max_event_time: int | None = Field(
        default=None, alias="maxEventTime", description="Latest event time"
    )
    min_event_time: int | None = Field(
        default=None, alias="minEventTime", description="Earliest event time"
    )
    total_byte_count: float | None = Field(
        default=None, alias="totalByteCount", description="Total bytes"
    )
    total_event_count: float | None = Field(
        default=None, alias="totalEventCount", description="Total events"
    )

    model_config = {"populate_by_name": True}


class DatasetUsageQueryCount(BaseModel):
    count: float = Field(..., description="Query count")
    start_time: int = Field(..., alias="startTime", description="Start time (epoch ms)")

    model_config = {"populate_by_name": True}


class DatasetUsageStatsResponse(BaseModel):
    linked_dashboards: list[dict[str, Any]] | None = Field(
        default=None, alias="linkedDashboards", description="Linked dashboards"
    )
    linked_notebooks: list[dict[str, Any]] | None = Field(
        default=None, alias="linkedNotebooks", description="Linked notebooks"
    )
    query_counts: list[DatasetUsageQueryCount] = Field(
        default_factory=list, alias="queryCounts", description="Query counts over time"
    )
    saved_queries: list[dict[str, Any]] | None = Field(
        default=None, alias="savedQueries", description="Saved queries"
    )
    top_users: list[dict[str, Any]] | None = Field(
        default=None, alias="topUsers", description="Top users"
    )

    model_config = {"populate_by_name": True}


class SearchJobList(BaseModel):
    """Response model for listing Search jobs."""

    items: list[SearchJob] = Field(default_factory=list, description="List of search jobs")
    count: int = Field(..., description="Total number of jobs")


class SearchDatasetList(BaseModel):
    """Response model for listing Search datasets."""

    items: list[SearchDataset] = Field(default_factory=list, description="List of datasets")
    count: int = Field(..., description="Total number of datasets")


class DashboardList(BaseModel):
    """Response model for listing dashboards."""

    items: list[Dashboard] = Field(default_factory=list, description="List of dashboards")
    count: int = Field(..., description="Total number of dashboards")


class SavedSearchList(BaseModel):
    """Response model for listing saved searches."""

    items: list[SavedSearch] = Field(default_factory=list, description="List of saved searches")
    count: int = Field(..., description="Total number of saved searches")


class SearchGroupList(BaseModel):
    """Response model for listing Search groups."""

    items: list[SearchGroup] = Field(default_factory=list, description="List of search groups")
    count: int = Field(..., description="Total number of groups")
