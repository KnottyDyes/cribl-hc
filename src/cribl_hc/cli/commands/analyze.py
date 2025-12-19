"""
Analyze command for running health check analysis.
"""

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalyzerOrchestrator, AnalysisProgress
from cribl_hc.cli.output import display_analysis_results
from cribl_hc.utils.logger import get_logger, configure_logging


console = Console()
log = get_logger(__name__)

app = typer.Typer(help="Run health check analysis")


@app.command()
def run(
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
        help="Cribl Stream leader URL (e.g., https://cribl.example.com)",
        envvar="CRIBL_URL",
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Bearer token for authentication",
        envvar="CRIBL_TOKEN",
        hide_input=True,
    ),
    objectives: Optional[List[str]] = typer.Option(
        None,
        "--objective",
        "-o",
        help="Objectives to analyze (default: all registered)",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-f",
        help="Output file path for JSON report",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        "-m",
        help="Generate Markdown report in addition to terminal output",
    ),
    deployment_id: str = typer.Option(
        "default",
        "--deployment-id",
        "-d",
        help="Deployment identifier for this analysis",
    ),
    max_api_calls: int = typer.Option(
        100,
        "--max-api-calls",
        help="Maximum API calls allowed (default: 100)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output (INFO level logging)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode (DEBUG level logging with detailed traces)",
    ),
):
    """
    Run health check analysis on a Cribl Stream deployment.

    Examples:

        # Using stored credentials
        cribl-hc analyze run --deployment prod

        # Using explicit URL and token
        cribl-hc analyze run --url https://cribl.example.com --token YOUR_TOKEN

        # Using environment variables
        export CRIBL_URL=https://cribl.example.com
        export CRIBL_TOKEN=your_token
        cribl-hc analyze run

        # Analyze specific objectives
        cribl-hc analyze run -p prod -o health -o config

        # Save results to file
        cribl-hc analyze run -p prod --output report.json --markdown
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
                raise typer.Exit(code=1)

            cred = credentials[deployment]
            url = cred.get("url")
            token = cred.get("token")

            console.print(f"[cyan]Using stored credentials for:[/cyan] {deployment}")
            console.print(f"[dim]URL:[/dim] {url}\n")

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]✗ Failed to load credentials:[/red] {str(e)}")
            raise typer.Exit(code=1)

    # Validate that we have URL and token from some source
    if not url or not token:
        console.print("[red]✗ Missing required credentials[/red]")
        console.print("\n[yellow]You must provide credentials in one of three ways:[/yellow]\n")
        console.print("1. [cyan]Stored credentials:[/cyan]")
        console.print("   cribl-hc config set prod --url URL --token TOKEN")
        console.print("   cribl-hc analyze run --deployment prod\n")
        console.print("2. [cyan]Command-line options:[/cyan]")
        console.print("   cribl-hc analyze run --url URL --token TOKEN\n")
        console.print("3. [cyan]Environment variables:[/cyan]")
        console.print("   export CRIBL_URL=https://cribl.example.com")
        console.print("   export CRIBL_TOKEN=your_token")
        console.print("   cribl-hc analyze run\n")
        raise typer.Exit(code=1)

    # Configure logging based on verbosity flags
    if debug:
        configure_logging(level="DEBUG", json_output=False)
        console.print("[yellow]🐛 Debug mode enabled - detailed logging active[/yellow]")
    elif verbose:
        configure_logging(level="INFO", json_output=False)
        console.print("[cyan]ℹ️  Verbose mode enabled[/cyan]")

    # Run async analysis
    asyncio.run(
        run_analysis_async(
            url=url,
            token=token,
            objectives=objectives,
            output_file=output_file,
            markdown=markdown,
            deployment_id=deployment_id,
            max_api_calls=max_api_calls,
            verbose=verbose,
            debug=debug,
        )
    )


async def run_analysis_async(
    url: str,
    token: str,
    objectives: Optional[List[str]],
    output_file: Optional[Path],
    markdown: bool,
    deployment_id: str,
    max_api_calls: int,
    verbose: bool = False,
    debug: bool = False,
):
    """
    Run analysis asynchronously.

    Args:
        url: Cribl Stream URL
        token: Authentication token
        objectives: List of objectives to analyze
        output_file: Optional output file path
        markdown: Whether to generate Markdown report
        deployment_id: Deployment identifier
        max_api_calls: Maximum API calls allowed
    """
    console.print(f"\n[cyan]Cribl Stream Health Check[/cyan]")
    console.print(f"[dim]Target:[/dim] {url}")
    console.print(f"[dim]Deployment:[/dim] {deployment_id}\n")

    if debug:
        log.debug("analysis_starting", url=url, deployment_id=deployment_id,
                  max_api_calls=max_api_calls, objectives=objectives)
        console.print(f"[dim]Debug: Max API calls: {max_api_calls}[/dim]")
        console.print(f"[dim]Debug: Objectives: {objectives or 'all registered'}[/dim]")

    # Test connection first
    console.print("[yellow]Testing connection...[/yellow]")
    if verbose or debug:
        log.info("testing_connection", url=url)
    async with CriblAPIClient(url, token) as client:
        connection_result = await client.test_connection()

        if not connection_result.success:
            console.print(f"[red]✗ Connection failed:[/red] {connection_result.error}")
            log.error("connection_failed", error=connection_result.error, url=url)
            raise typer.Exit(code=1)

        console.print(
            f"[green]✓ Connected successfully[/green] "
            f"[dim]({connection_result.response_time_ms:.0f}ms)[/dim]"
        )
        console.print(f"[dim]Cribl version:[/dim] {connection_result.cribl_version}\n")

        if debug:
            log.debug("connection_successful",
                     response_time_ms=connection_result.response_time_ms,
                     cribl_version=connection_result.cribl_version)

        # Initialize orchestrator
        if verbose or debug:
            log.info("initializing_orchestrator",
                    max_api_calls=max_api_calls,
                    continue_on_error=True)

        orchestrator = AnalyzerOrchestrator(
            client=client,
            max_api_calls=max_api_calls,
            continue_on_error=True,
        )

        # Run analysis with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            # Create progress task
            task_id = progress.add_task("Running analysis...", total=100)

            def progress_callback(analysis_progress: AnalysisProgress):
                """Update progress bar."""
                percentage = analysis_progress.get_percentage()
                progress.update(
                    task_id,
                    completed=percentage,
                    description=f"Analyzing: {analysis_progress.current_objective or 'complete'}",
                )

                if debug:
                    log.debug("analysis_progress",
                             current_objective=analysis_progress.current_objective,
                             completed_objectives=analysis_progress.completed_objectives,
                             total_objectives=analysis_progress.total_objectives,
                             percentage=percentage)

            # Run the analysis
            results = await orchestrator.run_analysis(
                objectives=objectives,
                progress_callback=progress_callback,
            )

            progress.update(task_id, completed=100, description="Analysis complete")

        # Create analysis run model
        analysis_run = orchestrator.create_analysis_run(results, deployment_id)

        if debug:
            log.debug("analysis_complete",
                     deployment_id=deployment_id,
                     status=analysis_run.status,
                     findings_count=len(analysis_run.findings),
                     recommendations_count=len(analysis_run.recommendations),
                     api_calls_used=analysis_run.api_calls_used,
                     duration_seconds=analysis_run.duration_seconds)

        # Validate performance targets
        _check_performance_targets(analysis_run, console, verbose or debug)

        # Display results
        console.print()
        if verbose:
            log.info("displaying_results",
                    findings_count=len(analysis_run.findings),
                    recommendations_count=len(analysis_run.recommendations))

        # Display standard terminal output
        display_analysis_results(results, analysis_run, console)

        # Save to JSON file if requested
        if output_file:
            if debug:
                log.debug("saving_json_report", output_file=str(output_file))
            save_json_report(analysis_run, output_file)
            console.print(f"\n[green]✓ JSON report saved to:[/green] {output_file}")

        # Generate Markdown report if requested
        if markdown:
            markdown_path = output_file or Path(f"{deployment_id}_report.md")
            if markdown_path.suffix != ".md":
                markdown_path = markdown_path.with_suffix(".md")

            if debug:
                log.debug("saving_markdown_report", output_file=str(markdown_path))
            save_markdown_report(analysis_run, results, markdown_path)
            console.print(f"[green]✓ Markdown report saved to:[/green] {markdown_path}")

        # Exit with appropriate code
        if analysis_run.status == "failed":
            console.print("\n[red]Analysis failed[/red]")
            raise typer.Exit(code=1)
        elif analysis_run.status == "partial":
            console.print("\n[yellow]Analysis partially completed[/yellow]")
            raise typer.Exit(code=2)
        else:
            console.print("\n[green]Analysis completed successfully[/green]")


def save_json_report(analysis_run, output_path: Path):
    """Save analysis results as JSON."""
    import json

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(analysis_run.model_dump(mode="json"), f, indent=2, default=str)


def save_markdown_report(analysis_run, results, output_path: Path):
    """Save analysis results as Markdown."""
    from cribl_hc.core.report_generator import MarkdownReportGenerator

    output_path.parent.mkdir(parents=True, exist_ok=True)

    generator = MarkdownReportGenerator()
    markdown_content = generator.generate(analysis_run, results)

    output_path.write_text(markdown_content)


def _check_performance_targets(analysis_run, console: Console, verbose: bool = False):
    """
    Check and display performance target validation.

    Args:
        analysis_run: Completed analysis run
        console: Rich console for output
        verbose: Whether to display detailed performance info
    """
    # Performance targets
    DURATION_TARGET = 300.0  # 5 minutes in seconds
    API_CALL_TARGET = 100

    duration = analysis_run.duration_seconds or 0.0
    api_calls = analysis_run.api_calls_used

    # Check duration target
    duration_ok = duration < DURATION_TARGET
    duration_percentage = (duration / DURATION_TARGET) * 100

    # Check API call budget
    api_calls_ok = api_calls < API_CALL_TARGET
    api_call_percentage = (api_calls / API_CALL_TARGET) * 100

    # Display warnings if targets are at risk or exceeded
    if not duration_ok:
        log.warning("performance_duration_exceeded",
                   duration_seconds=duration,
                   target_seconds=DURATION_TARGET)
        console.print(
            f"\n[red]⚠ Performance Warning:[/red] "
            f"Analysis took {duration:.1f}s (target: <{DURATION_TARGET}s)"
        )
    elif duration_percentage > 80 and verbose:
        console.print(
            f"[yellow]ℹ Performance:[/yellow] "
            f"Analysis took {duration:.1f}s ({duration_percentage:.0f}% of 5-minute target)"
        )

    if not api_calls_ok:
        log.warning("performance_api_budget_exceeded",
                   api_calls_used=api_calls,
                   api_call_target=API_CALL_TARGET)
        console.print(
            f"[red]⚠ Performance Warning:[/red] "
            f"Used {api_calls} API calls (budget: {API_CALL_TARGET})"
        )
    elif api_call_percentage > 80 and verbose:
        console.print(
            f"[yellow]ℹ Performance:[/yellow] "
            f"Used {api_calls}/{API_CALL_TARGET} API calls ({api_call_percentage:.0f}% of budget)"
        )

    # Log performance metrics for analysis
    if verbose:
        log.info("performance_metrics",
                duration_seconds=duration,
                duration_target=DURATION_TARGET,
                duration_ok=duration_ok,
                api_calls_used=api_calls,
                api_call_target=API_CALL_TARGET,
                api_calls_ok=api_calls_ok)
