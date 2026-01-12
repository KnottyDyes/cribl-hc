"""
TUI Results Viewer - Displays grouped analysis findings in Textual.
Mimics the GUI's ResultsPage grouping and display logic.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.cli.results_grouper import (
    group_findings,
    get_severity_counts,
    get_worker_group_display_name,
)


def render_results_summary(analysis: AnalysisRun) -> None:
    """
    Render a summary of the analysis results.
    
    Displays:
    - Total findings count
    - Breakdown by severity
    - Health score (if available)
    
    Args:
        analysis: The completed analysis run
    """
    console = Console()
    
    counts = get_severity_counts(analysis.findings)
    total = len(analysis.findings)
    
    # Create summary table
    summary_table = Table(
        title="[bold cyan]Analysis Summary[/bold cyan]",
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    
    # Add summary rows
    summary_table.add_row("Total Findings", f"[bold]{total}[/bold]")
    summary_table.add_row("[bold red]Critical[/bold red]", str(counts['critical']))
    summary_table.add_row("[bold orange1]High[/bold orange1]", str(counts['high']))
    summary_table.add_row("[bold yellow]Medium[/bold yellow]", str(counts['medium']))
    summary_table.add_row("[bold cyan]Low[/bold cyan]", str(counts['low']))
    summary_table.add_row("[bold]Info[/bold]", str(counts['info']))
    
    if analysis.health_score:
        summary_table.add_row(
            "Health Score",
            f"[bold]{analysis.health_score.overall_score:.1f}%[/bold]"
        )
    
    console.print(summary_table)
    console.print()


def render_grouped_findings(analysis: AnalysisRun) -> None:
    """
    Render findings grouped by worker group and grouping ID.
    
    Structure:
    - Worker Group 1
      - Finding Group 1 (count badge if multiple)
        - Finding 1
        - Finding 2 (if grouped)
      - Finding Group 2
    - Worker Group 2
      - ...
    
    Args:
        analysis: The completed analysis run
    """
    console = Console()
    
    if not analysis.findings:
        console.print("[yellow]No findings to display[/yellow]")
        return
    
    grouped = group_findings(analysis.findings)
    current_worker_group = None
    
    for group in grouped:
        # Print worker group header if it changed
        if group.worker_group != current_worker_group:
            current_worker_group = group.worker_group
            group_name = get_worker_group_display_name(group.worker_group)
            console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
            console.print(f"[bold cyan]{group_name}[/bold cyan]")
            console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")
        
        # Render the finding group
        render_finding_group(console, group)


def render_finding_group(console: Console, group) -> None:
    """
    Render a single finding group.
    
    Shows:
    - Severity badge and title
    - Count badge if multiple similar findings
    - First finding's description and affected components
    - Remediation steps if available
    
    Args:
        console: Rich console
        group: GroupedFinding object
    """
    first = group.findings[0]
    
    # Build severity badge
    severity_colors = {
        'critical': 'red',
        'high': 'orange1',
        'medium': 'yellow',
        'low': 'cyan',
        'info': 'white',
    }
    severity_color = severity_colors.get(group.severity, 'white')
    severity_text = f"[bold {severity_color}]{group.severity.upper()}[/bold {severity_color}]"
    
    # Build category badge
    category_text = f"[bold blue]{first.category}[/bold blue]"
    
    # Build title with badges
    title_parts = [severity_text, category_text]
    
    # Add grouped badge if applicable
    if group.is_grouped:
        count_text = f"[bold magenta]{group.finding_count} instances[/bold magenta]"
        title_parts.append(count_text)
    
    badges = " • ".join(title_parts)
    
    console.print(f"\n{badges}")
    console.print(f"[bold]{group.group_title}[/bold]")
    console.print(f"[dim]{first.description.split('.')[0]}.[/dim]")
    
    # Show affected components
    if first.affected_components:
        all_components = []
        for finding in group.findings:
            all_components.extend(finding.affected_components)
        
        # Deduplicate while preserving order
        unique_components = list(dict.fromkeys(all_components))
        
        if len(unique_components) <= 5:
            components_str = ", ".join(unique_components)
        else:
            components_str = ", ".join(unique_components[:5]) + f" (+{len(unique_components) - 5} more)"
        
        console.print(f"[dim]Components: {components_str}[/dim]")
    
    # Show impact if available
    if first.estimated_impact:
        console.print(f"[yellow]Impact: {first.estimated_impact}[/yellow]")
    
    # Show first few remediation steps
    if first.remediation_steps:
        console.print("[cyan]Remediation:[/cyan]")
        for i, step in enumerate(first.remediation_steps[:3], 1):
            console.print(f"  {i}. {step}")
        if len(first.remediation_steps) > 3:
            console.print(f"  ... and {len(first.remediation_steps) - 3} more steps")


def display_analysis_results(analysis: AnalysisRun) -> None:
    """
    Display the complete analysis results with summary and grouped findings.
    
    Args:
        analysis: The completed analysis run
    """
    console = Console()
    
    # Print header
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Analysis Results[/bold cyan]")
    console.print("=" * 60 + "\n")
    
    # Print summary
    render_results_summary(analysis)
    
    # Print grouped findings
    render_grouped_findings(analysis)
    
    console.print("\n" + "=" * 60)
    console.print(f"[dim]Total findings: {len(analysis.findings)}[/dim]")
    console.print("=" * 60 + "\n")
