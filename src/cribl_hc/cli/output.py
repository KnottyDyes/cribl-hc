"""
Rich terminal output formatting for analysis results.
"""

from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.analysis import AnalysisRun


def display_analysis_results(
    results: Dict[str, AnalyzerResult],
    analysis_run: AnalysisRun,
    console: Console,
):
    """
    Display analysis results in rich terminal format.

    Args:
        results: Dictionary of analyzer results
        analysis_run: Analysis run model
        console: Rich console instance
    """
    # Display overall summary
    display_summary(analysis_run, console)

    # Display findings by objective
    for objective, result in results.items():
        if result.findings:
            display_findings(objective, result, console)

    # Display recommendations
    all_recommendations = []
    for result in results.values():
        all_recommendations.extend(result.recommendations)

    if all_recommendations:
        display_recommendations(all_recommendations, console)


def display_summary(analysis_run: AnalysisRun, console: Console):
    """Display overall analysis summary."""
    # Determine status color
    status_colors = {
        "completed": "green",
        "partial": "yellow",
        "failed": "red",
        "running": "blue",
    }
    status_color = status_colors.get(analysis_run.status, "white")

    # Create summary table
    table = Table(title="Analysis Summary", show_header=False, box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Status", f"[{status_color}]{analysis_run.status.upper()}[/{status_color}]")
    table.add_row("Objectives Analyzed", ", ".join(analysis_run.objectives_analyzed))
    table.add_row("Total Findings", str(len(analysis_run.findings)))
    table.add_row(
        "  Critical",
        f"[red]{len([f for f in analysis_run.findings if f.severity == 'critical'])}[/red]"
    )
    table.add_row(
        "  High",
        f"[orange1]{len([f for f in analysis_run.findings if f.severity == 'high'])}[/orange1]"
    )
    table.add_row(
        "  Medium",
        f"[yellow]{len([f for f in analysis_run.findings if f.severity == 'medium'])}[/yellow]"
    )
    table.add_row("Total Recommendations", str(len(analysis_run.recommendations)))
    table.add_row("API Calls Used", f"{analysis_run.api_calls_used}/100")

    if analysis_run.duration_seconds:
        table.add_row("Duration", f"{analysis_run.duration_seconds:.2f}s")

    console.print(table)
    console.print()


def display_findings(objective: str, result: AnalyzerResult, console: Console):
    """Display findings for a specific objective."""
    console.print(Panel(
        f"[bold]{objective.upper()} Findings[/bold]",
        style="cyan"
    ))

    # Group findings by severity
    severity_order = ["critical", "high", "medium", "low", "info"]
    severity_colors = {
        "critical": "red",
        "high": "orange1",
        "medium": "yellow",
        "low": "blue",
        "info": "green",
    }

    for severity in severity_order:
        severity_findings = [f for f in result.findings if f.severity == severity]

        if not severity_findings:
            continue

        color = severity_colors.get(severity, "white")
        console.print(f"\n[{color}]● {severity.upper()}[/{color}]")

        for finding in severity_findings:
            # Create finding tree
            tree = Tree(f"[bold]{finding.title}[/bold]")
            tree.add(f"[dim]{finding.description}[/dim]")

            if finding.affected_components:
                components_str = ", ".join(finding.affected_components)
                tree.add(f"Components: {components_str}")

            if finding.estimated_impact:
                tree.add(f"Impact: {finding.estimated_impact}")

            console.print(tree)

    console.print()


def display_recommendations(recommendations, console: Console):
    """Display recommendations."""
    console.print(Panel(
        "[bold]Recommendations[/bold]",
        style="green"
    ))

    # Group by priority
    priority_order = ["p0", "p1", "p2", "p3"]
    priority_colors = {
        "p0": "red",
        "p1": "orange1",
        "p2": "yellow",
        "p3": "blue",
    }

    for priority in priority_order:
        priority_recs = [r for r in recommendations if r.priority == priority]

        if not priority_recs:
            continue

        color = priority_colors.get(priority, "white")
        console.print(f"\n[{color}]▶ {priority.upper()} PRIORITY[/{color}]")

        for i, rec in enumerate(priority_recs, 1):
            console.print(f"\n{i}. [bold]{rec.title}[/bold]")
            console.print(f"   [dim]{rec.description}[/dim]")

            if rec.implementation_steps:
                console.print("   [cyan]Steps:[/cyan]")
                for step_num, step in enumerate(rec.implementation_steps, 1):
                    console.print(f"     {step_num}. {step}")

            # Display implementation effort
            if rec.implementation_effort:
                console.print(f"   [dim]Effort: {rec.implementation_effort}[/dim]")

            # Display impact estimate time
            if rec.impact_estimate and rec.impact_estimate.time_to_implement:
                console.print(f"   [dim]Estimated time: {rec.impact_estimate.time_to_implement}[/dim]")

            if rec.documentation_links:
                console.print(f"   [dim]References: {', '.join(rec.documentation_links)}[/dim]")

    console.print()


def display_health_score(score: float, console: Console):
    """
    Display health score with visual indicator.

    Args:
        score: Health score (0-100)
        console: Rich console instance
    """
    # Determine color based on score
    if score >= 90:
        color = "green"
        status = "HEALTHY"
    elif score >= 70:
        color = "yellow"
        status = "DEGRADED"
    elif score >= 50:
        color = "orange1"
        status = "UNHEALTHY"
    else:
        color = "red"
        status = "CRITICAL"

    # Create score display
    score_text = f"[bold {color}]{score:.1f}/100[/bold {color}] - {status}"

    console.print(Panel(
        score_text,
        title="Overall Health Score",
        style=color,
        padding=(1, 2),
    ))


def format_api_usage(used: int, total: int = 100) -> str:
    """
    Format API usage as colored string.

    Args:
        used: Number of API calls used
        total: Total API calls allowed

    Returns:
        Formatted string with color
    """
    percentage = (used / total) * 100

    if percentage >= 90:
        color = "red"
    elif percentage >= 75:
        color = "yellow"
    else:
        color = "green"

    return f"[{color}]{used}/{total}[/{color}] ({percentage:.0f}%)"
