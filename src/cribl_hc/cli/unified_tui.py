"""
Unified Terminal User Interface for Cribl Health Check.

Provides a single, integrated interface for:
- Managing deployment credentials
- Running health check analyses
- Viewing analysis results

This serves as the foundation for the future GUI implementation.
"""

import asyncio


from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

from cribl_hc.cli.config_tui import ConfigTUI
from cribl_hc.cli.tui import HealthCheckTUI
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)

# --- Color Palette ---
PRIMARY_COLOR = "cyan"
SECONDARY_COLOR = "blue"
SUCCESS_COLOR = "green"
WARNING_COLOR = "yellow"
ERROR_COLOR = "red"
DIM_COLOR = "dim"
BACKGROUND_COLOR = "rgb(15,23,42)"  # slate-900
PANEL_BACKGROUND_COLOR = "rgb(30,41,59)"  # slate-800
PANEL_BORDER_COLOR = "rgb(56,189,248)"  # sky-400
ACCENT_COLOR = "bold rgb(14,165,233)"  # sky-500


class UnifiedTUI:
    """
    Unified Terminal User Interface for Cribl Health Check.

    Integrates credential management, health check execution,
    and results viewing into a single cohesive interface.

    Example:
        >>> tui = UnifiedTUI()
        >>> tui.run()
    """

    def __init__(self):
        """Initialize the unified TUI."""
        self.console = Console(style=f"white on {BACKGROUND_COLOR}")
        self.config_tui = ConfigTUI()
        self.results_tui = HealthCheckTUI(self.console)
        self.running = True

    def run(self) -> None:
        """Run the unified TUI main loop."""
        self.console.clear()
        self._show_welcome()

        while self.running:
            try:
                self._show_main_menu()
                choice = self._get_menu_choice()

                if choice == "1":
                    self._manage_deployments()
                elif choice == "2":
                    self._run_health_check()
                elif choice == "3":
                    self._view_recent_results()
                elif choice == "4":
                    self._show_settings()
                elif choice.lower() in ["q", "quit", "exit"]:
                    self._quit()
                else:
                    self.console.print(
                        f"[{WARNING_COLOR}]Invalid choice. Please try again.[/]",
                        justify="center",
                    )
                    self.console.line()

            except KeyboardInterrupt:
                self._quit()
            except Exception as e:
                log.error("unified_tui_error", error=str(e))
                self.console.print(f"[{ERROR_COLOR}]Error:[/red] {str(e)}\n")

    def _show_welcome(self) -> None:
        """Display welcome banner."""
        title = Text(
            "Cribl Health Check", justify="center", style="bold rgb(14,165,233) on rgb(15,23,42)"
        )
        subtitle = Text(
            "Interactive Terminal Interface",
            justify="center",
            style=f"{DIM_COLOR} on {BACKGROUND_COLOR}",
        )
        welcome_text = Text(
            "\nManage deployments, run analyses, and view results.",
            justify="center",
            style=f"white on {BACKGROUND_COLOR}",
        )

        panel = Panel(
            Text.assemble(title, "\n", subtitle, welcome_text),
            border_style=PANEL_BORDER_COLOR,
            padding=(2, 4),
            expand=False,
            style=f"white on {BACKGROUND_COLOR}",
        )
        self.console.print(Align.center(panel))
        self.console.line()

    def _show_main_menu(self) -> None:
        """Display main menu as interactive cards."""
        menu_items = [
            Panel(
                Text.assemble(
                    ("🚀", "bold magenta"),
                    "\n\n",
                    ("Manage Deployments\n", f"bold {PRIMARY_COLOR}"),
                    (
                        "Add, edit, test, and delete deployment credentials.",
                        DIM_COLOR,
                    ),
                ),
                title="[bold]1[/bold]",
                title_align="left",
                border_style=SECONDARY_COLOR,
                padding=(1, 2),
                style=f"white on {PANEL_BACKGROUND_COLOR}",
            ),
            Panel(
                Text.assemble(
                    ("❤️", "bold red"),
                    "\n\n",
                    ("Run Health Check\n", f"bold {PRIMARY_COLOR}"),
                    ("Analyze a Cribl deployment for health and best practices.", DIM_COLOR),
                ),
                title="[bold]2[/bold]",
                title_align="left",
                border_style=SECONDARY_COLOR,
                padding=(1, 2),
                style=f"white on {PANEL_BACKGROUND_COLOR}",
            ),
            Panel(
                Text.assemble(
                    ("📊", "bold green"),
                    "\n\n",
                    ("View Recent Results\n", f"bold {PRIMARY_COLOR}"),
                    ("Browse and export previous analysis results.", DIM_COLOR),
                ),
                title="[bold]3[/bold]",
                title_align="left",
                border_style=SECONDARY_COLOR,
                padding=(1, 2),
                style=f"white on {PANEL_BACKGROUND_COLOR}",
            ),
            Panel(
                Text.assemble(
                    ("⚙️", "bold yellow"),
                    "\n\n",
                    ("Settings\n", f"bold {PRIMARY_COLOR}"),
                    ("Configure tool preferences and behavior.", DIM_COLOR),
                ),
                title="[bold]4[/bold]",
                title_align="left",
                border_style=SECONDARY_COLOR,
                padding=(1, 2),
                style=f"white on {PANEL_BACKGROUND_COLOR}",
            ),
        ]
        self.console.print(Rule("Main Menu", style=ACCENT_COLOR))
        self.console.line()
        self.console.print(Columns(menu_items, equal=True, expand=True))
        self.console.line()

    def _get_menu_choice(self) -> str:
        """Get user's menu choice."""
        self.console.print(
            Align.center(
                Text.assemble(
                    (
                        "Enter a number to select an option, or ",
                        f"{DIM_COLOR} on {BACKGROUND_COLOR}",
                    ),
                    ("Q", f"bold {ERROR_COLOR} on {BACKGROUND_COLOR}"),
                    (" to quit.", f"{DIM_COLOR} on {BACKGROUND_COLOR}"),
                )
            )
        )
        return Prompt.ask(
            f"\n[{ACCENT_COLOR}]Select an option[/]",
            default="2",
            console=self.console,
        ).strip()

    def _manage_deployments(self) -> None:
        """Launch deployment management interface."""
        self.console.clear()

        # Show deployment management menu
        self._show_deployment_menu()
        choice = self._get_deployment_menu_choice()

        if choice == "1":
            self.config_tui._add_deployment()
        elif choice == "2":
            self.config_tui._edit_deployment()
        elif choice == "3":
            self.config_tui._delete_deployment()
        elif choice == "4":
            self.config_tui._test_connection()
        elif choice == "5":
            self.config_tui._view_deployments()
        elif choice == "6":
            self.config_tui._view_deployment_details()
        elif choice.lower() in ["b", "back"]:
            return

        # Pause before returning to main menu
        self.console.print()
        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
        self.console.clear()

    def _show_deployment_menu(self) -> None:
        """Display deployment management menu."""
        menu_text = Text()
        menu_text.append("Deployment Management\n\n", style="bold cyan")
        menu_text.append("1. Add New Deployment\n")
        menu_text.append("2. Edit Deployment\n")
        menu_text.append("3. Delete Deployment\n")
        menu_text.append("4. Test Connection\n")
        menu_text.append("5. View All Deployments\n")
        menu_text.append("6. View Deployment Details\n\n")
        menu_text.append("B. ", style="bold")
        menu_text.append("Back to Main Menu", style="dim")

        panel = Panel(
            menu_text, title="[bold]Manage Deployments[/bold]", border_style="cyan", padding=(1, 2)
        )
        self.console.print(panel)

    def _get_deployment_menu_choice(self) -> str:
        """Get deployment menu choice."""
        return Prompt.ask("\n[cyan]Select an option[/cyan]", default="1")

    def _run_health_check(self) -> None:
        """Run health check analysis."""

        from cribl_hc.cli.commands.config import load_credentials

        self.console.clear()
        self.console.print(
            Panel("[bold cyan]Run Health Check Analysis[/bold cyan]", border_style="cyan")
        )
        self.console.print()

        # Load available deployments
        try:
            credentials = load_credentials()
        except Exception as e:
            self.console.print(f"[red]Error loading credentials:[/red] {str(e)}\n")
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
            self.console.clear()
            return

        if not credentials:
            self.console.print("[yellow]No deployments configured.[/yellow]")
            self.console.print(
                "[dim]Please add a deployment first (Option 1: Manage Deployments)[/dim]\n"
            )
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
            self.console.clear()
            return

        # Show available deployments
        deployment_list = sorted(credentials.keys())
        default_deployment = deployment_list[0]

        self.console.print("[bold]Available Deployments:[/bold]")
        for i, deployment_id in enumerate(deployment_list, 1):
            url = credentials[deployment_id].get("url", "Unknown")
            self.console.print(f"  {i}. [cyan]{deployment_id}[/cyan] - {url}")
        self.console.print()

        # Get deployment selection with support for numbers, names, or Enter for default
        while True:
            selection = Prompt.ask(
                "[cyan]Select deployment (number or name)[/cyan]", default=default_deployment
            )

            # Handle empty input (Enter pressed) - use default
            if not selection:
                deployment_id = default_deployment
                break

            # Try to parse as number
            if selection.isdigit():
                idx = int(selection) - 1
                if 0 <= idx < len(deployment_list):
                    deployment_id = deployment_list[idx]
                    break
                else:
                    self.console.print(
                        f"[red]Invalid number. Please enter 1-{len(deployment_list)}[/red]"
                    )
                    continue

            # Try as deployment name
            if selection in credentials:
                deployment_id = selection
                break
            else:
                self.console.print(f"[red]Deployment '{selection}' not found[/red]")
                continue

        cred = credentials[deployment_id]
        url = cred.get("url")
        token = cred.get("token")

        # Run analysis
        self.console.print(f"\n[cyan]Starting health check for:[/cyan] {deployment_id}")
        self.console.print(f"[dim]URL:[/dim] {url}\n")

        try:
            analysis_run = asyncio.run(self._run_analysis_async(url, token, deployment_id))

            if analysis_run:
                # Display results
                self.console.clear()
                self.results_tui.display(analysis_run)
                self.console.print()
                Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        except Exception as e:
            log.error("health_check_failed", error=str(e), deployment_id=deployment_id)
            self.console.print(f"\n[red]Analysis failed:[/red] {str(e)}\n")
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        self.console.clear()

    async def _run_analysis_async(self, url: str, token: str, deployment_id: str):
        """Run health check analysis asynchronously."""
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

        from cribl_hc.core.api_client import CriblAPIClient
        from cribl_hc.core.orchestrator import AnalysisProgress, AnalyzerOrchestrator

        # Test connection
        self.console.print("[yellow]Testing connection...[/yellow]")
        async with CriblAPIClient(url, token) as client:
            connection_result = await client.test_connection()

            if not connection_result.success:
                self.console.print(f"[red]✗ Connection failed:[/red] {connection_result.error}")
                return None

            self.console.print(
                f"[green]✓ Connected successfully[/green] "
                f"[dim]({connection_result.response_time_ms:.0f}ms)[/dim]"
            )
            self.console.print(f"[dim]Cribl version:[/dim] {connection_result.cribl_version}\n")

            # Initialize orchestrator
            orchestrator = AnalyzerOrchestrator(
                client=client,
                max_api_calls=100,
                continue_on_error=True,
            )

            # Run analysis with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            ) as progress:
                task_id = progress.add_task("Running analysis...", total=100)

                def progress_callback(analysis_progress: AnalysisProgress):
                    """Update progress bar."""
                    percentage = analysis_progress.get_percentage()
                    progress.update(
                        task_id,
                        completed=percentage,
                        description=f"Analyzing: {analysis_progress.current_objective or 'complete'}",
                    )

                # Run the analysis
                results = await orchestrator.run_analysis(
                    objectives=None,  # All objectives
                    progress_callback=progress_callback,
                )

                progress.update(task_id, completed=100, description="Analysis complete")

            # Create analysis run model
            analysis_run = orchestrator.create_analysis_run(results, deployment_id)

            self.console.print("\n[green]✓ Analysis completed[/green]")
            self.console.print(f"[dim]Findings:[/dim] {len(analysis_run.findings)}")
            self.console.print(f"[dim]Recommendations:[/dim] {len(analysis_run.recommendations)}")
            self.console.print(
                f"[dim]Health Score:[/dim] {analysis_run.health_score.overall_score if analysis_run.health_score else 'N/A'}\n"
            )

            return analysis_run

    def _view_recent_results(self) -> None:
        """View recent analysis results."""
        self.console.clear()
        self.console.print(
            Panel(
                "[bold cyan]Recent Analysis Results[/bold cyan]\n\n"
                "[dim]This feature will display previously saved analysis results.[/dim]\n"
                "[dim]Feature coming soon![/dim]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.console.print()
        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
        self.console.clear()

    def _show_settings(self) -> None:
        """Show settings menu."""
        self.console.clear()
        self.console.print(
            Panel(
                "[bold cyan]Settings[/bold cyan]\n\n"
                "[dim]Configure tool preferences:[/dim]\n"
                "  • Default API call limit\n"
                "  • Default objectives to analyze\n"
                "  • Output format preferences\n"
                "  • Logging verbosity\n\n"
                "[dim]Feature coming soon![/dim]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self.console.print()
        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
        self.console.clear()

    def _quit(self) -> None:
        """Exit the TUI."""
        self.running = False
        self.console.clear()
        self.console.print("\n[cyan]Thank you for using Cribl Health Check![/cyan]\n")
