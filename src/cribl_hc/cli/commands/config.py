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


def create_api_client_from_credentials(deployment_name: str):
    """
    Create a CriblAPIClient from stored credentials.

    Supports both authentication methods:
    - Bearer Token (auth_type: 'bearer')
    - OAuth Client Credentials (auth_type: 'oauth')

    Args:
        deployment_name: Name of the deployment in stored credentials

    Returns:
        CriblAPIClient instance configured with the appropriate auth method

    Raises:
        ValueError: If deployment not found or credentials invalid
    """
    from cribl_hc.core.api_client import CriblAPIClient

    credentials = load_credentials()

    if deployment_name not in credentials:
        raise ValueError(f"No credentials found for deployment: {deployment_name}")

    cred = credentials[deployment_name]
    url = cred["url"]
    auth_type = cred.get("auth_type", "bearer")  # Default to bearer for backward compatibility

    if auth_type == "oauth":
        # OAuth authentication
        client_id = cred.get("client_id")
        client_secret = cred.get("client_secret")

        if not client_id or not client_secret:
            raise ValueError(f"OAuth credentials incomplete for deployment: {deployment_name}")

        return CriblAPIClient(
            base_url=url,
            client_id=client_id,
            client_secret=client_secret,
        )
    else:
        # Bearer token authentication
        token = cred.get("token")

        if not token:
            raise ValueError(f"Bearer token missing for deployment: {deployment_name}")

        return CriblAPIClient(
            base_url=url,
            auth_token=token,
        )


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
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Bearer token (direct authentication)",
    ),
    client_id: Optional[str] = typer.Option(
        None,
        "--client-id",
        help="API Client ID (OAuth authentication)",
    ),
    client_secret: Optional[str] = typer.Option(
        None,
        "--client-secret",
        help="API Client Secret (OAuth authentication)",
    ),
):
    """
    Store credentials for a deployment.

    Supports two authentication methods:

    1. Bearer Token (direct):
       cribl-hc config set prod --url https://cribl.example.com --token YOUR_TOKEN

    2. API Key/Secret (OAuth):
       cribl-hc config set prod --url https://cribl.example.com \\
         --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

    Credentials are encrypted and stored in ~/.cribl-hc/credentials.enc

    Examples:

        # Using bearer token (found in API Reference menu)
        cribl-hc config set prod --url https://cribl.example.com --token TOKEN

        # Using API credentials (created in Settings → API Settings)
        cribl-hc config set prod --url https://main-myorg.cribl.cloud \\
          --client-id abc123 --client-secret xyz789
    """
    try:
        # Validate authentication method
        has_token = token is not None
        has_client_creds = client_id is not None and client_secret is not None

        if not has_token and not has_client_creds:
            console.print("[red]✗ Error: Must provide either --token OR both --client-id and --client-secret[/red]")
            console.print("\n[cyan]Choose one authentication method:[/cyan]")
            console.print("  1. Bearer Token: --token YOUR_TOKEN")
            console.print("  2. API Credentials: --client-id ID --client-secret SECRET")
            raise typer.Exit(code=1)

        if has_token and has_client_creds:
            console.print("[yellow]⚠ Warning: Both token and client credentials provided[/yellow]")
            console.print("[yellow]  Using bearer token (client credentials will be ignored)[/yellow]")

        credentials = load_credentials()

        # Store credentials based on authentication method
        if has_token:
            credentials[name] = {
                "url": url,
                "auth_type": "bearer",
                "token": token,
            }
            console.print(f"[green]✓ Saved credentials for deployment:[/green] {name}")
            console.print(f"[dim]URL:[/dim] {url}")
            console.print(f"[dim]Auth Type:[/dim] Bearer Token")
        else:
            credentials[name] = {
                "url": url,
                "auth_type": "oauth",
                "client_id": client_id,
                "client_secret": client_secret,
            }
            console.print(f"[green]✓ Saved credentials for deployment:[/green] {name}")
            console.print(f"[dim]URL:[/dim] {url}")
            console.print(f"[dim]Auth Type:[/dim] OAuth (Client Credentials)")
            console.print(f"[dim]Client ID:[/dim] {client_id}")

        save_credentials(credentials)
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

        auth_type = cred.get('auth_type', 'bearer')  # Default to bearer for backward compatibility
        console.print(f"[dim]Auth Type:[/dim] {auth_type.capitalize()}")

        if auth_type == 'oauth':
            console.print(f"[dim]Client ID:[/dim] {cred.get('client_id', 'N/A')}")
            console.print(f"[dim]Client Secret:[/dim] {'*' * 40}")
        else:
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
        table.add_column("Auth Type")
        table.add_column("Credential", style="dim")

        for name, cred in credentials.items():
            auth_type = cred.get('auth_type', 'bearer')
            if auth_type == 'oauth':
                cred_display = f"Client ID: {cred.get('client_id', 'N/A')}"
            else:
                cred_display = f"{'*' * 20}"

            table.add_row(
                name,
                cred["url"],
                auth_type.capitalize(),
                cred_display,
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
