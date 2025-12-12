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
