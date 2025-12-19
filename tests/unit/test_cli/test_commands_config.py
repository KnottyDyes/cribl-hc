"""
Unit tests for config CLI command.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cribl_hc.cli.commands.config import (
    app,
    ensure_config_dir,
    get_or_create_key,
    load_credentials,
    save_credentials,
    CONFIG_DIR,
    CREDENTIALS_FILE,
    KEY_FILE,
)


runner = CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create temporary config directory for testing."""
    config_dir = tmp_path / ".cribl-hc"
    credentials_file = config_dir / "credentials.enc"
    key_file = config_dir / ".key"

    # Patch the module-level constants
    monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
    monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

    return config_dir


class TestEnsureConfigDir:
    """Test suite for ensure_config_dir function."""

    def test_creates_directory(self, temp_config_dir, monkeypatch):
        """Test that config directory is created."""
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)

        ensure_config_dir()

        assert temp_config_dir.exists()
        assert temp_config_dir.is_dir()

    def test_sets_restrictive_permissions(self, temp_config_dir, monkeypatch):
        """Test that directory has restrictive permissions."""
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)

        ensure_config_dir()

        # Check permissions (0o700 = rwx------)
        import stat
        mode = temp_config_dir.stat().st_mode
        assert stat.S_IMODE(mode) == 0o700

    def test_idempotent(self, temp_config_dir, monkeypatch):
        """Test that calling multiple times is safe."""
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)

        ensure_config_dir()
        ensure_config_dir()  # Should not raise

        assert temp_config_dir.exists()


class TestGetOrCreateKey:
    """Test suite for get_or_create_key function."""

    def test_creates_new_key(self, temp_config_dir, monkeypatch):
        """Test that new encryption key is created."""
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        key = get_or_create_key()

        assert key_file.exists()
        assert len(key) > 0
        assert isinstance(key, bytes)

    def test_returns_existing_key(self, temp_config_dir, monkeypatch):
        """Test that existing key is returned."""
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Create key first time
        key1 = get_or_create_key()

        # Get key second time
        key2 = get_or_create_key()

        # Should be the same key
        assert key1 == key2

    def test_key_file_permissions(self, temp_config_dir, monkeypatch):
        """Test that key file has restrictive permissions."""
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        get_or_create_key()

        # Check permissions (0o600 = rw-------)
        import stat
        mode = key_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600


class TestLoadSaveCredentials:
    """Test suite for credential storage functions."""

    def test_save_and_load_credentials(self, temp_config_dir, monkeypatch):
        """Test saving and loading credentials."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Save credentials
        test_creds = {
            "prod": {
                "url": "https://cribl.example.com",
                "token": "secret-token-123",
            }
        }
        save_credentials(test_creds)

        # Load credentials
        loaded_creds = load_credentials()

        assert loaded_creds == test_creds

    def test_load_empty_credentials(self, temp_config_dir, monkeypatch):
        """Test loading when no credentials file exists."""
        credentials_file = temp_config_dir / "credentials.enc"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)

        loaded_creds = load_credentials()

        assert loaded_creds == {}

    def test_credentials_file_permissions(self, temp_config_dir, monkeypatch):
        """Test that credentials file has restrictive permissions."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        save_credentials({"test": {"url": "http://test", "token": "token"}})

        # Check permissions (0o600 = rw-------)
        import stat
        mode = credentials_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600


class TestSetCommand:
    """Test suite for config set command."""

    def test_set_credential(self, temp_config_dir, monkeypatch):
        """Test setting credentials for a deployment."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        result = runner.invoke(
            app,
            [
                "set",
                "prod",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token-123",
            ],
        )

        assert result.exit_code == 0
        assert "Saved credentials for deployment: prod" in result.stdout
        assert credentials_file.exists()

        # Verify credentials were actually saved
        loaded = load_credentials()
        assert "prod" in loaded
        assert loaded["prod"]["url"] == "https://cribl.example.com"
        assert loaded["prod"]["token"] == "test-token-123"

    def test_set_credential_updates_existing(self, temp_config_dir, monkeypatch):
        """Test updating existing credentials."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Set initial credentials
        runner.invoke(
            app,
            [
                "set",
                "prod",
                "--url",
                "https://old.example.com",
                "--token",
                "old-token",
            ],
        )

        # Update credentials
        result = runner.invoke(
            app,
            [
                "set",
                "prod",
                "--url",
                "https://new.example.com",
                "--token",
                "new-token",
            ],
        )

        assert result.exit_code == 0

        # Verify updated credentials
        loaded = load_credentials()
        assert loaded["prod"]["url"] == "https://new.example.com"
        assert loaded["prod"]["token"] == "new-token"

    def test_set_credential_missing_url(self):
        """Test set command with missing URL."""
        result = runner.invoke(
            app,
            [
                "set",
                "prod",
                "--token",
                "test-token",
            ],
        )

        assert result.exit_code != 0


class TestGetCommand:
    """Test suite for config get command."""

    def test_get_credential(self, temp_config_dir, monkeypatch):
        """Test retrieving stored credentials."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Set credentials first
        save_credentials({
            "prod": {
                "url": "https://cribl.example.com",
                "token": "secret-token",
            }
        })

        result = runner.invoke(app, ["get", "prod"])

        assert result.exit_code == 0
        assert "Credentials for: prod" in result.stdout
        assert "https://cribl.example.com" in result.stdout
        assert "*" in result.stdout  # Token should be masked
        assert "secret-token" not in result.stdout  # Token should not be visible

    def test_get_nonexistent_credential(self, temp_config_dir, monkeypatch):
        """Test retrieving credentials that don't exist."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        result = runner.invoke(app, ["get", "nonexistent"])

        assert result.exit_code == 1
        assert "No credentials found for: nonexistent" in result.stdout


class TestListCommand:
    """Test suite for config list command."""

    def test_list_credentials(self, temp_config_dir, monkeypatch):
        """Test listing all stored credentials."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Set multiple credentials
        save_credentials({
            "prod": {
                "url": "https://prod.cribl.com",
                "token": "prod-token",
            },
            "dev": {
                "url": "https://dev.cribl.com",
                "token": "dev-token",
            },
        })

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "prod" in result.stdout
        assert "dev" in result.stdout
        assert "https://prod.cribl.com" in result.stdout
        assert "https://dev.cribl.com" in result.stdout
        # Tokens should be masked
        assert "prod-token" not in result.stdout
        assert "dev-token" not in result.stdout

    def test_list_empty_credentials(self, temp_config_dir, monkeypatch):
        """Test listing when no credentials are stored."""
        credentials_file = temp_config_dir / "credentials.enc"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No credentials stored" in result.stdout


class TestDeleteCommand:
    """Test suite for config delete command."""

    def test_delete_credential_with_confirmation(self, temp_config_dir, monkeypatch):
        """Test deleting credentials with --yes flag."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Set credentials first
        save_credentials({
            "prod": {
                "url": "https://cribl.example.com",
                "token": "token",
            }
        })

        result = runner.invoke(app, ["delete", "prod", "--yes"])

        assert result.exit_code == 0
        assert "Deleted credentials for: prod" in result.stdout

        # Verify credentials were deleted
        loaded = load_credentials()
        assert "prod" not in loaded

    def test_delete_nonexistent_credential(self, temp_config_dir, monkeypatch):
        """Test deleting credentials that don't exist."""
        credentials_file = temp_config_dir / "credentials.enc"
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.CREDENTIALS_FILE", credentials_file)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        result = runner.invoke(app, ["delete", "nonexistent", "--yes"])

        assert result.exit_code == 1
        assert "No credentials found for: nonexistent" in result.stdout


class TestExportKeyCommand:
    """Test suite for config export-key command."""

    def test_export_key_to_stdout(self, temp_config_dir, monkeypatch):
        """Test exporting encryption key to stdout."""
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Create a key first
        get_or_create_key()

        result = runner.invoke(app, ["export-key"])

        assert result.exit_code == 0
        assert "WARNING" in result.stdout
        # Key should be displayed
        assert len(result.stdout) > 50

    def test_export_key_to_file(self, temp_config_dir, monkeypatch, tmp_path):
        """Test exporting encryption key to file."""
        key_file = temp_config_dir / ".key"
        monkeypatch.setattr("cribl_hc.cli.commands.config.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("cribl_hc.cli.commands.config.KEY_FILE", key_file)

        # Create a key first
        original_key = get_or_create_key()

        output_file = tmp_path / "exported_key.txt"
        result = runner.invoke(app, ["export-key", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify exported key matches original
        exported_key = output_file.read_bytes()
        assert exported_key == original_key

        # Check file permissions
        import stat
        mode = output_file.stat().st_mode
        assert stat.S_IMODE(mode) == 0o600


class TestOAuthCredentialManagement:
    """Test suite for OAuth credential management."""

    def test_set_oauth_credentials(self, temp_config_dir):
        """Test setting OAuth credentials via CLI."""
        result = runner.invoke(
            app,
            [
                "set",
                "test-oauth",
                "--url",
                "https://main-myorg.cribl.cloud",
                "--client-id",
                "test_client_id_123",
                "--client-secret",
                "test_client_secret_456",
            ],
        )

        assert result.exit_code == 0
        assert "Saved credentials for deployment: test-oauth" in result.stdout

        # Verify credentials were saved correctly
        credentials = load_credentials()
        assert "test-oauth" in credentials
        assert credentials["test-oauth"]["url"] == "https://main-myorg.cribl.cloud"
        assert credentials["test-oauth"]["auth_type"] == "oauth"
        assert credentials["test-oauth"]["client_id"] == "test_client_id_123"
        assert credentials["test-oauth"]["client_secret"] == "test_client_secret_456"
        assert "token" not in credentials["test-oauth"]

    def test_set_bearer_token_credentials(self, temp_config_dir):
        """Test setting bearer token credentials via CLI."""
        result = runner.invoke(
            app,
            [
                "set",
                "test-bearer",
                "--url",
                "https://cribl.example.com",
                "--token",
                "my_bearer_token_abc",
            ],
        )

        assert result.exit_code == 0
        assert "Saved credentials for deployment: test-bearer" in result.stdout

        # Verify credentials were saved correctly
        credentials = load_credentials()
        assert "test-bearer" in credentials
        assert credentials["test-bearer"]["url"] == "https://cribl.example.com"
        assert credentials["test-bearer"]["auth_type"] == "bearer"
        assert credentials["test-bearer"]["token"] == "my_bearer_token_abc"
        assert "client_id" not in credentials["test-bearer"]
        assert "client_secret" not in credentials["test-bearer"]

    def test_set_requires_auth_credentials(self, temp_config_dir):
        """Test that set command requires either token or OAuth credentials."""
        result = runner.invoke(
            app,
            [
                "set",
                "test-invalid",
                "--url",
                "https://cribl.example.com",
                # No auth provided
            ],
        )

        assert result.exit_code == 1
        assert "Must provide either --token OR both --client-id and --client-secret" in result.stdout

    def test_set_oauth_requires_both_credentials(self, temp_config_dir):
        """Test that OAuth requires both client-id and client-secret."""
        # Only client-id provided
        result = runner.invoke(
            app,
            [
                "set",
                "test-partial",
                "--url",
                "https://cribl.example.com",
                "--client-id",
                "only_id",
            ],
        )

        assert result.exit_code == 1
        assert "Must provide either --token OR both --client-id and --client-secret" in result.stdout

    def test_get_displays_oauth_credentials(self, temp_config_dir):
        """Test that get command displays OAuth credentials properly."""
        # First set OAuth credentials
        credentials = {
            "test-oauth": {
                "url": "https://main-myorg.cribl.cloud",
                "auth_type": "oauth",
                "client_id": "display_test_client_id",
                "client_secret": "display_test_client_secret",
            }
        }
        save_credentials(credentials)

        result = runner.invoke(app, ["get", "test-oauth"])

        assert result.exit_code == 0
        assert "test-oauth" in result.stdout
        assert "https://main-myorg.cribl.cloud" in result.stdout
        assert "oauth" in result.stdout.lower()
        assert "display_test_client_id" in result.stdout
        # Secret should be present (masked with asterisks)

    def test_list_displays_both_auth_types(self, temp_config_dir):
        """Test that list command displays both auth types correctly."""
        # Set both OAuth and bearer token credentials
        credentials = {
            "prod-oauth": {
                "url": "https://main-myorg.cribl.cloud",
                "auth_type": "oauth",
                "client_id": "prod_client_id",
                "client_secret": "prod_client_secret",
            },
            "dev-bearer": {
                "url": "https://cribl.example.com",
                "auth_type": "bearer",
                "token": "dev_bearer_token",
            },
        }
        save_credentials(credentials)

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        # Check that both deployments are listed
        assert "prod-oauth" in result.stdout
        assert "dev-bearer" in result.stdout
        # Check that URLs are displayed (may be truncated with ...)
        assert "main-myorg" in result.stdout or "cribl.cloud" in result.stdout
        assert "cribl.example" in result.stdout

    def test_delete_oauth_credentials(self, temp_config_dir):
        """Test deleting OAuth credentials."""
        # First set OAuth credentials
        credentials = {
            "delete-me": {
                "url": "https://delete.example.com",
                "auth_type": "oauth",
                "client_id": "delete_client_id",
                "client_secret": "delete_client_secret",
            }
        }
        save_credentials(credentials)

        # Verify it exists
        assert "delete-me" in load_credentials()

        # Delete it
        result = runner.invoke(app, ["delete", "delete-me", "--yes"])

        assert result.exit_code == 0
        assert "Deleted credentials for: delete-me" in result.stdout

        # Verify it's gone
        credentials = load_credentials()
        assert "delete-me" not in credentials

    def test_update_from_bearer_to_oauth(self, temp_config_dir):
        """Test updating credentials from bearer token to OAuth."""
        # Start with bearer token
        credentials = {
            "update-test": {
                "url": "https://update.example.com",
                "auth_type": "bearer",
                "token": "old_bearer_token",
            }
        }
        save_credentials(credentials)

        # Update to OAuth
        result = runner.invoke(
            app,
            [
                "set",
                "update-test",
                "--url",
                "https://update.example.com",
                "--client-id",
                "new_client_id",
                "--client-secret",
                "new_client_secret",
            ],
        )

        assert result.exit_code == 0

        # Verify it's now OAuth
        credentials = load_credentials()
        assert credentials["update-test"]["auth_type"] == "oauth"
        assert credentials["update-test"]["client_id"] == "new_client_id"
        assert credentials["update-test"]["client_secret"] == "new_client_secret"
        assert "token" not in credentials["update-test"]

    def test_update_from_oauth_to_bearer(self, temp_config_dir):
        """Test updating credentials from OAuth to bearer token."""
        # Start with OAuth
        credentials = {
            "update-test": {
                "url": "https://update.example.com",
                "auth_type": "oauth",
                "client_id": "old_client_id",
                "client_secret": "old_client_secret",
            }
        }
        save_credentials(credentials)

        # Update to bearer token
        result = runner.invoke(
            app,
            [
                "set",
                "update-test",
                "--url",
                "https://update.example.com",
                "--token",
                "new_bearer_token",
            ],
        )

        assert result.exit_code == 0

        # Verify it's now bearer token
        credentials = load_credentials()
        assert credentials["update-test"]["auth_type"] == "bearer"
        assert credentials["update-test"]["token"] == "new_bearer_token"
        assert "client_id" not in credentials["update-test"]
        assert "client_secret" not in credentials["update-test"]

    @pytest.mark.asyncio
    async def test_create_api_client_from_oauth_credentials(self, temp_config_dir):
        """Test creating API client from stored OAuth credentials."""
        from cribl_hc.cli.commands.config import create_api_client_from_credentials

        # Save OAuth credentials
        credentials = {
            "api-test-oauth": {
                "url": "https://main-myorg.cribl.cloud",
                "auth_type": "oauth",
                "client_id": "api_test_client_id",
                "client_secret": "api_test_client_secret",
            }
        }
        save_credentials(credentials)

        # Create API client
        client = create_api_client_from_credentials("api-test-oauth")

        assert client is not None
        assert client.base_url == "https://main-myorg.cribl.cloud"
        assert client._oauth_manager is not None
        assert client._oauth_manager.client_id == "api_test_client_id"
        assert client._oauth_manager.client_secret == "api_test_client_secret"

    @pytest.mark.asyncio
    async def test_create_api_client_from_bearer_credentials(self, temp_config_dir):
        """Test creating API client from stored bearer token credentials."""
        from cribl_hc.cli.commands.config import create_api_client_from_credentials

        # Save bearer token credentials
        credentials = {
            "api-test-bearer": {
                "url": "https://cribl.example.com",
                "auth_type": "bearer",
                "token": "api_test_bearer_token",
            }
        }
        save_credentials(credentials)

        # Create API client
        client = create_api_client_from_credentials("api-test-bearer")

        assert client is not None
        assert client.base_url == "https://cribl.example.com"
        assert client.auth_token == "api_test_bearer_token"
        assert client._oauth_manager is None

    @pytest.mark.asyncio
    async def test_create_api_client_handles_missing_deployment(self, temp_config_dir):
        """Test that create_api_client raises error for missing deployment."""
        from cribl_hc.cli.commands.config import create_api_client_from_credentials

        with pytest.raises(ValueError, match="No credentials found for deployment"):
            create_api_client_from_credentials("non-existent-deployment")
