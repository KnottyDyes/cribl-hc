"""
List command for showing available analyzers.
"""

import typer
from rich.console import Console
from rich.table import Table

from cribl_hc.analyzers import list_objectives, get_analyzer


console = Console()
app = typer.Typer(help="List available analyzers")


@app.callback(invoke_without_command=True)
def list_analyzers(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information including permissions",
    ),
):
    """
    List all available analyzers.

    Shows analyzer names, API call estimates, and descriptions.

    Examples:

        # Basic list
        cribl-hc list

        # With detailed information
        cribl-hc list --verbose
    """
    objectives = list_objectives()

    if not objectives:
        console.print("[yellow]No analyzers registered[/yellow]")
        return

    # Create table
    if verbose:
        table = Table(title=f"Available Analyzers ({len(objectives)} total)")
        table.add_column("Analyzer", style="cyan", no_wrap=True)
        table.add_column("API Calls", justify="right", style="magenta")
        table.add_column("Permissions", style="green")
        table.add_column("Description", style="white")
    else:
        table = Table(title=f"Available Analyzers ({len(objectives)} total)")
        table.add_column("Analyzer", style="cyan", no_wrap=True)
        table.add_column("API Calls", justify="right", style="magenta")
        table.add_column("Description", style="white")

    # Add rows for each analyzer
    for obj in objectives:
        analyzer = get_analyzer(obj)
        api_calls = str(analyzer.get_estimated_api_calls())

        # Get description based on analyzer type
        descriptions = {
            "health": "Worker health & system status monitoring",
            "config": "Configuration validation & best practices",
            "resource": "CPU/memory/disk capacity planning",
        }
        description = descriptions.get(obj, "Health check analysis")

        if verbose:
            perms = ", ".join(analyzer.get_required_permissions())
            table.add_row(obj, api_calls, perms, description)
        else:
            table.add_row(obj, api_calls, description)

    console.print(table)

    # Show total estimated API calls
    total_calls = sum(
        get_analyzer(obj).get_estimated_api_calls() for obj in objectives
    )
    console.print(f"\n[dim]Total API calls if all analyzers run: {total_calls}/100[/dim]")

    # Show usage example
    console.print("\n[dim]Usage examples:[/dim]")
    console.print(f"  [cyan]cribl-hc analyze run[/cyan]                    # Run all analyzers")
    console.print(
        f"  [cyan]cribl-hc analyze run -o health[/cyan]          # Run specific analyzer"
    )
