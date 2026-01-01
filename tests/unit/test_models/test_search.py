"""
Unit tests for Cribl Search data models.

Tests use realistic data based on sandbox API discovery to validate model parsing.
"""

import pytest

from cribl_hc.models.search import (
    CPUMetrics,
    Dashboard,
    DashboardElement,
    DashboardList,
    DashboardSchedule,
    SavedSearch,
    SavedSearchList,
    SearchDataset,
    SearchDatasetList,
    SearchJob,
    SearchJobList,
    SearchJobMetadata,
)


class TestCPUMetrics:
    """Tests for CPUMetrics model."""

    def test_parse_minimal_metrics(self):
        """Test parsing CPU metrics with minimal fields."""
        data = {}

        metrics = CPUMetrics(**data)

        assert metrics.total_cpu_seconds is None
        assert metrics.billable_cpu_seconds is None
        assert metrics.executors_cpu_seconds is None

    def test_parse_full_metrics(self):
        """Test parsing complete CPU metrics."""
        data = {
            "totalCPUSeconds": 12.5,
            "billableCPUSeconds": 10.0,
            "executorsCPUSeconds": 8.5
        }

        metrics = CPUMetrics(**data)

        assert metrics.total_cpu_seconds == 12.5
        assert metrics.billable_cpu_seconds == 10.0
        assert metrics.executors_cpu_seconds == 8.5


class TestSearchJobMetadata:
    """Tests for SearchJobMetadata model."""

    def test_parse_metadata(self):
        """Test parsing search job metadata."""
        data = {
            "datasets": ["cribl_logs", "default_logs"],
            "providers": ["cribl_lake"],
            "operators": ["cribl", "where", "project"]
        }

        metadata = SearchJobMetadata(**data)

        assert metadata.datasets == ["cribl_logs", "default_logs"]
        assert metadata.providers == ["cribl_lake"]
        assert metadata.operators == ["cribl", "where", "project"]


class TestSearchJob:
    """Tests for SearchJob model."""

    def test_parse_minimal_job(self):
        """Test parsing search job with minimal fields."""
        data = {
            "id": "1766939703881.P0akH8"
        }

        job = SearchJob(**data)

        assert job.id == "1766939703881.P0akH8"
        assert job.query is None
        assert job.status is None

    def test_parse_running_job(self):
        """Test parsing a running search job."""
        data = {
            "id": "1766939703881.P0akH8",
            "query": "cribl dataset='cribl_logs' | where level == 'error'",
            "earliest": "-24h",
            "latest": "now",
            "status": "running",
            "user": "admin@cribl.io",
            "displayUsername": "Admin User",
            "timeCreated": 1766939703881,
            "timeStarted": 1766939703900
        }

        job = SearchJob(**data)

        assert job.id == "1766939703881.P0akH8"
        assert job.query == "cribl dataset='cribl_logs' | where level == 'error'"
        assert job.status == "running"
        assert job.earliest == "-24h"
        assert job.latest == "now"
        assert job.display_username == "Admin User"
        assert job.time_created == 1766939703881
        assert job.time_started == 1766939703900

    def test_parse_completed_job_with_metrics(self):
        """Test parsing completed job with CPU metrics."""
        data = {
            "id": "1766939703881.P0akH8",
            "query": "cribl dataset='cribl_logs' | count",
            "status": "completed",
            "cpuMetrics": {
                "totalCPUSeconds": 5.2,
                "billableCPUSeconds": 4.0,
                "executorsCPUSeconds": 3.5
            },
            "metadata": {
                "datasets": ["cribl_logs"],
                "providers": ["cribl_lake"],
                "operators": ["cribl", "count"]
            },
            "timeCreated": 1766939703881,
            "timeStarted": 1766939703900,
            "timeCompleted": 1766939710000,
            "resultCount": 1000
        }

        job = SearchJob(**data)

        assert job.status == "completed"
        assert job.cpu_metrics is not None
        assert job.cpu_metrics.total_cpu_seconds == 5.2
        assert job.cpu_metrics.billable_cpu_seconds == 4.0
        assert job.metadata is not None
        assert job.metadata.datasets == ["cribl_logs"]
        assert job.result_count == 1000
        assert job.time_completed == 1766939710000

    def test_parse_failed_job(self):
        """Test parsing a failed search job."""
        data = {
            "id": "1766939703881.P0akH8",
            "query": "invalid query syntax",
            "status": "failed",
            "error": "Query parse error: unexpected token 'syntax'"
        }

        job = SearchJob(**data)

        assert job.status == "failed"
        assert job.error == "Query parse error: unexpected token 'syntax'"


class TestSearchJobList:
    """Tests for SearchJobList model."""

    def test_parse_empty_job_list(self):
        """Test parsing empty job list from sandbox."""
        data = {
            "items": [],
            "count": 0
        }

        job_list = SearchJobList(**data)

        assert job_list.count == 0
        assert len(job_list.items) == 0

    def test_parse_job_list_with_items(self):
        """Test parsing job list with multiple jobs."""
        data = {
            "items": [
                {"id": "job1", "status": "completed"},
                {"id": "job2", "status": "running"},
                {"id": "job3", "status": "failed"}
            ],
            "count": 3
        }

        job_list = SearchJobList(**data)

        assert job_list.count == 3
        assert len(job_list.items) == 3
        assert job_list.items[0].id == "job1"
        assert job_list.items[1].status == "running"
        assert job_list.items[2].status == "failed"


class TestSearchDataset:
    """Tests for SearchDataset model."""

    def test_parse_minimal_dataset(self):
        """Test parsing dataset with minimal fields."""
        data = {
            "id": "cribl_logs"
        }

        dataset = SearchDataset(**data)

        assert dataset.id == "cribl_logs"
        assert dataset.provider is None
        assert dataset.enabled is True

    def test_parse_lake_dataset(self):
        """Test parsing Lake-backed search dataset."""
        data = {
            "id": "cribl_logs",
            "provider": "cribl_lake",
            "type": "cribl_lake",
            "description": "Cribl internal logs",
            "enabled": True
        }

        dataset = SearchDataset(**data)

        assert dataset.id == "cribl_logs"
        assert dataset.provider == "cribl_lake"
        assert dataset.type == "cribl_lake"
        assert dataset.description == "Cribl internal logs"

    def test_parse_edge_dataset(self):
        """Test parsing Edge fleet dataset."""
        data = {
            "id": "cribl_edge_appscope_events",
            "provider": "cribl_edge",
            "type": "cribl_edge",
            "description": "AppScope events from Edge fleet",
            "fleets": ["*"],
            "path": "/var/log/appscope/**",
            "filter": "sourcetype=appscope"
        }

        dataset = SearchDataset(**data)

        assert dataset.id == "cribl_edge_appscope_events"
        assert dataset.provider == "cribl_edge"
        assert dataset.fleets == ["*"]
        assert dataset.path == "/var/log/appscope/**"
        assert dataset.filter == "sourcetype=appscope"

    def test_parse_s3_dataset(self):
        """Test parsing S3-backed dataset."""
        data = {
            "id": "s3_archive_logs",
            "provider": "s3",
            "type": "s3",
            "description": "Archived logs in S3",
            "path": "s3://my-bucket/logs/**",
            "schemaFields": [
                {"name": "timestamp", "type": "datetime"},
                {"name": "message", "type": "string"}
            ]
        }

        dataset = SearchDataset(**data)

        assert dataset.id == "s3_archive_logs"
        assert dataset.provider == "s3"
        assert dataset.schema_fields is not None
        assert len(dataset.schema_fields) == 2


class TestSearchDatasetList:
    """Tests for SearchDatasetList model."""

    def test_parse_empty_dataset_list(self):
        """Test parsing empty dataset list from sandbox."""
        data = {
            "items": [],
            "count": 0
        }

        dataset_list = SearchDatasetList(**data)

        assert dataset_list.count == 0
        assert len(dataset_list.items) == 0

    def test_parse_dataset_list_with_items(self):
        """Test parsing dataset list with multiple datasets."""
        data = {
            "items": [
                {"id": "cribl_logs", "provider": "cribl_lake"},
                {"id": "edge_events", "provider": "cribl_edge"}
            ],
            "count": 2
        }

        dataset_list = SearchDatasetList(**data)

        assert dataset_list.count == 2
        assert len(dataset_list.items) == 2
        assert dataset_list.items[0].id == "cribl_logs"
        assert dataset_list.items[1].provider == "cribl_edge"


class TestDashboardElement:
    """Tests for DashboardElement model."""

    def test_parse_chart_element(self):
        """Test parsing chart dashboard element."""
        data = {
            "id": "elem-001",
            "type": "chart",
            "query": "cribl dataset='cribl_logs' | count by level",
            "config": {
                "chartType": "bar",
                "title": "Log Levels"
            }
        }

        element = DashboardElement(**data)

        assert element.id == "elem-001"
        assert element.type == "chart"
        assert element.query is not None
        assert element.config["chartType"] == "bar"


class TestDashboard:
    """Tests for Dashboard model."""

    def test_parse_minimal_dashboard(self):
        """Test parsing dashboard with minimal fields."""
        data = {
            "id": "dashboard-001"
        }

        dashboard = Dashboard(**data)

        assert dashboard.id == "dashboard-001"
        assert dashboard.name is None
        assert dashboard.elements is None

    def test_parse_full_dashboard(self):
        """Test parsing complete dashboard."""
        data = {
            "id": "dashboard-001",
            "name": "Operations Overview",
            "description": "Real-time operational metrics",
            "category": "operations",
            "elements": [
                {
                    "id": "elem-001",
                    "type": "chart",
                    "query": "cribl dataset='cribl_logs' | count"
                }
            ],
            "schedule": {
                "enabled": True,
                "cron": "0 * * * *",
                "timezone": "America/New_York"
            },
            "groups": ["admin", "operators"],
            "createdBy": "admin@cribl.io",
            "modifiedBy": "admin@cribl.io",
            "created": 1766939703881,
            "modified": 1766940000000
        }

        dashboard = Dashboard(**data)

        assert dashboard.id == "dashboard-001"
        assert dashboard.name == "Operations Overview"
        assert dashboard.category == "operations"
        assert len(dashboard.elements) == 1
        assert dashboard.elements[0].type == "chart"
        assert dashboard.schedule is not None
        assert dashboard.schedule.enabled is True
        assert dashboard.schedule.cron == "0 * * * *"
        assert dashboard.groups == ["admin", "operators"]
        assert dashboard.created_by == "admin@cribl.io"


class TestDashboardList:
    """Tests for DashboardList model."""

    def test_parse_empty_dashboard_list(self):
        """Test parsing empty dashboard list from sandbox."""
        data = {
            "items": [],
            "count": 0
        }

        dashboard_list = DashboardList(**data)

        assert dashboard_list.count == 0
        assert len(dashboard_list.items) == 0

    def test_parse_dashboard_list_with_items(self):
        """Test parsing dashboard list with multiple dashboards."""
        data = {
            "items": [
                {"id": "dash1", "name": "Dashboard 1"},
                {"id": "dash2", "name": "Dashboard 2"}
            ],
            "count": 2
        }

        dashboard_list = DashboardList(**data)

        assert dashboard_list.count == 2
        assert len(dashboard_list.items) == 2


class TestSavedSearch:
    """Tests for SavedSearch model."""

    def test_parse_minimal_saved_search(self):
        """Test parsing saved search with minimal fields."""
        data = {
            "id": "saved-001"
        }

        saved = SavedSearch(**data)

        assert saved.id == "saved-001"
        assert saved.name is None
        assert saved.query is None

    def test_parse_full_saved_search(self):
        """Test parsing complete saved search."""
        data = {
            "id": "saved-001",
            "name": "Error Log Query",
            "description": "Find all error-level log entries",
            "query": "cribl dataset='cribl_logs' | where level == 'error'",
            "earliest": "-7d",
            "latest": "now",
            "lib": "common_queries",
            "groups": ["admin", "support"],
            "createdBy": "admin@cribl.io",
            "modifiedBy": "admin@cribl.io",
            "created": 1766939703881,
            "modified": 1766940000000
        }

        saved = SavedSearch(**data)

        assert saved.id == "saved-001"
        assert saved.name == "Error Log Query"
        assert saved.description == "Find all error-level log entries"
        assert saved.query == "cribl dataset='cribl_logs' | where level == 'error'"
        assert saved.earliest == "-7d"
        assert saved.latest == "now"
        assert saved.lib == "common_queries"
        assert saved.groups == ["admin", "support"]
        assert saved.created_by == "admin@cribl.io"


class TestSavedSearchList:
    """Tests for SavedSearchList model."""

    def test_parse_empty_saved_search_list(self):
        """Test parsing empty saved search list from sandbox."""
        data = {
            "items": [],
            "count": 0
        }

        saved_list = SavedSearchList(**data)

        assert saved_list.count == 0
        assert len(saved_list.items) == 0

    def test_parse_saved_search_list_with_items(self):
        """Test parsing saved search list with multiple items."""
        data = {
            "items": [
                {"id": "saved1", "name": "Error Query"},
                {"id": "saved2", "name": "Warning Query"}
            ],
            "count": 2
        }

        saved_list = SavedSearchList(**data)

        assert saved_list.count == 2
        assert len(saved_list.items) == 2
        assert saved_list.items[0].name == "Error Query"
