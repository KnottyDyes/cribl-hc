"""
Unit tests for report generation.

Tests MarkdownReportGenerator and JSONReportGenerator including:
- Header and summary generation
- Findings section formatting
- Recommendations section formatting
- Appendix generation
- JSON report generation
- Edge cases and empty data handling
"""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4

from cribl_hc.core.report_generator import MarkdownReportGenerator, JSONReportGenerator
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate


@pytest.fixture
def sample_analysis_run():
    """Create a sample analysis run for testing."""
    now = datetime.utcnow()
    return AnalysisRun(
        id=str(uuid4()),
        deployment_id="test-deployment-123",
        started_at=now,
        completed_at=now + timedelta(seconds=45),
        status="completed",
        objectives_analyzed=["health", "config"],
        findings=[],
        recommendations=[],
        api_calls_used=25,
        duration_seconds=45.0,
        partial_completion=False
    )


@pytest.fixture
def sample_finding():
    """Create a sample finding."""
    return Finding(
        id="test-finding-1",
        title="High CPU Usage Detected",
        description="Worker nodes are experiencing elevated CPU usage above 90%",
        severity="high",
        category="health",
        confidence_level="high",
        affected_components=["worker-1", "worker-2"],
        estimated_impact="Performance degradation and potential data loss",
        remediation_steps=[
            "Scale up worker nodes",
            "Review pipeline configurations",
            "Enable CPU throttling"
        ],
        metadata={"threshold": 90, "current_max": 95.5}
    )


@pytest.fixture
def sample_recommendation():
    """Create a sample recommendation."""
    return Recommendation(
        id="test-rec-1",
        type="scaling",
        title="Scale Worker Capacity",
        description="Add additional worker nodes to distribute load",
        rationale="Current workers are consistently above 80% CPU utilization",
        priority="p1",
        category="performance",
        implementation_steps=[
            "Add 2 new worker nodes",
            "Configure load balancing",
            "Monitor CPU usage for 24 hours"
        ],
        implementation_effort="medium",
        impact_estimate=ImpactEstimate(
            time_to_implement="2-4 hours",
            risk_level="low",
            expected_benefit="Reduce CPU usage by 40%",
            performance_improvement="40% CPU reduction"
        ),
        documentation_links=[
            "https://docs.cribl.io/stream/scaling-workers"
        ]
    )


class TestMarkdownReportGeneratorBasics:
    """Test basic markdown report generation."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = MarkdownReportGenerator()
        assert generator is not None

    def test_generate_with_no_findings(self, sample_analysis_run):
        """Test report generation with no findings."""
        generator = MarkdownReportGenerator()
        results = {
            "health": AnalyzerResult(
                objective="health",
                success=True,
                findings=[],
                recommendations=[]
            )
        }

        report = generator.generate(sample_analysis_run, results)

        assert isinstance(report, str)
        assert "# Cribl Stream Health Check Report" in report
        assert sample_analysis_run.deployment_id in report
        assert "Executive Summary" in report

    def test_generate_with_findings(self, sample_analysis_run, sample_finding):
        """Test report generation with findings."""
        sample_analysis_run.findings = [sample_finding]

        generator = MarkdownReportGenerator()
        results = {
            "health": AnalyzerResult(
                objective="health",
                success=True,
                findings=[sample_finding],
                recommendations=[]
            )
        }

        report = generator.generate(sample_analysis_run, results)

        assert "HEALTH Findings" in report
        assert sample_finding.title in report
        assert sample_finding.description in report

    def test_generate_with_recommendations(self, sample_analysis_run, sample_recommendation):
        """Test report generation with recommendations."""
        sample_analysis_run.recommendations = [sample_recommendation]

        generator = MarkdownReportGenerator()
        results = {
            "health": AnalyzerResult(
                objective="health",
                success=True,
                findings=[],
                recommendations=[sample_recommendation]
            )
        }

        report = generator.generate(sample_analysis_run, results)

        assert "## Recommendations" in report
        assert sample_recommendation.title in report
        assert sample_recommendation.description in report


class TestMarkdownHeaderGeneration:
    """Test markdown header section."""

    def test_header_contains_deployment_id(self, sample_analysis_run):
        """Test header includes deployment ID."""
        generator = MarkdownReportGenerator()
        header = generator._generate_header(sample_analysis_run)

        assert sample_analysis_run.deployment_id in header
        assert "# Cribl Stream Health Check Report" in header

    def test_header_contains_timestamp(self, sample_analysis_run):
        """Test header includes formatted timestamp."""
        generator = MarkdownReportGenerator()
        header = generator._generate_header(sample_analysis_run)

        # Should contain date in YYYY-MM-DD format
        assert "Generated:" in header
        assert str(sample_analysis_run.started_at.year) in header

    def test_header_contains_status(self, sample_analysis_run):
        """Test header includes uppercase status."""
        generator = MarkdownReportGenerator()
        header = generator._generate_header(sample_analysis_run)

        assert "COMPLETED" in header
        assert "Status:" in header

    def test_header_contains_duration(self, sample_analysis_run):
        """Test header includes duration."""
        generator = MarkdownReportGenerator()
        header = generator._generate_header(sample_analysis_run)

        assert "Duration:" in header
        assert "45.00s" in header


class TestMarkdownSummaryGeneration:
    """Test markdown summary section."""

    def test_summary_with_no_findings(self, sample_analysis_run):
        """Test summary with zero findings."""
        generator = MarkdownReportGenerator()
        summary = generator._generate_summary(sample_analysis_run)

        assert "## Executive Summary" in summary
        assert "Total Findings | 0" in summary
        assert "Critical Issues | 0" in summary

    def test_summary_with_findings(self, sample_analysis_run):
        """Test summary counts findings correctly."""
        sample_analysis_run.findings = [
            Finding(id="1", title="Test", description="Test", severity="critical", category="test", confidence_level="high", affected_components=[], estimated_impact="High impact", remediation_steps=["Fix it"]),
            Finding(id="2", title="Test", description="Test", severity="high", category="test", confidence_level="high", affected_components=[], estimated_impact="Medium impact", remediation_steps=["Fix it"]),
            Finding(id="3", title="Test", description="Test", severity="high", category="test", confidence_level="high", affected_components=[], estimated_impact="Medium impact", remediation_steps=["Fix it"]),
            Finding(id="4", title="Test", description="Test", severity="medium", category="test", confidence_level="high", affected_components=[], estimated_impact="", remediation_steps=["Fix medium"]),
        ]

        generator = MarkdownReportGenerator()
        summary = generator._generate_summary(sample_analysis_run)

        assert "Total Findings | 4" in summary
        assert "Critical Issues | 1" in summary
        assert "High Severity | 2" in summary
        assert "Medium Severity | 1" in summary

    def test_summary_status_emoji(self, sample_analysis_run):
        """Test summary includes status emoji."""
        generator = MarkdownReportGenerator()

        # Completed status
        sample_analysis_run.status = "completed"
        summary = generator._generate_summary(sample_analysis_run)
        assert "✅" in summary

        # Partial status
        sample_analysis_run.status = "partial"
        summary = generator._generate_summary(sample_analysis_run)
        assert "⚠️" in summary

        # Failed status
        sample_analysis_run.status = "failed"
        summary = generator._generate_summary(sample_analysis_run)
        assert "❌" in summary

    def test_summary_includes_objectives(self, sample_analysis_run):
        """Test summary lists analyzed objectives."""
        generator = MarkdownReportGenerator()
        summary = generator._generate_summary(sample_analysis_run)

        assert "health" in summary
        assert "config" in summary
        assert "Objectives Analyzed" in summary

    def test_summary_includes_api_calls(self, sample_analysis_run):
        """Test summary shows API call usage."""
        generator = MarkdownReportGenerator()
        summary = generator._generate_summary(sample_analysis_run)

        assert "API Calls Used | 25/100" in summary


class TestMarkdownFindingsSection:
    """Test markdown findings section generation."""

    def test_findings_grouped_by_severity(self, sample_finding):
        """Test findings are grouped by severity."""
        generator = MarkdownReportGenerator()

        critical_finding = Finding(id="1", title="Critical", description="Critical issue", severity="critical", category="test", confidence_level="high", affected_components=[], estimated_impact="Critical impact", remediation_steps=["Fix critical"])
        low_finding = Finding(id="2", title="Low", description="Low issue", severity="low", category="test", confidence_level="high", affected_components=[], estimated_impact="", remediation_steps=[])

        result = AnalyzerResult(
            objective="health",
            success=True,
            findings=[low_finding, critical_finding, sample_finding],  # Out of order
            recommendations=[]
        )

        section = generator._generate_findings_section("health", result)

        # Should be ordered: critical, high, medium, low
        critical_pos = section.find("Critical")
        high_pos = section.find(sample_finding.title)
        low_pos = section.find("Low")

        assert critical_pos < high_pos < low_pos

    def test_findings_include_severity_emoji(self, sample_finding):
        """Test findings include severity emojis."""
        generator = MarkdownReportGenerator()
        result = AnalyzerResult(
            objective="health",
            success=True,
            findings=[sample_finding],
            recommendations=[]
        )

        section = generator._generate_findings_section("health", result)

        assert "🟠" in section  # High severity emoji

    def test_findings_include_components(self, sample_finding):
        """Test findings list affected components."""
        generator = MarkdownReportGenerator()
        result = AnalyzerResult(
            objective="health",
            success=True,
            findings=[sample_finding],
            recommendations=[]
        )

        section = generator._generate_findings_section("health", result)

        assert "worker-1" in section
        assert "worker-2" in section
        assert "Components:" in section

    def test_findings_include_impact(self, sample_finding):
        """Test findings include impact description."""
        generator = MarkdownReportGenerator()
        result = AnalyzerResult(
            objective="health",
            success=True,
            findings=[sample_finding],
            recommendations=[]
        )

        section = generator._generate_findings_section("health", result)

        assert "Impact:" in section
        assert sample_finding.estimated_impact in section

    def test_findings_include_metadata_as_json(self, sample_finding):
        """Test findings include metadata as JSON."""
        generator = MarkdownReportGenerator()
        result = AnalyzerResult(
            objective="health",
            success=True,
            findings=[sample_finding],
            recommendations=[]
        )

        section = generator._generate_findings_section("health", result)

        assert "Details:" in section
        assert "```json" in section
        assert "threshold" in section
        assert "90" in section


class TestMarkdownRecommendationsSection:
    """Test markdown recommendations section generation."""

    def test_recommendations_grouped_by_priority(self, sample_recommendation):
        """Test recommendations are grouped by priority."""
        generator = MarkdownReportGenerator()

        p0_rec = Recommendation(id="1", type="security", title="Critical", description="Critical fix", rationale="Security vulnerability", priority="p0", category="test", implementation_steps=["Step 1"], implementation_effort="high", impact_estimate=ImpactEstimate(performance_improvement="Critical fix"))
        p3_rec = Recommendation(id="2", type="optimization", title="Low Priority", description="Low priority", rationale="Nice to have", priority="p3", category="test", implementation_steps=["Step 1"], implementation_effort="low", impact_estimate=ImpactEstimate())

        recommendations = [p3_rec, sample_recommendation, p0_rec]  # Out of order

        section = generator._generate_recommendations_section(recommendations)

        # Should be ordered: p0, p1, p2, p3
        p0_pos = section.find("Critical")
        p1_pos = section.find(sample_recommendation.title)
        p3_pos = section.find("Low Priority")

        assert p0_pos < p1_pos < p3_pos

    def test_recommendations_include_priority_emoji(self, sample_recommendation):
        """Test recommendations include priority emojis."""
        generator = MarkdownReportGenerator()
        section = generator._generate_recommendations_section([sample_recommendation])

        assert "🟠" in section  # P1 priority emoji

    def test_recommendations_include_implementation_steps(self, sample_recommendation):
        """Test recommendations list implementation steps."""
        generator = MarkdownReportGenerator()
        section = generator._generate_recommendations_section([sample_recommendation])

        assert "Implementation Steps:" in section
        assert "Add 2 new worker nodes" in section
        assert "Configure load balancing" in section

    def test_recommendations_include_time_estimate(self, sample_recommendation):
        """Test recommendations include time estimate."""
        generator = MarkdownReportGenerator()
        section = generator._generate_recommendations_section([sample_recommendation])

        assert "Estimated Time:" in section
        assert "2-4 hours" in section

    def test_recommendations_include_documentation_links(self, sample_recommendation):
        """Test recommendations include documentation links."""
        generator = MarkdownReportGenerator()
        section = generator._generate_recommendations_section([sample_recommendation])

        assert "References:" in section
        assert "https://docs.cribl.io/stream/scaling-workers" in section


class TestMarkdownAppendixGeneration:
    """Test markdown appendix section."""

    def test_appendix_includes_analysis_id(self, sample_analysis_run):
        """Test appendix includes analysis ID."""
        generator = MarkdownReportGenerator()
        appendix = generator._generate_appendix(sample_analysis_run)

        assert "Analysis ID" in appendix
        assert sample_analysis_run.id in appendix

    def test_appendix_includes_timestamps(self, sample_analysis_run):
        """Test appendix includes start and completion timestamps."""
        generator = MarkdownReportGenerator()
        appendix = generator._generate_appendix(sample_analysis_run)

        assert "Started At" in appendix
        assert "Completed At" in appendix

    def test_appendix_includes_duration(self, sample_analysis_run):
        """Test appendix includes duration."""
        generator = MarkdownReportGenerator()
        appendix = generator._generate_appendix(sample_analysis_run)

        assert "Duration" in appendix
        assert "45.00 seconds" in appendix

    def test_appendix_includes_api_calls(self, sample_analysis_run):
        """Test appendix includes API call count."""
        generator = MarkdownReportGenerator()
        appendix = generator._generate_appendix(sample_analysis_run)

        assert "API Calls" in appendix
        assert "25/100" in appendix

    def test_appendix_handles_null_completion(self, sample_analysis_run):
        """Test appendix handles null completion time."""
        sample_analysis_run.completed_at = None
        generator = MarkdownReportGenerator()
        appendix = generator._generate_appendix(sample_analysis_run)

        assert "N/A" in appendix

    def test_appendix_includes_footer(self, sample_analysis_run):
        """Test appendix includes tool footer."""
        generator = MarkdownReportGenerator()
        appendix = generator._generate_appendix(sample_analysis_run)

        assert "cribl-hc" in appendix


class TestJSONReportGenerator:
    """Test JSON report generation."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = JSONReportGenerator()
        assert generator is not None

    def test_generate_returns_dict(self, sample_analysis_run):
        """Test generate returns dictionary."""
        generator = JSONReportGenerator()
        result = generator.generate(sample_analysis_run)

        assert isinstance(result, dict)

    def test_generated_dict_is_json_serializable(self, sample_analysis_run):
        """Test generated dict can be serialized to JSON."""
        generator = JSONReportGenerator()
        result = generator.generate(sample_analysis_run)

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

    def test_generated_json_includes_key_fields(self, sample_analysis_run):
        """Test generated JSON includes all key fields."""
        generator = JSONReportGenerator()
        result = generator.generate(sample_analysis_run)

        assert "id" in result
        assert "deployment_id" in result
        assert "status" in result
        assert "objectives_analyzed" in result
        assert "findings" in result
        assert "recommendations" in result

    def test_generated_json_preserves_data(self, sample_analysis_run, sample_finding):
        """Test generated JSON preserves original data."""
        sample_analysis_run.findings = [sample_finding]

        generator = JSONReportGenerator()
        result = generator.generate(sample_analysis_run)

        assert result["deployment_id"] == sample_analysis_run.deployment_id
        assert result["status"] == sample_analysis_run.status
        assert len(result["findings"]) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_results_dict(self, sample_analysis_run):
        """Test handling of empty results dictionary."""
        generator = MarkdownReportGenerator()
        report = generator.generate(sample_analysis_run, {})

        assert isinstance(report, str)
        assert "# Cribl Stream Health Check Report" in report

    def test_multiple_objectives_no_findings(self, sample_analysis_run):
        """Test multiple objectives with no findings."""
        generator = MarkdownReportGenerator()
        results = {
            "health": AnalyzerResult(objective="health", success=True, findings=[], recommendations=[]),
            "config": AnalyzerResult(objective="config", success=True, findings=[], recommendations=[]),
            "resource": AnalyzerResult(objective="resource", success=True, findings=[], recommendations=[]),
        }

        report = generator.generate(sample_analysis_run, results)

        assert isinstance(report, str)
        # Should not have findings sections
        assert "HEALTH Findings" not in report

    def test_findings_with_no_metadata(self):
        """Test findings without metadata field."""
        finding = Finding(
            id="test",
            title="Test Finding",
            description="Test",
            severity="high",
            category="test",
            confidence_level="high",
            affected_components=[],
            estimated_impact="Some impact",
            remediation_steps=["Fix it"]
        )

        generator = MarkdownReportGenerator()
        result = AnalyzerResult(
            objective="test",
            success=True,
            findings=[finding],
            recommendations=[]
        )

        section = generator._generate_findings_section("test", result)

        # Should not crash, metadata section is optional
        assert isinstance(section, str)

    def test_recommendations_with_minimal_data(self):
        """Test recommendations with minimal required fields."""
        rec = Recommendation(
            id="minimal",
            type="optimization",
            title="Minimal Recommendation",
            description="Test",
            rationale="Testing",
            priority="p2",
            category="test",
            implementation_steps=["Do something"],
            implementation_effort="low",
            impact_estimate=ImpactEstimate()
        )

        generator = MarkdownReportGenerator()
        section = generator._generate_recommendations_section([rec])

        assert "Minimal Recommendation" in section
        assert isinstance(section, str)
