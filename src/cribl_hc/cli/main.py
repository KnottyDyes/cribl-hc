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
def tui(
    legacy: bool = typer.Option(
        False,
        "--legacy",
        help="Use legacy simple TUI instead of modern interface"
    )
):
    """
    Launch interactive Terminal User Interface.

    Provides modern navigable interface for:
    - Managing deployment credentials
    - Running health check analyses
    - Viewing analysis results
    - Real-time status updates

    Use --legacy for the simple prompt-based interface.
    """
    try:
        if legacy:
            # Use legacy simple TUI
            from cribl_hc.cli.unified_tui import UnifiedTUI
            unified = UnifiedTUI()
            unified.run()
        else:
            # Use modern Textual-based TUI (default)
            from cribl_hc.cli.modern_tui import run_modern_tui
            run_modern_tui()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")


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
