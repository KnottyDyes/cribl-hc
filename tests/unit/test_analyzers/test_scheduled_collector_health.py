"""
Tests for ScheduledCollectorHealthAnalyzer.

Tests scheduled collector job health monitoring, failure detection,
schedule validation, and execution history analysis.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.scheduled_collector_health import ScheduledCollectorHealthAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_collector(
    collector_id: str,
    schedule: str | None = None,
    disabled: bool = False,
) -> dict:
    """Helper to create collector configuration."""
    collector = {
        "id": collector_id,
        "disabled": disabled,
    }
    if schedule:
        collector["schedule"] = schedule
    return collector


def create_job(
    job_id: str,
    collector_id: str,
    status: str = "completed",
    start_time: datetime | None = None,
    duration_sec: float | None = None,
) -> dict:
    """Helper to create job execution record."""
    if start_time is None:
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)

    job = {
        "id": job_id,
        "collectorId": collector_id,
        "status": status,
        "startTime": start_time.timestamp(),
    }
    if duration_sec is not None:
        job["duration"] = duration_sec
    return job


class TestScheduledCollectorHealthAnalyzer:
    """Test suite for ScheduledCollectorHealthAnalyzer."""

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_collectors = AsyncMock(return_value=[])
        client.get_jobs = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def analyzer(self):
        return ScheduledCollectorHealthAnalyzer()

    @pytest.mark.asyncio
    async def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "scheduled_collector_health"

    @pytest.mark.asyncio
    async def test_supported_products(self, analyzer):
        """Test supported products."""
        assert "stream" in analyzer.supported_products
        assert "edge" in analyzer.supported_products

    @pytest.mark.asyncio
    async def test_no_collectors_no_findings(self, mock_client, analyzer):
        """Test that no collectors produces no findings."""
        mock_client.get_collectors.return_value = []
        mock_client.get_jobs.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["scheduled_collectors_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_disabled_collector_skipped(self, mock_client, analyzer):
        """Test that disabled collectors are skipped."""
        mock_client.get_collectors.return_value = [
            create_collector("disabled-collector", schedule="0 * * * *", disabled=True),
        ]
        mock_client.get_jobs.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["scheduled_collectors_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_collector_without_schedule_skipped(self, mock_client, analyzer):
        """Test that collectors without schedule are skipped."""
        mock_client.get_collectors.return_value = [
            create_collector("no-schedule-collector"),
        ]
        mock_client.get_jobs.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["scheduled_collectors_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_invalid_schedule_high(self, mock_client, analyzer):
        """Test that invalid cron schedule is flagged as HIGH."""
        mock_client.get_collectors.return_value = [
            create_collector("bad-schedule", schedule="invalid cron"),
        ]
        mock_client.get_jobs.return_value = []

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert "Invalid Schedule" in finding.title

    @pytest.mark.asyncio
    async def test_collector_never_ran_critical(self, mock_client, analyzer):
        """Test that collector with no execution history is flagged as CRITICAL."""
        mock_client.get_collectors.return_value = [
            create_collector("never-ran", schedule="0 * * * *"),
        ]
        mock_client.get_jobs.return_value = []

        result = await analyzer.analyze(mock_client)

        never_ran_findings = [f for f in result.findings if "Never Executed" in f.title]
        assert len(never_ran_findings) == 1
        assert never_ran_findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_all_jobs_failed_critical(self, mock_client, analyzer):
        """Test that 100% failure rate is flagged as CRITICAL."""
        mock_client.get_collectors.return_value = [
            create_collector("all-failed", schedule="0 * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job("job1", "all-failed", status="failed", start_time=now - timedelta(hours=1)),
            create_job("job2", "all-failed", status="failed", start_time=now - timedelta(hours=2)),
            create_job("job3", "all-failed", status="failed", start_time=now - timedelta(hours=3)),
        ]

        result = await analyzer.analyze(mock_client)

        all_failed_findings = [f for f in result.findings if "All Jobs Failed" in f.title]
        assert len(all_failed_findings) == 1
        assert all_failed_findings[0].severity == "critical"
        assert all_failed_findings[0].metadata["failure_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_high_failure_rate_high(self, mock_client, analyzer):
        """Test that >50% failure rate is flagged as HIGH."""
        mock_client.get_collectors.return_value = [
            create_collector("high-failure", schedule="0 * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job(
                "job1", "high-failure", status="failed", start_time=now - timedelta(hours=1)
            ),
            create_job(
                "job2", "high-failure", status="failed", start_time=now - timedelta(hours=2)
            ),
            create_job(
                "job3", "high-failure", status="failed", start_time=now - timedelta(hours=3)
            ),
            create_job(
                "job4", "high-failure", status="completed", start_time=now - timedelta(hours=4)
            ),
            create_job(
                "job5", "high-failure", status="completed", start_time=now - timedelta(hours=5)
            ),
        ]

        result = await analyzer.analyze(mock_client)

        high_failure_findings = [f for f in result.findings if "High Failure Rate" in f.title]
        assert len(high_failure_findings) == 1
        assert high_failure_findings[0].severity == "high"
        assert high_failure_findings[0].metadata["failure_rate"] == 60.0

    @pytest.mark.asyncio
    async def test_stale_collector_high(self, mock_client, analyzer):
        """Test that collector with no recent jobs is flagged as HIGH."""
        mock_client.get_collectors.return_value = [
            create_collector("stale", schedule="0 * * * *"),
        ]
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        mock_client.get_jobs.return_value = [
            create_job("old-job", "stale", status="completed", start_time=old_time),
        ]

        result = await analyzer.analyze(mock_client)

        stale_findings = [f for f in result.findings if "Stale" in f.title]
        assert len(stale_findings) == 1
        assert stale_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_job_duration_exceeds_schedule_high(self, mock_client, analyzer):
        """Test that job duration exceeding schedule interval is flagged as HIGH."""
        mock_client.get_collectors.return_value = [
            create_collector("long-job", schedule="*/5 * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job(
                "job1",
                "long-job",
                status="completed",
                start_time=now - timedelta(hours=1),
                duration_sec=600,
            ),
        ]

        result = await analyzer.analyze(mock_client)

        duration_findings = [f for f in result.findings if "Duration Exceeds" in f.title]
        assert len(duration_findings) == 1
        assert duration_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_overlapping_schedules_medium(self, mock_client, analyzer):
        """Test that many collectors with same schedule is flagged as MEDIUM."""
        mock_client.get_collectors.return_value = [
            create_collector("collector1", schedule="0 * * * *"),
            create_collector("collector2", schedule="0 * * * *"),
            create_collector("collector3", schedule="0 * * * *"),
            create_collector("collector4", schedule="0 * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job("j1", "collector1", status="completed", start_time=now - timedelta(hours=1)),
            create_job("j2", "collector2", status="completed", start_time=now - timedelta(hours=1)),
            create_job("j3", "collector3", status="completed", start_time=now - timedelta(hours=1)),
            create_job("j4", "collector4", status="completed", start_time=now - timedelta(hours=1)),
        ]

        result = await analyzer.analyze(mock_client)

        overlap_findings = [f for f in result.findings if "Same Schedule" in f.title]
        assert len(overlap_findings) == 1
        assert overlap_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_overly_frequent_schedule_low(self, mock_client, analyzer):
        """Test that very frequent schedule is flagged as LOW."""
        mock_client.get_collectors.return_value = [
            create_collector("frequent", schedule="* * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job(
                "job1", "frequent", status="completed", start_time=now - timedelta(minutes=1)
            ),
        ]

        result = await analyzer.analyze(mock_client)

        frequent_findings = [f for f in result.findings if "Frequent Schedule" in f.title]
        assert len(frequent_findings) == 1
        assert frequent_findings[0].severity == "low"

    @pytest.mark.asyncio
    async def test_healthy_collector_no_findings(self, mock_client, analyzer):
        """Test that healthy collector produces no findings."""
        mock_client.get_collectors.return_value = [
            create_collector("healthy", schedule="0 * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job("job1", "healthy", status="completed", start_time=now - timedelta(hours=1)),
            create_job("job2", "healthy", status="completed", start_time=now - timedelta(hours=2)),
            create_job("job3", "healthy", status="completed", start_time=now - timedelta(hours=3)),
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["scheduled_collectors_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client, analyzer):
        """Test graceful handling of API errors."""
        mock_client.get_collectors.side_effect = Exception("API Error")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "API Error" in result.error
        assert len(result.findings) == 1
        assert result.findings[0].id == "scheduled-collector-analysis-error"

    @pytest.mark.asyncio
    async def test_metadata_includes_counts(self, mock_client, analyzer):
        """Test that metadata includes proper counts."""
        mock_client.get_collectors.return_value = [
            create_collector("c1", schedule="0 * * * *"),
            create_collector("c2", schedule="30 * * * *"),
        ]
        now = datetime.now(timezone.utc)
        mock_client.get_jobs.return_value = [
            create_job("j1", "c1", status="completed", start_time=now - timedelta(hours=1)),
            create_job("j2", "c2", status="failed", start_time=now - timedelta(hours=1)),
        ]

        result = await analyzer.analyze(mock_client)

        assert "scheduled_collectors_analyzed" in result.metadata
        assert "total_jobs_analyzed" in result.metadata
        assert "issues_found" in result.metadata
        assert result.metadata["scheduled_collectors_analyzed"] == 2
        assert result.metadata["total_jobs_analyzed"] == 2


class TestScheduledCollectorHealthAnalyzerHelpers:
    """Test helper methods of ScheduledCollectorHealthAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return ScheduledCollectorHealthAnalyzer()

    def test_is_valid_cron_valid(self, analyzer):
        """Test valid cron expressions."""
        assert analyzer._is_valid_cron("0 * * * *") is True
        assert analyzer._is_valid_cron("*/15 * * * *") is True
        assert analyzer._is_valid_cron("0 0 * * *") is True
        assert analyzer._is_valid_cron("0 0 1 * *") is True
        assert analyzer._is_valid_cron("0 0 * * 0") is True

    def test_is_valid_cron_invalid(self, analyzer):
        """Test invalid cron expressions."""
        assert analyzer._is_valid_cron("") is False
        assert analyzer._is_valid_cron("invalid") is False
        assert analyzer._is_valid_cron("* *") is False
        assert analyzer._is_valid_cron("0 0 0") is False

    def test_is_overly_frequent_schedule(self, analyzer):
        """Test overly frequent schedule detection."""
        assert analyzer._is_overly_frequent_schedule("* * * * *") is True
        assert analyzer._is_overly_frequent_schedule("*/1 * * * *") is True
        assert analyzer._is_overly_frequent_schedule("*/2 * * * *") is True
        assert analyzer._is_overly_frequent_schedule("*/5 * * * *") is False
        assert analyzer._is_overly_frequent_schedule("0 * * * *") is False

    def test_estimate_schedule_interval_seconds(self, analyzer):
        """Test schedule interval estimation."""
        assert analyzer._estimate_schedule_interval_seconds("* * * * *") == 60
        assert analyzer._estimate_schedule_interval_seconds("*/5 * * * *") == 300
        assert analyzer._estimate_schedule_interval_seconds("*/15 * * * *") == 900
        assert analyzer._estimate_schedule_interval_seconds("0 * * * *") == 3600
        assert analyzer._estimate_schedule_interval_seconds("0 */2 * * *") == 7200

    def test_is_job_successful(self, analyzer):
        """Test job success detection."""
        assert analyzer._is_job_successful({"status": "completed"}) is True
        assert analyzer._is_job_successful({"status": "success"}) is True
        assert analyzer._is_job_successful({"status": "succeeded"}) is True
        assert analyzer._is_job_successful({"status": "failed"}) is False
        assert analyzer._is_job_successful({"status": "error"}) is False
        assert analyzer._is_job_successful({"status": "timeout"}) is False
        assert analyzer._is_job_successful({"exitCode": 0}) is True
        assert analyzer._is_job_successful({"exitCode": 1}) is False

    def test_get_job_duration_seconds(self, analyzer):
        """Test job duration extraction."""
        assert analyzer._get_job_duration_seconds({"duration": 60}) == 60
        assert analyzer._get_job_duration_seconds({"duration": 3600}) == 3600
        assert analyzer._get_job_duration_seconds({"durationMs": 60000}) == 60
        assert analyzer._get_job_duration_seconds({}) is None

    def test_normalize_schedule(self, analyzer):
        """Test schedule normalization."""
        assert analyzer._normalize_schedule("0 * * * *") == "0 * * * *"
        assert analyzer._normalize_schedule("  0  *  *  *  *  ") == "0 * * * *"
        assert analyzer._normalize_schedule("0 * * * *") == "0 * * * *"

    def test_filter_scheduled_collectors(self, analyzer):
        """Test filtering scheduled collectors."""
        collectors = [
            {"id": "c1", "schedule": "0 * * * *"},
            {"id": "c2"},
            {"id": "c3", "schedule": "30 * * * *", "disabled": True},
            {"id": "c4", "cron": "*/15 * * * *"},
        ]
        result = analyzer._filter_scheduled_collectors(collectors)
        assert len(result) == 2
        assert result[0]["id"] == "c1"
        assert result[1]["id"] == "c4"

    def test_filter_jobs_for_collector(self, analyzer):
        """Test filtering jobs for a collector."""
        jobs = [
            {"id": "j1", "collectorId": "c1"},
            {"id": "j2", "collectorId": "c2"},
            {"id": "j3", "collector": "c1"},
        ]
        result = analyzer._filter_jobs_for_collector(jobs, "c1")
        assert len(result) == 2

    def test_get_recent_jobs(self, analyzer):
        """Test filtering recent jobs."""
        now = datetime.now(timezone.utc)
        jobs = [
            {"id": "j1", "startTime": (now - timedelta(hours=1)).timestamp()},
            {"id": "j2", "startTime": (now - timedelta(days=5)).timestamp()},
            {"id": "j3", "startTime": (now - timedelta(days=10)).timestamp()},
        ]
        result = analyzer._get_recent_jobs(jobs, days=7)
        assert len(result) == 2
