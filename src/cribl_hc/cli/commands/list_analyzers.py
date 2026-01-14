"""
List command for showing available analyzers.
"""

import typer
from rich.console import Console
from rich.table import Table

from cribl_hc.analyzers import get_analyzer, list_objectives

console = Console()
app = typer.Typer(help="List available analyzers")


def get_category_display_name(category: str) -> str:
    """
    Get a human-readable display name for an analyzer category.

    Args:
        category: The category identifier

    Returns:
        Formatted display name
    """
    category_names = {
        "core": "Core Health Analyzers",
        "security": "Security & Compliance",
        "performance": "Performance & Optimization",
        "data_quality": "Data Quality & Validation",
        "lake": "Cribl Lake",
        "search": "Cribl Search",
        "enterprise": "Enterprise Operations",
    }
    return category_names.get(category, f"Category: {category}")


@app.callback(invoke_without_command=True)
def list_analyzers(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information including permissions",
    ),
    group_by_category: bool = typer.Option(
        True,
        "--group-by-category/--no-group-by-category",
        help="Group analyzers by category (default: enabled)",
    ),
):
    """
    List all available analyzers.

    Shows analyzer names, API call estimates, and descriptions.
    Can optionally group analyzers by category for better organization.

    Examples:

        # Basic list grouped by category
        cribl-hc list

        # Flat list without grouping
        cribl-hc list --no-group-by-category

        # With detailed information
        cribl-hc list --verbose
    """
    objectives = list_objectives()

    if not objectives:
        console.print("[yellow]No analyzers registered[/yellow]")
        return

        if group_by_category:
            analyzers_by_category = {}
            for obj in objectives:
                analyzer = get_analyzer(obj)
                if analyzer is None:
                    continue
                category = getattr(analyzer, "category", "core")
                if category not in analyzers_by_category:
                    analyzers_by_category[category] = []
                analyzers_by_category[category].append((obj, analyzer))

        # Display grouped output
        total_analyzers = len(objectives)

        for category in sorted(analyzers_by_category.keys()):
            category_analyzers = analyzers_by_category[category]
            category_title = get_category_display_name(category)
            console.print(
                f"\n[bold blue]{category_title}[/bold blue] ({len(category_analyzers)} analyzers)"
            )

            # Create table for this category
            if verbose:
                table = Table(show_header=True, box=None, padding=(0, 2))
                table.add_column("Analyzer", style="cyan", no_wrap=True)
                table.add_column("API Calls", justify="right", style="magenta")
                table.add_column("Permissions", style="green")
                table.add_column("Description", style="white")
            else:
                table = Table(show_header=False, box=None, padding=(0, 2))
                table.add_column("Analyzer", style="cyan", no_wrap=True)
                table.add_column("API Calls", justify="right", style="magenta")
                table.add_column("Description", style="white")

            # Add rows for analyzers in this category
            for obj, analyzer in category_analyzers:
                if analyzer is None:
                    continue
                api_calls = str(analyzer.get_estimated_api_calls())

                # Get description based on analyzer type
                descriptions = {
                    "health": "Worker health & system status monitoring",
                    "config": "Configuration validation & best practices",
                    "resource": "CPU/memory/disk capacity planning",
                    "scripts": "Script inventory and validation signals",
                    "lake_storage_locations": "Lake storage location (BYOS) health",
                    "search_usage_groups": "Search usage group allocation hygiene",
                    "search_healthcheck": "Search healthcheck status",
                    "search_job_metrics": "Search job metrics summary",
                    "system_messages": "Core system message visibility",
                    "system_banners": "System banner visibility",
                    "system_certificates": "System certificate expiration",
                    "system_logs": "System log error summary",
                    "system_policies": "System policy inventory",
                    "system_settings": "System settings inventory",
                    "system_license_usage": "License usage and expiration",
                    "system_user_info": "User role hygiene",
                    "multi_deployment_comparison": "Compare health analysis across deployments",
                    "advanced_security": "Healthcare codes, financial data, compliance frameworks",
                }
                description = descriptions.get(obj, "Health check analysis")

                if verbose:
                    perms = ", ".join(analyzer.get_required_permissions()) if analyzer else ""
                    table.add_row(obj, api_calls, perms, description)
                else:
                    table.add_row(obj, api_calls, description)

            console.print(table)

        console.print(
            f"\n[dim]Total: {total_analyzers} analyzers across {len(analyzers_by_category)} categories[/dim]"
        )

    else:
        # Original flat list display
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
            if analyzer is None:
                continue
            api_calls = str(analyzer.get_estimated_api_calls())

            # Get description based on analyzer type
            descriptions = {
                "health": "Worker health & system status monitoring",
                "config": "Configuration validation & best practices",
                "resource": "CPU/memory/disk capacity planning",
                "scripts": "Script inventory and validation signals",
                "lake_storage_locations": "Lake storage location (BYOS) health",
                "search_usage_groups": "Search usage group allocation hygiene",
                "search_healthcheck": "Search healthcheck status",
                "search_job_metrics": "Search job metrics summary",
                "system_messages": "Core system message visibility",
                "system_banners": "System banner visibility",
                "system_certificates": "System certificate expiration",
                "system_logs": "System log error summary",
                "system_policies": "System policy inventory",
                "system_settings": "System settings inventory",
                "system_license_usage": "License usage and expiration",
                "system_user_info": "User role hygiene",
                "multi_deployment_comparison": "Compare health analysis across deployments",
                "advanced_security": "Healthcare codes, financial data, compliance frameworks",
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
        analyzer.get_estimated_api_calls()
        for obj in objectives
        if (analyzer := get_analyzer(obj)) is not None
    )
    console.print(f"\n[dim]Total API calls if all analyzers run: {total_calls}/100[/dim]")

    # Show usage example
    console.print("\n[dim]Usage examples:[/dim]")
    console.print("  [cyan]cribl-hc analyze run[/cyan]                    # Run all analyzers")
    console.print("  [cyan]cribl-hc analyze run -o health[/cyan]          # Run specific analyzer")
