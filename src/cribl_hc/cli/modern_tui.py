import re
from urllib.parse import urlparse

"""
Modern Terminal User Interface for Cribl Health Check.

Built with Textual - provides a Pocker-style navigable interface with:
- Panel-based layout with keyboard navigation
- Real-time status updates
- Visual health indicators
- Interactive deployment management
- Results history and export (JSON/MD)
"""

import asyncio
import contextlib
import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from cribl_hc.cli.commands.config import load_credentials, save_credentials
from cribl_hc.cli.results_grouper import (
    get_severity_counts,
    get_worker_group_display_name,
    group_findings,
)
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalyzerOrchestrator
from cribl_hc.core.report_generator import MarkdownReportGenerator
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class PasteCurlDialog(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    CSS = """
    PasteCurlDialog {
        align: center middle;
    }

    #paste-dialog {
        width: 80;
        height: 22;
        padding: 1 2;
        border: round #61afef;
        background: #282c34;
    }

    #paste-title {
        width: 100%;
        text-align: center;
        padding-bottom: 1;
        text-style: bold;
        color: #56b6c2;
    }

    #paste-hint {
        width: 100%;
        color: #5c6370;
        margin-bottom: 1;
    }

    #paste-area {
        height: 1fr;
        background: #1e222a;
        border: solid #61afef;
    }

    #paste-area:focus {
        border: solid #56b6c2;
    }

    #paste-button-row {
        width: 100%;
        align: center middle;
        padding-top: 1;
        height: auto;
    }

    #paste-button-row Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="paste-dialog"):
            yield Label("Paste Curl Command or Token", id="paste-title")
            yield Label("Paste the full command or a bearer token below.", id="paste-hint")
            yield TextArea(id="paste-area")
            with Horizontal(classes="button-row", id="paste-button-row"):
                yield Button("Parse", variant="success", id="btn-parse")
                yield Button("Cancel", variant="default", id="btn-cancel-paste")

    def _parse_curl_command(self, text: str) -> tuple[Optional[str], Optional[str]]:
        import re
        from urllib.parse import urlparse

        url = None
        token = None
        text_clean = text.replace("\\\n", " ").replace("\n", " ")

        bearer_match = re.search(r"[Bb]earer\s+([A-Za-z0-9_\-\.]+)", text_clean)
        if bearer_match:
            token = bearer_match.group(1).strip()

        url_match = re.search(r"https?://[^\s\"'<>]+", text_clean)
        if url_match:
            try:
                parsed = urlparse(url_match.group(0).strip().strip("'\""))
                url = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                pass

        if not token and not url and len(text.strip()) > 20:
            token = text.strip()

        return url, token

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-parse":
            text = self.query_one("#paste-area", TextArea).text
            if text.strip():
                url, token = self._parse_curl_command(text)
                self.dismiss((url, token))
            else:
                self.app.notify("No text to parse", severity="warning")
        elif event.button.id == "btn-cancel-paste":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddDeploymentDialog(ModalScreen):
    """Modal dialog for adding a new deployment."""

    BINDINGS = [("escape", "cancel")]

    CSS = """
    AddDeploymentDialog {
        align: center middle;
    }

    #dialog {
        width: 64;
        height: auto;
        padding: 0 1;
        border: round $primary;
        background: $panel;
    }

    #dialog-title {
        width: 100%;
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $accent;
    }

    .input-row {
        padding: 0 2;
        margin-bottom: 1;
    }

    .input-row Label {
        margin-bottom: 1;
        color: $text-muted;
    }

    .button-row {
        margin-top: 1;
        padding: 1;
        width: 100%;
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        """Create dialog widgets."""
        with Container(id="dialog"):
            yield Label("Add Deployment", id="dialog-title")
            with Container(classes="input-row"):
                yield Label("Deployment ID:")
                yield Input(placeholder="e.g., prod, dev, staging", id="input-id")
            with Container(classes="input-row"):
                yield Label("URL:")
                yield Input(placeholder="https://main-myorg.cribl.cloud", id="input-url")
            with Container(classes="input-row"):
                yield Label("Token:")
                yield Input(placeholder="Your bearer token", password=True, id="input-token")
            with Horizontal(classes="button-row"):
                yield Button("Paste Curl/Token", variant="primary", id="btn-paste-token")
            with Horizontal(classes="button-row"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def _handle_paste_result(self, result: Optional[tuple[Optional[str], Optional[str]]]) -> None:
        if result is None:
            return
        url, token = result
        if url:
            self.query_one("#input-url", Input).value = url
        if token:
            self.query_one("#input-token", Input).value = token
        if url or token:
            msg = f"Applied: {'URL + ' if url else ''}{'Token' if token else ''}"
            self.app.notify(msg, severity="information")
        else:
            self.app.notify("No URL or token found in pasted text", severity="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-paste-token":
            self.app.push_screen(PasteCurlDialog(), self._handle_paste_result)
            return

        if event.button.id == "btn-save":
            deployment_id = self.query_one("#input-id", Input).value.strip()
            url_input = self.query_one("#input-url", Input).value.strip()
            token_input = self.query_one("#input-token", Input).value.strip()

            url = url_input
            token = token_input

            url_input_clean = url_input.replace("\\\n", " ").replace("\n", " ")
            token_input_clean = token_input.replace("\\\n", " ").replace("\n", " ")

            if "curl" in url_input.lower() or "authorization" in url_input.lower():
                bearer = re.search(
                    r"(?:Bearer\s+|bearer\s+)([^\s\"']+)", url_input_clean, re.IGNORECASE
                )
                if bearer:
                    token = bearer.group(1).strip()
                url_match = re.search(r"https?://[^\s\"'<>]+", url_input_clean, re.IGNORECASE)
                if url_match:
                    try:
                        parsed = urlparse(url_match.group(0).strip().strip("'\""))
                        url = f"{parsed.scheme}://{parsed.netloc}"
                    except Exception:
                        url = url_match.group(0).strip().strip("'\"")

            if "curl" in token_input.lower() or "authorization" in token_input.lower():
                bearer = re.search(
                    r"(?:Bearer\s+|bearer\s+)([^\s\"']+)", token_input_clean, re.IGNORECASE
                )
                if bearer:
                    token = bearer.group(1).strip()
                url_match = re.search(r"https?://[^\s\"'<>]+", token_input_clean, re.IGNORECASE)
                if url_match and not url_input:
                    try:
                        parsed = urlparse(url_match.group(0).strip().strip("'\""))
                        url = f"{parsed.scheme}://{parsed.netloc}"
                    except Exception:
                        url = url_match.group(0).strip().strip("'\"")

            if not deployment_id or not url or not token:
                self.app.notify("All fields are required", severity="error")
                return

            try:
                credentials = load_credentials()
                credentials[deployment_id] = {"url": url, "token": token}
                save_credentials(credentials)
                self.app.notify(
                    f"Deployment '{deployment_id}' added successfully", severity="information"
                )
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Failed to save: {str(e)}", severity="error")
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class EditDeploymentDialog(ModalScreen):
    """Modal dialog for editing an existing deployment."""

    BINDINGS = [("escape", "cancel")]

    CSS = """
    EditDeploymentDialog {
        align: center middle;
    }

    #dialog {
        width: 64;
        height: auto;
        padding: 0 1;
        border: round $primary;
        background: $panel;
    }

    #dialog-title {
        width: 100%;
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $accent;
    }

    .input-row {
        padding: 0 2;
        margin-bottom: 1;
    }

    .input-row Label {
        margin-bottom: 1;
        color: $text-muted;
    }

    .button-row {
        margin-top: 1;
        padding: 1;
        width: 100%;
        align: center middle;
    }
    """

    def __init__(self, deployment_id: str, url: str, token: str):
        super().__init__()
        self.deployment_id = deployment_id
        self.initial_url = url
        self.initial_token = token

    def compose(self) -> ComposeResult:
        """Create dialog widgets."""
        with Container(id="dialog"):
            yield Label(f"Edit Deployment: {self.deployment_id}", id="dialog-title")
            with Container(classes="input-row"):
                yield Label("URL:")
                yield Input(value=self.initial_url, id="input-url")
            with Container(classes="input-row"):
                yield Label("Token:")
                yield Input(value=self.initial_token, password=True, id="input-token")
            with Horizontal(classes="button-row"):
                yield Button("Paste Curl/Token", variant="primary", id="btn-paste-token")
            with Horizontal(classes="button-row"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def _handle_paste_result(self, result: Optional[tuple[Optional[str], Optional[str]]]) -> None:
        if result is None:
            return
        url, token = result
        if url:
            self.query_one("#input-url", Input).value = url
        if token:
            self.query_one("#input-token", Input).value = token
        if url or token:
            msg = f"Applied: {'URL + ' if url else ''}{'Token' if token else ''}"
            self.app.notify(msg, severity="information")
        else:
            self.app.notify("No URL or token found in pasted text", severity="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-paste-token":
            self.app.push_screen(PasteCurlDialog(), self._handle_paste_result)
            return

        if event.button.id == "btn-save":
            url = self.query_one("#input-url", Input).value.strip()
            token = self.query_one("#input-token", Input).value.strip()

            if not url or not token:
                self.app.notify("All fields are required", severity="error")
                return

            try:
                credentials = load_credentials()
                credentials[self.deployment_id] = {"url": url, "token": token}
                save_credentials(credentials)
                self.app.notify(
                    f"Deployment '{self.deployment_id}' updated successfully",
                    severity="information",
                )
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Failed to save: {str(e)}", severity="error")
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ExportResultsDialog(ModalScreen):
    """Modal dialog for exporting analysis results."""

    BINDINGS = [("escape", "cancel")]

    CSS = """
    ExportResultsDialog {
        align: center middle;
    }

    #export-dialog {
        width: 64;
        height: auto;
        padding: 0 1;
        border: round $primary;
        background: $panel;
    }

    #export-title {
        width: 100%;
        text-align: center;
        padding: 1;
        text-style: bold;
        color: $accent;
    }

    .export-row {
        padding: 0 2;
        margin-bottom: 1;
    }

    .export-row Label {
        margin-bottom: 1;
        color: $text-muted;
    }

    .button-row {
        margin-top: 1;
        padding: 1;
        width: 100%;
        align: center middle;
    }
    """

    def __init__(self, analysis_run: AnalysisRun, results: dict):
        super().__init__()
        self.analysis_run = analysis_run
        self.results = results

    def compose(self) -> ComposeResult:
        """Create export dialog widgets."""
        with Container(id="export-dialog"):
            yield Label("Export Analysis Results", id="export-title")
            with Container(classes="export-row"):
                yield Label("Format:")
                yield Select(
                    [("JSON", "json"), ("Markdown", "md")], value="json", id="select-format"
                )
            with Container(classes="export-row"):
                yield Label("Filename:")
                yield Input(value=f"{self.analysis_run.deployment_id}_report", id="input-filename")
            with Horizontal(classes="button-row"):
                yield Button("Export", variant="success", id="btn-export")
                yield Button("Cancel", variant="default", id="btn-cancel-export")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-export":
            format_select = self.query_one("#select-format", Select)
            filename_input = self.query_one("#input-filename", Input)

            format_type = format_select.value
            base_filename = filename_input.value.strip()

            if not base_filename:
                self.app.notify("Filename is required", severity="error")
                return

            filename = f"{base_filename}.{format_type}"
            filepath = Path(filename)

            try:
                if format_type == "json":
                    self._export_json(filepath)
                else:
                    self._export_markdown(filepath)

                self.app.notify(f"Exported to {filepath}", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Export failed: {str(e)}", severity="error")
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def _export_json(self, filepath: Path) -> None:
        """Export results as JSON."""
        with open(filepath, "w") as f:
            json.dump(self.analysis_run.model_dump(mode="json"), f, indent=2, default=str)

    def _export_markdown(self, filepath: Path) -> None:
        """Export results as Markdown."""
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate(self.analysis_run, self.results)
        filepath.write_text(markdown_content)


class ResultsScreen(ModalScreen):
    """Modal screen for displaying grouped analysis results."""

    BINDINGS = [("escape", "cancel")]

    CSS = """
    ResultsScreen {
        align: left top;
    }

    #results-container {
        width: 100%;
        height: 100%;
        border: round $primary;
        background: $panel;
        padding: 0;
    }

    #results-header {
        dock: top;
        height: 3;
        padding: 0 1;
        background: $primary;
        color: $panel;
        text-style: bold;
    }

    #results-title {
        text-align: center;
        width: 100%;
    }

    #results-scroll {
        height: 1fr;
        padding: 1 2;
    }

    #results-footer {
        dock: bottom;
        height: 3;
        align: center middle;
        padding: 0 1;
        background: $panel;
        border-top: solid $primary;
    }

    .summary-table {
        margin: 1 2;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }

    .worker-group-header {
        padding: 0 1;
        margin-top: 2;
        margin-right: 2;
        margin-bottom: 1;
        margin-left: 2;
        text-style: bold;
        color: $accent;
        border-bottom: heavy $accent;
    }

    .finding-card {
        margin: 1 2;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }
    """

    def __init__(self, analysis: AnalysisRun):
        super().__init__()
        self.analysis = analysis

    def compose(self) -> ComposeResult:
        """Create the results screen layout."""
        with Container(id="results-container"):
            with Container(id="results-header"):
                yield Label("Analysis Results", id="results-title")

            with VerticalScroll(id="results-scroll"):
                # Summary section
                yield Static(self._render_summary(), classes="summary-table")

                # Grouped findings
                if self.analysis.findings:
                    grouped = group_findings(self.analysis.findings)
                    current_worker_group = None

                    for group in grouped:
                        # Worker group header
                        if group.worker_group != current_worker_group:
                            current_worker_group = group.worker_group
                            group_name = get_worker_group_display_name(group.worker_group)
                            yield Static(f"━━━ {group_name} ━━━", classes="worker-group-header")

                        # Finding card
                        yield Static(self._render_finding(group), classes="finding-card")
                else:
                    yield Static("[yellow]No findings to display[/yellow]")

            with Horizontal(id="results-footer"):
                yield Button("Close", variant="primary", id="btn-close-results")
                yield Button("Export", variant="success", id="btn-export-from-results")

    def _render_summary(self) -> str:
        """Render the summary section as Rich markup."""
        counts = get_severity_counts(self.analysis.findings)
        total = len(self.analysis.findings)

        lines = [
            "[bold cyan]━━━ Analysis Summary ━━━[/bold cyan]",
            "",
            f"[bold]Total Findings:[/bold] {total}",
            f"[bold red]Critical:[/bold red] {counts['critical']}",
            f"[bold #ff8c00]High:[/bold #ff8c00] {counts['high']}",
            f"[bold yellow]Medium:[/bold yellow] {counts['medium']}",
            f"[bold cyan]Low:[/bold cyan] {counts['low']}",
            f"[bold]Info:[/bold] {counts['info']}",
        ]

        if self.analysis.health_score:
            score = self.analysis.health_score.overall_score
            if score >= 80:
                color = "green"
            elif score >= 60:
                color = "yellow"
            else:
                color = "red"
            lines.append(f"[bold]Health Score:[/bold] [{color}]{score:.1f}%[/{color}]")

        return "\n".join(lines)

    def _render_finding(self, group) -> str:
        """Render a single finding group as Rich markup."""
        first = group.findings[0]

        # Severity color mapping
        severity_colors = {
            "critical": "red",
            "high": "#ff8c00",
            "medium": "yellow",
            "low": "cyan",
            "info": "white",
        }
        color = severity_colors.get(group.severity, "white")

        # Build badges line
        badges = [f"[bold {color}]{group.severity.upper()}[/bold {color}]"]
        badges.append(f"[bold blue]{first.category}[/bold blue]")
        if group.is_grouped:
            badges.append(f"[bold magenta]{group.finding_count} instances[/bold magenta]")

        lines = [
            " • ".join(badges),
            f"[bold]{group.group_title}[/bold]",
        ]

        # Description (first sentence)
        desc = first.description.split(".")[0] + "." if first.description else ""
        if desc:
            lines.append(f"[dim]{desc}[/dim]")

        # Affected components
        if first.affected_components:
            all_components = []
            for finding in group.findings:
                all_components.extend(finding.affected_components)
            unique_components = list(dict.fromkeys(all_components))
            components_str = ", ".join(unique_components)
            lines.append(f"[dim]Components: {components_str}[/dim]")

        if first.estimated_impact:
            lines.append(f"[yellow]Impact: {first.estimated_impact}[/yellow]")

        if first.remediation_steps:
            lines.append("[cyan]Remediation:[/cyan]")
            for i, step in enumerate(first.remediation_steps, 1):
                lines.append(f"  {i}. {step}")

        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-close-results":
            self.dismiss(None)
        elif event.button.id == "btn-export-from-results":
            self.dismiss("export")

    def action_cancel(self) -> None:
        self.dismiss(None)


@dataclass
class DeploymentStatusInfo:
    """Holds status information for a deployment."""

    health_status: str  # "healthy", "warning", "critical", "unknown"
    last_analyzed: Optional[datetime] = None


class DeploymentListItem(ListItem):
    """A ListItem that displays detailed deployment information."""

    def __init__(self, deployment_id: str, url: str, status_info: DeploymentStatusInfo):
        super().__init__(id=f"deploy-{deployment_id}")
        self.deployment_id = deployment_id
        self.url = url
        self.status_info = status_info

    def compose(self) -> ComposeResult:
        """Render the list item content."""
        from rich.text import Text

        status_map = {
            "healthy": ("[green]●[/green]", "Healthy"),
            "warning": ("[yellow]⚠[/yellow]", "Warning"),
            "critical": ("[red]✗[/red]", "Critical"),
            "unknown": ("[#5c6370]○[/#5c6370]", "Unknown"),
        }
        icon, _ = status_map.get(self.status_info.health_status, status_map["unknown"])

        main_line_text = Text.from_markup(f"{icon} {self.deployment_id}", style="bold")
        url_line_text = Text(f"  {self.url}", style="#61afef")

        if self.status_info.last_analyzed:
            timestamp = self.status_info.last_analyzed.strftime("%Y-%m-%d %H:%M:%S")
            last_analyzed_text = Text(f"  Analyzed: {timestamp}", style="#5c6370")
        else:
            last_analyzed_text = Text("  Analyzed: Never", style="#5c6370")

        yield Static(main_line_text)
        yield Static(url_line_text)
        yield Static(last_analyzed_text)


class DeploymentList(Static):
    """Widget displaying configured deployments with health indicators."""

    deployments = reactive({})
    selected_deployment: reactive[Optional[str]] = reactive(None)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("Deployments", classes="panel-title")
        yield ListView(id="deployment-list")
        with Horizontal(classes="button-row", id="deployment-buttons"):
            yield Button("Add", id="btn-add-deployment", variant="success")
            yield Button("Edit", id="btn-edit-deployment", variant="primary")
            yield Button("Delete", id="btn-delete-deployment", variant="error")

    def on_mount(self) -> None:
        """Load deployments on mount."""
        self.load_deployments()

    def load_deployments(self) -> None:
        """Load deployments from config."""
        try:
            self.deployments = load_credentials()
            self.refresh_list()
        except Exception as e:
            log.error("failed_to_load_deployments", error=str(e))

    def refresh_list(self) -> None:
        """Refresh the deployment list display."""
        list_view = self.query_one("#deployment-list", ListView)
        list_view.clear()

        if not self.deployments:
            list_view.append(ListItem(Label("No deployments configured")))
            return

        for deployment_id, config in sorted(self.deployments.items()):
            url = config.get("url", "Unknown")

            # TODO: Replace with actual persisted status
            mock_status = random.choice(["healthy", "warning", "critical", "unknown"])
            mock_last_analyzed = datetime.now(timezone.utc) if mock_status != "unknown" else None

            status_info = DeploymentStatusInfo(
                health_status=mock_status,
                last_analyzed=mock_last_analyzed,
            )

            item = DeploymentListItem(deployment_id, url, status_info)
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle deployment selection."""
        if event.item.id and event.item.id.startswith("deploy-"):
            deployment_id = event.item.id.replace("deploy-", "")
            self.selected_deployment = deployment_id


class AnalysisStatus(Static):
    """Widget showing current analysis status and progress."""

    current_deployment: Optional[str] = reactive(None)
    status = reactive("Idle")
    progress = reactive(0.0)
    api_calls = reactive(0)
    max_api_calls = reactive(100)
    duration = reactive(0.0)
    health_score: reactive[Optional[float]] = reactive(None)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("Analysis Status", classes="panel-title")
        with Grid(id="status-grid"):
            yield Vertical(
                Label("Status", classes="status-label"),
                Label(self.status, id="status-state"),
                classes="status-box",
            )
            yield Vertical(
                Label("Health Score", classes="status-label"),
                Label("N/A", id="health-score-value"),
                classes="status-box",
            )
            yield Vertical(
                Label("API Calls", classes="status-label"),
                Label(f"{self.api_calls}/{self.max_api_calls}", id="status-api-calls"),
                classes="status-box",
            )
            yield Vertical(
                Label("Duration", classes="status-label"),
                Label(f"{self.duration:.1f}s", id="status-duration"),
                classes="status-box",
            )
        yield ProgressBar(id="status-progress", total=100)
        with Horizontal(classes="button-row"):
            yield Button("Run Analysis", id="btn-run-analysis", variant="primary")
            yield Button("Export Results", id="btn-export-results", variant="success")

    def watch_current_deployment(self, deployment: Optional[str]) -> None:
        """Update display when deployment changes."""
        pass

    def watch_status(self, status: str) -> None:
        """Update display when status changes."""
        with contextlib.suppress(Exception):
            self.query_one("#status-state", Label).update(status)

    def watch_progress(self, progress: float) -> None:
        """Update progress bar."""
        with contextlib.suppress(Exception):
            self.query_one("#status-progress", ProgressBar).update(progress=progress)

    def watch_api_calls(self, calls: int) -> None:
        """Update API call count."""
        try:
            label = self.query_one("#status-api-calls", Label)
            label.update(f"{calls}/{self.max_api_calls}")
        except Exception:
            pass

    def watch_duration(self, duration: float) -> None:
        """Update duration display."""
        try:
            label = self.query_one("#status-duration", Label)
            label.update(f"{duration:.1f}s")
        except Exception:
            pass

    def watch_health_score(self, score: Optional[float]) -> None:
        """Update health score display."""
        try:
            label = self.query_one("#health-score-value", Label)
            if score is None:
                label.update("[#5c6370]N/A[/#5c6370]")
                return

            if score >= 80:
                color = "#98c379"
            elif score >= 60:
                color = "#d19a66"
            else:
                color = "#e06c75"

            label.update(f"[{color}]{score:.1f}%[/{color}]")
        except Exception:
            pass


class FindingsPanel(Static):
    """Widget displaying recent findings from analysis."""

    findings = reactive([])

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("Recent Findings", classes="panel-title")
        with VerticalScroll(id="findings-scroll"):
            yield DataTable(id="findings-table", zebra_stripes=True, show_cursor=True)

    def on_mount(self) -> None:
        """Set up the findings table."""
        table = self.query_one("#findings-table", DataTable)
        table.add_columns("Severity", "Category", "Issue", "Component")
        table.cursor_type = "row"
        table.show_header = True

    def watch_findings(self, findings: list) -> None:
        """Update findings display."""
        from rich.text import Text

        table = self.query_one("#findings-table", DataTable)
        table.clear()

        if not findings:
            table.add_row(
                Text(
                    "No findings from the last analysis.", justify="center", style="italic #5c6370"
                )
            )
            return

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 5))

        for finding in sorted_findings:
            severity = finding.severity

            severity_map = {
                "critical": ("red", "black"),
                "high": ("#d19a66", "black"),
                "medium": ("yellow", "black"),
                "low": ("#98c379", "black"),
                "info": ("#5c6370", "white"),
            }
            bg_color, color = severity_map.get(severity, ("white", "black"))

            severity_text = Text(f" {severity.upper()} ", style=f"{color} on {bg_color}")

            component = ", ".join(finding.affected_components[:2])
            if len(finding.affected_components) > 2:
                component += f" … (+{len(finding.affected_components) - 2})"

            title = finding.title
            if len(title) > 50:
                title = title[:47] + "..."

            table.add_row(
                severity_text,
                finding.category,
                title,
                component,
            )


class ResultsHistory(Static):
    """Widget displaying analysis history."""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("Analysis History", classes="panel-title")
        yield DataTable(id="history-table", zebra_stripes=True)
        yield Label("Select a row to view details", classes="help-text")

    def on_mount(self) -> None:
        """Set up the history table."""
        table = self.query_one("#history-table", DataTable)
        table.add_columns("Date", "Deployment", "Status", "Findings", "Health Score")
        table.cursor_type = "row"
        # TODO: Load historical results from storage


class CriblHealthCheckApp(App):
    """Modern TUI for Cribl Health Check - Pocker-style interface."""

    CSS = """
    /*
     * Refined Industrial/Utilitarian Theme
     * Color Palette:
     * - surface: #1e222a (deep slate)
     * - panel: #282c34 (dark gray)
     * - primary: #61afef (muted blue)
     * - accent: #56b6c2 (vibrant cyan)
     * - success: #98c379 (green)
     * - warning: #d19a66 (orange)
     * - error: #e06c75 (red)
     * - text: #abb2bf
     * - text-muted: #5c6370
     */

    Screen {
        background: #1e222a;
        color: #abb2bf;
    }

    App {
        background: #1e222a;
    }

    Header {
        background: #282c34;
        border-bottom: heavy #61afef;
        color: #abb2bf;
        text-style: bold;
    }

    Footer {
        background: #282c34;
        border-top: solid #61afef;
    }

    TabbedContent > .tabs {
        background: #1e222a;
    }

    TabbedContent > .tabs > .tab--highlight {
         background: #56b6c2;
         color: #282c34;
    }

    .panel {
        border: round #61afef;
        background: #282c34;
        padding: 0 1;
        margin: 1;
    }

    #left-panel {
        width: 35%;
        min-width: 30;
    }

    #right-panel {
        width: 1fr;
    }

    .panel-title {
        color: #56b6c2;
        text-style: bold;
        padding: 1;
        background: #282c34;
        width: 100%;
        text-align: center;
    }

    .help-text {
        color: #5c6370;
        text-style: italic;
        padding: 0 1;
    }

    #deployment-list-widget {
        height: 100%;
    }

    #deployment-list {
        height: 1fr;
        border: none;
        background: #282c34;
        margin: 0;
    }

    #deployment-list > ListItem {
        padding: 1;
        border-bottom: solid #5c6370;
    }

    #deployment-list > ListItem.--highlight {
        background: #61afef;
        color: #282c34;
        text-style: bold;
    }

    .button-row {
        width: 100%;
        align: center middle;
        padding-top: 1;
    }

    Button {
        min-width: 8;
        width: auto;
        margin: 0 1;
        border: solid #61afef;
    }

    Button:hover {
        border: solid #56b6c2;
        color: #56b6c2;
    }

    #analysis-status {
        height: auto;
        padding: 0 1;
    }

    #status-grid {
        grid-size: 2;
        grid-gutter: 1;
        padding-top: 1;
    }

    .status-box {
        height: auto;
        padding: 1;
        border: solid #61afef;
        align: center middle;
    }

    #health-score-value {
        text-style: bold;
        margin-top: 1;
    }

    ProgressBar {
        margin-top: 1;
        background: #1e222a;
        color: #56b6c2;
    }

    #findings-panel {
        height: 1fr;
        min-height: 10;
        padding-bottom: 1;
    }

    #findings-scroll {
        height: 1fr;
        width: 100%;
        background: #282c34;
    }

    #findings-table {
        height: auto;
        width: 100%;
    }

    #findings-table > .datatable--header {
        background: #61afef;
        color: #282c34;
        text-style: bold;
    }

    #results-history {
        height: 100%;
    }

    Input, Select {
        background: #1e222a;
        border: solid #61afef;
    }

    Input:focus, Select:focus {
        border: solid #56b6c2;
    }
    """

    TITLE = "Cribl Health Check"
    SUB_TITLE = "Interactive Terminal Interface"

    BINDINGS = [
        Binding("f1", "help", "Help", show=True),
        Binding("f2", "run_analysis", "Run Analysis", show=True),
        Binding("f3", "export", "Export", show=True),
        Binding("f5", "refresh", "Refresh", show=True),
        Binding("ctrl+c,q", "quit", "Quit", show=True),
    ]

    # Store current analysis results
    current_analysis: Optional[AnalysisRun] = None
    current_results: Optional[dict] = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"), Horizontal():
                # Left panel: Deployments
                with Vertical(id="left-panel", classes="panel"):
                    yield DeploymentList(id="deployment-list-widget")

                # Right panels: Status and Findings
                with Vertical(id="right-panel", classes="panel"):
                    yield AnalysisStatus(id="analysis-status")
                    yield FindingsPanel(id="findings-panel")

            with TabPane("Results History", id="tab-history"):
                yield ResultsHistory(id="results-history")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-add-deployment":
            self.action_add_deployment()
        elif event.button.id == "btn-edit-deployment":
            self.action_edit_deployment()
        elif event.button.id == "btn-delete-deployment":
            self.action_delete_deployment()
        elif event.button.id == "btn-run-analysis":
            self.action_run_analysis()
        elif event.button.id == "btn-export-results":
            self.action_export()

    def action_help(self) -> None:
        """Show help information."""
        help_text = """
# Cribl Health Check TUI - Help

## Keyboard Shortcuts
- F1: Show this help
- F2: Run analysis on selected deployment
- F3: Export current results
- F5: Refresh deployment list
- Q / Ctrl+C: Quit

## Navigation
- Use Tab to switch between panels
- Arrow keys to navigate lists and tables
- Enter to select items

## Features
- **Dashboard Tab**: View deployments, run analyses, see findings
- **Results History Tab**: Browse past analysis results

## Deployment Management
- Click "Add" to add new deployment
- Select deployment from list to analyze
- Click "Delete" to remove deployment

## Analysis
- Select a deployment from the list
- Click "Run Analysis" or press F2
- Results appear in the findings panel
- Export results with F3 (JSON or Markdown)
        """
        self.notify(help_text, severity="information", timeout=10)

    def action_run_analysis(self) -> None:
        """Run health check analysis on selected deployment."""
        deployment_widget = self.query_one("#deployment-list-widget", DeploymentList)
        selected = deployment_widget.selected_deployment

        if not selected:
            # Get first deployment
            if deployment_widget.deployments:
                selected = list(deployment_widget.deployments.keys())[0]
            else:
                self.notify("No deployments configured", severity="warning")
                return

        # Run analysis in background
        asyncio.create_task(self.run_analysis_async(selected))

    def action_refresh(self) -> None:
        """Refresh deployment list."""
        deployment_widget = self.query_one("#deployment-list-widget", DeploymentList)
        deployment_widget.load_deployments()
        self.notify("Refreshed", severity="information")

    def action_add_deployment(self) -> None:
        """Add new deployment via modal dialog."""

        def check_result(added: Any) -> None:
            if added:
                self.action_refresh()

        self.push_screen(AddDeploymentDialog(), check_result)

    def action_edit_deployment(self) -> None:
        """Edit selected deployment via modal dialog."""
        deployment_widget = self.query_one("#deployment-list-widget", DeploymentList)
        selected = deployment_widget.selected_deployment

        if not selected:
            self.notify("No deployment selected", severity="warning")
            return

        try:
            credentials = load_credentials()
            if selected not in credentials:
                self.notify("Deployment not found", severity="error")
                return

            # Get current credentials
            current = credentials[selected]
            url = current.get("url", "")
            token = current.get("token", "")

            # Show edit dialog
            def check_result(updated: Any) -> None:
                if updated:
                    self.action_refresh()

            self.push_screen(EditDeploymentDialog(selected, url, token), check_result)
        except Exception as e:
            self.notify(f"Error: {str(e)}", severity="error")

    def action_delete_deployment(self) -> None:
        """Delete selected deployment."""
        deployment_widget = self.query_one("#deployment-list-widget", DeploymentList)
        selected = deployment_widget.selected_deployment

        if not selected:
            self.notify("No deployment selected", severity="warning")
            return

        try:
            credentials = load_credentials()
            if selected in credentials:
                del credentials[selected]
                save_credentials(credentials)
                self.notify(f"Deleted '{selected}'", severity="information")
                self.action_refresh()
            else:
                self.notify("Deployment not found", severity="error")
        except Exception as e:
            self.notify(f"Delete failed: {str(e)}", severity="error")

    def action_export(self) -> None:
        """Export current analysis results."""
        if not self.current_analysis or not self.current_results:
            self.notify("No analysis results to export", severity="warning")
            return

        self.push_screen(ExportResultsDialog(self.current_analysis, self.current_results))

    async def run_analysis_async(self, deployment_id: str) -> None:
        """
        Run health check analysis asynchronously.

        Args:
            deployment_id: Deployment to analyze
        """
        status_widget = self.query_one("#analysis-status", AnalysisStatus)
        findings_widget = self.query_one("#findings-panel", FindingsPanel)

        try:
            # Load credentials
            credentials = load_credentials()
            if deployment_id not in credentials:
                self.notify(f"Deployment '{deployment_id}' not found", severity="error")
                return

            cred = credentials[deployment_id]
            url = cred.get("url")
            token = cred.get("token")

            # Update status
            status_widget.current_deployment = deployment_id
            status_widget.status = "Connecting..."
            status_widget.progress = 0.0
            status_widget.health_score = None
            status_widget.api_calls = 0
            status_widget.duration = 0.0

            # Test connection
            async with CriblAPIClient(url, token) as client:
                connection_result = await client.test_connection()

                if not connection_result.success:
                    status_widget.status = f"Failed: {connection_result.error}"
                    self.notify(f"Connection failed: {connection_result.error}", severity="error")
                    return

                status_widget.status = "Running analysis..."
                status_widget.progress = 10.0

                # Initialize orchestrator
                orchestrator = AnalyzerOrchestrator(
                    client=client,
                    max_api_calls=100,
                    continue_on_error=True,
                )

                # Progress callback
                def update_progress(analysis_progress):
                    percentage = analysis_progress.get_percentage()
                    status_widget.progress = percentage
                    status_widget.api_calls = orchestrator.client.get_api_calls_used()

                # Run analysis
                start_time = datetime.now(timezone.utc)
                results = await orchestrator.run_analysis(
                    objectives=None,
                    progress_callback=update_progress,
                )

                # Update duration
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                status_widget.duration = duration

                # Create analysis run
                analysis_run = orchestrator.create_analysis_run(results, deployment_id)

                # Store results for export
                self.current_analysis = analysis_run
                self.current_results = results

                # Update findings
                findings_widget.findings = analysis_run.findings

                # Update status
                status_widget.status = "Completed"
                status_widget.progress = 100.0
                if analysis_run.health_score:
                    status_widget.health_score = analysis_run.health_score.overall_score

                health_score_display = (
                    f"{analysis_run.health_score.overall_score:.1f}%"
                    if analysis_run.health_score
                    else "N/A"
                )
                self.notify(
                    f"Analysis complete: {len(analysis_run.findings)} findings, Health Score: {health_score_display}",
                    severity="information",
                    timeout=5,
                )

                # Show grouped results in modal
                def handle_results_dismiss(action: Any) -> None:
                    if action == "export":
                        self.action_export()

                self.push_screen(ResultsScreen(analysis_run), handle_results_dismiss)

        except Exception as e:
            log.error("analysis_failed", error=str(e), deployment_id=deployment_id)
            status_widget.status = f"Error: {str(e)}"
            self.notify(f"Analysis failed: {str(e)}", severity="error")


def run_modern_tui() -> None:
    """Launch the modern Textual-based TUI."""
    app = CriblHealthCheckApp()
    app.run()
