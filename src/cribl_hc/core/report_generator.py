"""
Report generation for analysis results in multiple formats.
"""

from datetime import datetime
from typing import Dict

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.analysis import AnalysisRun


class MarkdownReportGenerator:
    """
    Generate Markdown reports from analysis results.

    Example:
        >>> generator = MarkdownReportGenerator()
        >>> markdown = generator.generate(analysis_run, results)
        >>> Path("report.md").write_text(markdown)
    """

    def generate(
        self,
        analysis_run: AnalysisRun,
        results: Dict[str, AnalyzerResult],
    ) -> str:
        """
        Generate Markdown report.

        Args:
            analysis_run: Analysis run model
            results: Dictionary of analyzer results

        Returns:
            Markdown formatted report string
        """
        sections = []

        # Title and metadata
        sections.append(self._generate_header(analysis_run))

        # Executive summary
        sections.append(self._generate_summary(analysis_run))

        # Findings by objective
        for objective, result in results.items():
            if result.findings:
                sections.append(self._generate_findings_section(objective, result))

        # Recommendations
        all_recommendations = []
        for result in results.values():
            all_recommendations.extend(result.recommendations)

        if all_recommendations:
            sections.append(self._generate_recommendations_section(all_recommendations))

        # Appendix
        sections.append(self._generate_appendix(analysis_run))

        return "\n\n".join(sections)

    def _generate_header(self, analysis_run: AnalysisRun) -> str:
        """Generate report header."""
        return f"""# Cribl Stream Health Check Report

**Deployment:** {analysis_run.deployment_id}
**Generated:** {analysis_run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Status:** {analysis_run.status.upper()}
**Duration:** {analysis_run.duration_seconds:.2f}s
"""

    def _generate_summary(self, analysis_run: AnalysisRun) -> str:
        """Generate executive summary."""
        critical_count = len([f for f in analysis_run.findings if f.severity == "critical"])
        high_count = len([f for f in analysis_run.findings if f.severity == "high"])
        medium_count = len([f for f in analysis_run.findings if f.severity == "medium"])

        status_emoji = {
            "completed": "✅",
            "partial": "⚠️",
            "failed": "❌",
        }
        emoji = status_emoji.get(analysis_run.status, "ℹ️")

        return f"""## Executive Summary

{emoji} **Analysis Status:** {analysis_run.status.upper()}

### Key Metrics

| Metric | Value |
|--------|-------|
| Objectives Analyzed | {", ".join(analysis_run.objectives_analyzed)} |
| Total Findings | {len(analysis_run.findings)} |
| Critical Issues | {critical_count} |
| High Severity | {high_count} |
| Medium Severity | {medium_count} |
| Recommendations | {len(analysis_run.recommendations)} |
| API Calls Used | {analysis_run.api_calls_used}/100 |
"""

    def _generate_findings_section(self, objective: str, result: AnalyzerResult) -> str:
        """Generate findings section for an objective."""
        lines = [f"## {objective.upper()} Findings\n"]

        # Group by severity
        severity_order = ["critical", "high", "medium", "low", "info"]
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️",
        }

        for severity in severity_order:
            severity_findings = [f for f in result.findings if f.severity == severity]

            if not severity_findings:
                continue

            emoji = severity_emoji.get(severity, "•")
            lines.append(f"### {emoji} {severity.upper()}\n")

            for finding in severity_findings:
                lines.append(f"#### {finding.title}\n")
                lines.append(f"{finding.description}\n")

                if finding.affected_components:
                    components_str = ", ".join(f"`{c}`" for c in finding.affected_components)
                    lines.append(f"**Components:** {components_str}\n")

                if finding.estimated_impact:
                    lines.append(f"**Impact:** {finding.estimated_impact}\n")

                if finding.metadata:
                    lines.append("**Details:**\n```json")
                    import json
                    lines.append(json.dumps(finding.metadata, indent=2))
                    lines.append("```\n")

        return "\n".join(lines)

    def _generate_recommendations_section(self, recommendations) -> str:
        """Generate recommendations section."""
        lines = ["## Recommendations\n"]

        # Group by priority
        priority_order = ["p0", "p1", "p2", "p3"]
        priority_labels = {
            "p0": "CRITICAL",
            "p1": "HIGH",
            "p2": "MEDIUM",
            "p3": "LOW",
        }
        priority_emoji = {
            "p0": "🔴",
            "p1": "🟠",
            "p2": "🟡",
            "p3": "🔵",
        }

        for priority in priority_order:
            priority_recs = [r for r in recommendations if r.priority == priority]

            if not priority_recs:
                continue

            emoji = priority_emoji.get(priority, "•")
            label = priority_labels.get(priority, priority.upper())
            lines.append(f"### {emoji} {label} Priority\n")

            for i, rec in enumerate(priority_recs, 1):
                lines.append(f"#### {i}. {rec.title}\n")
                lines.append(f"{rec.description}\n")

                if rec.implementation_steps:
                    lines.append("**Implementation Steps:**\n")
                    for step_num, step in enumerate(rec.implementation_steps, 1):
                        lines.append(f"{step_num}. {step}")
                    lines.append("")

                if rec.impact_estimate and rec.impact_estimate.time_to_implement:
                    lines.append(f"**Estimated Time:** {rec.impact_estimate.time_to_implement}\n")

                if rec.documentation_links:
                    lines.append("**References:**")
                    for ref in rec.documentation_links:
                        lines.append(f"- {ref}")
                    lines.append("")

        return "\n".join(lines)

    def _generate_appendix(self, analysis_run: AnalysisRun) -> str:
        """Generate appendix with metadata."""
        return f"""## Appendix

### Analysis Metadata

| Field | Value |
|-------|-------|
| Analysis ID | `{analysis_run.id}` |
| Started At | {analysis_run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")} |
| Completed At | {analysis_run.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if analysis_run.completed_at else "N/A"} |
| Duration | {analysis_run.duration_seconds:.2f} seconds |
| API Calls | {analysis_run.api_calls_used}/100 |
| Partial Completion | {"Yes" if analysis_run.partial_completion else "No"} |

---

*Generated by cribl-hc - Cribl Stream Health Check Tool*
"""


class JSONReportGenerator:
    """
    Generate JSON reports from analysis results.

    Example:
        >>> generator = JSONReportGenerator()
        >>> json_data = generator.generate(analysis_run)
    """

    def generate(self, analysis_run: AnalysisRun) -> dict:
        """
        Generate JSON report.

        Args:
            analysis_run: Analysis run model

        Returns:
            Dictionary suitable for JSON serialization
        """
        return analysis_run.model_dump(mode="json")
