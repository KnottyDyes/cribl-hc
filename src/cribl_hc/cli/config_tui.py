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
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


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

        # Get deployment ID
        deployment_id = Prompt.ask("[cyan]Deployment ID[/cyan] (e.g., 'prod', 'dev', 'staging')")

        if not deployment_id or not deployment_id.strip():
            self.console.print("[red]Deployment ID cannot be empty.[/red]")
            return

        # Check if deployment already exists
        from cribl_hc.cli.commands.config import load_credentials
        try:
            credentials = load_credentials()
            if deployment_id in credentials:
                if not Confirm.ask(f"\n[yellow]Deployment '{deployment_id}' already exists. Overwrite?[/yellow]", default=False):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return
        except FileNotFoundError:
            credentials = {}

        # Get deployment type
        self.console.print("\n[dim]Deployment Types:[/dim]")
        self.console.print("  [cyan]1.[/cyan] Cribl Cloud (https://workspace-org.cribl.cloud)")
        self.console.print("  [cyan]2.[/cyan] Self-Hosted (https://your-server.com)")

        deployment_type = Prompt.ask("\n[cyan]Deployment type[/cyan]", choices=["1", "2"], default="1")

        # Get URL with validation
        if deployment_type == "1":
            self.console.print("\n[dim]Cribl Cloud URL format: https://<workspace>-<org>.cribl.cloud[/dim]")
            self.console.print("[dim]Example: https://main-mycompany.cribl.cloud[/dim]")

        url = Prompt.ask("\n[cyan]Cribl URL[/cyan]")

        if not url.startswith("http"):
            url = f"https://{url}"

        # Get API token
        self.console.print("\n[dim]Generate an API token in Cribl Settings > API Tokens[/dim]")
        token = Prompt.ask("[cyan]API Token[/cyan]", password=True)

        if not token or not token.strip():
            self.console.print("[red]API token cannot be empty.[/red]")
            return

        # Test connection before saving
        self.console.print("\n[yellow]Testing connection...[/yellow]")

        connection_ok = asyncio.run(self._test_connection_async(url, token))

        if not connection_ok:
            if not Confirm.ask("\n[yellow]Connection test failed. Save anyway?[/yellow]", default=False):
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
        self.console.print("\n[dim]Press Enter to keep current value[/dim]")

        new_url = Prompt.ask("[cyan]New URL[/cyan]", default=current_cred['url'])

        update_token = Confirm.ask("\n[cyan]Update API token?[/cyan]", default=False)
        new_token = current_cred['token']

        if update_token:
            new_token = Prompt.ask("[cyan]New API Token[/cyan]", password=True)
            if not new_token or not new_token.strip():
                new_token = current_cred['token']

        # Test connection before saving
        self.console.print("\n[yellow]Testing connection...[/yellow]")

        connection_ok = asyncio.run(self._test_connection_async(new_url, new_token))

        if not connection_ok:
            if not Confirm.ask("\n[yellow]Connection test failed. Save anyway?[/yellow]", default=False):
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
        """Delete a deployment configuration."""
        self.console.print("\n[bold cyan]Delete Deployment[/bold cyan]\n")

        from cribl_hc.cli.commands.config import load_credentials, save_credentials

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

        deployment_id = Prompt.ask("\n[cyan]Deployment ID to delete[/cyan]")

        if deployment_id not in credentials:
            self.console.print(f"[red]Deployment '{deployment_id}' not found.[/red]")
            return

        # Confirm deletion
        if not Confirm.ask(f"\n[yellow]Are you sure you want to delete '{deployment_id}'?[/yellow]", default=False):
            self.console.print("[yellow]Operation cancelled.[/yellow]")
            return

        # Delete
        del credentials[deployment_id]
        save_credentials(credentials)

        self.console.print(f"\n[green]✓ Deployment '{deployment_id}' deleted successfully![/green]")

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

        connection_ok = asyncio.run(self._test_connection_async(cred['url'], cred['token'], verbose=True))

        if connection_ok:
            self.console.print(f"\n[green]✓ Connection to '{deployment_id}' successful![/green]")
        else:
            self.console.print(f"\n[red]✗ Connection to '{deployment_id}' failed.[/red]")

    def _view_deployments(self) -> None:
        """View all configured deployments."""
        self.console.print("\n[bold cyan]Configured Deployments[/bold cyan]\n")

        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
        except FileNotFoundError:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured yet.[/yellow]")
            return

        # Create table
        table = Table(show_header=True, header_style="bold cyan", border_style="blue")
        table.add_column("Deployment ID", style="cyan")
        table.add_column("URL")
        table.add_column("Token", style="dim")

        for dep_id, cred in credentials.items():
            # Mask token
            token_masked = cred['token'][:8] + "..." + cred['token'][-4:] if len(cred['token']) > 12 else "***"

            table.add_row(dep_id, cred['url'], token_masked)

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(credentials)} deployment(s)[/dim]")

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
        details_text.append(f"Deployment ID: ", style="dim")
        details_text.append(f"{deployment_id}\n", style="cyan")
        details_text.append(f"URL: ", style="dim")
        details_text.append(f"{cred['url']}\n", style="white")
        details_text.append(f"Token: ", style="dim")

        # Show masked token with option to reveal
        token_masked = cred['token'][:8] + "..." + cred['token'][-4:] if len(cred['token']) > 12 else "***"
        details_text.append(f"{token_masked}\n", style="yellow")

        # Determine deployment type
        deployment_type = "Cribl Cloud" if ".cribl.cloud" in cred['url'] else "Self-Hosted"
        details_text.append(f"Type: ", style="dim")
        details_text.append(f"{deployment_type}", style="white")

        panel = Panel(details_text, title=f"[bold]{deployment_id}[/bold]", border_style="cyan", padding=(1, 2))
        self.console.print(panel)

        # Option to test connection
        if Confirm.ask("\n[cyan]Test connection?[/cyan]", default=True):
            self.console.print("\n[yellow]Testing connection...[/yellow]")
            connection_ok = asyncio.run(self._test_connection_async(cred['url'], cred['token'], verbose=True))

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
                        self.console.print(f"[green]✓ Connected successfully[/green] [dim]({result.response_time_ms:.0f}ms)[/dim]")
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
