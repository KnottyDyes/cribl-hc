"""
Config command for managing credentials and settings.
"""

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cribl_hc.cli.commands.branding import app as branding_app
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
    console.print("[green]✓ Created new encryption key[/green]")
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


def _extract_from_paste(text: str) -> dict[str, Optional[str]]:
    """
    Extract URL and token from pasted content.

    Handles:
    - curl commands: curl -H "Authorization: Bearer TOKEN" https://example.com/api/v1/...
    - Multi-line curl with backslash continuations
    - Raw URLs: https://example.com/api/v1/something
    - URLs with paths (strips to base URL)

    Args:
        text: Pasted content to parse

    Returns:
        Dictionary with 'url' and 'token' keys (values may be None)
    """
    result: dict[str, Optional[str]] = {"url": None, "token": None}

    cleaned_text = text.replace("\\\n", " ").replace("\n", " ")

    bearer_match = re.search(r"(?:Bearer\s+|bearer\s+)([^\s\"']+)", cleaned_text, re.IGNORECASE)
    if bearer_match:
        result["token"] = bearer_match.group(1).strip()

    url_match = re.search(r"https?://[^\s\"'<>]+", cleaned_text, re.IGNORECASE)
    if url_match:
        url = url_match.group(0).strip().strip("'\"")

        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            result["url"] = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            result["url"] = url

    return result


@app.command("add-from-curl")
def add_credential_from_curl(
    name: str = typer.Argument(
        ..., help="Deployment name/identifier (e.g., 'prod', 'dev', 'staging')"
    ),
):
    """
    Add credentials by pasting a curl command or API request.

    This command simplifies credential setup by extracting the URL and bearer token
    from a REST call. Useful for quickly setting up credentials from browser dev tools.

    How to use:
    1. Open Cribl Settings and copy a curl command from browser dev tools
    2. Run: cribl-hc config add-from-curl prod
    3. Paste the curl command when prompted
    4. Credentials are automatically extracted and saved

    Example curl command (from browser dev tools):
        curl -H "Authorization: Bearer sk_live_abc123xyz789" https://main-myorg.cribl.cloud/api/v1/system/status

    Examples:

        cribl-hc config add-from-curl prod
        cribl-hc config add-from-curl dev
    """
    try:
        credentials = load_credentials()

        if name in credentials:
            if not typer.confirm(
                f"Credentials for '{name}' already exist. Overwrite?", default=False
            ):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(code=0)

        console.print("\n[bold cyan]Add Credentials from REST Call[/bold cyan]")
        console.print(f"[dim]Deployment name:[/dim] {name}\n")

        console.print("[dim]Paste a curl command or API URL[/dim]")
        console.print(
            '[dim]Example:[/dim] curl -H "Authorization: Bearer TOKEN" https://cribl.example.com/api/...\n'
        )

        try:
            console.print(
                "[dim]Paste your curl command. To work around terminal input limits:[/dim]"
            )
            console.print("[dim]1. Save curl to a file: echo 'curl ...' > /tmp/curl.txt[/dim]")
            console.print("[dim]2. Then run: cribl-hc config set prod < /tmp/curl.txt[/dim]")
            console.print()

            lines = []
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    lines.append(line.rstrip("\n"))
                except (EOFError, KeyboardInterrupt):
                    break

            curl_input = "\n".join(lines)
        except KeyboardInterrupt:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)
        except Exception as e:
            console.print(f"[red]✗ Error reading input: {e}[/red]")
            raise typer.Exit(code=1)

        if not curl_input.strip():
            console.print("[red]✗ No input provided[/red]")
            raise typer.Exit(code=1)

        extracted = _extract_from_paste(curl_input)
        url = extracted["url"]
        token = extracted["token"]

        if not url:
            console.print("[red]✗ Could not extract URL from input[/red]")
            console.print("[dim]Make sure to paste a valid curl command or URL[/dim]")
            raise typer.Exit(code=1)

        if not token:
            console.print("[yellow]⚠ No token found in input[/yellow]")
            try:
                token = input("Enter bearer token manually: ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(code=0)

            if not token:
                console.print("[red]✗ Token cannot be empty[/red]")
                raise typer.Exit(code=1)

        console.print(f"\n[dim]Extracted URL:[/dim] {url}")
        console.print(f"[dim]Extracted Token:[/dim] {'*' * 40}")

        if not typer.confirm("\nSave these credentials?", default=True):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

        credentials[name] = {
            "url": url,
            "token": token,
        }

        save_credentials(credentials)

        console.print(f"\n[green]✓ Saved credentials for deployment:[/green] {name}")
        console.print(f"[dim]URL:[/dim] {url}")
        console.print(f"[dim]Use with:[/dim] cribl-hc analyze run --deployment {name}")

    except Exception as e:
        console.print(f"[red]✗ Failed to add credentials:[/red] {str(e)}")
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
    name: str = typer.Argument(None, help="Deployment name or '*' to delete all"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
):
    """
    Delete stored credentials for a deployment or all deployments.

    Use '*' as the deployment name to delete all credentials at once.
    Useful for cleaning up test credentials after testing.

    Examples:

        cribl-hc config delete prod
        cribl-hc config delete dev --yes
        cribl-hc config delete '*' --yes
        cribl-hc config delete '*'
    """
    try:
        credentials = load_credentials()

        if not credentials:
            console.print("[yellow]No credentials stored[/yellow]")
            raise typer.Exit(code=1)

        if name == "*":
            if not yes:
                console.print(
                    f"[yellow]⚠ This will delete ALL {len(credentials)} stored credentials:[/yellow]"
                )
                for cred_name in sorted(credentials.keys()):
                    console.print(f"  • {cred_name}")
                confirm = typer.confirm("\nDelete all credentials?", default=False)
                if not confirm:
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(code=0)

            credentials.clear()
            save_credentials(credentials)

            console.print(
                f"[green]✓ Deleted all credentials ({len(list(credentials.keys()))} removed)[/green]"
            )

        else:
            if name is None:
                console.print("[red]✗ Please specify a deployment name or '*' to delete all[/red]")
                raise typer.Exit(code=1)

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
        key_str = key.decode("utf-8")

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


app.add_typer(branding_app, name="branding", help="Manage branding configuration")
