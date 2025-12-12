"""
CLI command for testing connection to Cribl API.
"""

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cribl_hc.core.api_client import CriblAPIClient, ConnectionTestResult


console = Console()
app = typer.Typer(help="Test connection to Cribl Stream API")


def format_connection_result(result: ConnectionTestResult) -> None:
    """
    Format and display connection test result with rich styling.

    Args:
        result: ConnectionTestResult to display
    """
    if result.success:
        # Success - show green panel with details
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", "✓ Connected")
        table.add_row("Cribl Version", result.cribl_version or "Unknown")
        table.add_row(
            "Response Time", f"{result.response_time_ms:.0f}ms" if result.response_time_ms else "N/A"
        )
        table.add_row("API URL", result.api_url)

        panel = Panel(
            table,
            title="[bold green]Connection Test: SUCCESS[/bold green]",
            border_style="green",
        )
        console.print(panel)

    else:
        # Failure - show red panel with error details
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="red")

        table.add_row("Status", "✗ Failed")
        table.add_row("Message", result.message)
        if result.response_time_ms:
            table.add_row("Response Time", f"{result.response_time_ms:.0f}ms")
        table.add_row("API URL", result.api_url)
        if result.error:
            table.add_row("Error Details", result.error)

        panel = Panel(
            table,
            title="[bold red]Connection Test: FAILED[/bold red]",
            border_style="red",
        )
        console.print(panel)


async def _test_connection_async(
    url: str,
    token: str,
    timeout: float = 30.0,
) -> ConnectionTestResult:
    """
    Async helper to test connection.

    Args:
        url: Cribl leader URL
        token: Bearer authentication token
        timeout: Request timeout in seconds

    Returns:
        ConnectionTestResult
    """
    async with CriblAPIClient(url, token, timeout=timeout) as client:
        return await client.test_connection()


@app.command()
def test(
    deployment: Optional[str] = typer.Option(
        None,
        "--deployment",
        "-p",
        help="Use stored credentials for this deployment (from 'cribl-hc config set')",
    ),
    url: Optional[str] = typer.Option(
        None,
        "--url",
        "-u",
        help="Cribl leader URL (e.g., https://cribl.example.com)",
        envvar="CRIBL_URL",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Bearer authentication token",
        envvar="CRIBL_TOKEN",
        hide_input=True,
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Request timeout in seconds",
    ),
) -> None:
    """
    Test connection to Cribl Stream API.

    This command verifies that:
    - The Cribl leader URL is reachable
    - The authentication token is valid
    - The API is responding correctly
    - Cribl version can be detected

    Examples:

        # Using stored credentials
        cribl-hc test-connection test --deployment prod

        # Using explicit URL and token
        cribl-hc test-connection test --url https://cribl.example.com --token YOUR_TOKEN

        # Using environment variables
        export CRIBL_URL=https://cribl.example.com
        export CRIBL_TOKEN=your_token
        cribl-hc test-connection test
    """
    # Load credentials from stored profile if deployment specified
    if deployment:
        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
            if deployment not in credentials:
                console.print(f"[red]✗ No credentials found for deployment:[/red] {deployment}")
                console.print(f"[dim]Use 'cribl-hc config set {deployment}' to add credentials[/dim]")
                console.print(f"[dim]Or use 'cribl-hc config list' to see available deployments[/dim]")
                sys.exit(1)

            cred = credentials[deployment]
            url = cred.get("url")
            token = cred.get("token")

            console.print(f"[cyan]Using stored credentials for:[/cyan] {deployment}")
            console.print(f"[dim]URL:[/dim] {url}\n")

        except SystemExit:
            raise
        except Exception as e:
            console.print(f"[red]✗ Failed to load credentials:[/red] {str(e)}")
            sys.exit(1)

    # Validate that we have URL and token from some source
    if not url or not token:
        console.print("[red]✗ Missing required credentials[/red]")
        console.print("\n[yellow]You must provide credentials in one of three ways:[/yellow]\n")
        console.print("1. [cyan]Stored credentials:[/cyan]")
        console.print("   cribl-hc config set prod --url URL --token TOKEN")
        console.print("   cribl-hc test-connection test --deployment prod\n")
        console.print("2. [cyan]Command-line options:[/cyan]")
        console.print("   cribl-hc test-connection test --url URL --token TOKEN\n")
        console.print("3. [cyan]Environment variables:[/cyan]")
        console.print("   export CRIBL_URL=https://cribl.example.com")
        console.print("   export CRIBL_TOKEN=your_token")
        console.print("   cribl-hc test-connection test\n")
        sys.exit(1)

    console.print("\n[cyan]Testing connection to Cribl API...[/cyan]\n")

    # Run async connection test
    result = asyncio.run(_test_connection_async(url, token, timeout))

    # Display formatted result
    format_connection_result(result)

    # Exit with appropriate code
    if result.success:
        console.print("\n[green]Connection test passed! You can now run health checks.[/green]\n")
        sys.exit(0)
    else:
        console.print("\n[red]Connection test failed. Please verify your URL and token.[/red]\n")
        sys.exit(1)


def run_connection_test(
    url: str,
    token: str,
    timeout: float = 30.0,
    show_output: bool = True,
) -> ConnectionTestResult:
    """
    Programmatic interface for testing connection (for use in other modules).

    Args:
        url: Cribl leader URL
        token: Bearer token
        timeout: Request timeout in seconds
        show_output: Whether to display formatted output (default: True)

    Returns:
        ConnectionTestResult

    Example:
        >>> result = run_connection_test(
        ...     "https://cribl.example.com",
        ...     "my-token",
        ... )
        >>> if result.success:
        ...     print(f"Connected to {result.cribl_version}")
    """
    result = asyncio.run(_test_connection_async(url, token, timeout))

    if show_output:
        format_connection_result(result)

    return result


if __name__ == "__main__":
    app()
