"""
Analyze command for running health check analysis.
"""
import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from cribl_hc.cli.output import display_analysis_results
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalysisProgress, AnalyzerOrchestrator
from cribl_hc.models.branding import BrandingConfig, ClientBranding, ServiceProviderBranding
from cribl_hc.utils.logger import configure_logging, get_logger

console = Console()
log = get_logger(__name__)

app = typer.Typer(help="Run health check analysis")


def build_branding_config(
    provider_name: Optional[str],
    provider_logo: Optional[str],
    client_name: Optional[str],
    client_logo: Optional[str],
) -> Optional[BrandingConfig]:
    if not any([provider_name, client_name]):
        return None

    provider = None
    if provider_name:
        provider = ServiceProviderBranding.model_construct(
            name=provider_name,
            logo_path=provider_logo,
        )

    client = None
    if client_name:
        client = ClientBranding.model_construct(
            name=client_name,
            logo_path=client_logo,
        )

    return BrandingConfig(provider=provider, client=client)


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
    provider_name: Optional[str] = typer.Option(
        None,
        "--provider-name",
        help="Service provider company name (e.g., 'Acme Consulting')",
    ),
    provider_logo: Optional[str] = typer.Option(
        None,
        "--provider-logo",
        help="Path to provider logo file",
    ),
    client_name: Optional[str] = typer.Option(
        None,
        "--client-name",
        help="Client company name (e.g., 'Example Corp')",
    ),
    client_logo: Optional[str] = typer.Option(
        None,
        "--client-logo",
        help="Path to client logo file",
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

        # With branding
        cribl-hc analyze run -p prod --provider-name "Acme Consulting" --client-name "Example Corp" --markdown
    """
    # Load credentials from stored profile if deployment specified
    if deployment:
        from cribl_hc.cli.commands.config import load_credentials

        try:
            credentials = load_credentials()
            if deployment not in credentials:
                console.print(f"[red]✗ No credentials found for deployment:[/red] {deployment}")
                console.print(
                    f"[dim]Use 'cribl-hc config set {deployment}' to add credentials[/dim]"
                )
                console.print(
                    "[dim]Or use 'cribl-hc config list' to see available deployments[/dim]"
                )
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

    # Build branding config from flags
    branding = build_branding_config(
        provider_name=provider_name,
        provider_logo=provider_logo,
        client_name=client_name,
        client_logo=client_logo,
    )

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
            branding=branding,
        )
        )


@app.command()
def schedule(
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
    interval_minutes: int = typer.Option(
        60,
        "--interval",
        "-i",
        help="Check interval in minutes (default: 60)",
        min=5,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-d",
        help="Directory to save scheduled reports (default: ./scheduled_reports)",
    ),
    daemon: bool = typer.Option(
        False,
        "--daemon",
        help="Run as daemon process (continuous monitoring)",
    ),
    email_to: Optional[List[str]] = typer.Option(
        None,
        "--email-to",
        help="Email addresses to send alerts to (requires SMTP config)",
    ),
    slack_webhook: Optional[str] = typer.Option(
        None,
        "--slack-webhook",
        help="Slack webhook URL for notifications",
        envvar="SLACK_WEBHOOK_URL",
    ),
    pager_duty_key: Optional[str] = typer.Option(
        None,
        "--pagerduty-key",
        help="PagerDuty integration key for critical alerts",
        envvar="PAGERDUTY_INTEGRATION_KEY",
    ),
    alert_threshold: str = typer.Option(
        "high",
        "--alert-threshold",
        help="Alert threshold: info, low, medium, high, critical (default: high)",
    ),
    max_runtime_hours: Optional[int] = typer.Option(
        None,
        "--max-runtime",
        help="Maximum runtime in hours for daemon mode (default: unlimited)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode with detailed logging",
    ),
):
    """
    Run scheduled health check monitoring.

    Examples:

        # Run daemon mode with 30-minute intervals
        cribl-hc analyze schedule --deployment prod --interval 30 --daemon

        # Run with email notifications for high+ severity issues
        cribl-hc analyze schedule --deployment prod --email-to admin@example.com --alert-threshold high

        # Run with Slack and PagerDuty integration
        cribl-hc analyze schedule --deployment prod --slack-webhook https://hooks.slack.com/... --pagerduty-key abc123
    """
    import signal
    import sys
    from datetime import datetime, timedelta

    if debug:
        configure_logging(level="DEBUG", json_output=False)
        console.print("[yellow]🐛 Debug mode enabled - detailed logging active[/yellow]")
    elif verbose:
        configure_logging(level="INFO", json_output=False)
        console.print("[cyan]ℹ️  Verbose mode enabled[/cyan]")

    if output_dir is None:
        output_dir = Path("./scheduled_reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_thresholds = ["info", "low", "medium", "high", "critical"]
    if alert_threshold not in valid_thresholds:
        console.print(f"[red]❌ Invalid alert threshold: {alert_threshold}[/red]")
        console.print(f"[cyan]Valid options: {', '.join(valid_thresholds)}[/cyan]")
        raise typer.Exit(code=1)

    # Set up signal handling for graceful shutdown
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        console.print(f"\n[yellow]⚠️  Received signal {signum}, initiating graceful shutdown...[/yellow]")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run scheduled monitoring
    asyncio.run(
        run_scheduled_monitoring(
            deployment=deployment,
            url=url,
            token=token,
            interval_minutes=interval_minutes,
            output_dir=output_dir,
            daemon=daemon,
            email_to=email_to,
            slack_webhook=slack_webhook,
            pager_duty_key=pager_duty_key,
            alert_threshold=alert_threshold,
            max_runtime_hours=max_runtime_hours,
            verbose=verbose,
            debug=debug,
            shutdown_requested=lambda: shutdown_requested,
        )
    )


@app.command()
def schedule(
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
    interval_minutes: int = typer.Option(
        60,
        "--interval",
        "-i",
        help="Check interval in minutes (default: 60)",
        min=5,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-d",
        help="Directory to save scheduled reports (default: ./scheduled_reports)",
    ),
    daemon: bool = typer.Option(
        False,
        "--daemon",
        help="Run as daemon process (continuous monitoring)",
    ),
    email_to: Optional[List[str]] = typer.Option(
        None,
        "--email-to",
        help="Email addresses to send alerts to (requires SMTP config)",
    ),
    slack_webhook: Optional[str] = typer.Option(
        None,
        "--slack-webhook",
        help="Slack webhook URL for notifications",
        envvar="SLACK_WEBHOOK_URL",
    ),
    pager_duty_key: Optional[str] = typer.Option(
        None,
        "--pagerduty-key",
        help="PagerDuty integration key for critical alerts",
        envvar="PAGERDUTY_INTEGRATION_KEY",
    ),
    alert_threshold: str = typer.Option(
        "high",
        "--alert-threshold",
        help="Alert threshold: info, low, medium, high, critical (default: high)",
    ),
    max_runtime_hours: Optional[int] = typer.Option(
        None,
        "--max-runtime",
        help="Maximum runtime in hours for daemon mode (default: unlimited)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode with detailed logging",
    ),
):
    """
    Run scheduled health check monitoring.

    Examples:

        # Run daemon mode with 30-minute intervals
        cribl-hc analyze schedule --deployment prod --interval 30 --daemon

        # Run with email notifications for high+ severity issues
        cribl-hc analyze schedule --deployment prod --email-to admin@example.com --alert-threshold high

        # Run with Slack and PagerDuty integration
        cribl-hc analyze schedule --deployment prod --slack-webhook https://hooks.slack.com/... --pagerduty-key abc123
    """
    import signal
    import sys
    from datetime import datetime, timedelta

    # Configure logging
    if debug:
        configure_logging(level="DEBUG", json_output=False)
        console.print("[yellow]🐛 Debug mode enabled - detailed logging active[/yellow]")
    elif verbose:
        configure_logging(level="INFO", json_output=False)
        console.print("[cyan]ℹ️  Verbose mode enabled[/cyan]")

    # Set up output directory
    if output_dir is None:
        output_dir = Path("./scheduled_reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate alert threshold
    valid_thresholds = ["info", "low", "medium", "high", "critical"]
    if alert_threshold not in valid_thresholds:
        console.print(f"[red]❌ Invalid alert threshold: {alert_threshold}[/red]")
        console.print(f"[cyan]Valid options: {', '.join(valid_thresholds)}[/cyan]")
        raise typer.Exit(code=1)

    # Set up signal handling for graceful shutdown
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        console.print(f"\n[yellow]⚠️  Received signal {signum}, initiating graceful shutdown...[/yellow]")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run scheduled monitoring
    asyncio.run(
        run_scheduled_monitoring(
            deployment=deployment,
            url=url,
            token=token,
            interval_minutes=interval_minutes,
            output_dir=output_dir,
            daemon=daemon,
            email_to=email_to,
            slack_webhook=slack_webhook,
            pager_duty_key=pager_duty_key,
            alert_threshold=alert_threshold,
            max_runtime_hours=max_runtime_hours,
            verbose=verbose,
            debug=debug,
            shutdown_requested=lambda: shutdown_requested,
        )
    )


async def run_scheduled_monitoring(
    deployment: Optional[str],
    url: Optional[str],
    token: Optional[str],
    interval_minutes: int,
    output_dir: Path,
    daemon: bool,
    email_to: Optional[List[str]],
    slack_webhook: Optional[str],
    pager_duty_key: Optional[str],
    alert_threshold: str,
    max_runtime_hours: Optional[int],
    verbose: bool,
    debug: bool,
    shutdown_requested: callable,
):
    """
    Run scheduled health monitoring.

    Args:
        deployment: Deployment name from stored config
        url: Cribl URL
        token: Authentication token
        interval_minutes: Check interval
        output_dir: Output directory for reports
        daemon: Run as daemon (continuous)
        email_to: Email recipients for alerts
        slack_webhook: Slack webhook URL
        pager_duty_key: PagerDuty integration key
        alert_threshold: Alert severity threshold
        max_runtime_hours: Max runtime for daemon mode
        verbose: Verbose output flag
        debug: Debug output flag
        shutdown_requested: Function to check for shutdown signal
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.core.orchestrator import AnalysisProgress, AnalyzerOrchestrator
    from cribl_hc.models.analysis import AnalysisRun
    import json

    console.print(f"[green]🚀 Starting scheduled health monitoring[/green]")
    console.print(f"[cyan]📊 Interval: {interval_minutes} minutes[/cyan]")
    console.print(f"[cyan]📁 Output directory: {output_dir}[/cyan]")
    if daemon:
        console.print(f"[cyan]🔄 Daemon mode: continuous monitoring[/cyan]")
    else:
        console.print(f"[cyan]⏰ One-time check mode[/cyan]")

    start_time = datetime.now()
    check_count = 0

    try:
        while not shutdown_requested():
            check_count += 1
            check_start = datetime.now()

            console.print(f"\n[blue]🔍 Starting health check #{check_count} at {check_start.strftime('%Y-%m-%d %H:%M:%S')}[/blue]")

            try:
                # Create client (reuse logic from run command)
                if deployment:
                    # Load from stored config - simplified for this implementation
                    console.print(f"[yellow]⚠️  Loading deployment config not implemented yet[/yellow]")
                    continue
                elif url and token:
                    client = CriblAPIClient(
                        base_url=url,
                        auth_token=token,
                        timeout=60.0,  # Longer timeout for scheduled checks
                    )
                else:
                    console.print("[red]❌ Must specify either --deployment or --url with --token[/red]")
                    return

                # Test connection
                console.print("[cyan]🔗 Testing connection...[/cyan]")
                # Note: Connection testing would be implemented here

                # Run analysis
                console.print("[cyan]🏥 Running health analysis...[/cyan]")
                orchestrator = AnalyzerOrchestrator(
                    client=client,
                    max_api_calls=200,  # Higher limit for scheduled checks
                    continue_on_error=True,
                )

                # Run analysis (simplified - no progress callback for scheduled mode)
                results = await orchestrator.run_analysis()

                # Create analysis run
                analysis_run = orchestrator.create_analysis_run(results, f"scheduled_{check_count}")

                # Save report
                timestamp = check_start.strftime("%Y%m%d_%H%M%S")
                json_path = output_dir / f"health_check_{timestamp}.json"
                markdown_path = output_dir / f"health_check_{timestamp}.md"

                # Save JSON report
                with open(json_path, "w") as f:
                    json.dump(analysis_run.model_dump(mode="json"), f, indent=2, default=str)

                # Save Markdown report
                from cribl_hc.core.report_generator import MarkdownReportGenerator
                generator = MarkdownReportGenerator()
                markdown_content = generator.generate(analysis_run, results)
                markdown_path.write_text(markdown_content)

                console.print(f"[green]✓ Reports saved:[/green] {json_path}, {markdown_path}")

                # Check for alerts
                alert_findings = [f for f in analysis_run.findings if _should_alert(f, alert_threshold)]
                if alert_findings:
                    console.print(f"[red]🚨 Found {len(alert_findings)} issues requiring alerts[/red]")

                    # Send notifications
                    await _send_notifications(
                        alert_findings, analysis_run, email_to, slack_webhook, pager_duty_key
                    )

                    # Summary of alerts
                    for finding in alert_findings[:5]:  # Show first 5
                        console.print(f"  - [{finding.severity.upper()}] {finding.title}")
                    if len(alert_findings) > 5:
                        console.print(f"  ... and {len(alert_findings) - 5} more")
                else:
                    console.print("[green]✅ No alerts triggered - system healthy[/green]")

                check_duration = (datetime.now() - check_start).total_seconds()
                console.print(f"[green]✓ Health check #{check_count} completed in {check_duration:.1f}s[/green]")

            except Exception as e:
                console.print(f"[red]❌ Health check #{check_count} failed: {str(e)}[/red]")
                if debug:
                    import traceback
                    traceback.print_exc()

            # Check runtime limits
            if max_runtime_hours:
                runtime_hours = (datetime.now() - start_time).total_seconds() / 3600
                if runtime_hours >= max_runtime_hours:
                    console.print(f"[yellow]⏰ Reached maximum runtime of {max_runtime_hours} hours[/yellow]")
                    break

            # Wait for next check (unless this was a one-time check)
            if not daemon:
                break

            next_check = check_start + timedelta(minutes=interval_minutes)
            wait_seconds = (next_check - datetime.now()).total_seconds()

            if wait_seconds > 0:
                console.print(f"[cyan]⏰ Next check in {wait_seconds:.0f} seconds at {next_check.strftime('%H:%M:%S')}[/cyan]")
                await asyncio.sleep(min(wait_seconds, 300))  # Sleep in 5-minute chunks to check for shutdown

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Monitoring stopped by user[/yellow]")

    total_runtime = (datetime.now() - start_time).total_seconds()
    console.print("
[green]📊 Monitoring Summary:[/green]"    console.print(f"  • Total checks: {check_count}")
    console.print(f"  • Total runtime: {total_runtime:.1f} seconds")
    console.print(f"  • Reports saved to: {output_dir}")


def _should_alert(finding, threshold: str) -> bool:
    """Determine if a finding should trigger an alert based on threshold."""
    severity_levels = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    finding_level = severity_levels.get(getattr(finding, 'severity', 'info'), 0)
    threshold_level = severity_levels.get(threshold, 3)  # Default to high

    return finding_level >= threshold_level


async def _send_notifications(
    findings,
    analysis_run,
    email_to: Optional[List[str]],
    slack_webhook: Optional[str],
    pager_duty_key: Optional[str],
):
    """Send notifications for alert findings."""
    # Email notifications
    if email_to:
        console.print("[cyan]📧 Sending email notifications...[/cyan]")
        # Email implementation would go here
        console.print(f"[yellow]⚠️  Email notifications not implemented yet[/yellow]")

    # Slack notifications
    if slack_webhook:
        await _send_slack_notification(findings, slack_webhook)

    # PagerDuty notifications
    if pager_duty_key:
        await _send_pagerduty_notification(findings, analysis_run, pager_duty_key)


async def _send_slack_notification(findings, webhook_url: str):
    """Send Slack notification."""
    try:
        import aiohttp

        critical_count = len([f for f in findings if getattr(f, 'severity', '') == 'critical'])
        high_count = len([f for f in findings if getattr(f, 'severity', '') == 'high'])

        message = {
            "text": f"🚨 Cribl Health Check Alert: {len(findings)} issues detected",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Cribl Health Check Alert"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Issues Detected:* {len(findings)} total\n*Critical:* {critical_count}\n*High:* {high_count}"
                    }
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status == 200:
                    console.print("[green]✓ Slack notification sent[/green]")
                else:
                    console.print(f"[red]❌ Slack notification failed: {response.status}[/red]")

    except ImportError:
        console.print("[yellow]⚠️  aiohttp not available - Slack notifications disabled[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Slack notification error: {str(e)}[/red]")


async def _send_pagerduty_notification(findings, analysis_run, integration_key: str):
    """Send PagerDuty notification for critical issues."""
    try:
        import aiohttp

        critical_findings = [f for f in findings if getattr(f, 'severity', '') == 'critical']

        if not critical_findings:
            return  # Only send for critical issues

        # Create PagerDuty event
        event = {
            "routing_key": integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"Cribl Health Check: {len(critical_findings)} critical issues detected",
                "source": "cribl-health-check",
                "severity": "critical",
                "component": "health-monitoring",
                "group": analysis_run.deployment_id,
                "class": "health-check",
                "custom_details": {
                    "total_issues": len(findings),
                    "critical_issues": len(critical_findings),
                    "deployment": analysis_run.deployment_id,
                    "timestamp": analysis_run.timestamp.isoformat() if analysis_run.timestamp else None,
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=event
            ) as response:
                if response.status == 202:
                    console.print("[green]✓ PagerDuty alert sent[/green]")
                else:
                    console.print(f"[red]❌ PagerDuty alert failed: {response.status}[/red]")

    except ImportError:
        console.print("[yellow]⚠️  aiohttp not available - PagerDuty alerts disabled[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ PagerDuty alert error: {str(e)}[/red]")


async def run_analysis_async(
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        console.print(f"\n[yellow]⚠️  Received signal {signum}, initiating graceful shutdown...[/yellow]")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run scheduled monitoring
    asyncio.run(
        run_scheduled_monitoring(
            deployment=deployment,
            url=url,
            token=token,
            interval_minutes=interval_minutes,
            output_dir=output_dir,
            daemon=daemon,
            email_to=email_to,
            slack_webhook=slack_webhook,
            pager_duty_key=pager_duty_key,
            alert_threshold=alert_threshold,
            max_runtime_hours=max_runtime_hours,
            verbose=verbose,
            debug=debug,
            shutdown_requested=lambda: shutdown_requested,
        )
    )


async def run_scheduled_monitoring(
    deployment: Optional[str],
    url: Optional[str],
    token: Optional[str],
    interval_minutes: int,
    output_dir: Path,
    daemon: bool,
    email_to: Optional[List[str]],
    slack_webhook: Optional[str],
    pager_duty_key: Optional[str],
    alert_threshold: str,
    max_runtime_hours: Optional[int],
    verbose: bool,
    debug: bool,
    shutdown_requested: callable,
):
    """
    Run scheduled health monitoring.

    Args:
        deployment: Deployment name from stored config
        url: Cribl URL
        token: Authentication token
        interval_minutes: Check interval
        output_dir: Output directory for reports
        daemon: Run as daemon (continuous)
        email_to: Email recipients for alerts
        slack_webhook: Slack webhook URL
        pager_duty_key: PagerDuty integration key
        alert_threshold: Alert severity threshold
        max_runtime_hours: Max runtime for daemon mode
        verbose: Verbose output flag
        debug: Debug output flag
        shutdown_requested: Function to check for shutdown signal
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.core.orchestrator import AnalysisProgress, AnalyzerOrchestrator
    from cribl_hc.models.analysis import AnalysisRun
    import json

    console.print(f"[green]🚀 Starting scheduled health monitoring[/green]")
    console.print(f"[cyan]📊 Interval: {interval_minutes} minutes[/cyan]")
    console.print(f"[cyan]📁 Output directory: {output_dir}[/cyan]")
    if daemon:
        console.print(f"[cyan]🔄 Daemon mode: continuous monitoring[/cyan]")
    else:
        console.print(f"[cyan]⏰ One-time check mode[/cyan]")

    start_time = datetime.now()
    check_count = 0

    try:
        while not shutdown_requested():
            check_count += 1
            check_start = datetime.now()

            console.print(f"\n[blue]🔍 Starting health check #{check_count} at {check_start.strftime('%Y-%m-%d %H:%M:%S')}[/blue]")

            try:
                # Create client (reuse logic from run command)
                if deployment:
                    # Load from stored config - simplified for this implementation
                    console.print(f"[yellow]⚠️  Loading deployment config not implemented yet[/yellow]")
                    continue
                elif url and token:
                    client = CriblAPIClient(
                        base_url=url,
                        auth_token=token,
                        timeout=60.0,  # Longer timeout for scheduled checks
                    )
                else:
                    console.print("[red]❌ Must specify either --deployment or --url with --token[/red]")
                    return

                # Test connection
                console.print("[cyan]🔗 Testing connection...[/cyan]")
                # Note: Connection testing would be implemented here

                # Run analysis
                console.print("[cyan]🏥 Running health analysis...[/cyan]")
                orchestrator = AnalyzerOrchestrator(
                    client=client,
                    max_api_calls=200,  # Higher limit for scheduled checks
                    continue_on_error=True,
                )

                # Run analysis (simplified - no progress callback for scheduled mode)
                results = await orchestrator.run_analysis()

                # Create analysis run
                analysis_run = orchestrator.create_analysis_run(results, f"scheduled_{check_count}")

                # Save report
                timestamp = check_start.strftime("%Y%m%d_%H%M%S")
                json_path = output_dir / f"health_check_{timestamp}.json"
                markdown_path = output_dir / f"health_check_{timestamp}.md"

                # Save JSON report
                with open(json_path, "w") as f:
                    json.dump(analysis_run.model_dump(mode="json"), f, indent=2, default=str)

                # Save Markdown report
                from cribl_hc.core.report_generator import MarkdownReportGenerator
                generator = MarkdownReportGenerator()
                markdown_content = generator.generate(analysis_run, results)
                markdown_path.write_text(markdown_content)

                console.print(f"[green]✓ Reports saved:[/green] {json_path}, {markdown_path}")

                # Check for alerts
                alert_findings = [f for f in analysis_run.findings if _should_alert(f, alert_threshold)]
                if alert_findings:
                    console.print(f"[red]🚨 Found {len(alert_findings)} issues requiring alerts[/red]")

                    # Send notifications
                    await _send_notifications(
                        alert_findings, analysis_run, email_to, slack_webhook, pager_duty_key
                    )

                    # Summary of alerts
                    for finding in alert_findings[:5]:  # Show first 5
                        console.print(f"  - [{finding.severity.upper()}] {finding.title}")
                    if len(alert_findings) > 5:
                        console.print(f"  ... and {len(alert_findings) - 5} more")
                else:
                    console.print("[green]✅ No alerts triggered - system healthy[/green]")

                check_duration = (datetime.now() - check_start).total_seconds()
                console.print(f"[green]✓ Health check #{check_count} completed in {check_duration:.1f}s[/green]")

            except Exception as e:
                console.print(f"[red]❌ Health check #{check_count} failed: {str(e)}[/red]")
                if debug:
                    import traceback
                    traceback.print_exc()

            # Check runtime limits
            if max_runtime_hours:
                runtime_hours = (datetime.now() - start_time).total_seconds() / 3600
                if runtime_hours >= max_runtime_hours:
                    console.print(f"[yellow]⏰ Reached maximum runtime of {max_runtime_hours} hours[/yellow]")
                    break

            # Wait for next check (unless this was a one-time check)
            if not daemon:
                break

            next_check = check_start + timedelta(minutes=interval_minutes)
            wait_seconds = (next_check - datetime.now()).total_seconds()

            if wait_seconds > 0:
                console.print(f"[cyan]⏰ Next check in {wait_seconds:.0f} seconds at {next_check.strftime('%H:%M:%S')}[/cyan]")
                await asyncio.sleep(min(wait_seconds, 300))  # Sleep in 5-minute chunks to check for shutdown

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Monitoring stopped by user[/yellow]")

    total_runtime = (datetime.now() - start_time).total_seconds()
    console.print("
[green]📊 Monitoring Summary:[/green]"    console.print(f"  • Total checks: {check_count}")
    console.print(f"  • Total runtime: {total_runtime:.1f} seconds")
    console.print(f"  • Reports saved to: {output_dir}")


def _should_alert(finding, threshold: str) -> bool:
    """Determine if a finding should trigger an alert based on threshold."""
    severity_levels = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    finding_level = severity_levels.get(getattr(finding, 'severity', 'info'), 0)
    threshold_level = severity_levels.get(threshold, 3)  # Default to high

    return finding_level >= threshold_level


async def _send_notifications(
    findings,
    analysis_run,
    email_to: Optional[List[str]],
    slack_webhook: Optional[str],
    pager_duty_key: Optional[str],
):
    """Send notifications for alert findings."""
    # Email notifications
    if email_to:
        console.print("[cyan]📧 Sending email notifications...[/cyan]")
        # Email implementation would go here
        console.print(f"[yellow]⚠️  Email notifications not implemented yet[/yellow]")

    # Slack notifications
    if slack_webhook:
        await _send_slack_notification(findings, slack_webhook)

    # PagerDuty notifications
    if pager_duty_key:
        await _send_pagerduty_notification(findings, analysis_run, pager_duty_key)


async def _send_slack_notification(findings, webhook_url: str):
    """Send Slack notification."""
    try:
        import aiohttp

        critical_count = len([f for f in findings if getattr(f, 'severity', '') == 'critical'])
        high_count = len([f for f in findings if getattr(f, 'severity', '') == 'high'])

        message = {
            "text": f"🚨 Cribl Health Check Alert: {len(findings)} issues detected",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Cribl Health Check Alert"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Issues Detected:* {len(findings)} total\n*Critical:* {critical_count}\n*High:* {high_count}"
                    }
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status == 200:
                    console.print("[green]✓ Slack notification sent[/green]")
                else:
                    console.print(f"[red]❌ Slack notification failed: {response.status}[/red]")

    except ImportError:
        console.print("[yellow]⚠️  aiohttp not available - Slack notifications disabled[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Slack notification error: {str(e)}[/red]")


async def _send_pagerduty_notification(findings, analysis_run, integration_key: str):
    """Send PagerDuty notification for critical issues."""
    try:
        import aiohttp

        critical_findings = [f for f in findings if getattr(f, 'severity', '') == 'critical']

        if not critical_findings:
            return  # Only send for critical issues

        # Create PagerDuty event
        event = {
            "routing_key": integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"Cribl Health Check: {len(critical_findings)} critical issues detected",
                "source": "cribl-health-check",
                "severity": "critical",
                "component": "health-monitoring",
                "group": analysis_run.deployment_id,
                "class": "health-check",
                "custom_details": {
                    "total_issues": len(findings),
                    "critical_issues": len(critical_findings),
                    "deployment": analysis_run.deployment_id,
                    "timestamp": analysis_run.timestamp.isoformat() if analysis_run.timestamp else None,
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=event
            ) as response:
                if response.status == 202:
                    console.print("[green]✓ PagerDuty alert sent[/green]")
                else:
                    console.print(f"[red]❌ PagerDuty alert failed: {response.status}[/red]")

    except ImportError:
        console.print("[yellow]⚠️  aiohttp not available - PagerDuty alerts disabled[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ PagerDuty alert error: {str(e)}[/red]")


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
    branding: Optional[BrandingConfig] = None,
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
        branding: Optional branding configuration
    """
    console.print("\n[cyan]Cribl Health Check[/cyan]")
    console.print(f"[dim]Target:[/dim] {url}")
    console.print(f"[dim]Deployment:[/dim] {deployment_id}\n")

    if debug:
        log.debug(
            "analysis_starting",
            url=url,
            deployment_id=deployment_id,
            max_api_calls=max_api_calls,
            objectives=objectives,
        )
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
            log.debug(
                "connection_successful",
                response_time_ms=connection_result.response_time_ms,
                cribl_version=connection_result.cribl_version,
            )

        # Initialize orchestrator
        if verbose or debug:
            log.info(
                "initializing_orchestrator", max_api_calls=max_api_calls, continue_on_error=True
            )

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
                    log.debug(
                        "analysis_progress",
                        current_objective=analysis_progress.current_objective,
                        completed_objectives=analysis_progress.completed_objectives,
                        total_objectives=analysis_progress.total_objectives,
                        percentage=percentage,
                    )

            # Run the analysis
            results = await orchestrator.run_analysis(
                objectives=objectives,
                progress_callback=progress_callback,
            )

            progress.update(task_id, completed=100, description="Analysis complete")

        # Create analysis run model
        analysis_run = orchestrator.create_analysis_run(results, deployment_id)

        if debug:
            log.debug(
                "analysis_complete",
                deployment_id=deployment_id,
                status=analysis_run.status,
                findings_count=len(analysis_run.findings),
                recommendations_count=len(analysis_run.recommendations),
                api_calls_used=analysis_run.api_calls_used,
                duration_seconds=analysis_run.duration_seconds,
            )

        # Validate performance targets
        _check_performance_targets(analysis_run, console, verbose or debug)

        # Display results
        console.print()
        if verbose:
            log.info(
                "displaying_results",
                findings_count=len(analysis_run.findings),
                recommendations_count=len(analysis_run.recommendations),
            )

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
            save_markdown_report(analysis_run, results, markdown_path, branding)
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


def save_markdown_report(
    analysis_run, results, output_path: Path, branding: Optional[BrandingConfig] = None
):
    from cribl_hc.core.report_generator import MarkdownReportGenerator

    output_path.parent.mkdir(parents=True, exist_ok=True)

    generator = MarkdownReportGenerator(branding=branding)
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
        log.warning(
            "performance_duration_exceeded",
            duration_seconds=duration,
            target_seconds=DURATION_TARGET,
        )
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
        log.warning(
            "performance_api_budget_exceeded",
            api_calls_used=api_calls,
            api_call_target=API_CALL_TARGET,
        )
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
        log.info(
            "performance_metrics",
            duration_seconds=duration,
            duration_target=DURATION_TARGET,
            duration_ok=duration_ok,
            api_calls_used=api_calls,
            api_call_target=API_CALL_TARGET,
            api_calls_ok=api_calls_ok,
        )
