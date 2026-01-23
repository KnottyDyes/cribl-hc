"""
Report generation for analysis results in multiple formats.
With True Zero Tech (TZT) branding support.
"""

import json
from collections import defaultdict
from typing import Optional

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.branding import BrandingConfig, ThemeMode

# TZT Brand Colors
TZT_ORANGE = "#F26522"
TZT_ORANGE_DARK = "#EB4805"
TZT_DARK = "#231F20"
TZT_WHITE = "#FFFFFF"
TZT_GRAY_DARK = "#58595B"
TZT_GRAY_LIGHT = "#828282"
TZT_GREEN = "#6CAF3D"
TZT_RED = "#721923"

SEVERITY_COLORS = {
    "critical": TZT_RED,
    "high": TZT_ORANGE,
    "medium": "#F59E0B",
    "low": "#024B83",
    "info": TZT_GRAY_DARK,
}


def get_tzt_logo_base64() -> str:
    """Get the TZT logo as a base64 data URI."""
    from pathlib import Path

    assets_dir = Path(__file__).parent.parent / "assets"
    logo_b64_path = assets_dir / "tzt-logo-base64.txt"
    if logo_b64_path.exists():
        b64_data = logo_b64_path.read_text().strip()
        return f"data:image/png;base64,{b64_data}"
    return ""


class MarkdownReportGenerator:
    """Generate Markdown reports from analysis results with TZT branding."""

    def __init__(self, branding: Optional[BrandingConfig] = None):
        self.branding = branding or BrandingConfig.default()
        self.logo_base64 = get_tzt_logo_base64()

    def generate(
        self,
        analysis_run: AnalysisRun,
        results: Optional[dict[str, AnalyzerResult]] = None,
    ) -> str:
        sections = []
        sections.append(self._generate_header(analysis_run))
        sections.append(self._generate_version_info_md(analysis_run))
        sections.append(self._generate_summary(analysis_run))

        if results:
            for objective, result in results.items():
                if result.findings:
                    sections.append(self._generate_findings_section(objective, result))
        else:
            findings_by_obj = defaultdict(list)
            for f in analysis_run.findings:
                findings_by_obj[f.source_analyzer or "general"].append(f)

            for objective, findings in findings_by_obj.items():
                dummy_result = AnalyzerResult(objective=objective, findings=findings)
                sections.append(self._generate_findings_section(objective, dummy_result))

        all_recommendations = analysis_run.recommendations
        if not all_recommendations and results:
            all_recommendations = []
            for result in results.values():
                all_recommendations.extend(result.recommendations)

        if all_recommendations:
            sections.append(self._generate_recommendations_section(all_recommendations))

        sections.append(self._generate_appendix(analysis_run))
        return "\n\n".join(sections)

    def _generate_header(self, analysis_run: AnalysisRun) -> str:
        logo_md = ""
        if self.logo_base64:
            logo_md = f"![True Zero Tech]({self.logo_base64})\n\n"

        report_title = "Cribl Health Check Report"
        provider_info = "\n**Prepared by:** True Zero Tech"
        client_info = ""

        if self.branding.provider:
            if self.branding.provider.name:
                provider_info = f"\n**Prepared by:** {self.branding.provider.name}"
            if self.branding.provider.website:
                provider_info += (
                    f" | [{self.branding.provider.website}]({self.branding.provider.website})"
                )

        if self.branding.client:
            client_info = f"\n**Prepared for:** {self.branding.client.name}"
            if self.branding.client.identifier:
                client_info += f" (ID: {self.branding.client.identifier})"
            if self.branding.client.report_title:
                report_title = self.branding.client.report_title

        return (
            f"{logo_md}"
            f"# {report_title}\n\n"
            f"**Deployment:** {analysis_run.deployment_id}\n"
            f"**Generated:** {analysis_run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"**Status:** {analysis_run.status.upper()}\n"
            f"**Duration:** {analysis_run.duration_seconds or 0:.2f}s"
            f"{provider_info}{client_info}"
        )

    def _generate_version_info_md(self, analysis_run: AnalysisRun) -> str:
        v = analysis_run.version_info
        if not v or (not v.leader_version and not v.product_versions and not v.component_versions):
            return ""
        lines = ["## Deployment Inventory\n"]
        lines.append(f"- **Leader Version:** {v.leader_version or 'Unknown'}")
        lines.append(f"- **Product Type:** {v.product_type.upper() if v.product_type else 'N/A'}")
        lines.append(f"- **Total Nodes:** {len(v.component_versions)}")
        if v.product_versions:
            lines.append("\n### Product Variants")
            for name, version in v.product_versions.items():
                lines.append(f"- **{name.title()}:** {version}")
        if v.component_versions:
            lines.append("\n### Node Versions (Top 10)")
            lines.append("| Node ID | Version | Status | Group |")
            lines.append("|---------|---------|--------|-------|")
            for comp in v.component_versions[:10]:
                group = comp.metadata.get("group", "default")
                lines.append(f"| {comp.name} | {comp.version} | {comp.status} | {group} |")
        return "\n".join(lines)

    def _generate_summary(self, analysis_run: AnalysisRun) -> str:
        critical_count = len([f for f in analysis_run.findings if f.severity == "critical"])
        high_count = len([f for f in analysis_run.findings if f.severity == "high"])
        medium_count = len([f for f in analysis_run.findings if f.severity == "medium"])
        status_emoji = {"completed": "✅", "partial": "⚠️", "failed": "❌"}
        emoji = status_emoji.get(analysis_run.status, "ℹ️")
        return (
            f"## Executive Summary\n\n"
            f"{emoji} **Analysis Status:** {analysis_run.status.upper()}\n\n"
            f"### Key Metrics\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| Objectives Analyzed | {', '.join(analysis_run.objectives_analyzed)} |\n"
            f"| Total Findings | {len(analysis_run.findings)} |\n"
            f"| Critical Issues | {critical_count} |\n"
            f"| High Severity | {high_count} |\n"
            f"| Medium Severity | {medium_count} |\n"
            f"| Recommendations | {len(analysis_run.recommendations)} |\n"
            f"| API Calls Used | {analysis_run.api_calls_used}/100 |"
        )

    def _generate_findings_section(self, objective: str, result: AnalyzerResult) -> str:
        lines = [f"## {objective.upper()} Findings\n"]
        severity_order = ["critical", "high", "medium", "low", "info"]
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "ℹ️"}
        for severity in severity_order:
            severity_findings = [f for f in result.findings if f.severity == severity]
            if not severity_findings:
                continue
            lines.append(f"### {severity_emoji.get(severity, '•')} {severity.upper()}\n")
            for finding in severity_findings:
                wg_context = f" **(Group: {finding.worker_group})**" if finding.worker_group else ""
                lines.append(f"#### {finding.title}{wg_context}\n")
                lines.append(f"{finding.description}\n")
                if finding.affected_components:
                    lines.append(
                        f"**Components:** {', '.join(f'`{c}`' for c in finding.affected_components)}\n"
                    )
                if finding.estimated_impact:
                    lines.append(f"**Impact:** {finding.estimated_impact}\n")
                if finding.remediation_steps:
                    lines.append("**Remediation:**\n")
                    for step in finding.remediation_steps:
                        lines.append(f"- {step}")
                    lines.append("")
        return "\n".join(lines)

    def _generate_recommendations_section(self, recommendations) -> str:
        lines = ["## Recommendations\n"]
        priority_order = ["p0", "p1", "p2", "p3"]
        priority_emoji = {"p0": "🔴", "p1": "🟠", "p2": "🟡", "p3": "🔵"}
        for priority in priority_order:
            priority_recs = [r for r in recommendations if r.priority == priority]
            if not priority_recs:
                continue
            lines.append(f"### {priority_emoji.get(priority, '•')} {priority.upper()} Priority\n")
            for i, rec in enumerate(priority_recs, 1):
                lines.append(f"#### {i}. {rec.title}\n")
                lines.append(f"{rec.description}\n")
                if rec.implementation_steps:
                    lines.append("**Implementation Steps:**\n")
                    for step_num, step in enumerate(rec.implementation_steps, 1):
                        lines.append(f"{step_num}. {step}")
                    lines.append("")
        return "\n".join(lines)

    def _generate_appendix(self, analysis_run: AnalysisRun) -> str:
        footer_text = "*Report generated by True Zero Tech using cribl-hc*"
        if self.branding.provider and self.branding.provider.footer_text:
            footer_text = self.branding.provider.footer_text
        return (
            f"## Appendix\n\n### Analysis Metadata\n\n"
            f"| Field | Value |\n"
            f"|-------|-------|\n"
            f"| Analysis ID | `{analysis_run.id}` |\n"
            f"| Started At | {analysis_run.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')} |\n"
            f"| Completed At | {analysis_run.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if analysis_run.completed_at else 'N/A'} |\n"
            f"| Duration | {analysis_run.duration_seconds or 0:.2f}s |\n\n"
            f"---\n\n{footer_text}"
        )


class JSONReportGenerator:
    def generate(self, analysis_run: AnalysisRun) -> dict:
        return analysis_run.model_dump(mode="json")


class PDFReportGenerator:
    """Generate PDF reports from HTML with TZT branding using WeasyPrint."""

    def __init__(
        self, branding: Optional[BrandingConfig] = None, theme_mode: ThemeMode = ThemeMode.LIGHT
    ):
        self.html_generator = HTMLReportGenerator(branding=branding, theme_mode=theme_mode)

    def generate(
        self, analysis_run: AnalysisRun, results: Optional[dict[str, AnalyzerResult]] = None
    ) -> bytes:
        try:
            from weasyprint import HTML
        except ImportError as e:
            raise ImportError(
                "weasyprint is required for PDF generation. "
                "Install with: pip install cribl-health-check[web]"
            ) from e

        html_content = self.html_generator.generate(analysis_run, results)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes


class HTMLReportGenerator:
    """Generate professional HTML reports with TZT branding."""

    def __init__(
        self, branding: Optional[BrandingConfig] = None, theme_mode: ThemeMode = ThemeMode.LIGHT
    ):
        self.branding = branding or BrandingConfig.default()
        self.theme_mode = theme_mode
        self.logo_base64 = get_tzt_logo_base64()

    def generate(
        self, analysis_run: AnalysisRun, results: Optional[dict[str, AnalyzerResult]] = None
    ) -> str:
        findings_html = ""
        if results:
            findings_html = self._generate_findings_html(results)
        else:
            findings_by_obj = defaultdict(list)
            for f in analysis_run.findings:
                findings_by_obj[f.source_analyzer or "general"].append(f)
            reconstructed_results = {
                obj: AnalyzerResult(objective=obj, findings=fnds)
                for obj, fnds in findings_by_obj.items()
            }
            findings_html = self._generate_findings_html(reconstructed_results)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cribl Health Check Report</title>
    <style>
{self._generate_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header_html(analysis_run)}
        {self._generate_executive_summary_html(analysis_run)}
        {self._generate_version_info_html(analysis_run)}
        {findings_html}
        {self._generate_recommendations_html(analysis_run)}
        {self._generate_footer_html(analysis_run)}
    </div>
</body>
</html>"""

    def _generate_css(self) -> str:
        return f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Times New Roman', Times, serif;
            font-size: 12pt;
            line-height: 1.5;
            color: {TZT_DARK};
            background: {TZT_WHITE};
        }}
        .container {{
            max-width: 8.5in;
            margin: 0 auto;
            padding: 1in;
        }}
        
        /* Header */
        .header {{
            border-bottom: 3px solid {TZT_ORANGE};
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }}
        .header-content {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .logo {{
            height: 52px;
            width: auto;
        }}
        .header-info {{
            text-align: right;
            color: {TZT_GRAY_DARK};
            font-size: 10pt;
        }}
        .report-title {{
            font-size: 24pt;
            font-weight: bold;
            color: {TZT_DARK};
            margin-top: 1rem;
        }}
        .report-subtitle {{
            font-size: 14pt;
            color: {TZT_GRAY_LIGHT};
            margin-top: 0.25rem;
        }}
        
        /* Executive Summary */
        .executive-summary {{
            background: linear-gradient(135deg, {TZT_ORANGE}10, {TZT_ORANGE}05);
            border-left: 4px solid {TZT_ORANGE};
            padding: 1.5rem;
            margin: 2rem 0;
            border-radius: 0 8px 8px 0;
        }}
        .summary-title {{
            font-size: 16pt;
            font-weight: bold;
            color: {TZT_ORANGE};
            margin-bottom: 1rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-top: 1rem;
        }}
        .metric-card {{
            background: {TZT_WHITE};
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 28pt;
            font-weight: bold;
            color: {TZT_DARK};
        }}
        .metric-value.critical {{
            color: {TZT_RED};
        }}
        .metric-value.warning {{
            color: {TZT_ORANGE};
        }}
        .metric-value.success {{
            color: {TZT_GREEN};
        }}
        .metric-label {{
            font-size: 10pt;
            color: {TZT_GRAY_DARK};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        /* Health Score */
        .health-score {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .score-circle {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24pt;
            font-weight: bold;
            color: {TZT_WHITE};
        }}
        .score-circle.healthy {{
            background: {TZT_GREEN};
        }}
        .score-circle.warning {{
            background: {TZT_ORANGE};
        }}
        .score-circle.critical {{
            background: {TZT_RED};
        }}
        
        /* Sections */
        h2 {{
            font-size: 16pt;
            color: {TZT_ORANGE};
            border-bottom: 2px solid {TZT_ORANGE};
            padding-bottom: 0.5rem;
            margin: 2rem 0 1rem 0;
        }}
        h3 {{
            font-size: 14pt;
            color: {TZT_DARK};
            margin: 1.5rem 0 0.75rem 0;
        }}
        h4 {{
            font-size: 12pt;
            color: {TZT_GRAY_DARK};
            margin: 1rem 0 0.5rem 0;
        }}
        
        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 11pt;
        }}
        th {{
            background: {TZT_ORANGE};
            color: {TZT_WHITE};
            padding: 0.75rem;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        tr:nth-child(even) {{
            background: #f9fafb;
        }}
        tr:hover {{
            background: {TZT_ORANGE}10;
        }}
        
        /* Findings */
        .finding-card {{
            background: {TZT_WHITE};
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            border-left: 4px solid {TZT_GRAY_DARK};
        }}
        .finding-card.critical {{
            border-left-color: {TZT_RED};
            background: {TZT_RED}08;
        }}
        .finding-card.high {{
            border-left-color: {TZT_ORANGE};
            background: {TZT_ORANGE}08;
        }}
        .finding-card.medium {{
            border-left-color: #F59E0B;
            background: #F59E0B08;
        }}
        .finding-card.low {{
            border-left-color: #024B83;
            background: #024B8308;
        }}
        .finding-title {{
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 0.5rem;
        }}
        .finding-description {{
            color: {TZT_GRAY_DARK};
            margin-bottom: 0.5rem;
        }}
        .finding-meta {{
            font-size: 10pt;
            color: {TZT_GRAY_LIGHT};
        }}
        .severity-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 10pt;
            font-weight: bold;
            text-transform: uppercase;
            color: {TZT_WHITE};
        }}
        .severity-badge.critical {{
            background: {TZT_RED};
        }}
        .severity-badge.high {{
            background: {TZT_ORANGE};
        }}
        .severity-badge.medium {{
            background: #F59E0B;
        }}
        .severity-badge.low {{
            background: #024B83;
        }}
        .severity-badge.info {{
            background: {TZT_GRAY_DARK};
        }}
        
        /* Remediation Steps */
        .remediation {{
            background: #f0fdf4;
            border: 1px solid {TZT_GREEN};
            border-radius: 4px;
            padding: 0.75rem;
            margin-top: 0.75rem;
        }}
        .remediation-title {{
            font-weight: bold;
            color: {TZT_GREEN};
            margin-bottom: 0.5rem;
        }}
        .remediation ol {{
            margin-left: 1.5rem;
            color: {TZT_DARK};
        }}
        
        /* Footer */
        .footer {{
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 2px solid {TZT_ORANGE};
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: {TZT_GRAY_LIGHT};
            font-size: 10pt;
        }}
        .footer-logo {{
            height: 32px;
        }}
        
        /* Print Styles */
        @media print {{
            body {{
                font-size: 10pt;
            }}
            .container {{
                padding: 0.5in;
            }}
            .finding-card {{
                break-inside: avoid;
            }}
            .metrics-grid {{
                grid-template-columns: repeat(4, 1fr);
            }}
        }}
        """

    def _generate_header_html(self, analysis_run: AnalysisRun) -> str:
        logo_html = ""
        if self.logo_base64:
            logo_html = f'<img src="{self.logo_base64}" alt="True Zero Tech" class="logo">'

        return f"""
        <header class="header">
            <div class="header-content">
                {logo_html}
                <div class="header-info">
                    <div><strong>Deployment:</strong> {analysis_run.deployment_id}</div>
                    <div><strong>Generated:</strong> {analysis_run.started_at.strftime("%B %d, %Y at %H:%M UTC")}</div>
                    <div><strong>Duration:</strong> {analysis_run.duration_seconds or 0:.1f}s</div>
                </div>
            </div>
            <h1 class="report-title">Cribl Health Check Report</h1>
            <div class="report-subtitle">Comprehensive Infrastructure Analysis</div>
        </header>
        """

    def _generate_executive_summary_html(self, analysis_run: AnalysisRun) -> str:
        score = analysis_run.health_score.overall_score if analysis_run.health_score else 0
        score_class = "healthy" if score >= 80 else "warning" if score >= 60 else "critical"

        critical_count = len([f for f in analysis_run.findings if f.severity == "critical"])
        high_count = len([f for f in analysis_run.findings if f.severity == "high"])
        medium_count = len([f for f in analysis_run.findings if f.severity == "medium"])
        total_findings = len(analysis_run.findings)

        critical_class = "critical" if critical_count > 0 else ""
        high_class = "warning" if high_count > 0 else ""

        return f"""
        <section class="executive-summary">
            <div class="summary-title">Executive Summary</div>
            <div class="health-score">
                <div class="score-circle {score_class}">{score:.0f}</div>
                <div>
                    <strong>Health Score</strong><br>
                    <span style="color: {TZT_GRAY_LIGHT}">Overall system health assessment</span>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_findings}</div>
                    <div class="metric-label">Total Findings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {critical_class}">{critical_count}</div>
                    <div class="metric-label">Critical</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {high_class}">{high_count}</div>
                    <div class="metric-label">High</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{medium_count}</div>
                    <div class="metric-label">Medium</div>
                </div>
            </div>
        </section>
        """

    def _generate_version_info_html(self, analysis_run: AnalysisRun) -> str:
        v = analysis_run.version_info
        if not v:
            return ""

        rows = ""
        for c in v.component_versions[:10]:
            group = c.metadata.get("group", "default")
            status_color = TZT_GREEN if c.status == "healthy" else TZT_ORANGE
            rows += f"""
            <tr>
                <td>{c.name}</td>
                <td>{c.version}</td>
                <td style="color: {status_color}">{c.status}</td>
                <td>{group}</td>
            </tr>
            """

        return f"""
        <section>
            <h2>Deployment Inventory</h2>
            <p><strong>Leader Version:</strong> {v.leader_version or "Unknown"} | 
               <strong>Product:</strong> {v.product_type.upper() if v.product_type else "N/A"} | 
               <strong>Total Nodes:</strong> {len(v.component_versions)}</p>
            <table>
                <thead>
                    <tr>
                        <th>Node ID</th>
                        <th>Version</th>
                        <th>Status</th>
                        <th>Worker Group</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </section>
        """

    def _generate_findings_html(self, results: dict[str, AnalyzerResult]) -> str:
        html = ""
        severity_order = ["critical", "high", "medium", "low", "info"]

        for obj, res in results.items():
            if not res.findings:
                continue

            findings_html = ""
            for severity in severity_order:
                severity_findings = [f for f in res.findings if f.severity == severity]
                for finding in severity_findings:
                    wg = (
                        f' <span class="finding-meta">(Worker Group: {finding.worker_group})</span>'
                        if finding.worker_group
                        else ""
                    )

                    remediation_html = ""
                    if finding.remediation_steps:
                        steps = "".join(f"<li>{step}</li>" for step in finding.remediation_steps)
                        remediation_html = f"""
                        <div class="remediation">
                            <div class="remediation-title">Remediation Steps</div>
                            <ol>{steps}</ol>
                        </div>
                        """

                    components = ""
                    if finding.affected_components:
                        comps = ", ".join(f"<code>{c}</code>" for c in finding.affected_components)
                        components = (
                            f'<div class="finding-meta"><strong>Affected:</strong> {comps}</div>'
                        )

                    impact = ""
                    if finding.estimated_impact:
                        impact = f'<div class="finding-meta"><strong>Impact:</strong> {finding.estimated_impact}</div>'

                    findings_html += f"""
                    <div class="finding-card {severity}">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div class="finding-title">{finding.title}{wg}</div>
                            <span class="severity-badge {severity}">{severity}</span>
                        </div>
                        <div class="finding-description">{finding.description}</div>
                        {components}
                        {impact}
                        {remediation_html}
                    </div>
                    """

            if findings_html:
                html += f"""
                <section>
                    <h2>{obj.replace("_", " ").title()} Findings</h2>
                    {findings_html}
                </section>
                """

        return html

    def _generate_recommendations_html(self, analysis_run: AnalysisRun) -> str:
        if not analysis_run.recommendations:
            return ""

        recs_html = ""
        for rec in analysis_run.recommendations:
            steps = ""
            if rec.implementation_steps:
                steps_list = "".join(f"<li>{step}</li>" for step in rec.implementation_steps)
                steps = f"<ol>{steps_list}</ol>"

            recs_html += f"""
            <div class="finding-card">
                <div class="finding-title">{rec.title}</div>
                <div class="finding-description">{rec.description}</div>
                {steps}
            </div>
            """

        return f"""
        <section>
            <h2>Recommendations</h2>
            {recs_html}
        </section>
        """

    def _generate_footer_html(self, analysis_run: AnalysisRun) -> str:
        logo_html = ""
        if self.logo_base64:
            logo_html = f'<img src="{self.logo_base64}" alt="True Zero Tech" class="footer-logo">'

        return f"""
        <footer class="footer">
            <div>
                <strong>Analysis ID:</strong> {analysis_run.id}<br>
                Generated by True Zero Tech Health Check Tool
            </div>
            {logo_html}
        </footer>
        """
