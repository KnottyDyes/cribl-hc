"""
Report generation for analysis results in multiple formats.
"""

import json
from typing import Any, Dict, Optional

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.branding import BrandingConfig, ThemeMode


class MarkdownReportGenerator:
    """
    Generate Markdown reports from analysis results.
    """

    def __init__(self, branding: Optional[BrandingConfig] = None):
        self.branding = branding or BrandingConfig.default()

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
            from collections import defaultdict

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
        provider_info = ""
        client_info = ""
        report_title = "Cribl Health Check Report"

        if self.branding.provider:
            logo_src = self.branding.provider.logo_url or self.branding.provider.logo_path
            if logo_src:
                provider_info += f"\n![{self.branding.provider.name}]({logo_src})"
                if self.branding.provider.tagline:
                    provider_info += f"\n*{self.branding.provider.tagline}*"
                provider_info += "\n"
            provider_info += f"\n**Prepared by:** {self.branding.provider.name}"
            if self.branding.provider.website:
                provider_info += (
                    f" ([{self.branding.provider.website}]({self.branding.provider.website}))"
                )

        if self.branding.client:
            client_info = f"\n**Prepared for:** {self.branding.client.name}"
            if self.branding.client.identifier:
                client_info += f" (ID: {self.branding.client.identifier})"
            if self.branding.client.report_title:
                report_title = self.branding.client.report_title

        return (
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
                if finding.metadata:
                    lines.append(
                        "**Details:**\n```json\n"
                        + json.dumps(finding.metadata, indent=2)
                        + "\n```\n"
                    )
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
        footer_text = "*Generated by cribl-hc*"
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


class HTMLReportGenerator:
    """Generate HTML reports with full branding support."""

    def __init__(
        self, branding: Optional[BrandingConfig] = None, theme_mode: ThemeMode = ThemeMode.LIGHT
    ):
        self.branding = branding or BrandingConfig.default()
        self.theme_mode = theme_mode
        self.colors = self.branding.get_active_theme(theme_mode)

    def generate(
        self, analysis_run: AnalysisRun, results: Optional[dict[str, AnalyzerResult]] = None
    ) -> str:
        findings_html = ""
        if results:
            findings_html = self._generate_findings_html(results)
        else:
            from collections import defaultdict

            findings_by_obj = defaultdict(list)
            for f in analysis_run.findings:
                findings_by_obj[f.source_analyzer or "general"].append(f)
            reconstructed_results = {
                obj: AnalyzerResult(objective=obj, findings=fnds)
                for obj, fnds in findings_by_obj.items()
            }
            findings_html = self._generate_findings_html(reconstructed_results)

        return (
            f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
            f"<title>{self._get_report_title()}</title><style>{self._generate_css()}</style></head>"
            f"<body>{self._generate_header_html(analysis_run)}"
            f"{self._generate_summary_html(analysis_run)}"
            f"{self._generate_version_info_html(analysis_run)}"
            f"{findings_html}{self._generate_recommendations_html(analysis_run)}"
            f"{self._generate_footer_html(analysis_run)}</body></html>"
        )

    def _get_report_title(self) -> str:
        if self.branding.client and self.branding.client.report_title:
            return self.branding.client.report_title
        return "Cribl Health Check Report"

    def _generate_css(self) -> str:
        c = self.colors
        return (
            f":root{{--primary:{c.primary};--bg:{c.background};--fg:{c.foreground};--border:{c.border};"
            f"--radius:{self.branding.theme.border_radius};}}body{{font-family:sans-serif;"
            f"background:var(--bg);color:var(--fg);padding:2rem;max-width:1200px;margin:0 auto;}}"
            f".header{{margin-bottom:2rem;}}.logo{{max-height:48px;display:block;margin-bottom:0.25rem;}}"
            f".provider-tagline{{font-size:0.875rem;font-style:italic;margin-bottom:2rem;}}"
            f".version-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem;}}"
            f".version-card{{background:rgba(0,0,0,0.05);padding:1rem;border-radius:var(--radius);}}"
            f".version-item{{display:flex;justify-content:space-between;border-bottom:1px solid var(--border);}}"
            f".badge{{padding:0.25rem;border-radius:10px;font-size:0.75rem;}}table{{width:100%;"
            f"border-collapse:collapse;}}th,td{{border-bottom:1px solid var(--border);padding:0.5rem;}}"
        )

    def _generate_header_html(self, analysis_run: AnalysisRun) -> str:
        provider_branding = ""
        if self.branding.provider:
            logo_src = self.branding.provider.logo_base64 or self.branding.provider.logo_url
            if logo_src:
                tagline = (
                    f"<div class='provider-tagline'>{self.branding.provider.tagline}</div>"
                    if self.branding.provider.tagline
                    else ""
                )
                provider_branding = f"<img src='{logo_src}' class='logo'>{tagline}"
        return (
            f"<div class='header'>{provider_branding}<h1>{self._get_report_title()}</h1>"
            f"<p>Deployment: {analysis_run.deployment_id} | Generated: {analysis_run.started_at}</p></div>"
        )

    def _generate_version_info_html(self, analysis_run: AnalysisRun) -> str:
        v = analysis_run.version_info
        if not v:
            return ""
        items = "".join(
            [
                f"<tr><td>{c.name}</td><td>{c.version}</td><td>{c.status}</td><td>{c.metadata.get('group', 'N/A')}</td></tr>"
                for c in v.component_versions[:10]
            ]
        )
        return (
            f"<section><h2>Inventory</h2><div class='version-grid'><div class='version-card'>"
            f"<h3>Versions</h3><p>Leader: {v.leader_version}</p></div></div>"
            f"<table><tr><th>Node</th><th>Version</th><th>Status</th><th>Group</th></tr>{items}</table></section>"
        )

    def _generate_summary_html(self, analysis_run: AnalysisRun) -> str:
        score = analysis_run.health_score.overall_score if analysis_run.health_score else "N/A"
        return f"<section><h2>Summary</h2><p>Score: {score}/100</p></section>"

    def _generate_findings_html(self, results: dict[str, AnalyzerResult]) -> str:
        html = ""
        for obj, res in results.items():
            f_html = ""
            for f in res.findings:
                wg = f" <small>(Group: {f.worker_group})</small>" if f.worker_group else ""
                f_html += f"<div><h4>{f.title}{wg}</h4><p>{f.description}</p></div>"
            html += f"<section><h2>{obj.upper()} Findings</h2>{f_html}</section>"
        return html

    def _generate_recommendations_html(self, analysis_run: AnalysisRun) -> str:
        return ""

    def _generate_footer_html(self, analysis_run: AnalysisRun) -> str:
        return "<footer><p>Generated by cribl-hc</p></footer>"
