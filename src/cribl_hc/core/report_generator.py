"""
Report generation for analysis results in multiple formats.
"""

import json
from datetime import datetime
from typing import Dict, Optional

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.branding import BrandingConfig, ThemeMode


class MarkdownReportGenerator:
    """
    Generate Markdown reports from analysis results.

    Example:
        >>> generator = MarkdownReportGenerator()
        >>> markdown = generator.generate(analysis_run, results)
        >>> Path("report.md").write_text(markdown)
    """

    def __init__(self, branding: Optional[BrandingConfig] = None):
        self.branding = branding or BrandingConfig.default()

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
        provider_name = ""
        client_name = ""
        report_title = "Cribl Stream Health Check Report"

        if self.branding.provider:
            provider_name = f"\n**Prepared by:** {self.branding.provider.name}"
        if self.branding.client:
            client_name = f"\n**Prepared for:** {self.branding.client.name}"
            if self.branding.client.report_title:
                report_title = self.branding.client.report_title

        return f"""# {report_title}

**Deployment:** {analysis_run.deployment_id}
**Generated:** {analysis_run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Status:** {analysis_run.status.upper()}
**Duration:** {analysis_run.duration_seconds:.2f}s{provider_name}{client_name}
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
        footer_text = "*Generated by cribl-hc - Cribl Stream Health Check Tool*"
        if self.branding.provider and self.branding.provider.footer_text:
            footer_text = self.branding.provider.footer_text
        elif self.branding.report.show_footer and self.branding.provider:
            footer_text = f"*Generated by {self.branding.provider.name}*"

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

{footer_text}
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


class HTMLReportGenerator:
    """Generate HTML reports with full branding support."""

    def __init__(
        self,
        branding: Optional[BrandingConfig] = None,
        theme_mode: ThemeMode = ThemeMode.LIGHT,
    ):
        self.branding = branding or BrandingConfig.default()
        self.theme_mode = theme_mode
        self.colors = self.branding.get_active_theme(theme_mode)

    def generate(
        self,
        analysis_run: AnalysisRun,
        results: Dict[str, AnalyzerResult],
    ) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._get_report_title()}</title>
    <style>
{self._generate_css()}
    </style>
</head>
<body>
    {self._generate_header_html(analysis_run)}
    {self._generate_summary_html(analysis_run)}
    {self._generate_findings_html(results)}
    {self._generate_recommendations_html(analysis_run)}
    {self._generate_footer_html(analysis_run)}
</body>
</html>"""

    def _get_report_title(self) -> str:
        if self.branding.client and self.branding.client.report_title:
            return self.branding.client.report_title
        return "Cribl Stream Health Check Report"

    def _generate_css(self) -> str:
        c = self.colors
        font_family = self.branding.theme.font_family or (
            "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        )
        border_radius = self.branding.theme.border_radius

        custom_css = self.branding.report.custom_css or ""

        return f"""
        :root {{
            --primary: {c.primary};
            --primary-hover: {c.primary_hover};
            --primary-fg: {c.primary_foreground};
            --secondary: {c.secondary};
            --accent: {c.accent};
            --bg: {c.background};
            --bg-secondary: {c.background_secondary};
            --bg-tertiary: {c.background_tertiary};
            --fg: {c.foreground};
            --fg-secondary: {c.foreground_secondary};
            --fg-muted: {c.foreground_muted};
            --border: {c.border};
            --severity-critical: {c.severity_critical};
            --severity-high: {c.severity_high};
            --severity-medium: {c.severity_medium};
            --severity-low: {c.severity_low};
            --severity-info: {c.severity_info};
            --success: {c.success};
            --warning: {c.warning};
            --error: {c.error};
            --radius: {border_radius};
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: {font_family};
            background: var(--bg);
            color: var(--fg);
            line-height: 1.6;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}

        h1, h2, h3, h4 {{ color: var(--fg); margin-bottom: 1rem; }}
        h1 {{ font-size: 2rem; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; }}
        h2 {{ font-size: 1.5rem; color: var(--primary); margin-top: 2rem; }}
        h3 {{ font-size: 1.25rem; margin-top: 1.5rem; }}

        .header {{ margin-bottom: 2rem; }}
        .header-meta {{ display: flex; gap: 2rem; flex-wrap: wrap; color: var(--fg-secondary); }}
        .header-meta span {{ display: flex; align-items: center; gap: 0.5rem; }}

        .logo {{ max-height: 48px; margin-bottom: 1rem; }}

        .card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }}

        .metric {{
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: var(--radius);
            text-align: center;
        }}

        .metric-value {{ font-size: 2rem; font-weight: bold; color: var(--primary); }}
        .metric-label {{ font-size: 0.875rem; color: var(--fg-muted); }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-critical {{ background: var(--severity-critical); color: white; }}
        .badge-high {{ background: var(--severity-high); color: white; }}
        .badge-medium {{ background: var(--severity-medium); color: black; }}
        .badge-low {{ background: var(--severity-low); color: white; }}
        .badge-info {{ background: var(--severity-info); color: white; }}

        .finding {{
            border-left: 4px solid var(--border);
            padding-left: 1rem;
            margin: 1rem 0;
        }}

        .finding-critical {{ border-left-color: var(--severity-critical); }}
        .finding-high {{ border-left-color: var(--severity-high); }}
        .finding-medium {{ border-left-color: var(--severity-medium); }}
        .finding-low {{ border-left-color: var(--severity-low); }}
        .finding-info {{ border-left-color: var(--severity-info); }}

        .finding-title {{ font-weight: 600; margin-bottom: 0.5rem; }}
        .finding-description {{ color: var(--fg-secondary); }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}

        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{ background: var(--bg-tertiary); font-weight: 600; }}

        .footer {{
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            color: var(--fg-muted);
            font-size: 0.875rem;
            text-align: center;
        }}

        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 6rem;
            color: rgba(0, 0, 0, 0.05);
            pointer-events: none;
            z-index: -1;
        }}

        {custom_css}
        """

    def _generate_header_html(self, analysis_run: AnalysisRun) -> str:
        logo_html = ""
        if self.branding.report.show_provider_logo and self.branding.provider:
            logo_path = self.branding.provider.logo_url or self.branding.provider.logo_path
            if logo_path:
                logo_html = (
                    f'<img src="{logo_path}" alt="{self.branding.provider.name}" class="logo">'
                )

        provider_info = ""
        if self.branding.provider:
            provider_info = f"<span>Prepared by: {self.branding.provider.name}</span>"

        client_info = ""
        if self.branding.client:
            client_info = f"<span>Prepared for: {self.branding.client.name}</span>"

        return f"""
    <div class="header">
        {logo_html}
        <h1>{self._get_report_title()}</h1>
        <div class="header-meta">
            <span>Deployment: <strong>{analysis_run.deployment_id}</strong></span>
            <span>Generated: {analysis_run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")}</span>
            <span>Status: <span class="badge badge-{analysis_run.status}">{analysis_run.status.upper()}</span></span>
            {provider_info}
            {client_info}
        </div>
    </div>
        """

    def _generate_summary_html(self, analysis_run: AnalysisRun) -> str:
        findings = analysis_run.findings
        critical = len([f for f in findings if f.severity == "critical"])
        high = len([f for f in findings if f.severity == "high"])
        medium = len([f for f in findings if f.severity == "medium"])
        low = len([f for f in findings if f.severity == "low"])

        return f"""
    <section>
        <h2>Executive Summary</h2>
        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-value">{len(findings)}</div>
                <div class="metric-label">Total Findings</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: var(--severity-critical)">{critical}</div>
                <div class="metric-label">Critical</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: var(--severity-high)">{high}</div>
                <div class="metric-label">High</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: var(--severity-medium)">{medium}</div>
                <div class="metric-label">Medium</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: var(--severity-low)">{low}</div>
                <div class="metric-label">Low</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(analysis_run.recommendations)}</div>
                <div class="metric-label">Recommendations</div>
            </div>
        </div>
    </section>
        """

    def _generate_findings_html(self, results: Dict[str, AnalyzerResult]) -> str:
        sections = []
        severity_order = ["critical", "high", "medium", "low", "info"]

        for objective, result in results.items():
            if not result.findings:
                continue

            findings_html = ""
            for severity in severity_order:
                for finding in [f for f in result.findings if f.severity == severity]:
                    findings_html += f"""
            <div class="finding finding-{severity}">
                <div class="finding-title">
                    <span class="badge badge-{severity}">{severity}</span>
                    {finding.title}
                </div>
                <div class="finding-description">{finding.description}</div>
            </div>
                    """

            sections.append(f"""
    <section>
        <h2>{objective.upper()} Findings</h2>
        {findings_html}
    </section>
            """)

        return "\n".join(sections)

    def _generate_recommendations_html(self, analysis_run: AnalysisRun) -> str:
        if not analysis_run.recommendations:
            return ""

        rows = ""
        for rec in analysis_run.recommendations:
            rows += f"""
            <tr>
                <td><span class="badge badge-{rec.priority}">{rec.priority.upper()}</span></td>
                <td><strong>{rec.title}</strong><br><small>{rec.description}</small></td>
                <td>{rec.type}</td>
            </tr>
            """

        return f"""
    <section>
        <h2>Recommendations</h2>
        <table>
            <thead>
                <tr>
                    <th>Priority</th>
                    <th>Recommendation</th>
                    <th>Category</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </section>
        """

    def _generate_footer_html(self, analysis_run: AnalysisRun) -> str:
        watermark_html = ""
        if self.branding.report.show_watermark and self.branding.report.watermark_text:
            watermark_html = f'<div class="watermark">{self.branding.report.watermark_text}</div>'

        footer_text = "Generated by cribl-hc - Cribl Stream Health Check Tool"
        if self.branding.provider and self.branding.provider.footer_text:
            footer_text = self.branding.provider.footer_text
        elif self.branding.report.show_footer and self.branding.provider:
            footer_text = f"Generated by {self.branding.provider.name}"

        contact_info = ""
        if self.branding.provider:
            if self.branding.provider.website:
                contact_info += f' | <a href="{self.branding.provider.website}">{self.branding.provider.website}</a>'
            if self.branding.provider.contact_email:
                contact_info += f' | <a href="mailto:{self.branding.provider.contact_email}">{self.branding.provider.contact_email}</a>'

        return f"""
    {watermark_html}
    <footer class="footer">
        <p>{footer_text}{contact_info}</p>
        <p>Analysis ID: {analysis_run.id} | Duration: {analysis_run.duration_seconds:.2f}s</p>
    </footer>
        """
