"""
Unit tests for Configuration TUI module.
"""

from unittest.mock import Mock, patch, AsyncMock

import pytest

from cribl_hc.cli.config_tui import ConfigTUI


class TestConfigTUI:
    """Test the ConfigTUI class."""

    def test_init(self):
        """Test TUI initialization."""
        tui = ConfigTUI()
        assert tui.console is not None
        assert tui.config_file is not None
        assert tui.running is True

    def test_show_welcome(self):
        """Test welcome banner display."""
        tui = ConfigTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui._show_welcome()
            # Should print welcome panel
            assert mock_print.called

    def test_show_menu(self):
        """Test menu display."""
        tui = ConfigTUI()

        with patch.object(tui.console, "print") as mock_print:
            tui._show_menu()
            # Should print menu panel
            assert mock_print.called

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    def test_get_menu_choice(self, mock_prompt):
        """Test menu choice input."""
        tui = ConfigTUI()

        mock_prompt.return_value = "1"
        choice = tui._get_menu_choice()
        assert choice == "1"

        mock_prompt.return_value = "q"
        choice = tui._get_menu_choice()
        assert choice == "q"

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.config_tui.Confirm.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.commands.config.save_credentials")
    @patch("cribl_hc.cli.config_tui.asyncio.run")
    def test_add_deployment_success(self, mock_run, mock_save, mock_load, mock_confirm, mock_prompt):
        """Test adding a new deployment successfully."""
        tui = ConfigTUI()

        # Mock user inputs
        mock_prompt.side_effect = [
            "prod",  # deployment ID
            "1",  # deployment type (cloud)
            "https://main-test.cribl.cloud",  # URL
            "test-token-123",  # token
        ]

        mock_load.return_value = {}  # No existing deployments
        mock_run.return_value = True  # Connection test passes
        mock_confirm.return_value = True

        with patch.object(tui.console, "print"):
            tui._add_deployment()

        # Verify credentials were saved
        mock_save.assert_called_once()
        saved_creds = mock_save.call_args[0][0]
        assert "prod" in saved_creds
        assert saved_creds["prod"]["url"] == "https://main-test.cribl.cloud"
        assert saved_creds["prod"]["token"] == "test-token-123"

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_add_deployment_empty_id(self, mock_load, mock_prompt):
        """Test adding deployment with empty ID."""
        tui = ConfigTUI()

        mock_prompt.return_value = ""  # Empty deployment ID
        mock_load.return_value = {}

        with patch.object(tui.console, "print") as mock_print:
            tui._add_deployment()

            # Should show error and not save
            error_calls = [call for call in mock_print.call_args_list if "cannot be empty" in str(call)]
            assert len(error_calls) > 0

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.config_tui.Confirm.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_add_deployment_already_exists_cancel(self, mock_load, mock_confirm, mock_prompt):
        """Test cancelling overwrite of existing deployment."""
        tui = ConfigTUI()

        mock_prompt.return_value = "prod"
        mock_load.return_value = {"prod": {"url": "https://old.com", "token": "old-token"}}
        mock_confirm.return_value = False  # Don't overwrite

        with patch.object(tui.console, "print") as mock_print:
            tui._add_deployment()

            # Should show cancellation message
            cancel_calls = [call for call in mock_print.call_args_list if "cancelled" in str(call).lower()]
            assert len(cancel_calls) > 0

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.config_tui.Confirm.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.commands.config.save_credentials")
    @patch("cribl_hc.cli.config_tui.asyncio.run")
    def test_edit_deployment_success(self, mock_run, mock_save, mock_load, mock_confirm, mock_prompt):
        """Test editing an existing deployment."""
        tui = ConfigTUI()

        existing_creds = {
            "prod": {"url": "https://old.com", "token": "old-token"}
        }

        mock_load.return_value = existing_creds
        mock_prompt.side_effect = [
            "prod",  # deployment to edit
            "https://new.com",  # new URL
        ]
        mock_confirm.side_effect = [
            True,  # update token
        ]
        mock_run.return_value = True  # Connection test passes

        # Mock password prompt for token
        with patch("cribl_hc.cli.config_tui.Prompt.ask", side_effect=[
            "prod",
            "https://new.com",
            "new-token",
        ]):
            with patch.object(tui.console, "print"):
                tui._edit_deployment()

        # Should save updated credentials
        mock_save.assert_called_once()

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_edit_deployment_not_found(self, mock_load, mock_prompt):
        """Test editing non-existent deployment."""
        tui = ConfigTUI()

        mock_load.return_value = {"prod": {"url": "https://test.com", "token": "token"}}
        mock_prompt.return_value = "nonexistent"

        with patch.object(tui.console, "print") as mock_print:
            tui._edit_deployment()

            # Should show not found error
            error_calls = [call for call in mock_print.call_args_list if "not found" in str(call).lower()]
            assert len(error_calls) > 0

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.config_tui.Confirm.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.commands.config.save_credentials")
    def test_delete_deployment_success(self, mock_save, mock_load, mock_confirm, mock_prompt):
        """Test deleting a deployment."""
        tui = ConfigTUI()

        mock_load.return_value = {
            "prod": {"url": "https://test.com", "token": "token"},
            "dev": {"url": "https://dev.com", "token": "dev-token"},
        }
        mock_prompt.return_value = "prod"
        mock_confirm.return_value = True  # Confirm deletion

        with patch.object(tui.console, "print"):
            tui._delete_deployment()

        # Verify deployment was removed
        mock_save.assert_called_once()
        saved_creds = mock_save.call_args[0][0]
        assert "prod" not in saved_creds
        assert "dev" in saved_creds

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.config_tui.Confirm.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_delete_deployment_cancelled(self, mock_load, mock_confirm, mock_prompt):
        """Test cancelling deployment deletion."""
        tui = ConfigTUI()

        mock_load.return_value = {"prod": {"url": "https://test.com", "token": "token"}}
        mock_prompt.return_value = "prod"
        mock_confirm.return_value = False  # Cancel deletion

        with patch.object(tui.console, "print") as mock_print:
            tui._delete_deployment()

            # Should show cancellation message
            cancel_calls = [call for call in mock_print.call_args_list if "cancelled" in str(call).lower()]
            assert len(cancel_calls) > 0

    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_view_deployments_empty(self, mock_load):
        """Test viewing deployments when none configured."""
        tui = ConfigTUI()

        mock_load.return_value = {}

        with patch.object(tui.console, "print") as mock_print:
            tui._view_deployments()

            # Should show no deployments message
            no_deps_calls = [call for call in mock_print.call_args_list if "No deployments" in str(call)]
            assert len(no_deps_calls) > 0

    @patch("cribl_hc.cli.commands.config.load_credentials")
    def test_view_deployments_with_data(self, mock_load):
        """Test viewing deployments with configured data."""
        tui = ConfigTUI()

        mock_load.return_value = {
            "prod": {"url": "https://prod.com", "token": "prod-token-12345678"},
            "dev": {"url": "https://dev.com", "token": "dev-token-12345678"},
        }

        with patch.object(tui.console, "print") as mock_print:
            tui._view_deployments()

            # Should print table and total count
            assert mock_print.called
            # Check that it printed the count
            count_calls = [call for call in mock_print.call_args_list if "Total:" in str(call) or "deployment" in str(call)]
            assert len(count_calls) > 0

    @patch("cribl_hc.cli.config_tui.Prompt.ask")
    @patch("cribl_hc.cli.config_tui.Confirm.ask")
    @patch("cribl_hc.cli.commands.config.load_credentials")
    @patch("cribl_hc.cli.config_tui.asyncio.run")
    def test_view_deployment_details_with_test(self, mock_run, mock_load, mock_confirm, mock_prompt):
        """Test viewing deployment details with connection test."""
        tui = ConfigTUI()

        mock_load.return_value = {
            "prod": {"url": "https://main-test.cribl.cloud", "token": "test-token"}
        }
        mock_prompt.return_value = "prod"
        mock_confirm.return_value = True  # Test connection
        mock_run.return_value = True  # Connection succeeds

        with patch.object(tui.console, "print"):
            tui._view_deployment_details()

        # Should run connection test
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_async_success(self):
        """Test successful connection test."""
        tui = ConfigTUI()

        # Mock successful connection
        mock_client = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.response_time_ms = 150.0
        mock_result.cribl_version = "4.5.0"

        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.test_connection.return_value = mock_result
        mock_client.is_edge = False

        with patch("cribl_hc.cli.config_tui.CriblAPIClient", return_value=mock_client):
            with patch.object(tui.console, "print"):
                result = await tui._test_connection_async("https://test.com", "token", verbose=True)

        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_async_failure(self):
        """Test failed connection test."""
        tui = ConfigTUI()

        # Mock failed connection
        mock_client = AsyncMock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error = "Connection timeout"

        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.test_connection.return_value = mock_result

        with patch("cribl_hc.cli.config_tui.CriblAPIClient", return_value=mock_client):
            with patch.object(tui.console, "print"):
                result = await tui._test_connection_async("https://test.com", "token", verbose=True)

        assert result is False

    def test_run_quit_immediately(self):
        """Test running TUI and quitting immediately."""
        tui = ConfigTUI()

        with patch.object(tui, "_show_welcome"), \
             patch.object(tui, "_show_menu"), \
             patch.object(tui, "_get_menu_choice", return_value="q"), \
             patch.object(tui.console, "print"), \
             patch.object(tui.console, "clear"):
            tui.run()

        # Should have stopped running
        assert tui.running is False
