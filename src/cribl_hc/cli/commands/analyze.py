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
from cribl_hc.utils.logger import get_logger


console = Console()
log = get_logger(__name__)

app = typer.Typer(help="Run health check analysis")


@app.command()
def run(
    url: str = typer.Option(
        ...,
        "--url",
        "-u",
        help="Cribl Stream leader URL (e.g., https://cribl.example.com)",
        envvar="CRIBL_URL",
    ),
    token: str = typer.Option(
        ...,
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
):
    """
    Run health check analysis on a Cribl Stream deployment.

    Examples:

        # Analyze all objectives
        cribl-hc analyze run --url https://cribl.example.com --token YOUR_TOKEN

        # Analyze specific objectives
        cribl-hc analyze run -u https://cribl.example.com -t TOKEN -o health -o config

        # Save results to file
        cribl-hc analyze run -u URL -t TOKEN --output report.json

        # Generate Markdown report
        cribl-hc analyze run -u URL -t TOKEN --markdown
    """
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

    # Test connection first
    console.print("[yellow]Testing connection...[/yellow]")
    async with CriblAPIClient(url, token) as client:
        connection_result = await client.test_connection()

        if not connection_result.success:
            console.print(f"[red]✗ Connection failed:[/red] {connection_result.error}")
            raise typer.Exit(code=1)

        console.print(
            f"[green]✓ Connected successfully[/green] "
            f"[dim]({connection_result.response_time_ms:.0f}ms)[/dim]"
        )
        console.print(f"[dim]Cribl version:[/dim] {connection_result.cribl_version}\n")

        # Initialize orchestrator
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

            # Run the analysis
            results = await orchestrator.run_analysis(
                objectives=objectives,
                progress_callback=progress_callback,
            )

            progress.update(task_id, completed=100, description="Analysis complete")

        # Create analysis run model
        analysis_run = orchestrator.create_analysis_run(results, deployment_id)

        # Display results in terminal
        console.print()
        display_analysis_results(results, analysis_run, console)

        # Save to JSON file if requested
        if output_file:
            save_json_report(analysis_run, output_file)
            console.print(f"\n[green]✓ JSON report saved to:[/green] {output_file}")

        # Generate Markdown report if requested
        if markdown:
            markdown_path = output_file or Path(f"{deployment_id}_report.md")
            if markdown_path.suffix != ".md":
                markdown_path = markdown_path.with_suffix(".md")

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
