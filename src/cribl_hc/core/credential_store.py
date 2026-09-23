"""
Encrypted storage for Cribl deployment credentials.

Both the CLI and the REST API use this module, so the storage location, file
permissions and key handling are defined once rather than in whichever layer
happened to need them first.

Key resolution, first match wins:

1. ``CRIBL_HC_MASTER_KEY`` - a urlsafe-base64 Fernet key. For CI and
   containers, where writing a key file next to the data is undesirable.
2. ``CRIBL_HC_MASTER_PASSPHRASE`` - derived with PBKDF2-HMAC-SHA256 over a
   salt stored beside the credential file. The passphrase itself is never
   written to disk, so the ciphertext is useless without it.
3. A generated key file in the config directory.

Option 3 is the convenient default, and it is worth being plain about what it
buys: the key sits in the same directory as the ciphertext, so it protects
against a stray backup or a shared filesystem being read casually, not against
anyone who can already read that directory as your user. Options 1 and 2 are
the ones that separate key from data. This is why the store audits file modes
and warns rather than claiming the data is simply "encrypted at rest".
"""

from __future__ import annotations

import base64
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)

ENV_CONFIG_DIR = "CRIBL_HC_CONFIG_DIR"
ENV_MASTER_KEY = "CRIBL_HC_MASTER_KEY"
ENV_MASTER_PASSPHRASE = "CRIBL_HC_MASTER_PASSPHRASE"

DEFAULT_CONFIG_DIR = Path.home() / ".cribl-hc"

# Fields that must never be printed, logged or returned by a listing.
SECRET_FIELDS = frozenset({"token", "client_secret", "password", "api_key"})

_PBKDF2_ITERATIONS = 600_000  # OWASP guidance for PBKDF2-HMAC-SHA256
_SALT_BYTES = 16


class CredentialStoreError(Exception):
    """Raised when the credential store cannot be read or written."""


def default_config_dir() -> Path:
    """Config directory, honouring CRIBL_HC_CONFIG_DIR."""
    override = os.environ.get(ENV_CONFIG_DIR)
    return Path(override).expanduser() if override else DEFAULT_CONFIG_DIR


def redact(credential: dict[str, Any]) -> dict[str, Any]:
    """Copy a credential with secret values replaced by a placeholder."""
    return {
        key: ("********" if key in SECRET_FIELDS and value else value)
        for key, value in credential.items()
    }


class CredentialStore:
    """Reads and writes the encrypted credential file."""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        credentials_file: Optional[Path] = None,
        key_file: Optional[Path] = None,
    ) -> None:
        self.config_dir = Path(config_dir) if config_dir else default_config_dir()
        self.credentials_file = (
            Path(credentials_file) if credentials_file else self.config_dir / "credentials.enc"
        )
        self.key_file = Path(key_file) if key_file else self.config_dir / ".key"
        self.salt_file = self.config_dir / ".salt"

    # -- key handling ----------------------------------------------------

    def _derive_from_passphrase(self, passphrase: str) -> bytes:
        """Derive a Fernet key from a passphrase, creating the salt if needed."""
        if self.salt_file.exists():
            salt = self.salt_file.read_bytes()
        else:
            salt = os.urandom(_SALT_BYTES)
            self._ensure_config_dir()
            self._write_private(self.salt_file, salt)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=_PBKDF2_ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))

    def resolve_key(self) -> bytes:
        """Return the Fernet key, creating a key file only as a last resort."""
        env_key = os.environ.get(ENV_MASTER_KEY)
        if env_key:
            return env_key.encode("utf-8") if isinstance(env_key, str) else env_key

        passphrase = os.environ.get(ENV_MASTER_PASSPHRASE)
        if passphrase:
            return self._derive_from_passphrase(passphrase)

        if self.key_file.exists():
            self._warn_if_readable(self.key_file)
            return self.key_file.read_bytes()

        key = Fernet.generate_key()
        self._ensure_config_dir()
        self._write_private(self.key_file, key)
        log.info(
            "credential_key_created",
            path=str(self.key_file),
            message=(
                "Generated a key file beside the credential store. Set "
                f"{ENV_MASTER_PASSPHRASE} to keep the key off disk instead."
            ),
        )
        return key

    # -- filesystem helpers ----------------------------------------------

    def _ensure_config_dir(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.config_dir.chmod(0o700)
        except OSError:  # pragma: no cover - platform dependent
            pass

    def _write_private(self, path: Path, data: bytes) -> None:
        """Write owner-only, replacing the target atomically.

        A partial write would leave the credential file undecryptable, so the
        new content lands in a temporary file in the same directory and is then
        renamed over the old one.
        """
        self._ensure_config_dir()
        fd, tmp_name = tempfile.mkstemp(dir=str(self.config_dir), prefix=".tmp-")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            tmp_path.chmod(0o600)
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

    def _warn_if_readable(self, path: Path) -> None:
        """Warn when a private file is readable by group or others."""
        try:
            mode = path.stat().st_mode
        except OSError:  # pragma: no cover - race with deletion
            return
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            log.warning(
                "credential_file_permissions",
                path=str(path),
                mode=oct(stat.S_IMODE(mode)),
                message="File is accessible beyond its owner; chmod 600 it.",
            )

    # -- credential access -----------------------------------------------

    def load(self) -> dict[str, dict[str, Any]]:
        """Return every stored credential, or an empty mapping if none exist."""
        if not self.credentials_file.exists():
            return {}

        self._warn_if_readable(self.credentials_file)
        fernet = Fernet(self.resolve_key())
        try:
            decrypted = fernet.decrypt(self.credentials_file.read_bytes())
        except InvalidToken as e:
            raise CredentialStoreError(
                "Could not decrypt the credential store. The key does not match "
                "the data - check which of "
                f"{ENV_MASTER_KEY}, {ENV_MASTER_PASSPHRASE} or {self.key_file} "
                "was used to write it."
            ) from e

        data = json.loads(decrypted)
        return data if isinstance(data, dict) else {}

    def save(self, credentials: dict[str, dict[str, Any]]) -> None:
        """Encrypt and write the whole credential mapping."""
        fernet = Fernet(self.resolve_key())
        payload = fernet.encrypt(json.dumps(credentials, indent=2).encode("utf-8"))
        self._write_private(self.credentials_file, payload)

    def get(self, name: str) -> Optional[dict[str, Any]]:
        return self.load().get(name)

    def put(self, name: str, credential: dict[str, Any]) -> None:
        credentials = self.load()
        credentials[name] = credential
        self.save(credentials)

    def delete(self, name: str) -> bool:
        credentials = self.load()
        if name not in credentials:
            return False
        del credentials[name]
        self.save(credentials)
        return True

    def names(self) -> list[str]:
        return sorted(self.load().keys())

    def prune(self, prefix: str) -> list[str]:
        """Delete every credential whose name starts with prefix."""
        credentials = self.load()
        removed = sorted(name for name in credentials if name.startswith(prefix))
        if removed:
            for name in removed:
                del credentials[name]
            self.save(credentials)
        return removed
