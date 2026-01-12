"""
API command group for running the backend server.
"""

import socket

import typer
import uvicorn
from rich.console import Console

console = Console()
app = typer.Typer(help="Run API server")


def find_free_port() -> int:
    """Find a free port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.bind(("", 0))
        connection.listen(1)
        return connection.getsockname()[1]


@app.command()
def serve(
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="Host to bind to",
    ),
    port: int = typer.Option(
        8080,
        "--port",
        help="Port to run on (0 for auto-assign)",
    ),
    reload: bool = typer.Option(
        True,
        "--reload",
        help="Enable auto-reload",
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Uvicorn log level",
    ),
):
    """
    Run the FastAPI backend server.
    """
    if port == 0:
        port = find_free_port()
        console.print(f"[cyan]Auto-selected port:[/cyan] {port}")

    console.print(f"[green]Starting API server[/green] on {host}:{port}")

    uvicorn.run(
        "cribl_hc.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
