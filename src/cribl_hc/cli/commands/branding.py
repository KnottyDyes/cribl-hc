"""
Branding configuration management CLI commands.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cribl_hc.models.branding import BrandingConfig, ServiceProviderBranding, ClientBranding
from cribl_hc.core.branding_manager import get_branding_manager

console = Console()
app = typer.Typer(help="Manage branding configuration")


@app.command("set")
def set_branding(
    provider_name: Optional[str] = typer.Option(
        None,
        "--provider-name",
        "-p",
        help="Service provider company name",
    ),
    provider_logo: Optional[str] = typer.Option(
        None,
        "--provider-logo",
        help="Path to provider logo file",
    ),
    client_name: Optional[str] = typer.Option(
        None,
        "--client-name",
        "-c",
        help="Client company name",
    ),
    client_logo: Optional[str] = typer.Option(
        None,
        "--client-logo",
        help="Path to client logo file",
    ),
):
    """
    Set branding configuration for reports.

    Branding settings are stored in ~/.cribl-hc/branding.json

    Examples:

        # Set provider branding
        cribl-hc config branding set --provider-name "Acme Consulting" --provider-logo acme.png

        # Set client branding
        cribl-hc config branding set --client-name "Example Corp" --client-logo example.png

        # Set both provider and client
        cribl-hc config branding set -p "Acme Consulting" -c "Example Corp"
    """
    manager = get_branding_manager()
    current = manager.load()

    provider = current.provider
    if provider_name:
        provider_data = {"name": provider_name}
        if provider_logo:
            provider_data["logo_path"] = provider_logo
        provider = ServiceProviderBranding.model_construct(**provider_data)

    client = current.client
    if client_name:
        client_data = {"name": client_name}
        if client_logo:
            client_data["logo_path"] = client_logo
        client = ClientBranding.model_construct(**client_data)

    updated_config = BrandingConfig(
        provider=provider or current.provider,
        client=client or current.client,
        theme=current.theme,
        report=current.report,
    )

    manager.save(updated_config)

    console.print("[green]✓ Branding configuration saved[/green]")
    console.print(f"[dim]Location:[/dim] {manager.config_path}")


@app.command("show")
def show_branding():
    """
    Show current branding configuration.

    Examples:

        cribl-hc config branding show
    """
    manager = get_branding_manager()
    config = manager.load()

    table = Table(title="Current Branding Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Provider Name", config.provider.name if config.provider else "Not set")
    table.add_row("Provider Logo", config.provider.logo_path or "" if config.provider else "Not set")
    table.add_row("Client Name", config.client.name if config.client else "Not set")
    table.add_row("Client Logo", config.client.logo_path or "" if config.client else "Not set")

    console.print(table)
    console.print(f"\n[dim]Config file:[/dim] {manager.config_path}")


@app.command("reset")
def reset_branding():
    """
    Reset branding to default configuration.

    This removes all custom branding settings.

    Examples:

        cribl-hc config branding reset
    """
    typer.confirm("Are you sure you want to reset branding to defaults?", abort=True)

    manager = get_branding_manager()
    manager.reset()

    console.print("[green]✓ Branding configuration reset to defaults[/green]")
