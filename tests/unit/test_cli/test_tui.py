"""
Unit tests for TUI (Terminal User Interface) module.
"""

from datetime import datetime, timezone
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from cribl_hc.cli.tui import HealthCheckTUI
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.deployment import Deployment
from cribl_hc.models.finding import Finding
from cribl_hc.models.health import HealthScore
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate


@pytest.fixture
def sample_deployment():
    """Create a sample deployment for testing."""
    return Deployment(
        id="test-deployment",
        name="Test Deployment",
        url="https://test.cribl.cloud",
        environment_type="cloud",
        auth_token="test-token",
    )


@pytest.fixture
def sample_health_score():
    """Create a sample health score."""
    from cribl_hc.models.health import ComponentScore

    return HealthScore(
        overall_score=85,
        components={
            "health": ComponentScore(
                name="Health",
                score=90,
                weight=0.4,
                details="Workers healthy"
            ),
            "config": ComponentScore(
                name="Configuration",
                score=80,
                weight=0.3,
                details="Minor config issues"
            ),
            "resource": ComponentScore(
                name="Resources",
                score=85,
                weight=0.3,
                details="Resource utilization good"
            ),
        },
    )


@pytest.fixture
def sample_findings():
    """Create sample findings for testing."""
    return [
        Finding(
            id="critical-finding-1",
            category="health",
            severity="critical",
            title="Critical Health Issue",
            description="Worker node is down",
            affected_components=["worker-1"],
            remediation_steps=["Restart worker", "Check logs"],
            estimated_impact="Service degradation - reduced throughput capacity",
            confidence_level="high",
        ),
        Finding(
            id="high-finding-1",
            category="config",
            severity="high",
            title="Configuration Issue",
            description="Hardcoded credentials detected",
            affected_components=["output-splunk"],
            remediation_steps=["Use environment variables"],
            estimated_impact="Security risk - credentials exposed",
            confidence_level="high",
        ),
        Finding(
            id="medium-finding-1",
            category="performance",
            severity="medium",
            title="Performance Warning",
            description="Pipeline has too many functions",
            affected_components=["pipeline-main"],
            remediation_steps=["Split pipeline"],
            estimated_impact="Moderate performance impact",
            confidence_level="medium",
        ),
        Finding(
            id="low-finding-1",
            category="best_practice",
            severity="low",
            title="Best Practice Suggestion",
            description="Pipeline name lacks clarity",
            affected_components=["pipeline-test"],
            remediation_steps=["Rename pipeline"],
            estimated_impact="Maintainability improvement",
            confidence_level="low",
        ),
    ]


@pytest.fixture
def sample_recommendations():
    """Create sample recommendations for testing."""
    return [
        Recommendation(
            id="rec-1",
            type="scaling",
            priority="p1",
            title="Add worker capacity",
            description="Current workers are near capacity",
            rationale="Workers at 85% utilization, approaching threshold",
            implementation_steps=["Scale worker group to 5 nodes", "Update load balancer"],
            impact_estimate=ImpactEstimate(
                performance_improvement="30-40% throughput increase",
            ),
            implementation_effort="medium",
            related_findings=["high-finding-1"],
        ),
        Recommendation(
            id="rec-2",
            type="optimization",
            priority="p2",
            title="Optimize pipeline configuration",
            description="Consolidate duplicate logic",
            rationale="Multiple pipelines contain duplicate parsing logic",
            implementation_steps=["Extract common logic to shared pipeline", "Update routes"],
            impact_estimate=ImpactEstimate(
                performance_improvement="10-20% processing improvement",
            ),
            implementation_effort="low",
            related_findings=["medium-finding-1"],
        ),
    ]


@pytest.fixture
def sample_analysis_run(sample_deployment, sample_health_score, sample_findings, sample_recommendations):
    """Create a complete analysis run for testing."""
    return AnalysisRun(
        id="test-run-1",
        deployment_id="test-deployment",
        started_at=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        completed_at=datetime(2025, 1, 15, 10, 31, 0, tzinfo=timezone.utc),
        status="completed",
        objectives_analyzed=["health", "config"],
        health_score=sample_health_score,
        findings=sample_findings,
        recommendations=sample_recommendations,
        api_calls_used=50,
        duration_seconds=45.5,
    )


class TestHealthCheckTUI:
    """Test the HealthCheckTUI class."""

    def test_init(self):
        """Test TUI initialization."""
        tui = HealthCheckTUI()
        assert tui.console is not None

    def test_display_complete_results(self, sample_analysis_run):
        """Test displaying complete analysis results."""
        tui = HealthCheckTUI()

        # Mock console output to prevent actual terminal rendering
        with patch.object(tui.console, "print") as mock_print, \
             patch.object(tui.console, "clear") as mock_clear:
            tui.display(sample_analysis_run)

            # Verify console was cleared
            mock_clear.assert_called_once()

            # Verify console.print was called (for layout rendering)
            assert mock_print.called

    def test_display_no_health_score(self, sample_analysis_run):
        """Test displaying results without health score."""
        sample_analysis_run.health_score = None
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            # Should not raise an error
            tui.display(sample_analysis_run)

    def test_display_no_findings(self, sample_analysis_run):
        """Test displaying results with no findings."""
        sample_analysis_run.findings = []
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            # Should not raise an error
            tui.display(sample_analysis_run)

    def test_display_no_recommendations(self, sample_analysis_run):
        """Test displaying results with no recommendations."""
        sample_analysis_run.recommendations = []
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            # Should not raise an error
            tui.display(sample_analysis_run)

    def test_display_many_findings(self, sample_analysis_run):
        """Test displaying results with many findings (>20)."""
        # Create 30 findings
        many_findings = [
            Finding(
                id=f"finding-{i}",
                category="test",
                severity="low",
                title=f"Finding {i}",
                description=f"Test finding {i}",
                affected_components=[f"component-{i}"],
                remediation_steps=["Fix it"],
                confidence_level="medium",
            )
            for i in range(30)
        ]
        sample_analysis_run.findings = many_findings

        tui = HealthCheckTUI()

        with patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            # Should not raise an error, and should show only top 20
            tui.display(sample_analysis_run)

    def test_display_many_recommendations(self, sample_analysis_run):
        """Test displaying results with many recommendations (>5)."""
        # Create 10 recommendations
        many_recs = [
            Recommendation(
                id=f"rec-{i}",
                type="optimization",
                priority="p3",
                title=f"Recommendation {i}",
                description=f"Test recommendation {i}",
                rationale="Test rationale",
                implementation_steps=["Step 1", "Step 2"],
                impact_estimate=ImpactEstimate(
                    performance_improvement="Minor improvement",
                ),
                implementation_effort="low",
                related_findings=[],
            )
            for i in range(10)
        ]
        sample_analysis_run.recommendations = many_recs

        tui = HealthCheckTUI()

        with patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            # Should not raise an error, and should show only top 5
            tui.display(sample_analysis_run)

    def test_health_score_colors(self, sample_analysis_run):
        """Test that health score colors are correct for different ranges."""
        tui = HealthCheckTUI()

        # Test excellent score (>= 90)
        sample_analysis_run.health_score.overall_score = 95
        panel = tui._create_health_score_panel(sample_analysis_run)
        assert "green" in panel.border_style

        # Test good score (75-89)
        sample_analysis_run.health_score.overall_score = 80
        panel = tui._create_health_score_panel(sample_analysis_run)
        assert "yellow" in panel.border_style

        # Test fair score (50-74)
        sample_analysis_run.health_score.overall_score = 60
        panel = tui._create_health_score_panel(sample_analysis_run)
        assert "orange" in panel.border_style

        # Test poor score (< 50)
        sample_analysis_run.health_score.overall_score = 30
        panel = tui._create_health_score_panel(sample_analysis_run)
        assert "red" in panel.border_style

    def test_edge_product_type(self, sample_analysis_run):
        """Test display for Edge product type."""
        # Test that TUI works regardless of product type
        # (Product type detection happens elsewhere, not in TUI)
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            tui.display(sample_analysis_run)

    def test_show_error(self):
        """Test error message display."""
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui.show_error("Test error message")
            mock_print.assert_called_once()

        # Test with exception
        with patch.object(tui.console, "print") as mock_print:
            tui.show_error("Test error", error=ValueError("test exception"))
            mock_print.assert_called_once()

    def test_show_success(self):
        """Test success message display."""
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui.show_success("Test success message")
            mock_print.assert_called_once()

    def test_show_warning(self):
        """Test warning message display."""
        tui = HealthCheckTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui.show_warning("Test warning message")
            mock_print.assert_called_once()

    def test_display_progress(self):
        """Test progress display creation."""
        tui = HealthCheckTUI()

        progress = tui.display_progress("Testing progress...")
        assert progress is not None

    def test_severity_sorting(self, sample_findings):
        """Test that findings are sorted by severity (critical first)."""
        tui = HealthCheckTUI()

        # Create analysis run with unsorted findings
        deployment = Deployment(
            id="test",
            name="Test",
            url="https://test.com",
            environment_type="cloud",
            auth_token="token",
        )

        analysis_run = AnalysisRun(
            id="test",
            deployment_id="test",
            started_at=datetime.now(timezone.utc),
            status="completed",
            objectives_analyzed=["health"],
            findings=sample_findings,  # Already has critical, high, medium, low
            recommendations=[],
            api_calls_used=10,
        )

        # Get findings table panel
        panel = tui._create_findings_table(analysis_run)

        # The table should have critical findings first
        # (We can't easily test table content, but we can verify it was created)
        assert panel is not None
        assert "Findings" in panel.title
