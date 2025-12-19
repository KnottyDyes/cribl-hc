"""
Unit tests for Unified TUI module.
"""

from unittest.mock import Mock, patch, AsyncMock

import pytest

from cribl_hc.cli.unified_tui import UnifiedTUI


class TestUnifiedTUI:
    """Test the UnifiedTUI class."""

    def test_init(self):
        """Test TUI initialization."""
        tui = UnifiedTUI()
        assert tui.console is not None
        assert tui.config_tui is not None
        assert tui.results_tui is not None
        assert tui.running is True

    def test_show_welcome(self):
        """Test welcome banner display."""
        tui = UnifiedTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui._show_welcome()
            # Should print welcome panel
            assert mock_print.called

    def test_show_main_menu(self):
        """Test main menu display."""
        tui = UnifiedTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui._show_main_menu()
            # Should print menu panel
            assert mock_print.called

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    def test_get_menu_choice(self, mock_prompt):
        """Test menu choice input."""
        tui = UnifiedTUI()

        mock_prompt.return_value = "1"
        choice = tui._get_menu_choice()
        assert choice == "1"

        mock_prompt.return_value = "q"
        choice = tui._get_menu_choice()
        assert choice == "q"

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    def test_manage_deployments_add(self, mock_prompt):
        """Test managing deployments - add option."""
        tui = UnifiedTUI()

        # User selects option 1 (add), then back
        mock_prompt.side_effect = ["1", ""]

        with patch.object(tui.config_tui, "_add_deployment") as mock_add, \
             patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"):
            tui._manage_deployments()
            mock_add.assert_called_once()

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    def test_manage_deployments_back(self, mock_prompt):
        """Test managing deployments - back option."""
        tui = UnifiedTUI()

        # User selects back immediately
        mock_prompt.return_value = "b"

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"):
            tui._manage_deployments()
            # Should return without calling any config_tui methods

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_run_health_check_no_deployments(self, mock_load, mock_prompt):
        """Test running health check with no configured deployments."""
        tui = UnifiedTUI()

        mock_load.return_value = {}  # No deployments
        mock_prompt.return_value = ""  # Press enter to continue

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print") as mock_print:
            tui._run_health_check()

            # Should show no deployments message
            no_deps_calls = [call for call in mock_print.call_args_list
                           if "No deployments" in str(call)]
            assert len(no_deps_calls) > 0

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.unified_tui.asyncio.run")
    def test_run_health_check_success(self, mock_run, mock_load, mock_prompt):
        """Test running health check successfully."""
        tui = UnifiedTUI()

        # Mock credentials
        mock_load.return_value = {
            "prod": {"url": "https://test.com", "token": "test-token"}
        }

        # User selects prod deployment, then presses enter to continue
        mock_prompt.side_effect = ["prod", ""]

        # Mock successful analysis
        from cribl_hc.models.analysis import AnalysisRun
        from datetime import datetime, timezone

        mock_analysis_run = AnalysisRun(
            id="test-run",
            deployment_id="prod",
            started_at=datetime.now(timezone.utc),
            status="completed",
            objectives_analyzed=["health"],
            findings=[],
            recommendations=[],
            api_calls_used=10
        )
        mock_run.return_value = mock_analysis_run

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"), \
             patch.object(tui.results_tui, "display") as mock_display:
            tui._run_health_check()

            # Should display results
            mock_display.assert_called_once_with(mock_analysis_run)

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_run_health_check_load_error(self, mock_load, mock_prompt):
        """Test running health check with credential load error."""
        tui = UnifiedTUI()

        # Mock credential loading error
        mock_load.side_effect = Exception("Failed to load")
        mock_prompt.return_value = ""  # Press enter to continue

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print") as mock_print:
            tui._run_health_check()

            # Should show error message
            error_calls = [call for call in mock_print.call_args_list
                          if "Error loading credentials" in str(call)]
            assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_run_analysis_async_connection_failure(self):
        """Test async analysis with connection failure."""
        tui = UnifiedTUI()

        # Mock failed connection
        mock_client = AsyncMock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Connection refused"

        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.test_connection.return_value = mock_result

        with patch("cribl_hc.cli.unified_tui.CriblAPIClient", return_value=mock_client), \
             patch.object(tui.console, "print"):
            result = await tui._run_analysis_async("https://test.com", "token", "test-deploy")

            # Should return None on connection failure
            assert result is None

    @pytest.mark.asyncio
    async def test_run_analysis_async_success(self):
        """Test async analysis success."""
        from cribl_hc.models.analysis import AnalysisRun
        from datetime import datetime, timezone

        tui = UnifiedTUI()

        # Mock successful connection and analysis
        mock_client = AsyncMock()
        mock_conn_result = Mock()
        mock_conn_result.success = True
        mock_conn_result.response_time_ms = 100.0
        mock_conn_result.cribl_version = "4.5.0"

        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.test_connection.return_value = mock_conn_result

        # Mock orchestrator
        mock_orchestrator = AsyncMock()
        mock_results = {}
        mock_orchestrator.run_analysis.return_value = mock_results

        mock_analysis_run = AnalysisRun(
            id="test-run",
            deployment_id="test-deploy",
            started_at=datetime.now(timezone.utc),
            status="completed",
            objectives_analyzed=["health"],
            findings=[],
            recommendations=[],
            api_calls_used=10
        )
        mock_orchestrator.create_analysis_run.return_value = mock_analysis_run

        with patch("cribl_hc.cli.unified_tui.CriblAPIClient", return_value=mock_client), \
             patch("cribl_hc.cli.unified_tui.AnalyzerOrchestrator", return_value=mock_orchestrator), \
             patch.object(tui.console, "print"):
            result = await tui._run_analysis_async("https://test.com", "token", "test-deploy")

            # Should return analysis run
            assert result is not None
            assert result.deployment_id == "test-deploy"

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    def test_view_recent_results(self, mock_prompt):
        """Test viewing recent results (placeholder)."""
        tui = UnifiedTUI()

        mock_prompt.return_value = ""  # Press enter to continue

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"):
            tui._view_recent_results()
            # Just verify it doesn't crash - functionality is placeholder

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    def test_show_settings(self, mock_prompt):
        """Test showing settings (placeholder)."""
        tui = UnifiedTUI()

        mock_prompt.return_value = ""  # Press enter to continue

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"):
            tui._show_settings()
            # Just verify it doesn't crash - functionality is placeholder

    def test_quit(self):
        """Test quit functionality."""
        tui = UnifiedTUI()

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"):
            tui._quit()

            # Should set running to False
            assert tui.running is False

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.unified_tui.asyncio.run")
    def test_run_health_check_select_by_number(self, mock_run, mock_load, mock_prompt):
        """Test selecting deployment by number."""
        tui = UnifiedTUI()

        # Mock credentials with multiple deployments
        mock_load.return_value = {
            "prod": {"url": "https://prod.com", "token": "prod-token"},
            "dev": {"url": "https://dev.com", "token": "dev-token"},
        }

        # User selects deployment by number (2 = "prod" after sorting)
        mock_prompt.side_effect = ["2", ""]  # Select number 2, then press enter to continue

        # Mock successful analysis
        from cribl_hc.models.analysis import AnalysisRun
        from datetime import datetime, timezone

        mock_analysis_run = AnalysisRun(
            id="test-run",
            deployment_id="prod",
            started_at=datetime.now(timezone.utc),
            status="completed",
            objectives_analyzed=["health"],
            findings=[],
            recommendations=[],
            api_calls_used=10
        )
        mock_run.return_value = mock_analysis_run

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"), \
             patch.object(tui.results_tui, "display") as mock_display:
            tui._run_health_check()

            # Should display results for "prod" (2nd in sorted list)
            mock_display.assert_called_once()

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.unified_tui.asyncio.run")
    def test_run_health_check_select_by_default(self, mock_run, mock_load, mock_prompt):
        """Test selecting deployment by pressing Enter (default)."""
        tui = UnifiedTUI()

        # Mock credentials
        mock_load.return_value = {
            "prod": {"url": "https://prod.com", "token": "prod-token"},
            "dev": {"url": "https://dev.com", "token": "dev-token"},
        }

        # User presses Enter (empty string) to select default (first sorted = "dev")
        mock_prompt.side_effect = ["", ""]  # Empty for default, then press enter to continue

        # Mock successful analysis
        from cribl_hc.models.analysis import AnalysisRun
        from datetime import datetime, timezone

        mock_analysis_run = AnalysisRun(
            id="test-run",
            deployment_id="dev",
            started_at=datetime.now(timezone.utc),
            status="completed",
            objectives_analyzed=["health"],
            findings=[],
            recommendations=[],
            api_calls_used=10
        )
        mock_run.return_value = mock_analysis_run

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print"), \
             patch.object(tui.results_tui, "display") as mock_display:
            tui._run_health_check()

            # Should display results for default deployment
            mock_display.assert_called_once()

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_run_health_check_invalid_number_then_valid(self, mock_load, mock_prompt):
        """Test selecting deployment with invalid number, then valid selection."""
        tui = UnifiedTUI()

        # Mock credentials
        mock_load.return_value = {
            "prod": {"url": "https://prod.com", "token": "prod-token"}
        }

        # User enters invalid number (5), then valid name (prod), then press enter
        mock_prompt.side_effect = ["5", "prod", ""]

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print") as mock_print, \
             patch("cribl_hc.cli.unified_tui.asyncio.run"):
            tui._run_health_check()

            # Should show invalid number error
            error_calls = [call for call in mock_print.call_args_list
                          if "Invalid number" in str(call)]
            assert len(error_calls) > 0

    @patch("cribl_hc.cli.unified_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_run_health_check_invalid_name_then_valid(self, mock_load, mock_prompt):
        """Test selecting deployment with invalid name, then valid selection."""
        tui = UnifiedTUI()

        # Mock credentials
        mock_load.return_value = {
            "prod": {"url": "https://prod.com", "token": "prod-token"}
        }

        # User enters invalid name (staging), then valid name (prod), then press enter
        mock_prompt.side_effect = ["staging", "prod", ""]

        with patch.object(tui.console, "clear"), \
             patch.object(tui.console, "print") as mock_print, \
             patch("cribl_hc.cli.unified_tui.asyncio.run"):
            tui._run_health_check()

            # Should show not found error
            error_calls = [call for call in mock_print.call_args_list
                          if "not found" in str(call)]
            assert len(error_calls) > 0

    def test_run_quit_immediately(self):
        """Test running TUI and quitting immediately."""
        tui = UnifiedTUI()

        with patch.object(tui, "_show_welcome"), \
             patch.object(tui, "_show_main_menu"), \
             patch.object(tui, "_get_menu_choice", return_value="q"), \
             patch.object(tui, "_quit") as mock_quit:
            tui.run()

            # Should have called quit
            mock_quit.assert_called_once()
