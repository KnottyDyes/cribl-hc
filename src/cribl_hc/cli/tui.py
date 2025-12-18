"""
Terminal User Interface (TUI) for Cribl Health Check.

Provides an interactive dashboard for viewing analysis results with:
- Health score display
- Findings summary table
- Top recommendations
- Real-time updates
"""

from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation


class HealthCheckTUI:
    """
    Terminal User Interface for displaying health check results.

    Example:
        >>> tui = HealthCheckTUI()
        >>> tui.display(analysis_result)
    """

    def __init__(self):
        """Initialize the TUI."""
        self.console = Console()

    def display(self, result: AnalysisRun) -> None:
        """
        Display analysis results in an interactive dashboard.

        Args:
            result: AnalysisRun object with health check results
        """
        # Clear console
        self.console.clear()

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        # Split body into columns
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=3)
        )

        # Split left column
        layout["left"].split_column(
            Layout(name="health_score", size=8),
            Layout(name="summary")
        )

        # Build panels
        layout["header"].update(self._create_header(result))
        layout["health_score"].update(self._create_health_score_panel(result))
        layout["summary"].update(self._create_summary_panel(result))
        layout["right"].update(self._create_findings_table(result))
        layout["footer"].update(self._create_footer(result))

        # Render
        self.console.print(layout)

        # Show recommendations if any
        if result.recommendations:
            self.console.print("\n")
            self.console.print(self._create_recommendations_panel(result))

    def display_progress(self, message: str) -> Progress:
        """
        Display a progress spinner for long-running operations.

        Args:
            message: Progress message to display

        Returns:
            Progress object (use with context manager)
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        )

    def _create_header(self, result: AnalysisRun) -> Panel:
        """Create header panel with deployment info."""
        # deployment_id is a string, not a Deployment object
        deployment_name = result.deployment_id if result.deployment_id else "Unknown"
        timestamp = result.started_at.strftime("%Y-%m-%d %H:%M:%S UTC") if result.started_at else "N/A"

        header_text = Text()
        header_text.append("Cribl Health Check", style="bold cyan")
        header_text.append(f"\nDeployment: {deployment_name}", style="dim")
        header_text.append(f" | Analysis Time: {timestamp}", style="dim")

        return Panel(header_text, border_style="cyan")

    def _create_health_score_panel(self, result: AnalysisRun) -> Panel:
        """Create health score display panel."""
        if not result.health_score:
            return Panel("No health score available", title="Health Score", border_style="yellow")

        score = result.health_score.overall_score

        # Determine color based on score
        if score >= 90:
            color = "green"
            status = "Excellent"
        elif score >= 75:
            color = "yellow"
            status = "Good"
        elif score >= 50:
            color = "orange3"
            status = "Fair"
        else:
            color = "red"
            status = "Poor"

        # Create score display
        score_text = Text()
        score_text.append(f"{score:.1f}", style=f"bold {color}")
        score_text.append("/100\n", style="dim")
        score_text.append(f"{status}", style=f"{color}")

        return Panel(
            score_text,
            title="Overall Health Score",
            border_style=color,
            padding=(1, 2)
        )

    def _create_summary_panel(self, result: AnalysisRun) -> Panel:
        """Create summary statistics panel."""
        # Count findings by severity
        critical = len([f for f in result.findings if f.severity == "critical"])
        high = len([f for f in result.findings if f.severity == "high"])
        medium = len([f for f in result.findings if f.severity == "medium"])
        low = len([f for f in result.findings if f.severity == "low"])

        summary_text = Text()
        summary_text.append("Findings by Severity:\n\n", style="bold")

        if critical > 0:
            summary_text.append(f"  Critical: {critical}\n", style="bold red")
        else:
            summary_text.append(f"  Critical: {critical}\n", style="dim")

        if high > 0:
            summary_text.append(f"  High:     {high}\n", style="bold orange3")
        else:
            summary_text.append(f"  High:     {high}\n", style="dim")

        if medium > 0:
            summary_text.append(f"  Medium:   {medium}\n", style="yellow")
        else:
            summary_text.append(f"  Medium:   {medium}\n", style="dim")

        summary_text.append(f"  Low:      {low}\n", style="dim" if low == 0 else "blue")

        # Add recommendations count
        summary_text.append(f"\nRecommendations: {len(result.recommendations)}", style="cyan")

        return Panel(summary_text, title="Summary", border_style="blue")

    def _create_findings_table(self, result: AnalysisRun) -> Panel:
        """Create findings summary table."""
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            expand=True
        )

        table.add_column("Severity", width=10)
        table.add_column("Category", width=12)
        table.add_column("Title", ratio=2)
        table.add_column("Components", width=15)

        # Sort findings by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(
            result.findings,
            key=lambda f: severity_order.get(f.severity, 4)
        )

        # Limit to top 20 findings for display
        display_findings = sorted_findings[:20]

        for finding in display_findings:
            # Color code severity
            if finding.severity == "critical":
                severity_style = "bold red"
            elif finding.severity == "high":
                severity_style = "bold orange3"
            elif finding.severity == "medium":
                severity_style = "yellow"
            else:
                severity_style = "blue"

            # Truncate title if too long
            title = finding.title
            if len(title) > 60:
                title = title[:57] + "..."

            # Show first affected component
            component = finding.affected_components[0] if finding.affected_components else "N/A"
            if len(component) > 15:
                component = component[:12] + "..."

            table.add_row(
                Text(finding.severity.upper(), style=severity_style),
                finding.category,
                title,
                component
            )

        # Add footer if more findings exist
        if len(result.findings) > 20:
            table.caption = f"Showing 20 of {len(result.findings)} findings"

        return Panel(table, title="Findings", border_style="blue")

    def _create_recommendations_panel(self, result: AnalysisRun) -> Panel:
        """Create recommendations list panel."""
        # Sort by priority (p0 first, p1, p2, p3)
        priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
        sorted_recs = sorted(
            result.recommendations,
            key=lambda r: priority_order.get(r.priority, 4)
        )

        # Limit to top 5 recommendations
        top_recs = sorted_recs[:5]

        rec_text = Text()

        for i, rec in enumerate(top_recs, 1):
            # Color code by priority
            if rec.priority == "p0":
                priority_style = "bold red"
            elif rec.priority == "p1":
                priority_style = "bold yellow"
            elif rec.priority == "p2":
                priority_style = "cyan"
            else:
                priority_style = "blue"

            rec_text.append(f"{i}. ", style="bold cyan")
            rec_text.append(rec.title, style="bold")
            rec_text.append(f" (Priority: ", style="dim")
            rec_text.append(rec.priority.upper(), style=priority_style)
            rec_text.append(")\n", style="dim")
            rec_text.append(f"   {rec.description}\n", style="dim")

            if i < len(top_recs):
                rec_text.append("\n")

        # Add footer if more recommendations exist
        if len(result.recommendations) > 5:
            rec_text.append(f"\n... and {len(result.recommendations) - 5} more recommendations", style="dim italic")

        return Panel(rec_text, title="Top Recommendations", border_style="green")

    def _create_footer(self, result: AnalysisRun) -> Panel:
        """Create footer with navigation hints."""
        footer_text = Text()
        footer_text.append("Use ", style="dim")
        footer_text.append("--output", style="cyan")
        footer_text.append(" to save full report | ", style="dim")
        footer_text.append("--markdown", style="cyan")
        footer_text.append(" for human-readable format", style="dim")

        return Panel(footer_text, border_style="dim")

    def show_error(self, message: str, error: Optional[Exception] = None) -> None:
        """
        Display an error message.

        Args:
            message: Error message to display
            error: Optional exception object
        """
        error_text = Text()
        error_text.append("ERROR: ", style="bold red")
        error_text.append(message, style="red")

        if error:
            error_text.append(f"\n\nDetails: {str(error)}", style="dim red")

        panel = Panel(error_text, border_style="red", title="Error")
        self.console.print(panel)

    def show_success(self, message: str) -> None:
        """
        Display a success message.

        Args:
            message: Success message to display
        """
        success_text = Text(message, style="bold green")
        panel = Panel(success_text, border_style="green", title="Success")
        self.console.print(panel)

    def show_warning(self, message: str) -> None:
        """
        Display a warning message.

        Args:
            message: Warning message to display
        """
        warning_text = Text(message, style="bold yellow")
        panel = Panel(warning_text, border_style="yellow", title="Warning")
        self.console.print(panel)
