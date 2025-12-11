"""
Unit tests for AnalysisRun model.
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.finding import Finding
from cribl_hc.models.health import ComponentScore, HealthScore
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.models.worker import ResourceUtilization, WorkerNode


class TestAnalysisRun:
    """Test AnalysisRun model validation and behavior."""

    def test_valid_analysis_run_creation(self):
        """Test creating a valid analysis run."""
        run = AnalysisRun(
            deployment_id="prod-cribl",
            status="running",
            objectives_analyzed=["health"],
            api_calls_used=0,
        )

        assert run.deployment_id == "prod-cribl"
        assert run.status == "running"
        assert run.objectives_analyzed == ["health"]
        assert run.api_calls_used == 0
        assert run.id is not None  # UUID generated
        assert isinstance(run.started_at, datetime)
        assert run.completed_at is None
        assert run.duration_seconds is None
        assert run.health_score is None
        assert run.findings == []
        assert run.recommendations == []
        assert run.worker_nodes == []
        assert run.errors == []
        assert run.partial_completion is False

    def test_all_status_values(self):
        """Test all valid status values."""
        statuses = ["running", "completed", "partial", "failed"]

        for status in statuses:
            run = AnalysisRun(
                deployment_id="test",
                status=status,  # type: ignore
                objectives_analyzed=["health"],
                api_calls_used=0,
            )
            assert run.status == status

    def test_invalid_status(self):
        """Test that invalid status is rejected."""
        with pytest.raises(ValidationError):
            AnalysisRun(
                deployment_id="test",
                status="pending",  # type: ignore
                objectives_analyzed=["health"],
                api_calls_used=0,
            )

    def test_api_calls_budget_limit(self):
        """Test API calls budget validation (<= 100)."""
        # Valid: at limit
        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=100,
        )
        assert run.api_calls_used == 100

        # Invalid: over budget
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRun(
                deployment_id="test",
                status="completed",
                objectives_analyzed=["health"],
                api_calls_used=101,
            )

        errors = exc_info.value.errors()
        # Check for either Field constraint error or custom validator error
        assert any(
            "exceeds budget" in str(e.get("msg", ""))
            or "less_than_equal" in str(e.get("type", ""))
            for e in errors
        )

    def test_duration_limit_validation(self):
        """Test duration validation (<= 300 seconds)."""
        # Valid: at limit
        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=50,
            duration_seconds=300.0,
        )
        assert run.duration_seconds == 300.0

        # Invalid: over limit
        with pytest.raises(ValidationError):
            AnalysisRun(
                deployment_id="test",
                status="completed",
                objectives_analyzed=["health"],
                api_calls_used=50,
                duration_seconds=301.0,
            )

    def test_completed_at_after_started_at(self):
        """Test that completed_at must be after started_at."""
        started = datetime(2025, 12, 10, 14, 0, 0)

        # Valid: completed after started
        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=50,
            started_at=started,
            completed_at=started + timedelta(minutes=3),
        )
        assert run.completed_at > run.started_at

        # Invalid: completed before started
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRun(
                deployment_id="test",
                status="completed",
                objectives_analyzed=["health"],
                api_calls_used=50,
                started_at=started,
                completed_at=started - timedelta(minutes=1),
            )

        errors = exc_info.value.errors()
        assert any("after started_at" in str(e.get("msg", "")) for e in errors)

    def test_objectives_analyzed_required(self):
        """Test that at least one objective is required."""
        # Valid: one objective
        run = AnalysisRun(
            deployment_id="test",
            status="running",
            objectives_analyzed=["health"],
            api_calls_used=0,
        )
        assert len(run.objectives_analyzed) == 1

        # Invalid: empty list
        with pytest.raises(ValidationError):
            AnalysisRun(
                deployment_id="test",
                status="running",
                objectives_analyzed=[],
                api_calls_used=0,
            )

    def test_analysis_run_with_health_score(self):
        """Test analysis run with health score."""
        health_score = HealthScore(
            overall_score=78,
            components={
                "workers": ComponentScore(
                    name="Workers", score=85, weight=1.0, details="Good"
                )
            },
        )

        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=15,
            health_score=health_score,
        )

        assert run.health_score is not None
        assert run.health_score.overall_score == 78

    def test_analysis_run_with_findings(self):
        """Test analysis run with findings."""
        findings = [
            Finding(
                id="finding-001",
                category="health",
                severity="high",
                title="Memory issue",
                description="High memory usage",
                confidence_level="high",
                remediation_steps=["Increase memory"],
                estimated_impact="Potential crash",
            )
        ]

        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=20,
            findings=findings,
        )

        assert len(run.findings) == 1
        assert run.findings[0].id == "finding-001"

    def test_analysis_run_with_recommendations(self):
        """Test analysis run with recommendations."""
        recommendations = [
            Recommendation(
                id="rec-001",
                type="optimization",
                priority="p1",
                title="Optimize",
                description="Improve performance",
                rationale="Efficiency",
                implementation_steps=["Step 1"],
                before_state="Slow",
                after_state="Fast",
                impact_estimate=ImpactEstimate(performance_improvement="2x faster"),
                implementation_effort="low",
            )
        ]

        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=25,
            recommendations=recommendations,
        )

        assert len(run.recommendations) == 1
        assert run.recommendations[0].id == "rec-001"

    def test_analysis_run_with_worker_nodes(self):
        """Test analysis run with worker nodes."""
        workers = [
            WorkerNode(
                id="worker-001",
                name="Worker 1",
                group_id="default",
                host="10.0.0.1",
                version="4.5.2",
                health_status="healthy",
                resource_utilization=ResourceUtilization(
                    cpu_percent=50,
                    memory_used_gb=8,
                    memory_total_gb=16,
                    memory_percent=50,
                    disk_used_gb=50,
                    disk_total_gb=100,
                    disk_percent=50,
                ),
                connectivity_status="connected",
            )
        ]

        run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=10,
            worker_nodes=workers,
        )

        assert len(run.worker_nodes) == 1
        assert run.worker_nodes[0].id == "worker-001"

    def test_analysis_run_with_errors(self):
        """Test analysis run with errors."""
        run = AnalysisRun(
            deployment_id="test",
            status="partial",
            objectives_analyzed=["health", "config"],
            api_calls_used=30,
            errors=["Failed to fetch config data", "API timeout"],
            partial_completion=True,
        )

        assert len(run.errors) == 2
        assert run.partial_completion is True
        assert "API timeout" in run.errors

    def test_uuid_generation(self):
        """Test that UUID is automatically generated."""
        run1 = AnalysisRun(
            deployment_id="test",
            status="running",
            objectives_analyzed=["health"],
            api_calls_used=0,
        )

        run2 = AnalysisRun(
            deployment_id="test",
            status="running",
            objectives_analyzed=["health"],
            api_calls_used=0,
        )

        # Each run should have a unique ID
        assert run1.id != run2.id
        assert len(run1.id) == 36  # UUID format
        assert len(run2.id) == 36
