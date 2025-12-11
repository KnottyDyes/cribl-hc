"""
Config command for managing credentials and settings.
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cribl_hc.utils.crypto import CredentialEncryptor, generate_master_key
from cribl_hc.utils.logger import get_logger


console = Console()
log = get_logger(__name__)

app = typer.Typer(help="Manage credentials and configuration")

# Default config directory
CONFIG_DIR = Path.home() / ".cribl-hc"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.enc"
KEY_FILE = CONFIG_DIR / ".key"


def ensure_config_dir():
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Set restrictive permissions
    CONFIG_DIR.chmod(0o700)


def get_or_create_key() -> bytes:
    """Get existing encryption key or create new one."""
    ensure_config_dir()

    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()

    # Generate new key
    key = generate_master_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)  # Restrictive permissions
    console.print(f"[green]✓ Created new encryption key[/green]")
    return key


def load_credentials() -> dict:
    """Load encrypted credentials."""
    if not CREDENTIALS_FILE.exists():
        return {}

    key = get_or_create_key()
    encryptor = CredentialEncryptor(master_key=key)

    encrypted_data = CREDENTIALS_FILE.read_bytes()
    decrypted_json = encryptor.decrypt(encrypted_data)

    return json.loads(decrypted_json)


def save_credentials(credentials: dict):
    """Save encrypted credentials."""
    ensure_config_dir()

    key = get_or_create_key()
    encryptor = CredentialEncryptor(master_key=key)

    json_data = json.dumps(credentials, indent=2)
    encrypted_data = encryptor.encrypt(json_data)

    CREDENTIALS_FILE.write_bytes(encrypted_data)
    CREDENTIALS_FILE.chmod(0o600)  # Restrictive permissions


@app.command("set")
def set_credential(
    name: str = typer.Argument(..., help="Deployment name/identifier"),
    url: str = typer.Option(..., "--url", "-u", help="Cribl Stream URL"),
    token: str = typer.Option(
        ...,
        "--token",
        "-t",
        help="Bearer token",
        prompt=True,
        hide_input=True,
    ),
):
    """
    Store credentials for a deployment.

    Credentials are encrypted and stored in ~/.cribl-hc/credentials.enc

    Examples:

        cribl-hc config set prod --url https://cribl.example.com --token TOKEN
        cribl-hc config set dev -u https://dev.cribl.local -t TOKEN
    """
    try:
        credentials = load_credentials()

        credentials[name] = {
            "url": url,
            "token": token,
        }

        save_credentials(credentials)

        console.print(f"[green]✓ Saved credentials for deployment:[/green] {name}")
        console.print(f"[dim]URL:[/dim] {url}")
        console.print(f"[dim]Storage:[/dim] {CREDENTIALS_FILE}")

    except Exception as e:
        console.print(f"[red]✗ Failed to save credentials:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command("get")
def get_credential(
    name: str = typer.Argument(..., help="Deployment name"),
):
    """
    Retrieve stored credentials for a deployment.

    Examples:

        cribl-hc config get prod
    """
    try:
        credentials = load_credentials()

        if name not in credentials:
            console.print(f"[red]✗ No credentials found for:[/red] {name}")
            console.print(f"[dim]Use 'cribl-hc config set {name}' to add credentials[/dim]")
            raise typer.Exit(code=1)

        cred = credentials[name]
        console.print(f"[cyan]Credentials for:[/cyan] {name}")
        console.print(f"[dim]URL:[/dim] {cred['url']}")
        console.print(f"[dim]Token:[/dim] {'*' * 40}")

    except Exception as e:
        console.print(f"[red]✗ Failed to retrieve credentials:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command("list")
def list_credentials():
    """
    List all stored deployments.

    Examples:

        cribl-hc config list
    """
    try:
        credentials = load_credentials()

        if not credentials:
            console.print("[yellow]No credentials stored[/yellow]")
            console.print("[dim]Use 'cribl-hc config set' to add credentials[/dim]")
            return

        table = Table(title="Stored Deployments")
        table.add_column("Name", style="cyan")
        table.add_column("URL")
        table.add_column("Token", style="dim")

        for name, cred in credentials.items():
            table.add_row(
                name,
                cred["url"],
                f"{'*' * 20}",
            )

        console.print(table)
        console.print(f"\n[dim]Storage location:[/dim] {CREDENTIALS_FILE}")

    except Exception as e:
        console.print(f"[red]✗ Failed to list credentials:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command("delete")
def delete_credential(
    name: str = typer.Argument(..., help="Deployment name"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """
    Delete stored credentials for a deployment.

    Examples:

        cribl-hc config delete prod
        cribl-hc config delete dev --yes
    """
    try:
        credentials = load_credentials()

        if name not in credentials:
            console.print(f"[red]✗ No credentials found for:[/red] {name}")
            raise typer.Exit(code=1)

        if not yes:
            confirm = typer.confirm(f"Delete credentials for '{name}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(code=0)

        del credentials[name]
        save_credentials(credentials)

        console.print(f"[green]✓ Deleted credentials for:[/green] {name}")

    except Exception as e:
        console.print(f"[red]✗ Failed to delete credentials:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command("export-key")
def export_key(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: display to stdout)",
    ),
):
    """
    Export encryption key (use with caution).

    WARNING: This exports the master encryption key used to protect
    your credentials. Store it securely.

    Examples:

        cribl-hc config export-key
        cribl-hc config export-key --output backup-key.txt
    """
    try:
        key = get_or_create_key()
        key_str = key.decode('utf-8')

        if output:
            output.write_text(key_str)
            output.chmod(0o600)
            console.print(f"[green]✓ Key exported to:[/green] {output}")
        else:
            console.print("[yellow]WARNING: Keep this key secure![/yellow]")
            console.print(f"\n{key_str}\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to export key:[/red] {str(e)}")
        raise typer.Exit(code=1)
