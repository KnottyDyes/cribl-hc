"""
Interactive Terminal User Interface for configuration management.

Provides a menu-driven interface for managing Cribl deployment credentials:
- Add new deployments
- Edit existing deployments
- Delete deployments
- Test connections
- View deployment details
"""

import asyncio
import re
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)

COLOR_PRIMARY = "rgb(14,165,233)"
COLOR_SECONDARY = "rgb(56,189,248)"
COLOR_SUCCESS = "rgb(34,197,94)"
COLOR_WARNING = "rgb(234,179,8)"
COLOR_ERROR = "rgb(239,68,68)"
COLOR_BG = "rgb(15,23,42)"
COLOR_PANEL_BG = "rgb(30,41,59)"


class ConfigTUI:
    """
    Interactive TUI for configuration management.

    Example:
        >>> tui = ConfigTUI()
        >>> tui.run()
    """

    def __init__(self):
        """Initialize the configuration TUI."""
        self.console = Console()
        self.config_file = Path.home() / ".cribl-hc" / "config.json"
        self.running = True

    @staticmethod
    def _extract_from_paste(text: str) -> dict[str, Optional[str]]:
        """
        Extract URL and token from pasted content.

        Handles:
        - curl commands: curl -H "Authorization: Bearer TOKEN" https://example.com/api/v1/...
        - Raw URLs: https://example.com/api/v1/something
        - URLs with paths (strips to base URL)

        Args:
            text: Pasted content to parse

        Returns:
            Dictionary with 'url' and 'token' keys (values may be None)
        """
        result: dict[str, Optional[str]] = {"url": None, "token": None}

        # Extract Bearer token from curl command or Authorization header
        bearer_match = re.search(r"(?:Bearer\s+|bearer\s+)([A-Za-z0-9_\-.]+)", text, re.IGNORECASE)
        if bearer_match:
            result["token"] = bearer_match.group(1)

        # Extract URL (handles both curl and raw URLs)
        url_match = re.search(r"(https?://[^\s\"'<>]+)", text, re.IGNORECASE)
        if url_match:
            url = url_match.group(1)

            # Strip API path - keep only base URL
            # Example: https://cribl.example.com/api/v1/system/status -> https://cribl.example.com
            try:
                from urllib.parse import urlparse

                parsed = urlparse(url)
                result["url"] = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                # If URL parsing fails, use as-is
                result["url"] = url

        return result

    def _create_deployment_card(
        self, dep_id: str, url: str, token: str, status: str = "✓"
    ) -> Panel:
        """Create a styled card for a deployment."""
        status_color = COLOR_SUCCESS if status == "✓" else COLOR_ERROR
        status_symbol = f"[{status_color}]{status}[/]"

        content = Text.assemble(
            (f"📦 ", "bold cyan"),
            (f"{dep_id}\n", f"bold {COLOR_PRIMARY}"),
            ("URL: ", "dim"),
            (f"{url}\n", "white"),
            ("Token: ", "dim"),
            (f"{token[:8]}...{token[-4:]}\n", "dim"),
            ("Status: ", "dim"),
            status_symbol,
        )

        return Panel(
            content,
            border_style=COLOR_SECONDARY,
            padding=(1, 2),
            style=f"white on {COLOR_PANEL_BG}",
        )

    def run(self) -> None:
        """Run the interactive configuration TUI."""
        self.console.clear()
        self._show_welcome()

        while self.running:
            try:
                self._show_menu()
                choice = self._get_menu_choice()

                if choice == "1":
                    self._add_deployment()
                elif choice == "2":
                    self._edit_deployment()
                elif choice == "3":
                    self._delete_deployment()
                elif choice == "4":
                    self._test_connection()
                elif choice == "5":
                    self._view_deployments()
                elif choice == "6":
                    self._view_deployment_details()
                elif choice == "q":
                    self.running = False
                    self.console.print("\n[cyan]Goodbye![/cyan]")
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Operation cancelled.[/yellow]")
                if Confirm.ask("\nExit configuration manager?", default=False):
                    self.running = False
                    self.console.print("[cyan]Goodbye![/cyan]")
            except Exception as e:
                self.console.print(f"\n[red]Error: {str(e)}[/red]")
                log.error("config_tui_error", error=str(e))

    def _show_welcome(self) -> None:
        """Display welcome banner."""
        welcome_text = Text()
        welcome_text.append("Cribl Health Check", style="bold cyan")
        welcome_text.append("\nConfiguration Manager", style="cyan")
        welcome_text.append("\n\nManage deployment credentials and connections", style="dim")

        panel = Panel(welcome_text, border_style="cyan", padding=(1, 2))
        self.console.print(panel)
        self.console.print()

    def _show_menu(self) -> None:
        """Display main menu."""
        menu_text = Text()
        menu_text.append("Configuration Menu\n\n", style="bold white")
        menu_text.append("1. ", style="cyan")
        menu_text.append("Add New Deployment\n", style="white")
        menu_text.append("2. ", style="cyan")
        menu_text.append("Edit Deployment\n", style="white")
        menu_text.append("3. ", style="cyan")
        menu_text.append("Delete Deployment\n", style="white")
        menu_text.append("4. ", style="cyan")
        menu_text.append("Test Connection\n", style="white")
        menu_text.append("5. ", style="cyan")
        menu_text.append("View All Deployments\n", style="white")
        menu_text.append("6. ", style="cyan")
        menu_text.append("View Deployment Details\n", style="white")
        menu_text.append("q. ", style="cyan")
        menu_text.append("Quit\n", style="white")

        panel = Panel(menu_text, border_style="blue", padding=(1, 2))
        self.console.print(panel)

    def _get_menu_choice(self) -> str:
        """Get user's menu choice."""
        return Prompt.ask("\n[cyan]Choose an option[/cyan]", default="q").lower()

    def _add_deployment(self) -> None:
        """Add a new deployment configuration."""
        self.console.print("\n[bold cyan]Add New Deployment[/bold cyan]\n")
        self.console.print("[dim]DEBUG: Starting _add_deployment[/dim]")

        # Get deployment ID - use input() for better stdin handling
        try:
            self.console.print("[dim]DEBUG: About to ask for Deployment ID[/dim]")
            deployment_id = input(
                "[cyan]Deployment ID[/cyan] (e.g., 'prod', 'dev', 'staging'): "
            ).strip()
            self.console.print(f"[dim]DEBUG: Got deployment_id: {deployment_id}[/dim]")
        except (EOFError, KeyboardInterrupt):
            self.console.print("[yellow]Cancelled.[/yellow]")
            return

        if not deployment_id:
            self.console.print("[red]Deployment ID cannot be empty.[/red]")
            return

        self.console.print(f"[dim]DEBUG: Proceeding with deployment_id={deployment_id}[/dim]")

        if not deployment_id:
            self.console.print("[red]Deployment ID cannot be empty.[/red]")
            return

        # Check if deployment already exists
        from cribl_hc.cli.commands.config import load_credentials

        try:
            self.console.print("[dim]DEBUG: Loading credentials[/dim]")
            credentials = load_credentials()
            self.console.print(f"[dim]DEBUG: Loaded {len(credentials)} credentials[/dim]")
            if deployment_id in credentials:
                if not Confirm.ask(
                    f"\n[yellow]Deployment '{deployment_id}' already exists. Overwrite?[/yellow]",
                    default=False,
                ):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return
        except FileNotFoundError:
            self.console.print("[dim]DEBUG: No credentials file found[/dim]")
            credentials = {}
        except Exception as e:
            self.console.print(f"[red]DEBUG: Error loading credentials: {e}[/red]")
            credentials = {}

        self.console.print("[dim]DEBUG: About to ask for deployment type[/dim]")

        # Get deployment type
        self.console.print("\n[dim]Deployment Types:[/dim]")
        self.console.print("  [cyan]1.[/cyan] Cribl Cloud (https://workspace-org.cribl.cloud)")
        self.console.print("  [cyan]2.[/cyan] Self-Hosted (https://your-server.com)")

        deployment_type = Prompt.ask(
            "\n[cyan]Deployment type[/cyan]", choices=["1", "2"], default="1"
        )

        # Get URL with validation
        if deployment_type == "1":
            self.console.print(
                "\n[dim]Cribl Cloud URL format: https://<workspace>-<org>.cribl.cloud[/dim]"
            )
            self.console.print("[dim]Example: https://main-mycompany.cribl.cloud[/dim]")

        # Try curl first
        self.console.print("\n[dim]Quickest option: Paste full curl command[/dim]")
        self.console.print(
            '[dim]Example: curl -H "Authorization: Bearer TOKEN" https://url/api/v1/...[/dim]'
        )
        use_curl = Confirm.ask("\n[cyan]Do you have a curl command to paste?[/cyan]", default=True)

        url = None
        token = None

        if use_curl:
            curl_command = Prompt.ask("[cyan]Paste curl command[/cyan]")
            extracted = self._extract_from_paste(curl_command)
            url = extracted["url"]
            token = extracted["token"]

            if url:
                self.console.print(f"[green]✓ Extracted URL: {url}[/green]")
            if token:
                self.console.print(f"[green]✓ Extracted token[/green]")

            if not url or not token:
                self.console.print(
                    "\n[yellow]Could not extract complete credentials from curl command.[/yellow]"
                )
                self.console.print("[dim]Completing manually...[/dim]")

        # Get URL if not extracted
        if not url:
            self.console.print("\n[dim]Generate an API token in Cribl Settings > API Tokens[/dim]")
            url_input = Prompt.ask("[cyan]Cribl URL[/cyan]")
            url = url_input

        # Get token if not extracted
        if not token:
            token_input = Prompt.ask("[cyan]API Token[/cyan]", password=False)
            token = token_input

        # Validate
        if not url or not url.strip():
            self.console.print("[red]URL cannot be empty.[/red]")
            return

        if not token or not token.strip():
            self.console.print("[red]API token cannot be empty.[/red]")
            return

        if not url.startswith("http"):
            url = f"https://{url}"

        # Test connection before saving
        self.console.print("\n[yellow]Testing connection...[/yellow]")

        connection_ok = asyncio.run(self._test_connection_async(url, token))

        if not connection_ok:
            if not Confirm.ask(
                "\n[yellow]Connection test failed. Save anyway?[/yellow]", default=False
            ):
                self.console.print("[yellow]Operation cancelled.[/yellow]")
                return

        # Save credentials
        from cribl_hc.cli.commands.config import save_credentials

        credentials[deployment_id] = {
            "url": url,
            "token": token,
        }

        save_credentials(credentials)

        self.console.print(f"\n[green]✓ Deployment '{deployment_id}' saved successfully![/green]")

    def _edit_deployment(self) -> None:
        """Edit an existing deployment configuration."""
        self.console.print("\n[bold cyan]Edit Deployment[/bold cyan]\n")

        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
        except FileNotFoundError:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        # Show available deployments
        self.console.print("[dim]Available deployments:[/dim]")
        for dep_id in credentials.keys():
            self.console.print(f"  • {dep_id}")

        deployment_id = Prompt.ask("\n[cyan]Deployment ID to edit[/cyan]")

        if deployment_id not in credentials:
            self.console.print(f"[red]Deployment '{deployment_id}' not found.[/red]")
            return

        current_cred = credentials[deployment_id]

        # Show current values
        self.console.print(f"\n[dim]Current URL:[/dim] {current_cred['url']}")
        self.console.print(f"[dim]Current Token:[/dim] {'*' * 20}")

        # Get new values (allow empty to keep current)
        self.console.print("\n[dim]Press Enter to keep current value or paste a curl command[/dim]")
        self.console.print(
            "[dim]Tip: Paste a curl command or API URL - we'll extract the base URL[/dim]"
        )

        new_url_input = Prompt.ask("[cyan]New URL[/cyan]", default=current_cred["url"])
        extracted = self._extract_from_paste(new_url_input)
        new_url = extracted["url"] or new_url_input

        update_token = Confirm.ask("\n[cyan]Update API token?[/cyan]", default=False)
        new_token = current_cred["token"]

        if update_token:
            self.console.print(
                "[dim]Tip: Paste a curl command - we'll extract the token automatically[/dim]"
            )
            new_token_input = Prompt.ask("[cyan]New API Token[/cyan]", password=False)
            extracted = self._extract_from_paste(new_token_input)
            new_token = extracted["token"] or new_token_input
            if not new_token or not new_token.strip():
                new_token = current_cred["token"]

        # Test connection before saving
        self.console.print("\n[yellow]Testing connection...[/yellow]")

        connection_ok = asyncio.run(self._test_connection_async(new_url, new_token))

        if not connection_ok:
            if not Confirm.ask(
                "\n[yellow]Connection test failed. Save anyway?[/yellow]", default=False
            ):
                self.console.print("[yellow]Operation cancelled.[/yellow]")
                return

        # Save updated credentials
        from cribl_hc.cli.commands.config import save_credentials

        credentials[deployment_id] = {
            "url": new_url,
            "token": new_token,
        }

        save_credentials(credentials)

        self.console.print(f"\n[green]✓ Deployment '{deployment_id}' updated successfully![/green]")

    def _delete_deployment(self) -> None:
        """Delete deployments with safe edit mode and checkbox selection."""
        from cribl_hc.cli.commands.config import load_credentials, save_credentials

        try:
            credentials = load_credentials()
        except FileNotFoundError:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        self.console.clear()
        self.console.print(Rule("Delete Deployments - Edit Mode", style="bold cyan"))
        self.console.print("[dim]Select deployments to delete using the checkboxes below[/dim]\n")

        dep_list = sorted(credentials.keys())
        selected = {}

        self.console.print("[bold]Deployments:[/bold]\n")
        for i, dep_id in enumerate(dep_list, 1):
            url = credentials[dep_id].get("url", "Unknown")
            self.console.print(f"  [{i}] ☐ {dep_id:<15} {url}")

        self.console.print("\n[bold]Controls:[/bold]")
        self.console.print("  [A]ll   - Select all deployments")
        self.console.print("  [N]one  - Deselect all deployments")
        self.console.print("  [Q]uit  - Cancel and go back\n")

        while True:
            self.console.print("[bold]Edit Mode:[/bold]")
            self.console.print("  Type credential number to toggle (e.g., 1, 2, 3...)")
            self.console.print(
                "  Type 'A' for all, 'N' for none, 'D' to delete selected, 'Q' to quit\n"
            )

            choice = Prompt.ask("[cyan]Enter command[/cyan]", default="").lower().strip()

            if choice == "q":
                self.console.print("[yellow]Cancelled.[/yellow]")
                return

            if choice == "a":
                selected = {dep_id: True for dep_id in dep_list}
                self.console.clear()
                self.console.print(Rule("Delete Deployments - Edit Mode", style="bold cyan"))
                self.console.print(
                    "[dim]Select deployments to delete using the checkboxes below[/dim]\n"
                )
                self.console.print("[bold]Deployments:[/bold]\n")
                for i, dep_id in enumerate(dep_list, 1):
                    url = credentials[dep_id].get("url", "Unknown")
                    marker = "☑" if selected.get(dep_id) else "☐"
                    self.console.print(f"  [{i}] {marker} {dep_id:<15} {url}")
                self.console.print()
                continue

            if choice == "n":
                selected = {}
                self.console.clear()
                self.console.print(Rule("Delete Deployments - Edit Mode", style="bold cyan"))
                self.console.print(
                    "[dim]Select deployments to delete using the checkboxes below[/dim]\n"
                )
                self.console.print("[bold]Deployments:[/bold]\n")
                for i, dep_id in enumerate(dep_list, 1):
                    url = credentials[dep_id].get("url", "Unknown")
                    marker = "☑" if selected.get(dep_id) else "☐"
                    self.console.print(f"  [{i}] {marker} {dep_id:<15} {url}")
                self.console.print()
                continue

            if choice == "d":
                to_delete = list(selected.keys())
                if not to_delete:
                    self.console.print("[yellow]No deployments selected.[/yellow]\n")
                    continue

                self.console.print(
                    f"\n[bold red]⚠ WARNING:[/bold red] About to delete {len(to_delete)} deployment(s):"
                )
                for dep_id in to_delete:
                    self.console.print(f"  • {dep_id}")

                if not Confirm.ask(
                    "\n[bold red]Delete these deployments permanently?[/bold red]",
                    default=False,
                ):
                    self.console.print("[yellow]Cancelled.[/yellow]")
                    return

                for dep_id in to_delete:
                    del credentials[dep_id]

                save_credentials(credentials)
                self.console.print(
                    f"\n[green]✓ Deleted {len(to_delete)} deployment(s) successfully![/green]"
                )
                return

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(dep_list):
                    dep_id = dep_list[idx]
                    selected[dep_id] = not selected.get(dep_id, False)
                    self.console.clear()
                    self.console.print(Rule("Delete Deployments - Edit Mode", style="bold cyan"))
                    self.console.print(
                        "[dim]Select deployments to delete using the checkboxes below[/dim]\n"
                    )
                    self.console.print("[bold]Deployments:[/bold]\n")
                    for i, d_id in enumerate(dep_list, 1):
                        url = credentials[d_id].get("url", "Unknown")
                        marker = "☑" if selected.get(d_id) else "☐"
                        self.console.print(f"  [{i}] {marker} {d_id:<15} {url}")
                    self.console.print()
                else:
                    self.console.print(f"[red]Invalid number. Choose 1-{len(dep_list)}[/red]\n")
            else:
                self.console.print(
                    "[red]Invalid command. Use 1-N for numbers, A/N/D/Q for commands.[/red]\n"
                )

    def _test_connection(self) -> None:
        """Test connection to a deployment."""
        self.console.print("\n[bold cyan]Test Connection[/bold cyan]\n")

        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
        except FileNotFoundError:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        # Show available deployments
        self.console.print("[dim]Available deployments:[/dim]")
        for dep_id in credentials.keys():
            self.console.print(f"  • {dep_id}")

        deployment_id = Prompt.ask("\n[cyan]Deployment ID to test[/cyan]")

        if deployment_id not in credentials:
            self.console.print(f"[red]Deployment '{deployment_id}' not found.[/red]")
            return

        cred = credentials[deployment_id]

        self.console.print(f"\n[yellow]Testing connection to {cred['url']}...[/yellow]")

        connection_ok = asyncio.run(
            self._test_connection_async(cred["url"], cred["token"], verbose=True)
        )

        if connection_ok:
            self.console.print(f"\n[green]✓ Connection to '{deployment_id}' successful![/green]")
        else:
            self.console.print(f"\n[red]✗ Connection to '{deployment_id}' failed.[/red]")

    def _view_deployments(self) -> None:
        """View all configured deployments in card-based layout."""
        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
        except FileNotFoundError:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        self.console.print(Rule("Configured Deployments", style=COLOR_PRIMARY))
        self.console.line()

        dep_list = sorted(credentials.keys())
        cards = []

        for dep_id in dep_list:
            cred = credentials[dep_id]
            card = self._create_deployment_card(dep_id, cred["url"], cred["token"])
            cards.append(card)

        if len(cards) <= 2:
            for card in cards:
                self.console.print(card)
                self.console.line()
        else:
            for i in range(0, len(cards), 2):
                if i + 1 < len(cards):
                    self.console.print(Columns([cards[i], cards[i + 1]], equal=True, expand=True))
                else:
                    self.console.print(cards[i])
                self.console.line()

        summary = Text.assemble(
            ("Total: ", "dim"),
            (f"{len(credentials)}", f"bold {COLOR_PRIMARY}"),
            (" deployment(s) | ", "dim"),
            ("Tip: ", "dim"),
            ("Use 'Edit' to update or 'Delete' to remove", "dim"),
        )
        self.console.print(Align.center(summary))

    def _view_deployment_details(self) -> None:
        """View detailed information about a specific deployment."""
        self.console.print("\n[bold cyan]Deployment Details[/bold cyan]\n")

        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
        except FileNotFoundError:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        # Show available deployments
        self.console.print("[dim]Available deployments:[/dim]")
        for dep_id in credentials.keys():
            self.console.print(f"  • {dep_id}")

        deployment_id = Prompt.ask("\n[cyan]Deployment ID[/cyan]")

        if deployment_id not in credentials:
            self.console.print(f"[red]Deployment '{deployment_id}' not found.[/red]")
            return

        cred = credentials[deployment_id]

        # Create details panel
        details_text = Text()
        details_text.append("Deployment ID: ", style="dim")
        details_text.append(f"{deployment_id}\n", style="cyan")
        details_text.append("URL: ", style="dim")
        details_text.append(f"{cred['url']}\n", style="white")
        details_text.append("Token: ", style="dim")

        # Show masked token with option to reveal
        token_masked = (
            cred["token"][:8] + "..." + cred["token"][-4:] if len(cred["token"]) > 12 else "***"
        )
        details_text.append(f"{token_masked}\n", style="yellow")

        # Determine deployment type
        deployment_type = "Cribl Cloud" if ".cribl.cloud" in cred["url"] else "Self-Hosted"
        details_text.append("Type: ", style="dim")
        details_text.append(f"{deployment_type}", style="white")

        panel = Panel(
            details_text, title=f"[bold]{deployment_id}[/bold]", border_style="cyan", padding=(1, 2)
        )
        self.console.print(panel)

        # Option to test connection
        if Confirm.ask("\n[cyan]Test connection?[/cyan]", default=True):
            self.console.print("\n[yellow]Testing connection...[/yellow]")
            connection_ok = asyncio.run(
                self._test_connection_async(cred["url"], cred["token"], verbose=True)
            )

            if connection_ok:
                self.console.print("[green]✓ Connection successful![/green]")
            else:
                self.console.print("[red]✗ Connection failed.[/red]")

    async def _test_connection_async(self, url: str, token: str, verbose: bool = False) -> bool:
        """
        Test connection to Cribl API asynchronously.

        Args:
            url: Cribl API URL
            token: API token
            verbose: Show detailed connection info

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with CriblAPIClient(url, token) as client:
                result = await client.test_connection()

                if result.success:
                    if verbose:
                        self.console.print(
                            f"[green]✓ Connected successfully[/green] [dim]({result.response_time_ms:.0f}ms)[/dim]"
                        )
                        self.console.print(f"[dim]Cribl version:[/dim] {result.cribl_version}")

                        # Show product type
                        product_type = "Cribl Edge" if client.is_edge else "Cribl Stream"
                        self.console.print(f"[dim]Product:[/dim] {product_type}")
                    return True
                else:
                    if verbose:
                        self.console.print(f"[red]✗ Connection failed:[/red] {result.error}")
                    return False

        except Exception as e:
            if verbose:
                self.console.print(f"[red]✗ Connection error:[/red] {str(e)}")
            log.error("connection_test_failed", url=url, error=str(e))
            return False
