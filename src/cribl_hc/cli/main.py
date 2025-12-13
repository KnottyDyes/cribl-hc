"""
Main CLI entry point for cribl-hc.
"""

import typer
from rich.console import Console

from cribl_hc.cli import test_connection
from cribl_hc.cli.commands import analyze, config, list_analyzers


console = Console()
app = typer.Typer(
    name="cribl-hc",
    help="Cribl Stream Health Check Tool - Comprehensive deployment analysis and monitoring",
    add_completion=False,
)

# Register commands
app.add_typer(
    analyze.app,
    name="analyze",
    help="Run health check analysis",
)

app.add_typer(
    config.app,
    name="config",
    help="Manage credentials and configuration",
)

app.add_typer(
    test_connection.app,
    name="test-connection",
    help="Test connection to Cribl Stream API",
)

app.add_typer(
    list_analyzers.app,
    name="list",
    help="List available analyzers",
)


@app.command()
def version():
    """Show cribl-hc version information."""
    from cribl_hc import __version__

    console.print(f"[cyan]cribl-hc[/cyan] version [green]{__version__}[/green]")


def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
