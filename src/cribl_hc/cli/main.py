"""
Main CLI entry point for cribl-hc.
"""

import typer
from rich.console import Console

from cribl_hc.cli import test_connection


console = Console()
app = typer.Typer(
    name="cribl-hc",
    help="Cribl Stream Health Check Tool - Comprehensive deployment analysis and monitoring",
    add_completion=False,
)

# Register test-connection command
app.add_typer(
    test_connection.app,
    name="test-connection",
    help="Test connection to Cribl Stream API",
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
