"""
Unit tests for health scoring algorithms.

Tests ComponentHealth and HealthScorer classes including:
- Worker health scoring with resource thresholds
- Overall health aggregation
- Deployment health calculation
- Status determination
- Edge cases and boundary conditions
"""

import pytest

from cribl_hc.core.health_scorer import (
    ComponentHealth,
    HealthScorer,
    calculate_worker_health,
)


class TestComponentHealth:
    """Test ComponentHealth data class."""

    def test_initialization(self):
        """Test component health initialization."""
        health = ComponentHealth(
            name="test-component",
            score=85.5,
            status="degraded",
            issues=["High CPU"],
            metrics={"cpu": 85.0}
        )

        assert health.name == "test-component"
        assert health.score == 85.5
        assert health.status == "degraded"
        assert health.issues == ["High CPU"]
        assert health.metrics == {"cpu": 85.0}

    def test_initialization_defaults(self):
        """Test component health with default values."""
        health = ComponentHealth(
            name="test",
            score=100.0,
            status="healthy"
        )

        assert health.issues == []
        assert health.metrics == {}

    def test_is_healthy_true(self):
        """Test is_healthy returns true for score >= 90."""
        health = ComponentHealth("test", score=90.0, status="healthy")
        assert health.is_healthy() is True

        health = ComponentHealth("test", score=95.0, status="healthy")
        assert health.is_healthy() is True

        health = ComponentHealth("test", score=100.0, status="healthy")
        assert health.is_healthy() is True

    def test_is_healthy_false(self):
        """Test is_healthy returns false for score < 90."""
        health = ComponentHealth("test", score=89.9, status="degraded")
        assert health.is_healthy() is False

        health = ComponentHealth("test", score=70.0, status="degraded")
        assert health.is_healthy() is False

    def test_is_critical_true(self):
        """Test is_critical returns true for score < 50."""
        health = ComponentHealth("test", score=49.9, status="critical")
        assert health.is_critical() is True

        health = ComponentHealth("test", score=0.0, status="critical")
        assert health.is_critical() is True

    def test_is_critical_false(self):
        """Test is_critical returns false for score >= 50."""
        health = ComponentHealth("test", score=50.0, status="unhealthy")
        assert health.is_critical() is False

        health = ComponentHealth("test", score=70.0, status="degraded")
        assert health.is_critical() is False

    def test_repr(self):
        """Test string representation."""
        health = ComponentHealth("worker-1", score=85.0, status="degraded")
        repr_str = repr(health)

        assert "worker-1" in repr_str
        assert "85" in repr_str
        assert "degraded" in repr_str


class TestHealthScorerConstants:
    """Test HealthScorer threshold constants."""

    def test_health_thresholds(self):
        """Test health status thresholds are correct."""
        scorer = HealthScorer()

        assert scorer.HEALTHY_THRESHOLD == 90.0
        assert scorer.DEGRADED_THRESHOLD == 70.0
        assert scorer.UNHEALTHY_THRESHOLD == 50.0

    def test_resource_thresholds(self):
        """Test resource usage thresholds."""
        scorer = HealthScorer()

        assert scorer.CPU_WARNING_THRESHOLD == 80.0
        assert scorer.CPU_CRITICAL_THRESHOLD == 90.0
        assert scorer.MEMORY_WARNING_THRESHOLD == 80.0
        assert scorer.MEMORY_CRITICAL_THRESHOLD == 90.0
        assert scorer.DISK_WARNING_THRESHOLD == 80.0
        assert scorer.DISK_CRITICAL_THRESHOLD == 90.0


class TestScoreToStatus:
    """Test status determination from scores."""

    def test_healthy_status(self):
        """Test healthy status for scores >= 90."""
        scorer = HealthScorer()

        assert scorer._score_to_status(100.0) == "healthy"
        assert scorer._score_to_status(95.0) == "healthy"
        assert scorer._score_to_status(90.0) == "healthy"

    def test_degraded_status(self):
        """Test degraded status for scores 70-89."""
        scorer = HealthScorer()

        assert scorer._score_to_status(89.9) == "degraded"
        assert scorer._score_to_status(80.0) == "degraded"
        assert scorer._score_to_status(70.0) == "degraded"

    def test_unhealthy_status(self):
        """Test unhealthy status for scores 50-69."""
        scorer = HealthScorer()

        assert scorer._score_to_status(69.9) == "unhealthy"
        assert scorer._score_to_status(60.0) == "unhealthy"
        assert scorer._score_to_status(50.0) == "unhealthy"

    def test_critical_status(self):
        """Test critical status for scores < 50."""
        scorer = HealthScorer()

        assert scorer._score_to_status(49.9) == "critical"
        assert scorer._score_to_status(25.0) == "critical"
        assert scorer._score_to_status(0.0) == "critical"


class TestWorkerHealthScoring:
    """Test worker health scoring algorithm."""

    def test_perfect_health(self):
        """Test worker with perfect health (all resources low)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 50.0, 50.0, 50.0)

        assert health.score == 100.0
        assert health.status == "healthy"
        assert health.issues == []
        assert health.name == "worker-1"

    def test_cpu_warning(self):
        """Test worker with high CPU (80-89%)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 85.0, 50.0, 50.0)

        assert health.score == 85.0  # 100 - 15
        assert health.status == "degraded"
        assert len(health.issues) == 1
        assert "CPU high" in health.issues[0]
        assert "85.0%" in health.issues[0]

    def test_cpu_critical(self):
        """Test worker with critical CPU (>= 90%)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 95.0, 50.0, 50.0)

        assert health.score == 60.0  # 100 - 40
        assert health.status == "unhealthy"
        assert len(health.issues) == 1
        assert "CPU critical" in health.issues[0]

    def test_memory_warning(self):
        """Test worker with high memory (80-89%)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 50.0, 85.0, 50.0)

        assert health.score == 85.0  # 100 - 15
        assert health.status == "degraded"
        assert len(health.issues) == 1
        assert "Memory high" in health.issues[0]

    def test_memory_critical(self):
        """Test worker with critical memory (>= 90%)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 50.0, 92.0, 50.0)

        assert health.score == 60.0  # 100 - 40
        assert health.status == "unhealthy"
        assert len(health.issues) == 1
        assert "Memory critical" in health.issues[0]

    def test_disk_warning(self):
        """Test worker with high disk usage (80-89%)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 50.0, 50.0, 85.0)

        assert health.score == 90.0  # 100 - 10
        assert health.status == "healthy"
        assert len(health.issues) == 1
        assert "Disk high" in health.issues[0]

    def test_disk_critical(self):
        """Test worker with critical disk usage (>= 90%)."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 50.0, 50.0, 95.0)

        assert health.score == 70.0  # 100 - 30
        assert health.status == "degraded"
        assert len(health.issues) == 1
        assert "Disk critical" in health.issues[0]

    def test_multiple_warnings(self):
        """Test worker with multiple warning-level issues."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 85.0, 85.0, 85.0)

        # 100 - 15 (CPU) - 15 (Memory) - 10 (Disk) = 60
        assert health.score == 60.0
        assert health.status == "unhealthy"
        assert len(health.issues) == 3
        assert any("CPU high" in issue for issue in health.issues)
        assert any("Memory high" in issue for issue in health.issues)
        assert any("Disk high" in issue for issue in health.issues)

    def test_all_critical(self):
        """Test worker with all resources critical."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 95.0, 95.0, 95.0)

        # 100 - 40 (CPU) - 40 (Memory) - 30 (Disk) = -10 -> 0 (clamped)
        assert health.score == 0.0
        assert health.status == "critical"
        assert len(health.issues) == 3
        assert any("CPU critical" in issue for issue in health.issues)
        assert any("Memory critical" in issue for issue in health.issues)
        assert any("Disk critical" in issue for issue in health.issues)

    def test_mixed_critical_and_warning(self):
        """Test worker with mixed severity issues."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 95.0, 85.0, 50.0)

        # 100 - 40 (CPU critical) - 15 (Memory warning) = 45
        assert health.score == 45.0
        assert health.status == "critical"
        assert len(health.issues) == 2

    def test_boundary_values_at_thresholds(self):
        """Test exact threshold boundary values."""
        scorer = HealthScorer()

        # Exactly at warning threshold
        health = scorer.score_worker_health("worker-1", 80.0, 50.0, 50.0)
        assert health.score == 85.0  # Should trigger warning

        # Just below warning threshold
        health = scorer.score_worker_health("worker-1", 79.9, 50.0, 50.0)
        assert health.score == 100.0  # Should NOT trigger

        # Exactly at critical threshold
        health = scorer.score_worker_health("worker-1", 90.0, 50.0, 50.0)
        assert health.score == 60.0  # Should trigger critical

        # Just below critical threshold
        health = scorer.score_worker_health("worker-1", 89.9, 50.0, 50.0)
        assert health.score == 85.0  # Should trigger warning, not critical

    def test_metrics_captured(self):
        """Test that raw metrics are captured."""
        scorer = HealthScorer()
        health = scorer.score_worker_health("worker-1", 75.0, 82.5, 91.0)

        assert health.metrics["cpu_usage"] == 75.0
        assert health.metrics["memory_usage"] == 82.5
        assert health.metrics["disk_usage"] == 91.0

    def test_extreme_values(self):
        """Test edge cases with extreme values."""
        scorer = HealthScorer()

        # Zero usage
        health = scorer.score_worker_health("worker-1", 0.0, 0.0, 0.0)
        assert health.score == 100.0
        assert health.status == "healthy"

        # 100% usage
        health = scorer.score_worker_health("worker-1", 100.0, 100.0, 100.0)
        assert health.score == 0.0
        assert health.status == "critical"


class TestOverallHealthScoring:
    """Test overall health aggregation."""

    def test_single_healthy_component(self):
        """Test overall health with single healthy component."""
        scorer = HealthScorer()
        component = ComponentHealth("c1", score=95.0, status="healthy")

        overall = scorer.score_overall_health([component])

        assert overall.score == 95.0
        assert overall.status == "healthy"
        assert overall.name == "overall"

    def test_multiple_healthy_components(self):
        """Test overall health with all healthy components."""
        scorer = HealthScorer()
        components = [
            ComponentHealth("c1", score=95.0, status="healthy"),
            ComponentHealth("c2", score=92.0, status="healthy"),
            ComponentHealth("c3", score=98.0, status="healthy"),
        ]

        overall = scorer.score_overall_health(components)

        # Average: (95 + 92 + 98) / 3 = 95.0
        assert overall.score == 95.0
        assert overall.status == "healthy"

    def test_mixed_health_no_critical(self):
        """Test overall health with mixed but no critical components."""
        scorer = HealthScorer()
        components = [
            ComponentHealth("c1", score=90.0, status="healthy"),
            ComponentHealth("c2", score=75.0, status="degraded"),
            ComponentHealth("c3", score=60.0, status="unhealthy"),
        ]

        overall = scorer.score_overall_health(components)

        # Average: (90 + 75 + 60) / 3 = 75.0, no critical penalty
        assert overall.score == 75.0
        assert overall.status == "degraded"

    def test_critical_component_penalty(self):
        """Test penalty applied for critical components."""
        scorer = HealthScorer()
        components = [
            ComponentHealth("c1", score=90.0, status="healthy"),
            ComponentHealth("c2", score=90.0, status="healthy"),
            ComponentHealth("c3", score=40.0, status="critical"),  # Critical
        ]

        overall = scorer.score_overall_health(components)

        # Average: (90 + 90 + 40) / 3 = 73.33
        # Critical penalty: (1 / 3) * 20 = 6.67
        # Final: 73.33 - 6.67 = 66.66
        assert 66.0 <= overall.score <= 67.0
        assert overall.status == "unhealthy"

    def test_multiple_critical_components(self):
        """Test multiple critical components increase penalty."""
        scorer = HealthScorer()
        components = [
            ComponentHealth("c1", score=90.0, status="healthy"),
            ComponentHealth("c2", score=30.0, status="critical"),
            ComponentHealth("c3", score=20.0, status="critical"),
        ]

        overall = scorer.score_overall_health(components)

        # Average: (90 + 30 + 20) / 3 = 46.67
        # Critical penalty: (2 / 3) * 20 = 13.33
        # Final: 46.67 - 13.33 = 33.34
        assert 33.0 <= overall.score <= 34.0
        assert overall.status == "critical"

    def test_empty_components_list(self):
        """Test overall health with no components."""
        scorer = HealthScorer()
        overall = scorer.score_overall_health([])

        assert overall.score == 0.0
        assert overall.status == "unknown"
        assert "No components to assess" in overall.issues

    def test_issues_aggregation(self):
        """Test that component issues are aggregated."""
        scorer = HealthScorer()
        components = [
            ComponentHealth("c1", score=85.0, status="degraded", issues=["High CPU"]),
            ComponentHealth("c2", score=70.0, status="degraded", issues=["High memory", "Disk full"]),
        ]

        overall = scorer.score_overall_health(components)

        # Should have 3 issues total, prefixed with component names
        assert len(overall.issues) == 3
        assert any("c1: High CPU" in issue for issue in overall.issues)
        assert any("c2: High memory" in issue for issue in overall.issues)
        assert any("c2: Disk full" in issue for issue in overall.issues)

    def test_metrics_captured_in_overall(self):
        """Test that overall metrics are captured."""
        scorer = HealthScorer()
        components = [
            ComponentHealth("c1", score=90.0, status="healthy"),
            ComponentHealth("c2", score=30.0, status="critical"),
        ]

        overall = scorer.score_overall_health(components)

        assert overall.metrics["total_components"] == 2
        assert overall.metrics["critical_components"] == 1
        assert "avg_component_score" in overall.metrics


class TestDeploymentHealthScoring:
    """Test deployment health calculation."""

    def test_all_workers_healthy(self):
        """Test deployment with all workers healthy."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=10,
            total_workers=10,
            critical_findings=0,
            high_findings=0
        )

        assert health.score == 100.0
        assert health.status == "healthy"
        assert health.issues == []

    def test_some_unhealthy_workers(self):
        """Test deployment with some unhealthy workers."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=8,
            total_workers=10,
            critical_findings=0,
            high_findings=0
        )

        # 8/10 = 80% healthy = 80.0 score
        assert health.score == 80.0
        assert health.status == "degraded"
        assert len(health.issues) == 1
        assert "2/10 workers unhealthy" in health.issues[0]

    def test_critical_findings_penalty(self):
        """Test penalty for critical findings."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=10,
            total_workers=10,
            critical_findings=2,
            high_findings=0
        )

        # Base: 100, Critical penalty: 2 * 15 = 30, Final: 70
        assert health.score == 70.0
        assert health.status == "degraded"
        assert any("2 critical findings" in issue for issue in health.issues)

    def test_high_findings_penalty(self):
        """Test penalty for high severity findings."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=10,
            total_workers=10,
            critical_findings=0,
            high_findings=4
        )

        # Base: 100, High penalty: 4 * 5 = 20, Final: 80
        assert health.score == 80.0
        assert health.status == "degraded"
        assert any("4 high severity findings" in issue for issue in health.issues)

    def test_combined_penalties(self):
        """Test combined penalties from workers and findings."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=7,
            total_workers=10,
            critical_findings=1,
            high_findings=3
        )

        # Base: 70 (70% healthy)
        # Critical: 1 * 15 = 15
        # High: 3 * 5 = 15
        # Final: 70 - 15 - 15 = 40
        assert health.score == 40.0
        assert health.status == "critical"

    def test_no_workers(self):
        """Test deployment with no workers."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=0,
            total_workers=0,
            critical_findings=0,
            high_findings=0
        )

        assert health.score == 0.0
        assert health.status == "unknown"
        assert "No workers detected" in health.issues

    def test_all_workers_unhealthy(self):
        """Test deployment with all workers unhealthy."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=0,
            total_workers=5,
            critical_findings=0,
            high_findings=0
        )

        assert health.score == 0.0
        assert health.status == "critical"
        assert "5/5 workers unhealthy" in health.issues[0]

    def test_score_cannot_go_negative(self):
        """Test that score is clamped to 0."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=5,
            total_workers=10,
            critical_findings=10,  # Would cause negative score
            high_findings=10
        )

        assert health.score == 0.0
        assert health.status == "critical"

    def test_metrics_captured_in_deployment(self):
        """Test deployment metrics are captured."""
        scorer = HealthScorer()
        health = scorer.score_deployment_health(
            healthy_workers=7,
            total_workers=10,
            critical_findings=2,
            high_findings=3
        )

        assert health.metrics["total_workers"] == 10
        assert health.metrics["healthy_workers"] == 7
        assert health.metrics["unhealthy_workers"] == 3
        assert health.metrics["critical_findings"] == 2
        assert health.metrics["high_findings"] == 3


class TestColorFormatting:
    """Test status color and formatting utilities."""

    def test_get_status_color(self):
        """Test status to color mapping."""
        scorer = HealthScorer()

        assert "\033[92m" in scorer.get_status_color("healthy")  # Green
        assert "\033[93m" in scorer.get_status_color("degraded")  # Yellow
        assert "\033[91m" in scorer.get_status_color("unhealthy")  # Red
        assert "\033[95m" in scorer.get_status_color("critical")  # Magenta
        assert "\033[90m" in scorer.get_status_color("unknown")  # Gray

    def test_get_status_color_unknown(self):
        """Test color for unknown status."""
        scorer = HealthScorer()
        # Unknown status should return reset code
        assert "\033[0m" in scorer.get_status_color("invalid-status")

    def test_format_health_summary(self):
        """Test health summary formatting."""
        scorer = HealthScorer()
        health = ComponentHealth("test", score=85.5, status="degraded")

        summary = scorer.format_health_summary(health)

        assert "DEGRADED" in summary
        assert "86/100" in summary or "85/100" in summary  # Rounded
        assert "\033[93m" in summary  # Yellow color for degraded
        assert "\033[0m" in summary  # Reset code


class TestConvenienceFunction:
    """Test convenience function."""

    def test_calculate_worker_health(self):
        """Test calculate_worker_health convenience function."""
        health = calculate_worker_health("worker-1", 50.0, 50.0, 50.0)

        assert isinstance(health, ComponentHealth)
        assert health.name == "worker-1"
        assert health.score == 100.0
        assert health.status == "healthy"

    def test_convenience_function_with_issues(self):
        """Test convenience function returns proper issues."""
        health = calculate_worker_health("worker-2", 95.0, 85.0, 70.0)

        assert health.score < 100.0
        assert len(health.issues) > 0
        assert any("CPU critical" in issue for issue in health.issues)
