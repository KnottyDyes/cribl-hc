"""
Config command for managing credentials and settings.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional

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


def _extract_from_paste(text: str) -> Dict[str, Optional[str]]:
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
    result: Dict[str, Optional[str]] = {"url": None, "token": None}

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

        if name in credentials and not typer.confirm(
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
            console.print("[dim]Option 1: Paste curl command[/dim]")
            console.print("[dim]Option 2: Enter URL and token separately[/dim]")
            console.print()

            choice = typer.prompt("Choose (1 or 2)", default="2")

            if choice == "1":
                console.print(
                    "[dim]Paste curl command line by line (press Enter after each line, then Ctrl+D when done):[/dim]"
                )
                lines = []
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    pass

                curl_input = "\n".join(lines)
            else:
                console.print("[dim]Enter deployment URL:[/dim]")
                url = typer.prompt("URL")

                console.print("[dim]Enter bearer token:[/dim]")
                token = typer.prompt("Token")

                curl_input = f"-H 'Authorization: Bearer {token}' {url}"
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled[/yellow]")
            raise typer.Exit(code=0)

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


pii_app = typer.Typer(help="Manage custom sensitive data patterns")


@pii_app.command("list")
def list_pii_patterns():
    """
    List all custom sensitive data patterns.

    Shows configured patterns with their details and status.

    Examples:

        cribl-hc config pii list
    """
    import yaml
    from pathlib import Path

    patterns_file = Path(__file__).parent.parent.parent / "rules" / "custom_pii_patterns.yaml"

    try:
        if not patterns_file.exists():
            console.print("[yellow]No custom PII patterns configured[/yellow]")
            console.print(f"[dim]Create patterns file at: {patterns_file}[/dim]")
            console.print("[dim]Or run 'cribl-hc config pii add' to create one[/dim]")
            return

        with open(patterns_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("custom_patterns"):
            console.print("[yellow]No custom PII patterns configured[/yellow]")
            return

        patterns = data["custom_patterns"]

        table = Table(title=f"Custom PII Patterns ({len(patterns)} configured)")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Category", style="magenta")
        table.add_column("Severity", style="red")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")

        for pattern in patterns:
            status = (
                "[green]Enabled[/green]" if pattern.get("enabled", True) else "[red]Disabled[/red]"
            )
            table.add_row(
                pattern["name"],
                pattern["category"],
                pattern["severity"].upper(),
                pattern["description"],
                status,
            )

        console.print(table)
        console.print(f"\n[dim]Configuration file: {patterns_file}[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to list PII patterns:[/red] {str(e)}")
        raise typer.Exit(code=1)


@pii_app.command("add")
def add_pii_pattern(
    name: str = typer.Option(..., "--name", "-n", help="Pattern name (unique identifier)"),
    pattern: str = typer.Option(..., "--pattern", "-p", help="Regular expression pattern"),
    description: str = typer.Option(..., "--description", "-d", help="Human-readable description"),
    severity: str = typer.Option(
        "medium", "--severity", "-s", help="Severity level (critical/high/medium/low/info)"
    ),
    category: str = typer.Option("custom", "--category", "-c", help="Pattern category"),
    remediation: str = typer.Option(..., "--remediation", "-r", help="Suggested remediation steps"),
):
    """
    Add a new custom sensitive data pattern.

    Examples:

        cribl-hc config pii add \\
            --name employee_id \\
            --pattern "\\bEMP\\d{6}\\b" \\
            --description "Employee ID in EMPXXXXXX format" \\
            --severity medium \\
            --category corporate \\
            --remediation "Mask employee IDs in production logs"

        cribl-hc config pii add -n ssn -p "\\b\\d{3}-\\d{2}-\\d{4}\\b" \\
            -d "Social Security Number" -s critical -c personal \\
            -r "Never log SSNs, use tokenization instead"
    """
    import yaml
    from pathlib import Path

    valid_severities = ["critical", "high", "medium", "low", "info"]
    if severity not in valid_severities:
        console.print(f"[red]✗ Invalid severity: {severity}[/red]")
        console.print(f"[cyan]Valid options: {', '.join(valid_severities)}[/cyan]")
        raise typer.Exit(code=1)

    patterns_file = Path(__file__).parent.parent.parent / "rules" / "custom_pii_patterns.yaml"

    try:
        data = {"custom_patterns": []}
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                existing_data = yaml.safe_load(f)
                if existing_data and "custom_patterns" in existing_data:
                    data = existing_data

        for existing in data["custom_patterns"]:
            if existing["name"] == name:
                console.print(f"[red]✗ Pattern with name '{name}' already exists[/red]")
                console.print(
                    "[dim]Use 'cribl-hc config pii edit' to modify existing patterns[/dim]"
                )
                raise typer.Exit(code=1)

        new_pattern = {
            "name": name,
            "pattern": pattern,
            "description": description,
            "severity": severity,
            "category": category,
            "remediation": remediation,
            "enabled": True,
        }

        data["custom_patterns"].append(new_pattern)

        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        with open(patterns_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓ Added custom PII pattern:[/green] {name}")
        console.print(f"[dim]Configuration saved to: {patterns_file}[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to add PII pattern:[/red] {str(e)}")
        raise typer.Exit(code=1)

    patterns_file = Path(__file__).parent.parent.parent / "rules" / "custom_pii_patterns.yaml"

    try:
        # Load existing patterns
        data = {"custom_patterns": []}
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                existing_data = yaml.safe_load(f)
                if existing_data and "custom_patterns" in existing_data:
                    data = existing_data

        # Check for duplicate names
        for existing in data["custom_patterns"]:
            if existing["name"] == name:
                console.print(f"[red]✗ Pattern with name '{name}' already exists[/red]")
                console.print(
                    "[dim]Use 'cribl-hc config pii edit' to modify existing patterns[/dim]"
                )
                raise typer.Exit(code=1)

        # Add new pattern
        new_pattern = {
            "name": name,
            "pattern": pattern,
            "description": description,
            "severity": severity,
            "category": category,
            "remediation": remediation,
            "enabled": True,
        }

        data["custom_patterns"].append(new_pattern)

        # Save updated file
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        with open(patterns_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓ Added custom PII pattern:[/green] {name}")
        console.print(f"[dim]Configuration saved to: {patterns_file}[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Failed to add PII pattern:[/red] {str(e)}")
        raise typer.Exit(code=1)


@pii_app.command("edit")
def edit_pii_pattern(
    name: str = typer.Argument(..., help="Pattern name to edit"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="New regex pattern"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="New severity level"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="New category"),
    remediation: Optional[str] = typer.Option(
        None, "--remediation", "-r", help="New remediation steps"
    ),
    enable: bool = typer.Option(None, "--enable/--disable", help="Enable or disable pattern"),
):
    """
    Edit an existing custom sensitive data pattern.

    Only specify the fields you want to change.

    Examples:

        cribl-hc config pii edit employee_id --severity high
        cribl-hc config pii edit ssn --disable
        cribl-hc config pii edit project_code --pattern "\\bPRJ-[A-Z]{3}-\\d{5}\\b"
    """
    import yaml
    from pathlib import Path

    patterns_file = Path(__file__).parent.parent.parent / "rules" / "custom_pii_patterns.yaml"

    try:
        if not patterns_file.exists():
            console.print("[red]✗ No PII patterns configuration file found[/red]")
            raise typer.Exit(code=1)

        with open(patterns_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("custom_patterns"):
            console.print("[red]✗ No PII patterns configured[/red]")
            raise typer.Exit(code=1)

        found = False
        for pattern_dict in data["custom_patterns"]:
            if isinstance(pattern_dict, dict) and pattern_dict.get("name") == name:
                if pattern is not None:
                    pattern_dict["pattern"] = pattern
                if description is not None:
                    pattern_dict["description"] = description
                if severity is not None:
                    valid_severities = ["critical", "high", "medium", "low", "info"]
                    if severity not in valid_severities:
                        console.print(f"[red]✗ Invalid severity: {severity}[/red]")
                        console.print(f"[cyan]Valid options: {', '.join(valid_severities)}[/cyan]")
                        raise typer.Exit(code=1)
                    pattern_dict["severity"] = severity
                if category is not None:
                    pattern_dict["category"] = category
                if remediation is not None:
                    pattern_dict["remediation"] = remediation
                if enable is not None:
                    pattern_dict["enabled"] = enable

                found = True
                break

        if not found:
            console.print(f"[red]✗ Pattern '{name}' not found[/red]")
            raise typer.Exit(code=1)

        with open(patterns_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓ Updated PII pattern:[/green] {name}")

    except Exception as e:
        console.print(f"[red]✗ Failed to edit PII pattern:[/red] {str(e)}")
        raise typer.Exit(code=1)

        with open(patterns_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("custom_patterns"):
            console.print("[red]✗ No PII patterns configured[/red]")
            raise typer.Exit(code=1)

        # Find and update pattern
        found = False
        for pattern_dict in data["custom_patterns"]:
            if isinstance(pattern_dict, dict) and pattern_dict.get("name") == name:
                if pattern is not None:
                    pattern_dict["pattern"] = pattern
                if description is not None:
                    pattern_dict["description"] = description
                if severity is not None:
                    valid_severities = ["critical", "high", "medium", "low", "info"]
                    if severity not in valid_severities:
                        console.print(f"[red]✗ Invalid severity: {severity}[/red]")
                        console.print(f"[cyan]Valid options: {', '.join(valid_severities)}[/cyan]")
                        raise typer.Exit(code=1)
                    pattern_dict["severity"] = severity
                if category is not None:
                    pattern_dict["category"] = category
                if remediation is not None:
                    pattern_dict["remediation"] = remediation
                if enable is not None:
                    pattern_dict["enabled"] = enable

                found = True
                break

        if not found:
            console.print(f"[red]✗ Pattern '{name}' not found[/red]")
            raise typer.Exit(code=1)

        # Save updated file
        with open(patterns_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓ Updated PII pattern:[/green] {name}")

    except Exception as e:
        console.print(f"[red]✗ Failed to edit PII pattern:[/red] {str(e)}")
        raise typer.Exit(code=1)


@pii_app.command("remove")
def remove_pii_pattern(
    name: str = typer.Argument(..., help="Pattern name to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Remove a custom sensitive data pattern.

    Examples:

        cribl-hc config pii remove employee_id
        cribl-hc config pii remove ssn --yes
    """
    import yaml
    from pathlib import Path

    patterns_file = Path(__file__).parent.parent.parent / "rules" / "custom_pii_patterns.yaml"

    try:
        if not patterns_file.exists():
            console.print("[red]✗ No PII patterns configuration file found[/red]")
            raise typer.Exit(code=1)

        with open(patterns_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("custom_patterns"):
            console.print("[red]✗ No PII patterns configured[/red]")
            raise typer.Exit(code=1)

        original_count = len(data["custom_patterns"])
        data["custom_patterns"] = [p for p in data["custom_patterns"] if p["name"] != name]

        if len(data["custom_patterns"]) == original_count:
            console.print(f"[red]✗ Pattern '{name}' not found[/red]")
            raise typer.Exit(code=1)

        if not yes:
            confirm = typer.confirm(f"Remove PII pattern '{name}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(code=0)

        with open(patterns_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓ Removed PII pattern:[/green] {name}")

    except Exception as e:
        console.print(f"[red]✗ Failed to remove PII pattern:[/red] {str(e)}")
        raise typer.Exit(code=1)

        with open(patterns_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("custom_patterns"):
            console.print("[red]✗ No PII patterns configured[/red]")
            raise typer.Exit(code=1)

        # Find and remove pattern
        original_count = len(data["custom_patterns"])
        data["custom_patterns"] = [p for p in data["custom_patterns"] if p["name"] != name]

        if len(data["custom_patterns"]) == original_count:
            console.print(f"[red]✗ Pattern '{name}' not found[/red]")
            raise typer.Exit(code=1)

        if not yes:
            confirm = typer.confirm(f"Remove PII pattern '{name}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(code=0)

        # Save updated file
        with open(patterns_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓ Removed PII pattern:[/green] {name}")

    except Exception as e:
        console.print(f"[red]✗ Failed to remove PII pattern:[/red] {str(e)}")
        raise typer.Exit(code=1)


@pii_app.command("validate")
def validate_pii_patterns():
    """
    Validate custom PII pattern configurations.

    Checks for syntax errors, invalid regex patterns, and missing required fields.

    Examples:

        cribl-hc config pii validate
    """
    import re
    import yaml
    from pathlib import Path

    patterns_file = Path(__file__).parent.parent.parent / "rules" / "custom_pii_patterns.yaml"

    try:
        if not patterns_file.exists():
            console.print("[yellow]No PII patterns configuration file found[/yellow]")
            return

        with open(patterns_file, "r") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("custom_patterns"):
            console.print("[yellow]No PII patterns configured[/yellow]")
            return

        patterns = data["custom_patterns"]
        errors = []
        warnings = []

        required_fields = ["name", "pattern", "description", "severity", "category", "remediation"]
        valid_severities = ["critical", "high", "medium", "low", "info"]

        for i, pattern in enumerate(patterns):
            for field in required_fields:
                if field not in pattern:
                    errors.append(
                        f"Pattern {i + 1} ('{pattern.get('name', 'unknown')}'): missing required field '{field}'"
                    )

            if "severity" in pattern and pattern["severity"] not in valid_severities:
                errors.append(
                    f"Pattern '{pattern.get('name', 'unknown')}': invalid severity '{pattern['severity']}'"
                )

            if "pattern" in pattern:
                try:
                    re.compile(pattern["pattern"])
                except re.error as e:
                    errors.append(
                        f"Pattern '{pattern.get('name', 'unknown')}': invalid regex '{pattern['pattern']}': {e}"
                    )

            name = pattern.get("name")
            if name:
                duplicates = [p for p in patterns if p.get("name") == name]
                if len(duplicates) > 1:
                    warnings.append(
                        f"Duplicate pattern name: '{name}' (appears {len(duplicates)} times)"
                    )

        if errors:
            console.print(f"[red]❌ Validation failed with {len(errors)} errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(code=1)

        if warnings:
            console.print(f"[yellow]⚠️  Validation passed with {len(warnings)} warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")

        console.print(f"[green]✅ All {len(patterns)} patterns validated successfully[/green]")

    except yaml.YAMLError as e:
        console.print(f"[red]❌ YAML syntax error in configuration file:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ Validation failed:[/red] {str(e)}")
        raise typer.Exit(code=1)

        if warnings:
            console.print(f"[yellow]⚠️  Validation passed with {len(warnings)} warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")

        console.print(f"[green]✅ All {len(patterns)} patterns validated successfully[/green]")

    except yaml.YAMLError as e:
        console.print(f"[red]❌ YAML syntax error in configuration file:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ Validation failed:[/red] {str(e)}")
        raise typer.Exit(code=1)


app.add_typer(pii_app, name="pii", help="Manage custom sensitive data patterns")
app.add_typer(branding_app, name="branding", help="Manage branding configuration")
