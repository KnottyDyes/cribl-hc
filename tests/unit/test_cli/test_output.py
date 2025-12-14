"""
Unit tests for CLI output formatting.
"""

from io import StringIO

import pytest
from rich.console import Console

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.cli.output import (
    display_analysis_results,
    display_summary,
    display_findings,
    display_recommendations,
    display_health_score,
    format_api_usage,
)
from cribl_hc.models.analysis import AnalysisRun, Finding, Recommendation
from tests.helpers import create_test_finding, create_test_recommendation, create_test_analysis_run


@pytest.fixture
def console():
    """Create a console for testing."""
    return Console(file=StringIO(), force_terminal=True, width=120)


@pytest.fixture
def sample_finding():
    """Create a sample finding."""
    return Finding(
        id="finding-cpu-001",
        title="High CPU Usage",
        description="Worker CPU usage is at 95%",
        severity="high",
        category="health",
        affected_components=["worker-1"],
        remediation_steps=["Scale workers", "Optimize pipelines"],
        estimated_impact="May cause performance degradation",
        confidence_level="high",
    )


@pytest.fixture
def sample_recommendation():
    """Create a sample recommendation."""
    from cribl_hc.models.recommendation import ImpactEstimate

    return Recommendation(
        id="rec-001",
        type="scaling",
        priority="p1",
        title="Scale Workers",
        description="Add more workers to distribute load",
        rationale="Current workers are overutilized with CPU at 95%",
        implementation_steps=[
            "Review current worker allocation",
            "Add 2 additional workers",
            "Monitor CPU usage after scaling",
        ],
        before_state="3 workers at 95% CPU",
        after_state="5 workers at 60% CPU",
        impact_estimate=ImpactEstimate(
            performance_improvement="Reduce CPU usage by 35%",
            time_to_implement="30 minutes",
        ),
        implementation_effort="low",
        related_findings=[],
        documentation_links=["https://docs.cribl.io/scaling"],
    )


@pytest.fixture
def sample_analysis_run(sample_finding, sample_recommendation):
    """Create a sample analysis run."""
    return AnalysisRun(
        deployment_id="test-deployment",
        status="completed",
        objectives_analyzed=["health", "config"],
        api_calls_used=45,
        duration_seconds=12.5,
        findings=[sample_finding],
        recommendations=[sample_recommendation],
    )


@pytest.fixture
def sample_analyzer_result(sample_finding, sample_recommendation):
    """Create a sample analyzer result."""
    result = AnalyzerResult(objective="health")
    result.add_finding(sample_finding)
    result.add_recommendation(sample_recommendation)
    return result


class TestDisplaySummary:
    """Test suite for display_summary function."""

    def test_displays_completed_status(self, console, sample_analysis_run):
        """Test summary display for completed analysis."""
        display_summary(sample_analysis_run, console)

        output = console.file.getvalue()
        assert "COMPLETED" in output
        assert "test-deployment" not in output  # deployment ID not in summary
        assert "45/100" in output  # API calls

    def test_displays_partial_status(self, console, sample_finding):
        """Test summary display for partial completion."""
        analysis_run = AnalysisRun(
            deployment_id="test",
            status="partial",
            objectives_analyzed=["health"],
            api_calls_used=80,
            duration_seconds=10.0,
            findings=[sample_finding],
            recommendations=[],
            partial_completion=True,
        )

        display_summary(analysis_run, console)

        output = console.file.getvalue()
        assert "PARTIAL" in output

    def test_displays_failed_status(self, console):
        """Test summary display for failed analysis."""
        analysis_run = create_test_analysis_run(
            deployment_id="test",
            status="failed",
            objectives_analyzed=["health"],  # Must have at least one
            api_calls_used=5,
        )

        display_summary(analysis_run, console)

        output = console.file.getvalue()
        assert "FAILED" in output

    def test_displays_metrics(self, console, sample_analysis_run):
        """Test that key metrics are displayed."""
        display_summary(sample_analysis_run, console)

        output = console.file.getvalue()
        assert "health, config" in output  # Objectives
        assert "Total Findings" in output
        assert "API Calls Used" in output
        assert "Duration" in output
        assert "12.50s" in output

    def test_severity_counts(self, console):
        """Test display of severity counts."""
        findings = [
            Finding(
                title="Critical Issue",
                description="Test",
                severity="critical",
                category="test",
                affected_component="test",
            ),
            Finding(
                title="High Issue",
                description="Test",
                severity="high",
                category="test",
                affected_component="test",
            ),
            Finding(
                title="Medium Issue",
                description="Test",
                severity="medium",
                category="test",
                affected_component="test",
            ),
        ]

        analysis_run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=10,
            duration_seconds=5.0,
            findings=findings,
            recommendations=[],
        )

        display_summary(analysis_run, console)

        output = console.file.getvalue()
        assert "1" in output  # Critical count
        assert "Critical" in output


class TestDisplayFindings:
    """Test suite for display_findings function."""

    def test_displays_finding_title(self, console, sample_analyzer_result):
        """Test that finding title is displayed."""
        display_findings("health", sample_analyzer_result, console)

        output = console.file.getvalue()
        assert "High CPU Usage" in output
        assert "HEALTH Findings" in output

    def test_displays_finding_details(self, console, sample_analyzer_result):
        """Test that finding details are displayed."""
        display_findings("health", sample_analyzer_result, console)

        output = console.file.getvalue()
        assert "Worker CPU usage is at 95%" in output
        assert "worker-1" in output
        assert "May cause performance degradation" in output

    def test_groups_by_severity(self, console):
        """Test that findings are grouped by severity."""
        result = AnalyzerResult(objective="health")
        result.add_finding(
            Finding(
                title="Critical",
                description="Critical issue",
                severity="critical",
                category="test",
                affected_component="test",
            )
        )
        result.add_finding(
            Finding(
                title="High",
                description="High issue",
                severity="high",
                category="test",
                affected_component="test",
            )
        )

        display_findings("health", result, console)

        output = console.file.getvalue()
        # Critical should appear before High
        critical_pos = output.find("CRITICAL")
        high_pos = output.find("HIGH")
        assert critical_pos < high_pos

    def test_no_findings_displays_nothing(self, console):
        """Test that no output when no findings."""
        result = AnalyzerResult(objective="health")

        # Should not raise
        display_findings("health", result, console)


class TestDisplayRecommendations:
    """Test suite for display_recommendations function."""

    def test_displays_recommendation_title(self, console, sample_recommendation):
        """Test that recommendation title is displayed."""
        display_recommendations([sample_recommendation], console)

        output = console.file.getvalue()
        assert "Scale Workers" in output
        assert "Recommendations" in output

    def test_displays_remediation_steps(self, console, sample_recommendation):
        """Test that remediation steps are displayed."""
        display_recommendations([sample_recommendation], console)

        output = console.file.getvalue()
        assert "Review current worker allocation" in output
        assert "Add 2 additional workers" in output
        assert "Monitor CPU usage after scaling" in output

    def test_displays_estimated_effort(self, console, sample_recommendation):
        """Test that estimated effort is displayed."""
        display_recommendations([sample_recommendation], console)

        output = console.file.getvalue()
        assert "Effort: low" in output
        assert "30 minutes" in output  # From impact_estimate.time_to_implement

    def test_displays_references(self, console, sample_recommendation):
        """Test that references are displayed."""
        display_recommendations([sample_recommendation], console)

        output = console.file.getvalue()
        assert "https://docs.cribl.io/scaling" in output

    def test_groups_by_priority(self, console):
        """Test that recommendations are grouped by priority."""
        from cribl_hc.models.recommendation import ImpactEstimate

        recs = [
            Recommendation(
                id="rec-low",
                type="test",
                title="Low Priority",
                description="Low",
                rationale="Test",
                priority="p3",
                implementation_steps=["Step 1"],
                impact_estimate=ImpactEstimate(),
                implementation_effort="low",
            ),
            Recommendation(
                id="rec-crit",
                type="test",
                title="Critical Priority",
                description="Critical",
                rationale="Test",
                priority="p0",
                implementation_steps=["Step 1"],
                impact_estimate=ImpactEstimate(performance_improvement="Test"),
                implementation_effort="high",
            ),
        ]

        display_recommendations(recs, console)

        output = console.file.getvalue()
        # P0 should appear before P3
        p0_pos = output.find("P0")
        p3_pos = output.find("P3")
        assert p0_pos < p3_pos


class TestDisplayAnalysisResults:
    """Test suite for display_analysis_results function."""

    def test_displays_complete_results(
        self, console, sample_analyzer_result, sample_analysis_run
    ):
        """Test displaying complete analysis results."""
        results = {"health": sample_analyzer_result}

        display_analysis_results(results, sample_analysis_run, console)

        output = console.file.getvalue()
        assert "Analysis Summary" in output
        assert "HEALTH Findings" in output
        assert "Recommendations" in output

    def test_displays_multiple_objectives(self, console, sample_finding, sample_recommendation):
        """Test displaying results from multiple objectives."""
        result1 = AnalyzerResult(objective="health")
        result1.add_finding(sample_finding)

        result2 = AnalyzerResult(objective="config")
        result2.add_finding(
            Finding(
                title="Config Issue",
                description="Test",
                severity="medium",
                category="config",
                affected_component="test",
            )
        )

        results = {"health": result1, "config": result2}

        analysis_run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health", "config"],
            api_calls_used=20,
            duration_seconds=5.0,
            findings=[sample_finding],
            recommendations=[sample_recommendation],
        )

        display_analysis_results(results, analysis_run, console)

        output = console.file.getvalue()
        assert "HEALTH Findings" in output
        assert "CONFIG Findings" in output


class TestDisplayHealthScore:
    """Test suite for display_health_score function."""

    def test_healthy_score(self, console):
        """Test display of healthy score (90+)."""
        display_health_score(95.0, console)

        output = console.file.getvalue()
        assert "95.0/100" in output
        assert "HEALTHY" in output

    def test_degraded_score(self, console):
        """Test display of degraded score (70-89)."""
        display_health_score(75.0, console)

        output = console.file.getvalue()
        assert "75.0/100" in output
        assert "DEGRADED" in output

    def test_unhealthy_score(self, console):
        """Test display of unhealthy score (50-69)."""
        display_health_score(60.0, console)

        output = console.file.getvalue()
        assert "60.0/100" in output
        assert "UNHEALTHY" in output

    def test_critical_score(self, console):
        """Test display of critical score (<50)."""
        display_health_score(30.0, console)

        output = console.file.getvalue()
        assert "30.0/100" in output
        assert "CRITICAL" in output


class TestFormatApiUsage:
    """Test suite for format_api_usage function."""

    def test_low_usage(self):
        """Test formatting of low API usage (<75%)."""
        formatted = format_api_usage(50, 100)

        assert "50/100" in formatted
        assert "50%" in formatted

    def test_medium_usage(self):
        """Test formatting of medium API usage (75-89%)."""
        formatted = format_api_usage(80, 100)

        assert "80/100" in formatted
        assert "80%" in formatted

    def test_high_usage(self):
        """Test formatting of high API usage (90+%)."""
        formatted = format_api_usage(95, 100)

        assert "95/100" in formatted
        assert "95%" in formatted

    def test_custom_total(self):
        """Test formatting with custom total."""
        formatted = format_api_usage(40, 50)

        assert "40/50" in formatted
        assert "80%" in formatted
