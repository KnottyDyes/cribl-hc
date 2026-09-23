"""
Tests for the encrypted credential store.
"""

import os
import stat

import pytest
from cryptography.fernet import Fernet

from cribl_hc.core.credential_store import (
    ENV_CONFIG_DIR,
    ENV_MASTER_KEY,
    ENV_MASTER_PASSPHRASE,
    CredentialStore,
    CredentialStoreError,
    default_config_dir,
    redact,
)


@pytest.fixture
def store(tmp_path):
    """A store rooted in a temporary directory."""
    return CredentialStore(config_dir=tmp_path / "config")


@pytest.fixture(autouse=True)
def clear_key_env(monkeypatch):
    """Each test decides its own key source."""
    monkeypatch.delenv(ENV_MASTER_KEY, raising=False)
    monkeypatch.delenv(ENV_MASTER_PASSPHRASE, raising=False)


class TestRoundTrip:
    def test_empty_store_reads_as_empty(self, store):
        assert store.load() == {}

    def test_put_then_get(self, store):
        store.put("prod", {"url": "https://cribl.example.com", "token": "secret"})
        assert store.get("prod") == {"url": "https://cribl.example.com", "token": "secret"}

    def test_get_missing_returns_none(self, store):
        assert store.get("nope") is None

    def test_delete_reports_whether_it_removed_anything(self, store):
        store.put("prod", {"token": "secret"})
        assert store.delete("prod") is True
        assert store.delete("prod") is False

    def test_names_are_sorted(self, store):
        for name in ("zeta", "alpha", "mu"):
            store.put(name, {"token": "x"})
        assert store.names() == ["alpha", "mu", "zeta"]

    def test_ciphertext_does_not_contain_the_secret(self, store):
        store.put("prod", {"token": "super-secret-value"})
        assert b"super-secret-value" not in store.credentials_file.read_bytes()


class TestPrune:
    def test_removes_only_the_matching_prefix(self, store):
        store.put("analysis-test-aaa", {"token": "x"})
        store.put("analysis-test-bbb", {"token": "x"})
        store.put("prod", {"token": "x"})

        removed = store.prune("analysis-test-")

        assert removed == ["analysis-test-aaa", "analysis-test-bbb"]
        assert store.names() == ["prod"]

    def test_no_match_leaves_the_store_alone(self, store):
        store.put("prod", {"token": "x"})
        assert store.prune("nothing-") == []
        assert store.names() == ["prod"]


class TestKeyResolution:
    def test_env_key_is_preferred_and_writes_no_key_file(self, store, monkeypatch):
        monkeypatch.setenv(ENV_MASTER_KEY, Fernet.generate_key().decode())
        store.put("prod", {"token": "x"})
        assert store.get("prod") == {"token": "x"}
        assert not store.key_file.exists()

    def test_passphrase_derives_a_key_without_storing_it(self, store, monkeypatch):
        monkeypatch.setenv(ENV_MASTER_PASSPHRASE, "correct horse battery staple")
        store.put("prod", {"token": "x"})

        assert not store.key_file.exists()
        assert store.salt_file.exists()  # salt is public, the passphrase is not
        assert store.get("prod") == {"token": "x"}

    def test_same_passphrase_reads_back_across_instances(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_MASTER_PASSPHRASE, "shared passphrase")
        CredentialStore(config_dir=tmp_path).put("prod", {"token": "x"})

        reopened = CredentialStore(config_dir=tmp_path)
        assert reopened.get("prod") == {"token": "x"}

    def test_wrong_passphrase_is_reported_clearly(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_MASTER_PASSPHRASE, "right passphrase")
        CredentialStore(config_dir=tmp_path).put("prod", {"token": "x"})

        monkeypatch.setenv(ENV_MASTER_PASSPHRASE, "wrong passphrase")
        with pytest.raises(CredentialStoreError, match="could not decrypt|Could not decrypt"):
            CredentialStore(config_dir=tmp_path).load()

    def test_key_file_is_the_fallback(self, store):
        store.put("prod", {"token": "x"})
        assert store.key_file.exists()


class TestFilePermissions:
    def test_written_files_are_owner_only(self, store):
        store.put("prod", {"token": "x"})

        for path in (store.credentials_file, store.key_file):
            mode = stat.S_IMODE(path.stat().st_mode)
            assert mode == 0o600, f"{path} is {oct(mode)}"

    def test_config_dir_is_owner_only(self, store):
        store.put("prod", {"token": "x"})
        assert stat.S_IMODE(store.config_dir.stat().st_mode) == 0o700

    def test_loose_permissions_are_reported(self, store, monkeypatch):
        store.put("prod", {"token": "x"})
        store.credentials_file.chmod(0o644)

        warnings = []
        monkeypatch.setattr(
            "cribl_hc.core.credential_store.log.warning",
            lambda event, **kw: warnings.append((event, kw)),
        )

        store.load()

        assert any(event == "credential_file_permissions" for event, _ in warnings)

    def test_owner_only_permissions_are_not_reported(self, store, monkeypatch):
        store.put("prod", {"token": "x"})

        warnings = []
        monkeypatch.setattr(
            "cribl_hc.core.credential_store.log.warning",
            lambda event, **kw: warnings.append((event, kw)),
        )

        store.load()

        assert not warnings


class TestAtomicWrite:
    def test_a_failed_write_leaves_the_previous_content_intact(self, store, monkeypatch):
        store.put("prod", {"token": "original"})
        original = store.credentials_file.read_bytes()

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError):
            store.put("prod", {"token": "replacement"})

        assert store.credentials_file.read_bytes() == original

    def test_no_temporary_files_are_left_behind(self, store):
        store.put("prod", {"token": "x"})
        assert not list(store.config_dir.glob(".tmp-*"))


class TestConfigDirResolution:
    def test_env_override_is_honoured(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV_CONFIG_DIR, str(tmp_path / "elsewhere"))
        assert default_config_dir() == tmp_path / "elsewhere"

    def test_default_is_under_home(self, monkeypatch):
        monkeypatch.delenv(ENV_CONFIG_DIR, raising=False)
        assert default_config_dir().name == ".cribl-hc"


class TestRedaction:
    def test_secret_fields_are_masked(self):
        out = redact({"url": "https://x", "token": "secret", "client_secret": "also-secret"})
        assert out["url"] == "https://x"
        assert out["token"] == "********"
        assert out["client_secret"] == "********"

    def test_empty_secrets_are_left_alone(self):
        assert redact({"token": ""})["token"] == ""

    def test_non_secret_fields_pass_through(self):
        assert redact({"auth_type": "bearer"})["auth_type"] == "bearer"
