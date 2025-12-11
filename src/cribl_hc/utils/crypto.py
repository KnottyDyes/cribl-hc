"""
Credential encryption using cryptography Fernet for secure storage.

This module provides encryption/decryption for bearer tokens and other sensitive data.
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class CredentialEncryptor:
    """
    Encrypts and decrypts credentials using Fernet symmetric encryption.

    Uses PBKDF2 key derivation from a master password/key for enhanced security.
    """

    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize credential encryptor.

        Args:
            master_key: Master encryption key (32 bytes).
                       If None, generates a new key (NOT RECOMMENDED for production)

        Example:
            >>> # Generate and save a master key once
            >>> key = Fernet.generate_key()
            >>> # Store key securely (environment variable, key management service, etc.)
            >>>
            >>> # Use the key for encryption
            >>> encryptor = CredentialEncryptor(master_key=key)
            >>> encrypted = encryptor.encrypt("my-bearer-token")
            >>> decrypted = encryptor.decrypt(encrypted)
        """
        if master_key is None:
            # Generate a new key (for testing only - not secure for production)
            log.warning("generating_new_encryption_key", message="Using generated key - not secure for production")
            master_key = Fernet.generate_key()

        self.fernet = Fernet(master_key)
        self.master_key = master_key

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a plaintext credential.

        Args:
            plaintext: Plaintext credential (e.g., bearer token)

        Returns:
            Encrypted credential as bytes

        Example:
            >>> encryptor = CredentialEncryptor(master_key=b'...')
            >>> encrypted = encryptor.encrypt("my-secret-token")
            >>> print(encrypted)
            b'gAAAAA...'
        """
        try:
            plaintext_bytes = plaintext.encode('utf-8')
            encrypted_bytes = self.fernet.encrypt(plaintext_bytes)
            log.debug("credential_encrypted", length=len(encrypted_bytes))
            return encrypted_bytes
        except Exception as e:
            log.error("encryption_failed", error=str(e))
            raise

    def decrypt(self, encrypted: bytes) -> str:
        """
        Decrypt an encrypted credential.

        Args:
            encrypted: Encrypted credential bytes

        Returns:
            Decrypted plaintext credential

        Raises:
            InvalidToken: If decryption fails (wrong key, corrupted data)

        Example:
            >>> encryptor = CredentialEncryptor(master_key=b'...')
            >>> encrypted = b'gAAAAA...'
            >>> plaintext = encryptor.decrypt(encrypted)
            >>> print(plaintext)
            'my-secret-token'
        """
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted)
            plaintext = decrypted_bytes.decode('utf-8')
            log.debug("credential_decrypted")
            return plaintext
        except InvalidToken as e:
            log.error("decryption_failed", error="Invalid token or corrupted data")
            raise ValueError("Failed to decrypt credential - invalid key or corrupted data") from e
        except Exception as e:
            log.error("decryption_failed", error=str(e))
            raise

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new Fernet encryption key.

        Returns:
            32-byte encryption key (base64 encoded)

        Example:
            >>> key = CredentialEncryptor.generate_key()
            >>> print(key)
            b'Zj5vBpTH...'
        """
        return Fernet.generate_key()

    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Derive an encryption key from a password using PBKDF2.

        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generates random if None)

        Returns:
            Tuple of (derived_key, salt) - both should be stored

        Example:
            >>> key, salt = CredentialEncryptor.derive_key_from_password("my-password")
            >>> # Store both key and salt securely
            >>> encryptor = CredentialEncryptor(master_key=key)
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommendation (2023)
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key, salt


# Convenience functions for simple use cases

_default_encryptor: Optional[CredentialEncryptor] = None


def get_default_encryptor() -> CredentialEncryptor:
    """
    Get the default credential encryptor instance.

    Creates a new instance with generated key if none exists.
    For production, initialize with a proper master key first.

    Returns:
        Default CredentialEncryptor instance
    """
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = CredentialEncryptor()
    return _default_encryptor


def set_master_key(master_key: bytes) -> None:
    """
    Set the master encryption key for the default encryptor.

    Args:
        master_key: 32-byte Fernet key

    Example:
        >>> from cribl_hc.utils.crypto import set_master_key, encrypt_credential
        >>> # Load key from secure storage
        >>> key = os.environ['CRIBL_HC_ENCRYPTION_KEY'].encode()
        >>> set_master_key(key)
        >>> encrypted = encrypt_credential("my-token")
    """
    global _default_encryptor
    _default_encryptor = CredentialEncryptor(master_key=master_key)


def encrypt_credential(plaintext: str) -> bytes:
    """
    Encrypt a credential using the default encryptor.

    Args:
        plaintext: Plaintext credential

    Returns:
        Encrypted credential bytes

    Example:
        >>> encrypted = encrypt_credential("my-bearer-token")
    """
    return get_default_encryptor().encrypt(plaintext)


def decrypt_credential(encrypted: bytes) -> str:
    """
    Decrypt a credential using the default encryptor.

    Args:
        encrypted: Encrypted credential bytes

    Returns:
        Decrypted plaintext credential

    Example:
        >>> plaintext = decrypt_credential(encrypted_bytes)
    """
    return get_default_encryptor().decrypt(encrypted)


def generate_master_key() -> bytes:
    """
    Generate a new master encryption key.

    Returns:
        32-byte Fernet key (base64 encoded)

    Example:
        >>> key = generate_master_key()
        >>> # Save to secure storage (environment variable, secrets manager, etc.)
        >>> print(key.decode())  # For display/storage only
    """
    return CredentialEncryptor.generate_key()
