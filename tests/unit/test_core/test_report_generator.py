"""
Unit tests for report generators.
"""

import json

import pytest

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.report_generator import MarkdownReportGenerator, JSONReportGenerator
from cribl_hc.models.analysis import AnalysisRun, Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate


@pytest.fixture
def sample_finding():
    """Create a sample finding."""
    return Finding(
        id="finding-001",
        title="High CPU Usage",
        description="Worker CPU at 95%",
        severity="high",
        category="health",
        affected_components=["worker-1"],
        remediation_steps=["Scale workers"],
        estimated_impact="Performance degradation",
        confidence_level="high",
    )


@pytest.fixture
def sample_recommendation():
    """Create a sample recommendation."""
    return Recommendation(
        id="rec-001",
        type="scaling",
        priority="p1",
        title="Add Workers",
        description="Scale to 5 workers",
        rationale="Current workers overutilized",
        implementation_steps=["Add 2 workers", "Monitor"],
        impact_estimate=ImpactEstimate(performance_improvement="35% CPU reduction"),
        implementation_effort="low",
    )


@pytest.fixture
def sample_analysis_run(sample_finding, sample_recommendation):
    """Create a sample analysis run."""
    return AnalysisRun(
        deployment_id="test-deployment",
        status="completed",
        objectives_analyzed=["health"],
        api_calls_used=25,
        duration_seconds=10.5,
        findings=[sample_finding],
        recommendations=[sample_recommendation],
    )


@pytest.fixture
def sample_results(sample_finding, sample_recommendation):
    """Create sample analyzer results."""
    result = AnalyzerResult(objective="health")
    result.add_finding(sample_finding)
    result.add_recommendation(sample_recommendation)
    return {"health": result}


class TestMarkdownReportGenerator:
    """Test suite for MarkdownReportGenerator."""

    def test_generate_complete_report(self, sample_analysis_run, sample_results):
        """Test generating a complete Markdown report."""
        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, sample_results)

        assert markdown is not None
        assert isinstance(markdown, str)
        assert len(markdown) > 100

    def test_report_contains_header(self, sample_analysis_run, sample_results):
        """Test that report contains header section."""
        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, sample_results)

        assert "# Cribl Stream Health Check Report" in markdown
        assert "test-deployment" in markdown
        assert "COMPLETED" in markdown

    def test_report_contains_summary(self, sample_analysis_run, sample_results):
        """Test that report contains executive summary."""
        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, sample_results)

        assert "## Executive Summary" in markdown
        assert "Key Metrics" in markdown
        assert "25/100" in markdown  # API calls

    def test_report_contains_findings(self, sample_analysis_run, sample_results):
        """Test that report contains findings section."""
        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, sample_results)

        assert "HEALTH Findings" in markdown
        assert "High CPU Usage" in markdown
        assert "Worker CPU at 95%" in markdown

    def test_report_contains_recommendations(self, sample_analysis_run, sample_results):
        """Test that report contains recommendations section."""
        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, sample_results)

        assert "## Recommendations" in markdown
        assert "Add Workers" in markdown
        assert "Scale to 5 workers" in markdown

    def test_report_contains_appendix(self, sample_analysis_run, sample_results):
        """Test that report contains appendix."""
        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, sample_results)

        assert "## Appendix" in markdown
        assert "Analysis Metadata" in markdown

    def test_severity_ordering(self, sample_analysis_run, sample_results):
        """Test that findings are ordered by severity."""
        # Add multiple severities
        critical_finding = Finding(
            id="finding-critical",
            title="Critical Issue",
            description="Critical",
            severity="critical",
            category="health",
            affected_components=["worker-1"],
            remediation_steps=["Fix immediately"],
            estimated_impact="Service at risk",
            confidence_level="high",
        )

        medium_finding = Finding(
            id="finding-medium",
            title="Medium Issue",
            description="Medium",
            severity="medium",
            category="health",
            affected_components=["worker-2"],
            remediation_steps=["Fix soon"],
            estimated_impact="Minor impact",
            confidence_level="medium",
        )

        sample_analysis_run.findings = [medium_finding, critical_finding]
        result = AnalyzerResult(objective="health")
        result.findings = [medium_finding, critical_finding]
        results = {"health": result}

        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, results)

        # Critical should appear before Medium
        critical_pos = markdown.find("CRITICAL")
        medium_pos = markdown.find("MEDIUM")
        assert critical_pos < medium_pos

    def test_priority_ordering(self, sample_analysis_run):
        """Test that recommendations are ordered by priority."""
        p0_rec = Recommendation(
            id="rec-p0",
            type="urgent",
            priority="p0",
            title="Critical Fix",
            description="Fix now",
            rationale="Critical",
            implementation_steps=["Fix"],
            impact_estimate=ImpactEstimate(performance_improvement="Critical"),
            implementation_effort="high",
        )

        p2_rec = Recommendation(
            id="rec-p2",
            type="normal",
            priority="p2",
            title="Medium Priority",
            description="Fix later",
            rationale="Medium",
            implementation_steps=["Fix"],
            impact_estimate=ImpactEstimate(),
            implementation_effort="low",
        )

        sample_analysis_run.recommendations = [p2_rec, p0_rec]
        result = AnalyzerResult(objective="health")
        result.recommendations = [p2_rec, p0_rec]
        results = {"health": result}

        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, results)

        # P0 (CRITICAL) should appear before P2 (MEDIUM)
        critical_pos = markdown.find("CRITICAL Priority")
        medium_pos = markdown.find("MEDIUM Priority")
        assert critical_pos < medium_pos

    def test_empty_findings(self, sample_analysis_run):
        """Test report with no findings."""
        sample_analysis_run.findings = []
        result = AnalyzerResult(objective="health")
        results = {"health": result}

        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, results)

        # Should still have header and summary
        assert "# Cribl Stream Health Check Report" in markdown
        assert "## Executive Summary" in markdown

    def test_empty_recommendations(self, sample_analysis_run):
        """Test report with no recommendations."""
        sample_analysis_run.recommendations = []
        result = AnalyzerResult(objective="health")
        results = {"health": result}

        generator = MarkdownReportGenerator()
        markdown = generator.generate(sample_analysis_run, results)

        # Should not have recommendations section
        assert "## Recommendations" not in markdown

    def test_multiple_objectives(self, sample_finding, sample_recommendation):
        """Test report with multiple objectives."""
        analysis_run = AnalysisRun(
            deployment_id="test",
            status="completed",
            objectives_analyzed=["health", "config"],
            api_calls_used=50,
            duration_seconds=15.0,
            findings=[sample_finding],
            recommendations=[sample_recommendation],
        )

        health_result = AnalyzerResult(objective="health")
        health_result.add_finding(sample_finding)

        config_result = AnalyzerResult(objective="config")
        config_finding = Finding(
            id="finding-config",
            title="Config Issue",
            description="Config problem",
            severity="medium",
            category="config",
            affected_components=["config-1"],
            remediation_steps=["Fix config"],
            estimated_impact="Minor",
            confidence_level="medium",
        )
        config_result.add_finding(config_finding)

        results = {"health": health_result, "config": config_result}

        generator = MarkdownReportGenerator()
        markdown = generator.generate(analysis_run, results)

        assert "HEALTH Findings" in markdown
        assert "CONFIG Findings" in markdown


class TestJSONReportGenerator:
    """Test suite for JSONReportGenerator."""

    def test_generate_json_report(self, sample_analysis_run):
        """Test generating JSON report."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_analysis_run)

        assert isinstance(report, dict)
        assert "deployment_id" in report
        assert report["deployment_id"] == "test-deployment"

    def test_json_contains_all_fields(self, sample_analysis_run):
        """Test that JSON contains all expected fields."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_analysis_run)

        expected_fields = [
            "id",
            "deployment_id",
            "started_at",
            "status",
            "objectives_analyzed",
            "api_calls_used",
            "duration_seconds",
            "findings",
            "recommendations",
        ]

        for field in expected_fields:
            assert field in report

    def test_json_serializable(self, sample_analysis_run):
        """Test that report is JSON serializable."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_analysis_run)

        # Should be able to serialize to JSON string
        json_str = json.dumps(report, default=str)
        assert isinstance(json_str, str)

        # Should be able to deserialize
        parsed = json.loads(json_str)
        assert parsed["deployment_id"] == "test-deployment"

    def test_json_findings_structure(self, sample_analysis_run):
        """Test that findings are properly structured in JSON."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_analysis_run)

        assert "findings" in report
        assert isinstance(report["findings"], list)
        assert len(report["findings"]) == 1

        finding = report["findings"][0]
        assert "id" in finding
        assert "title" in finding
        assert "severity" in finding

    def test_json_recommendations_structure(self, sample_analysis_run):
        """Test that recommendations are properly structured in JSON."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_analysis_run)

        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)
        assert len(report["recommendations"]) == 1

        rec = report["recommendations"][0]
        assert "id" in rec
        assert "title" in rec
        assert "priority" in rec

    def test_json_metrics(self, sample_analysis_run):
        """Test that metrics are included in JSON."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_analysis_run)

        assert report["api_calls_used"] == 25
        assert report["duration_seconds"] == 10.5
        assert report["status"] == "completed"
