"""
Unit tests for HealthScorer.
"""

import pytest

from cribl_hc.core.health_scorer import (
    ComponentHealth,
    HealthScorer,
    calculate_worker_health,
)


class TestComponentHealth:
    """Test suite for ComponentHealth."""

    def test_init(self):
        """Test ComponentHealth initialization."""
        health = ComponentHealth(
            name="worker-1",
            score=85.0,
            status="degraded",
            issues=["High CPU"],
            metrics={"cpu": 90.0},
        )

        assert health.name == "worker-1"
        assert health.score == 85.0
        assert health.status == "degraded"
        assert health.issues == ["High CPU"]
        assert health.metrics == {"cpu": 90.0}

    def test_init_defaults(self):
        """Test ComponentHealth with default values."""
        health = ComponentHealth(
            name="test",
            score=100.0,
            status="healthy",
        )

        assert health.issues == []
        assert health.metrics == {}

    def test_is_healthy(self):
        """Test is_healthy method."""
        healthy = ComponentHealth("test", 95.0, "healthy")
        assert healthy.is_healthy() is True

        degraded = ComponentHealth("test", 85.0, "degraded")
        assert degraded.is_healthy() is False

    def test_is_critical(self):
        """Test is_critical method."""
        critical = ComponentHealth("test", 30.0, "critical")
        assert critical.is_critical() is True

        healthy = ComponentHealth("test", 95.0, "healthy")
        assert healthy.is_critical() is False

    def test_repr(self):
        """Test string representation."""
        health = ComponentHealth("worker-1", 85.0, "degraded")
        repr_str = repr(health)

        assert "worker-1" in repr_str
        assert "85" in repr_str
        assert "degraded" in repr_str


class TestHealthScorer:
    """Test suite for HealthScorer."""

    def test_init(self):
        """Test HealthScorer initialization."""
        scorer = HealthScorer()
        assert scorer is not None

    def test_score_worker_health_all_healthy(self):
        """Test scoring healthy worker."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=40.0,
        )

        assert health.name == "worker-1"
        assert health.score == 100.0
        assert health.status == "healthy"
        assert len(health.issues) == 0

    def test_score_worker_health_high_cpu(self):
        """Test scoring worker with high CPU."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=85.0,  # Warning threshold
            memory_usage=60.0,
            disk_usage=40.0,
        )

        assert health.score == 85.0  # 100 - 15
        assert health.status == "degraded"
        assert len(health.issues) == 1
        assert "CPU" in health.issues[0]

    def test_score_worker_health_critical_cpu(self):
        """Test scoring worker with critical CPU."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=95.0,  # Critical threshold
            memory_usage=60.0,
            disk_usage=40.0,
        )

        assert health.score == 60.0  # 100 - 40
        assert health.status == "unhealthy"
        assert len(health.issues) == 1
        assert "critical" in health.issues[0].lower()

    def test_score_worker_health_high_memory(self):
        """Test scoring worker with high memory."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=50.0,
            memory_usage=85.0,  # Warning
            disk_usage=40.0,
        )

        assert health.score == 85.0
        assert health.status == "degraded"
        assert "Memory" in health.issues[0]

    def test_score_worker_health_critical_memory(self):
        """Test scoring worker with critical memory."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=50.0,
            memory_usage=95.0,  # Critical
            disk_usage=40.0,
        )

        assert health.score == 60.0
        assert health.status == "unhealthy"
        assert "Memory" in health.issues[0]

    def test_score_worker_health_high_disk(self):
        """Test scoring worker with high disk."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=85.0,  # Warning
        )

        assert health.score == 90.0  # 100 - 10
        assert health.status == "healthy"  # Still above 90
        assert "Disk" in health.issues[0]

    def test_score_worker_health_critical_disk(self):
        """Test scoring worker with critical disk."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=95.0,  # Critical
        )

        assert health.score == 70.0  # 100 - 30
        assert health.status == "degraded"
        assert "Disk" in health.issues[0]

    def test_score_worker_health_multiple_issues(self):
        """Test scoring worker with multiple issues."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=95.0,  # -40
            memory_usage=92.0,  # -40
            disk_usage=91.0,  # -30
        )

        assert health.score == 0.0  # 100 - 110, capped at 0
        assert health.status == "critical"
        assert len(health.issues) == 3

    def test_score_worker_health_metrics_stored(self):
        """Test that metrics are stored in ComponentHealth."""
        scorer = HealthScorer()
        health = scorer.score_worker_health(
            worker_id="worker-1",
            cpu_usage=75.0,
            memory_usage=65.0,
            disk_usage=55.0,
        )

        assert health.metrics["cpu_usage"] == 75.0
        assert health.metrics["memory_usage"] == 65.0
        assert health.metrics["disk_usage"] == 55.0

    def test_score_overall_health_all_healthy(self):
        """Test overall health with all healthy components."""
        scorer = HealthScorer()

        components = [
            ComponentHealth("w1", 100.0, "healthy"),
            ComponentHealth("w2", 95.0, "healthy"),
            ComponentHealth("w3", 98.0, "healthy"),
        ]

        overall = scorer.score_overall_health(components)

        assert overall.name == "overall"
        assert overall.score > 90.0
        assert overall.status == "healthy"

    def test_score_overall_health_mixed(self):
        """Test overall health with mixed component health."""
        scorer = HealthScorer()

        components = [
            ComponentHealth("w1", 100.0, "healthy"),
            ComponentHealth("w2", 75.0, "degraded"),
            ComponentHealth("w3", 80.0, "degraded"),
        ]

        overall = scorer.score_overall_health(components)

        # Average is 85, no critical components
        assert 80.0 <= overall.score <= 90.0
        assert overall.status == "degraded"

    def test_score_overall_health_with_critical(self):
        """Test overall health with critical components."""
        scorer = HealthScorer()

        components = [
            ComponentHealth("w1", 100.0, "healthy"),
            ComponentHealth("w2", 30.0, "critical"),  # Critical!
        ]

        overall = scorer.score_overall_health(components)

        # Average is 65, but with critical penalty
        assert overall.score < 65.0
        assert overall.metrics["critical_components"] == 1

    def test_score_overall_health_no_components(self):
        """Test overall health with no components."""
        scorer = HealthScorer()

        overall = scorer.score_overall_health([])

        assert overall.score == 0.0
        assert overall.status == "unknown"
        assert len(overall.issues) > 0

    def test_score_deployment_health_all_healthy(self):
        """Test deployment health with all workers healthy."""
        scorer = HealthScorer()

        health = scorer.score_deployment_health(
            healthy_workers=10,
            total_workers=10,
            critical_findings=0,
            high_findings=0,
        )

        assert health.score == 100.0
        assert health.status == "healthy"
        assert len(health.issues) == 0

    def test_score_deployment_health_some_unhealthy(self):
        """Test deployment health with some unhealthy workers."""
        scorer = HealthScorer()

        health = scorer.score_deployment_health(
            healthy_workers=8,
            total_workers=10,
            critical_findings=0,
            high_findings=0,
        )

        assert health.score == 80.0
        assert health.status == "degraded"
        assert len(health.issues) == 1

    def test_score_deployment_health_with_findings(self):
        """Test deployment health with critical findings."""
        scorer = HealthScorer()

        health = scorer.score_deployment_health(
            healthy_workers=10,
            total_workers=10,
            critical_findings=2,  # -30 points
            high_findings=3,  # -15 points
        )

        assert health.score == 55.0  # 100 - 30 - 15
        assert health.status == "unhealthy"
        assert "critical findings" in health.issues[0]

    def test_score_deployment_health_no_workers(self):
        """Test deployment health with no workers."""
        scorer = HealthScorer()

        health = scorer.score_deployment_health(
            healthy_workers=0,
            total_workers=0,
        )

        assert health.score == 0.0
        assert health.status == "unknown"
        assert "No workers" in health.issues[0]

    def test_score_to_status_thresholds(self):
        """Test status threshold boundaries."""
        scorer = HealthScorer()

        assert scorer._score_to_status(100.0) == "healthy"
        assert scorer._score_to_status(90.0) == "healthy"
        assert scorer._score_to_status(89.9) == "degraded"
        assert scorer._score_to_status(70.0) == "degraded"
        assert scorer._score_to_status(69.9) == "unhealthy"
        assert scorer._score_to_status(50.0) == "unhealthy"
        assert scorer._score_to_status(49.9) == "critical"
        assert scorer._score_to_status(0.0) == "critical"

    def test_get_status_color(self):
        """Test status color codes."""
        scorer = HealthScorer()

        assert scorer.get_status_color("healthy") == "\033[92m"
        assert scorer.get_status_color("degraded") == "\033[93m"
        assert scorer.get_status_color("unhealthy") == "\033[91m"
        assert scorer.get_status_color("critical") == "\033[95m"
        assert scorer.get_status_color("unknown") == "\033[90m"

    def test_format_health_summary(self):
        """Test health summary formatting."""
        scorer = HealthScorer()

        health = ComponentHealth("test", 95.0, "healthy")
        summary = scorer.format_health_summary(health)

        assert "HEALTHY" in summary
        assert "95" in summary
        assert "\033[92m" in summary  # Green color
        assert "\033[0m" in summary  # Reset color

    def test_thresholds_are_consistent(self):
        """Test that all thresholds are properly defined."""
        scorer = HealthScorer()

        # Health status thresholds
        assert scorer.HEALTHY_THRESHOLD == 90.0
        assert scorer.DEGRADED_THRESHOLD == 70.0
        assert scorer.UNHEALTHY_THRESHOLD == 50.0

        # Resource thresholds
        assert scorer.CPU_WARNING_THRESHOLD == 80.0
        assert scorer.CPU_CRITICAL_THRESHOLD == 90.0
        assert scorer.MEMORY_WARNING_THRESHOLD == 80.0
        assert scorer.MEMORY_CRITICAL_THRESHOLD == 90.0
        assert scorer.DISK_WARNING_THRESHOLD == 80.0
        assert scorer.DISK_CRITICAL_THRESHOLD == 90.0


class TestCalculateWorkerHealth:
    """Test suite for calculate_worker_health convenience function."""

    def test_calculate_worker_health(self):
        """Test convenience function."""
        health = calculate_worker_health(
            worker_id="worker-1",
            cpu_usage=85.0,
            memory_usage=70.0,
            disk_usage=60.0,
        )

        assert health.name == "worker-1"
        assert health.status == "degraded"
        assert health.score == 85.0

    def test_calculate_worker_health_healthy(self):
        """Test convenience function with healthy worker."""
        health = calculate_worker_health(
            worker_id="worker-1",
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=40.0,
        )

        assert health.status == "healthy"
        assert health.score == 100.0

    def test_calculate_worker_health_critical(self):
        """Test convenience function with critical worker."""
        health = calculate_worker_health(
            worker_id="worker-1",
            cpu_usage=95.0,
            memory_usage=92.0,
            disk_usage=91.0,
        )

        assert health.status == "critical"
        assert health.score == 0.0
