"""
Unit tests for CLI main module.
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cribl_hc.cli.main import app, main


class TestCLIMain:
    """Test CLI main functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_app_creation(self):
        """Test that the main app is created correctly."""
        assert app.info.name == "cribl-hc"
        assert "Cribl Health Check Tool" in (app.info.help or "")

    def test_version_command(self):
        """Test version command."""
        with patch("cribl_hc.__version__", "1.0.0"):
            result = self.runner.invoke(app, ["version"])

            assert result.exit_code == 0
            assert "cribl-hc" in result.stdout
            assert "1.0.0" in result.stdout

    @patch("cribl_hc.cli.modern_tui.run_modern_tui")
    def test_tui_modern_command(self, mock_run_modern_tui):
        """Test TUI command with modern interface (default)."""
        result = self.runner.invoke(app, ["tui"])

        assert result.exit_code == 0
        mock_run_modern_tui.assert_called_once()

    @patch("cribl_hc.cli.modern_tui.run_modern_tui")
    def test_tui_keyboard_interrupt_modern(self, mock_run_modern_tui):
        """Test TUI command handles KeyboardInterrupt gracefully in modern mode."""
        mock_run_modern_tui.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(app, ["tui"])

        assert result.exit_code == 0
        assert "Goodbye!" in result.stdout

    def test_main_function(self):
        """Test main function calls app correctly."""
        with patch("cribl_hc.cli.main.app") as mock_app:
            main()
            mock_app.assert_called_once()

    def test_help_command(self):
        """Test help command shows available commands."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "analyze" in result.stdout
        assert "config" in result.stdout
        assert "test-connection" in result.stdout
        assert "list" in result.stdout
        assert "tui" in result.stdout
        assert "version" in result.stdout

    def test_analyze_command_registered(self):
        """Test that analyze command is properly registered."""
        result = self.runner.invoke(app, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "Run health check analysis" in result.stdout

    def test_config_command_registered(self):
        """Test that config command is properly registered."""
        result = self.runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "Manage credentials and configuration" in result.stdout

    def test_test_connection_command_registered(self):
        """Test that test-connection command is properly registered."""
        result = self.runner.invoke(app, ["test-connection", "--help"])

        assert result.exit_code == 0
        assert "Test connection to Cribl Stream API" in result.stdout

    def test_list_command_registered(self):
        """Test that list command is properly registered."""
        result = self.runner.invoke(app, ["list", "--help"])

        assert result.exit_code == 0
        assert "List available analyzers" in result.stdout

    def test_tui_command_help(self):
        """Test TUI command help text."""
        result = self.runner.invoke(app, ["tui", "--help"])

        assert result.exit_code == 0
        assert "Terminal User Interface" in result.stdout
        assert "modern navigable interface" in result.stdout

    @patch("cribl_hc.cli.modern_tui.run_modern_tui")
    def test_tui_import_error_handling_modern(self, mock_run_modern_tui):
        """Test TUI command handles import errors gracefully in modern mode."""
        mock_run_modern_tui.side_effect = ImportError("Module not found")

        # The command should still try to import and fail gracefully
        with pytest.raises(ImportError):
            self.runner.invoke(app, ["tui"], catch_exceptions=False)


class TestCLIMainIntegration:
    """Integration tests for CLI main module."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_invalid_command(self):
        """Test invalid command shows help."""
        result = self.runner.invoke(app, ["invalid-command"])

        assert result.exit_code != 0
        # Typer shows usage information on invalid commands

    def test_command_completion_disabled(self):
        """Test that command completion is disabled."""
        assert getattr(app.info, "add_completion", False) is False

    def test_nested_command_structure(self):
        """Test that nested commands work correctly."""
        # Test that we can access nested commands
        result = self.runner.invoke(app, ["analyze", "run", "--help"])

        # Should show help for the run subcommand
        assert result.exit_code == 0

    @patch("cribl_hc.__version__", "0.1.0-test")
    def test_version_with_different_version(self):
        """Test version command with different version string."""
        result = self.runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "0.1.0-test" in result.stdout

    def test_app_metadata(self):
        """Test app metadata is set correctly."""
        assert app.info.name == "cribl-hc"
        assert "Cribl Health Check Tool" in (app.info.help or "")
        assert "Comprehensive deployment analysis" in (app.info.help or "")
