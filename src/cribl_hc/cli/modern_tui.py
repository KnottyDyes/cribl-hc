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
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Button,
    Static,
    Label,
    DataTable,
    ProgressBar,
    TabbedContent,
    TabPane,
    ListView,
    ListItem,
    Input,
    Select,
    RadioSet,
    RadioButton,
)
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.reactive import reactive

from cribl_hc.cli.commands.config import load_credentials, save_credentials
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalyzerOrchestrator
from cribl_hc.core.report_generator import MarkdownReportGenerator
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class AddDeploymentDialog(ModalScreen):
    """Modal dialog for adding a new deployment."""

    CSS = """
    AddDeploymentDialog {
        align: center middle;
    }

    #dialog {
        width: 70;
        height: 35;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #dialog-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .input-row {
        height: 4;
        margin: 1 0;
    }

    .auth-section {
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    RadioSet {
        height: 3;
        margin: 0 0 1 0;
    }

    .button-row {
        height: 5;
        align: center middle;
        margin-top: 2;
    }

    .button-row Button {
        min-width: 12;
        margin: 0 1;
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

            # Authentication method selection
            with Container(classes="auth-section"):
                yield Label("Authentication Method:")
                with RadioSet(id="auth-method"):
                    yield RadioButton("Bearer Token (Quick Start)", value=True, id="radio-bearer")
                    yield RadioButton("API Credentials (Production)", id="radio-oauth")

                # Bearer token inputs
                with Container(id="bearer-inputs"):
                    with Container(classes="input-row"):
                        yield Label("Token:")
                        yield Input(placeholder="Your bearer token", password=True, id="input-token")

                # OAuth inputs (hidden by default)
                with Container(id="oauth-inputs", classes="hidden"):
                    with Container(classes="input-row"):
                        yield Label("Client ID:")
                        yield Input(placeholder="Your client ID", id="input-client-id")
                    with Container(classes="input-row"):
                        yield Label("Client Secret:")
                        yield Input(placeholder="Your client secret", password=True, id="input-client-secret")

            with Horizontal(classes="button-row"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Toggle auth input fields based on selection."""
        if event.pressed.id == "radio-bearer":
            self.query_one("#bearer-inputs").remove_class("hidden")
            self.query_one("#oauth-inputs").add_class("hidden")
        else:
            self.query_one("#bearer-inputs").add_class("hidden")
            self.query_one("#oauth-inputs").remove_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            # Get common input values
            deployment_id = self.query_one("#input-id", Input).value.strip()
            url = self.query_one("#input-url", Input).value.strip()

            if not deployment_id or not url:
                self.app.notify("Deployment ID and URL are required", severity="error")
                return

            # Determine auth method
            auth_method = self.query_one("#auth-method", RadioSet)
            use_bearer = auth_method.pressed_button.id == "radio-bearer"

            try:
                credentials = load_credentials()

                if use_bearer:
                    # Bearer token auth
                    token = self.query_one("#input-token", Input).value.strip()
                    if not token:
                        self.app.notify("Token is required", severity="error")
                        return
                    credentials[deployment_id] = {
                        "url": url,
                        "auth_type": "bearer",
                        "token": token
                    }
                else:
                    # OAuth auth
                    client_id = self.query_one("#input-client-id", Input).value.strip()
                    client_secret = self.query_one("#input-client-secret", Input).value.strip()
                    if not client_id or not client_secret:
                        self.app.notify("Client ID and Secret are required", severity="error")
                        return
                    credentials[deployment_id] = {
                        "url": url,
                        "auth_type": "oauth",
                        "client_id": client_id,
                        "client_secret": client_secret
                    }

                save_credentials(credentials)
                self.app.notify(f"Deployment '{deployment_id}' added successfully", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Failed to save: {str(e)}", severity="error")
        else:
            self.dismiss(False)


class EditDeploymentDialog(ModalScreen):
    """Modal dialog for editing an existing deployment."""

    CSS = """
    EditDeploymentDialog {
        align: center middle;
    }

    #dialog {
        width: 70;
        height: 35;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #dialog-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .input-row {
        height: 4;
        margin: 1 0;
    }

    .auth-section {
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .button-row {
        height: 5;
        align: center middle;
        margin-top: 2;
    }

    .button-row Button {
        min-width: 12;
        margin: 0 1;
    }
    """

    def __init__(self, deployment_id: str, credential_data: dict):
        super().__init__()
        self.deployment_id = deployment_id
        self.initial_url = credential_data.get("url", "")
        self.auth_type = credential_data.get("auth_type", "bearer")
        self.initial_token = credential_data.get("token", "")
        self.initial_client_id = credential_data.get("client_id", "")
        self.initial_client_secret = credential_data.get("client_secret", "")

    def compose(self) -> ComposeResult:
        """Create dialog widgets."""
        with Container(id="dialog"):
            yield Label(f"Edit Deployment: {self.deployment_id}", id="dialog-title")
            with Container(classes="input-row"):
                yield Label("URL:")
                yield Input(value=self.initial_url, id="input-url")

            # Authentication method selection
            with Container(classes="auth-section"):
                yield Label("Authentication Method:")
                with RadioSet(id="auth-method"):
                    yield RadioButton(
                        "Bearer Token (Quick Start)",
                        value=(self.auth_type == "bearer"),
                        id="radio-bearer"
                    )
                    yield RadioButton(
                        "API Credentials (Production)",
                        value=(self.auth_type == "oauth"),
                        id="radio-oauth"
                    )

                # Bearer token inputs
                bearer_classes = "bearer-inputs" if self.auth_type == "bearer" else "bearer-inputs hidden"
                with Container(id="bearer-inputs", classes=bearer_classes):
                    with Container(classes="input-row"):
                        yield Label("Token:")
                        yield Input(
                            value=self.initial_token,
                            placeholder="Your bearer token",
                            password=True,
                            id="input-token"
                        )

                # OAuth inputs
                oauth_classes = "oauth-inputs" if self.auth_type == "oauth" else "oauth-inputs hidden"
                with Container(id="oauth-inputs", classes=oauth_classes):
                    with Container(classes="input-row"):
                        yield Label("Client ID:")
                        yield Input(
                            value=self.initial_client_id,
                            placeholder="Your client ID",
                            id="input-client-id"
                        )
                    with Container(classes="input-row"):
                        yield Label("Client Secret:")
                        yield Input(
                            value=self.initial_client_secret,
                            placeholder="Your client secret",
                            password=True,
                            id="input-client-secret"
                        )

            with Horizontal(classes="button-row"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Toggle auth input fields based on selection."""
        if event.pressed.id == "radio-bearer":
            self.query_one("#bearer-inputs").remove_class("hidden")
            self.query_one("#oauth-inputs").add_class("hidden")
        else:
            self.query_one("#bearer-inputs").add_class("hidden")
            self.query_one("#oauth-inputs").remove_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            # Get common input values
            url = self.query_one("#input-url", Input).value.strip()

            if not url:
                self.app.notify("URL is required", severity="error")
                return

            # Determine which authentication method is selected
            auth_method = self.query_one("#auth-method", RadioSet)
            use_bearer = auth_method.pressed_button.id == "radio-bearer"

            # Update credentials based on auth method
            try:
                credentials = load_credentials()

                if use_bearer:
                    token = self.query_one("#input-token", Input).value.strip()
                    if not token:
                        self.app.notify("Bearer token is required", severity="error")
                        return
                    credentials[self.deployment_id] = {
                        "url": url,
                        "auth_type": "bearer",
                        "token": token
                    }
                else:
                    client_id = self.query_one("#input-client-id", Input).value.strip()
                    client_secret = self.query_one("#input-client-secret", Input).value.strip()
                    if not client_id or not client_secret:
                        self.app.notify("Client ID and Client Secret are required", severity="error")
                        return
                    credentials[self.deployment_id] = {
                        "url": url,
                        "auth_type": "oauth",
                        "client_id": client_id,
                        "client_secret": client_secret
                    }

                save_credentials(credentials)
                self.app.notify(f"Deployment '{self.deployment_id}' updated successfully", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.app.notify(f"Failed to save: {str(e)}", severity="error")
        else:
            self.dismiss(False)


class ExportResultsDialog(ModalScreen):
    """Modal dialog for exporting analysis results."""

    CSS = """
    ExportResultsDialog {
        align: center middle;
    }

    #export-dialog {
        width: 60;
        height: 23;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #export-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .export-row {
        height: 4;
        margin: 1 0;
    }

    .button-row {
        height: 5;
        align: center middle;
        margin-top: 2;
    }

    .button-row Button {
        min-width: 12;
        margin: 0 1;
    }
    """

    def __init__(self, analysis_run: AnalysisRun, results: Dict):
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
                    [("JSON", "json"), ("Markdown", "md")],
                    value="json",
                    id="select-format"
                )
            with Container(classes="export-row"):
                yield Label("Filename:")
                yield Input(
                    value=f"{self.analysis_run.deployment_id}_report",
                    id="input-filename"
                )
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

            # Add extension
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

    def _export_json(self, filepath: Path) -> None:
        """Export results as JSON."""
        with open(filepath, "w") as f:
            json.dump(
                self.analysis_run.model_dump(mode="json"),
                f,
                indent=2,
                default=str
            )

    def _export_markdown(self, filepath: Path) -> None:
        """Export results as Markdown."""
        generator = MarkdownReportGenerator()
        markdown_content = generator.generate(self.analysis_run, self.results)
        filepath.write_text(markdown_content)


class DeploymentList(Static):
    """Widget displaying configured deployments with health indicators."""

    deployments = reactive({})
    selected_deployment = reactive(None)

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
            # TODO: Add health indicator based on last analysis
            status_icon = "○"  # ● for healthy, ⚠ for warning, ✗ for error
            item = ListItem(
                Label(f"{status_icon} {deployment_id}\n  {url}"),
                id=f"deploy-{deployment_id}"
            )
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle deployment selection."""
        if event.item.id and event.item.id.startswith("deploy-"):
            deployment_id = event.item.id.replace("deploy-", "")
            self.selected_deployment = deployment_id


class AnalysisStatus(Static):
    """Widget showing current analysis status and progress."""

    current_deployment = reactive(None)
    status = reactive("Idle")
    progress = reactive(0)
    api_calls = reactive(0)
    max_api_calls = reactive(100)
    duration = reactive(0.0)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Label("Analysis Status", classes="panel-title")
        yield Label(id="status-deployment")
        yield Label(id="status-state")
        yield ProgressBar(id="status-progress", total=100)
        yield Label(id="status-api-calls")
        yield Label(id="status-duration")
        with Horizontal(classes="button-row"):
            yield Button("Run Analysis", id="btn-run-analysis", variant="primary")
            yield Button("Export Results", id="btn-export-results", variant="success")

    def watch_current_deployment(self, deployment: Optional[str]) -> None:
        """Update display when deployment changes."""
        label = self.query_one("#status-deployment", Label)
        if deployment:
            label.update(f"Current: {deployment}")
        else:
            label.update("Current: None")

    def watch_status(self, status: str) -> None:
        """Update display when status changes."""
        label = self.query_one("#status-state", Label)
        label.update(f"Status: {status}")

    def watch_progress(self, progress: int) -> None:
        """Update progress bar."""
        bar = self.query_one("#status-progress", ProgressBar)
        bar.update(progress=progress)

    def watch_api_calls(self, calls: int) -> None:
        """Update API call count."""
        label = self.query_one("#status-api-calls", Label)
        label.update(f"API Calls: {calls}/{self.max_api_calls}")

    def watch_duration(self, duration: float) -> None:
        """Update duration display."""
        label = self.query_one("#status-duration", Label)
        label.update(f"Duration: {duration:.1f}s")


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

        # Show all findings, sorted by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.severity, 4)
        )[:15]  # Limit to 15 for better viewport fit

        for finding in sorted_findings:
            # Icon and color scheme based on severity
            severity_display = {
                "critical": ("⚠", "red"),
                "high": ("⚠", "red"),
                "medium": ("ℹ", "yellow"),
                "low": ("·", "green")
            }

            icon, color = severity_display.get(finding.severity, ("·", "white"))

            # Create colored severity text
            severity_text = Text()
            severity_text.append(f"{icon} ", style=color)
            severity_text.append(finding.severity.upper(), style=f"bold {color}")

            component = ", ".join(finding.affected_components[:2])
            if len(finding.affected_components) > 2:
                component += f" +{len(finding.affected_components) - 2}"

            table.add_row(
                severity_text,
                finding.category,
                finding.title[:40],  # Truncate long titles
                component
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
    Screen {
        background: $surface;
    }

    .panel-title {
        color: $accent;
        text-style: bold;
        margin: 1;
    }

    .help-text {
        color: $text-muted;
        text-style: italic;
        margin: 1;
    }

    #deployment-list {
        height: auto;
        min-height: 10;
        max-height: 20;
        border: solid $primary;
        margin: 1;
    }

    .button-row {
        height: auto;
        align: center middle;
        margin: 1;
        padding: 1;
    }

    Button {
        margin: 0 1;
        min-width: 10;
    }

    #left-panel {
        width: 35%;
        border-right: solid $primary;
        padding: 1;
    }

    #right-panel {
        width: 65%;
        padding: 1;
        height: 100%;
    }

    #deployment-list-widget {
        height: 100%;
    }

    #deployment-buttons {
        dock: bottom;
    }

    #analysis-status {
        border: solid $primary;
        padding: 1;
        margin: 1;
        height: 18;
        max-height: 18;
    }

    #findings-panel {
        border: solid $primary;
        padding: 1;
        margin: 1;
        height: 1fr;
        min-height: 10;
    }

    #findings-scroll {
        height: 100%;
        width: 100%;
    }

    #findings-table {
        height: auto;
        width: 100%;
    }

    #results-history {
        border: solid $primary;
        padding: 1;
        margin: 1;
        height: 100%;
    }

    DataTable {
        height: auto;
    }

    ProgressBar {
        margin: 1 0;
    }

    Input {
        width: 100%;
    }

    Select {
        width: 100%;
    }

    .hidden {
        display: none;
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
    current_results: Optional[Dict] = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"):
                with Horizontal():
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

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE

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
        def check_result(added: bool) -> None:
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

            # Show edit dialog
            def check_result(updated: bool) -> None:
                if updated:
                    self.action_refresh()

            self.push_screen(EditDeploymentDialog(selected, current), check_result)
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
            status_widget.progress = 0

            # Test connection
            async with CriblAPIClient(url, token) as client:
                connection_result = await client.test_connection()

                if not connection_result.success:
                    status_widget.status = f"Failed: {connection_result.error}"
                    self.notify(f"Connection failed: {connection_result.error}", severity="error")
                    return

                status_widget.status = "Running analysis..."
                status_widget.progress = 10

                # Initialize orchestrator
                orchestrator = AnalyzerOrchestrator(
                    client=client,
                    max_api_calls=100,
                    continue_on_error=True,
                )

                # Progress callback
                def update_progress(analysis_progress):
                    percentage = analysis_progress.get_percentage()
                    status_widget.progress = int(percentage)
                    status_widget.api_calls = orchestrator.api_calls_used

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
                status_widget.progress = 100

                health_score = analysis_run.health_score.overall_score if analysis_run.health_score else "N/A"
                self.notify(
                    f"Analysis complete: {len(analysis_run.findings)} findings, Health Score: {health_score}",
                    severity="information",
                    timeout=5
                )

        except Exception as e:
            log.error("analysis_failed", error=str(e), deployment_id=deployment_id)
            status_widget.status = f"Error: {str(e)}"
            self.notify(f"Analysis failed: {str(e)}", severity="error")


def run_modern_tui() -> None:
    """Launch the modern Textual-based TUI."""
    app = CriblHealthCheckApp()
    app.run()
