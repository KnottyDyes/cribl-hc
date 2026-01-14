"""
Unit tests for CLI list analyzers command.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cribl_hc.cli.commands.list_analyzers import app, list_analyzers


class TestListAnalyzersCommand:
    """Test list analyzers CLI command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_basic(self, mock_get_analyzer, mock_list_objectives):
        """Test basic list analyzers command."""
        # Mock objectives
        mock_list_objectives.return_value = ["health", "config", "resource"]

        # Mock analyzer instances
        mock_health_analyzer = MagicMock()
        mock_health_analyzer.get_estimated_api_calls.return_value = 15
        mock_health_analyzer.get_required_permissions.return_value = ["read:workers", "read:system"]

        mock_config_analyzer = MagicMock()
        mock_config_analyzer.get_estimated_api_calls.return_value = 25
        mock_config_analyzer.get_required_permissions.return_value = [
            "read:pipelines",
            "read:routes",
        ]

        mock_resource_analyzer = MagicMock()
        mock_resource_analyzer.get_estimated_api_calls.return_value = 10
        mock_resource_analyzer.get_required_permissions.return_value = ["read:workers"]

        mock_get_analyzer.side_effect = [
            mock_health_analyzer,
            mock_config_analyzer,
            mock_resource_analyzer,
            mock_health_analyzer,  # Called again for total calculation
            mock_config_analyzer,
            mock_resource_analyzer,
        ]

        result = self.runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Available Analyzers (3 total)" in result.stdout
        assert "health" in result.stdout
        assert "config" in result.stdout
        assert "resource" in result.stdout
        assert "15" in result.stdout  # API calls for health
        assert "25" in result.stdout  # API calls for config
        assert "10" in result.stdout  # API calls for resource
        assert "Total API calls if all analyzers run: 50/100" in result.stdout

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_verbose(self, mock_get_analyzer, mock_list_objectives):
        """Test list analyzers command with verbose flag."""
        # Mock objectives
        mock_list_objectives.return_value = ["health"]

        # Mock analyzer instance
        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 20
        mock_analyzer.get_required_permissions.return_value = ["read:workers", "read:system"]

        mock_get_analyzer.return_value = mock_analyzer

        result = self.runner.invoke(app, ["--verbose"])

        assert result.exit_code == 0
        assert "Available Analyzers (1 total)" in result.stdout
        assert "health" in result.stdout
        assert "20" in result.stdout
        assert "read:workers, read:system" in result.stdout
        assert "Permissions" in result.stdout  # Verbose table includes permissions column

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    def test_list_analyzers_no_analyzers(self, mock_list_objectives):
        """Test list analyzers command when no analyzers are registered."""
        mock_list_objectives.return_value = []

        result = self.runner.invoke(app, [])

        assert result.exit_code == 0
        assert "No analyzers registered" in result.stdout

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_descriptions(self, mock_get_analyzer, mock_list_objectives):
        """Test that analyzer descriptions are shown correctly."""
        # Mock objectives
        mock_list_objectives.return_value = ["health", "config", "resource", "unknown"]

        # Mock analyzer instances
        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 5
        mock_analyzer.get_required_permissions.return_value = ["read:test"]

        mock_get_analyzer.return_value = mock_analyzer

        result = self.runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Worker health & system status monitoring" in result.stdout
        assert "Configuration validation & best practices" in result.stdout
        assert "CPU/memory/disk capacity planning" in result.stdout
        assert "Health check analysis" in result.stdout  # Default description for unknown

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_usage_examples(self, mock_get_analyzer, mock_list_objectives):
        """Test that usage examples are shown."""
        mock_list_objectives.return_value = ["health"]

        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 10
        mock_analyzer.get_required_permissions.return_value = ["read:test"]

        mock_get_analyzer.return_value = mock_analyzer

        result = self.runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Usage examples:" in result.stdout
        assert "cribl-hc analyze run" in result.stdout
        assert "cribl-hc analyze run -o health" in result.stdout

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_total_calculation(self, mock_get_analyzer, mock_list_objectives):
        """Test that total API calls are calculated correctly."""
        mock_list_objectives.return_value = ["health", "config"]

        # Mock analyzer instances with different API call counts
        mock_health_analyzer = MagicMock()
        mock_health_analyzer.get_estimated_api_calls.return_value = 30
        mock_health_analyzer.get_required_permissions.return_value = ["read:workers"]

        mock_config_analyzer = MagicMock()
        mock_config_analyzer.get_estimated_api_calls.return_value = 45
        mock_config_analyzer.get_required_permissions.return_value = ["read:pipelines"]

        # Mock the calls in order: first for table display, then for total calculation
        mock_get_analyzer.side_effect = [
            mock_health_analyzer,  # For table row
            mock_config_analyzer,  # For table row
            mock_health_analyzer,  # For total calculation
            mock_config_analyzer,  # For total calculation
        ]

        result = self.runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Total API calls if all analyzers run: 75/100" in result.stdout

    def test_list_analyzers_help(self):
        """Test list analyzers help command."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "List available analyzers" in result.stdout
        assert "--verbose" in result.stdout
        assert (
            "Show detailed information including" in result.stdout
            and "permissions" in result.stdout
        )

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_short_verbose_flag(self, mock_get_analyzer, mock_list_objectives):
        """Test list analyzers command with short verbose flag."""
        mock_list_objectives.return_value = ["health"]

        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 15
        mock_analyzer.get_required_permissions.return_value = ["read:workers"]

        mock_get_analyzer.return_value = mock_analyzer

        result = self.runner.invoke(app, ["-v"])

        assert result.exit_code == 0
        assert "Permissions" in result.stdout
        assert "read:workers" in result.stdout

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_table_formatting(self, mock_get_analyzer, mock_list_objectives):
        """Test that table formatting is correct."""
        mock_list_objectives.return_value = ["health", "config"]

        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 20
        mock_analyzer.get_required_permissions.return_value = ["read:workers", "read:system"]

        mock_get_analyzer.return_value = mock_analyzer

        # Test basic table
        result = self.runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Analyzer" in result.stdout
        assert "API Calls" in result.stdout
        assert "Description" in result.stdout

        # Test verbose table
        result_verbose = self.runner.invoke(app, ["--verbose"])
        assert result_verbose.exit_code == 0
        assert "Permissions" in result_verbose.stdout

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_empty_permissions(self, mock_get_analyzer, mock_list_objectives):
        """Test list analyzers with analyzer that has no required permissions."""
        mock_list_objectives.return_value = ["health"]

        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 10
        mock_analyzer.get_required_permissions.return_value = []  # No permissions

        mock_get_analyzer.return_value = mock_analyzer

        result = self.runner.invoke(app, ["--verbose"])

        assert result.exit_code == 0
        # Should handle empty permissions gracefully
        assert "health" in result.stdout

    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_error_handling(self, mock_get_analyzer, mock_list_objectives):
        """Test list analyzers handles analyzer errors gracefully."""
        mock_list_objectives.return_value = ["health"]

        # Mock analyzer that raises an exception
        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.side_effect = Exception("Test error")

        mock_get_analyzer.return_value = mock_analyzer

        # The command should handle exceptions gracefully
        with pytest.raises(Exception):
            self.runner.invoke(app, [], catch_exceptions=False)


class TestListAnalyzersFunction:
    """Test the list_analyzers function directly."""

    @patch("cribl_hc.cli.commands.list_analyzers.console")
    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_function_basic(
        self, mock_get_analyzer, mock_list_objectives, mock_console
    ):
        """Test list_analyzers function with basic parameters."""
        mock_list_objectives.return_value = ["health"]

        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 15
        mock_analyzer.get_required_permissions.return_value = ["read:workers"]

        mock_get_analyzer.return_value = mock_analyzer

        list_analyzers(verbose=False)

        # Verify console.print was called
        assert mock_console.print.call_count >= 1

    @patch("cribl_hc.cli.commands.list_analyzers.console")
    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    def test_list_analyzers_function_no_objectives(self, mock_list_objectives, mock_console):
        """Test list_analyzers function when no objectives are available."""
        mock_list_objectives.return_value = []

        list_analyzers(verbose=False)

        # Should print "No analyzers registered" message
        mock_console.print.assert_called_with("[yellow]No analyzers registered[/yellow]")

    @patch("cribl_hc.cli.commands.list_analyzers.console")
    @patch("cribl_hc.cli.commands.list_analyzers.list_objectives")
    @patch("cribl_hc.cli.commands.list_analyzers.get_analyzer")
    def test_list_analyzers_function_verbose(
        self, mock_get_analyzer, mock_list_objectives, mock_console
    ):
        """Test list_analyzers function with verbose=True."""
        mock_list_objectives.return_value = ["health"]

        mock_analyzer = MagicMock()
        mock_analyzer.get_estimated_api_calls.return_value = 20
        mock_analyzer.get_required_permissions.return_value = ["read:workers", "read:system"]

        mock_get_analyzer.return_value = mock_analyzer

        list_analyzers(verbose=True)

        # Verify console.print was called multiple times (table + total + examples)
        assert mock_console.print.call_count >= 3
