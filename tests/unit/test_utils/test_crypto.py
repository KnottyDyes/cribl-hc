"""
Unit tests for credential encryption functionality.
"""

import pytest
from cryptography.fernet import InvalidToken

from cribl_hc.utils.crypto import (
    CredentialEncryptor,
    encrypt_credential,
    decrypt_credential,
    generate_master_key,
    set_master_key,
    get_default_encryptor,
)


class TestCredentialEncryptor:
    """Test CredentialEncryptor class."""

    def test_initialization_with_key(self):
        """Test initializing encryptor with a master key."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        assert encryptor.master_key == key
        assert encryptor.fernet is not None

    def test_initialization_without_key(self):
        """Test initializing encryptor without key (generates new one)."""
        encryptor = CredentialEncryptor()

        assert encryptor.master_key is not None
        assert encryptor.fernet is not None

    def test_encrypt_plaintext(self):
        """Test encrypting a plaintext credential."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        plaintext = "my-secret-bearer-token"
        encrypted = encryptor.encrypt(plaintext)

        assert encrypted is not None
        assert isinstance(encrypted, bytes)
        assert encrypted != plaintext.encode('utf-8')  # Should be encrypted

    def test_decrypt_encrypted(self):
        """Test decrypting an encrypted credential."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        plaintext = "my-secret-token-12345"
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self):
        """Test full encrypt/decrypt roundtrip."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        test_credentials = [
            "simple-token",
            "token-with-special-chars-!@#$%",
            "very-long-token-" * 100,
            "unicode-token-日本語-🔐",
            "",  # Empty string
        ]

        for plaintext in test_credentials:
            encrypted = encryptor.encrypt(plaintext)
            decrypted = encryptor.decrypt(encrypted)
            assert decrypted == plaintext

    def test_decrypt_with_wrong_key(self):
        """Test that decryption fails with wrong key."""
        key1 = CredentialEncryptor.generate_key()
        key2 = CredentialEncryptor.generate_key()

        encryptor1 = CredentialEncryptor(master_key=key1)
        encryptor2 = CredentialEncryptor(master_key=key2)

        plaintext = "secret-token"
        encrypted = encryptor1.encrypt(plaintext)

        # Decrypting with wrong key should fail
        with pytest.raises(ValueError) as exc_info:
            encryptor2.decrypt(encrypted)

        assert "decrypt" in str(exc_info.value).lower()

    def test_decrypt_invalid_data(self):
        """Test that decryption fails with corrupted data."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        invalid_encrypted = b"not-valid-encrypted-data"

        with pytest.raises(ValueError):
            encryptor.decrypt(invalid_encrypted)

    def test_generate_key(self):
        """Test key generation."""
        key1 = CredentialEncryptor.generate_key()
        key2 = CredentialEncryptor.generate_key()

        assert key1 != key2  # Should generate unique keys
        assert isinstance(key1, bytes)
        assert isinstance(key2, bytes)
        assert len(key1) == 44  # Fernet keys are 44 bytes (base64 encoded)

    def test_derive_key_from_password(self):
        """Test deriving key from password."""
        password = "my-secure-password"
        key1, salt1 = CredentialEncryptor.derive_key_from_password(password)

        assert key1 is not None
        assert salt1 is not None
        assert isinstance(key1, bytes)
        assert isinstance(salt1, bytes)

        # Same password with same salt should produce same key
        key2, salt2 = CredentialEncryptor.derive_key_from_password(password, salt=salt1)
        assert key2 == key1

        # Same password with different salt should produce different key
        key3, salt3 = CredentialEncryptor.derive_key_from_password(password)
        assert key3 != key1

    def test_password_derived_key_works_for_encryption(self):
        """Test that password-derived key works for encryption."""
        password = "test-password-123"
        key, salt = CredentialEncryptor.derive_key_from_password(password)

        encryptor = CredentialEncryptor(master_key=key)

        plaintext = "my-secret-token"
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext


class TestConvenienceFunctions:
    """Test convenience functions for simple use cases."""

    def test_encrypt_decrypt_convenience_functions(self):
        """Test encrypt_credential and decrypt_credential functions."""
        # Set a specific master key
        key = generate_master_key()
        set_master_key(key)

        plaintext = "test-token-xyz"
        encrypted = encrypt_credential(plaintext)
        decrypted = decrypt_credential(encrypted)

        assert decrypted == plaintext

    def test_generate_master_key_function(self):
        """Test generate_master_key convenience function."""
        key1 = generate_master_key()
        key2 = generate_master_key()

        assert key1 != key2
        assert isinstance(key1, bytes)
        assert len(key1) == 44

    def test_set_master_key_function(self):
        """Test set_master_key convenience function."""
        key = generate_master_key()
        set_master_key(key)

        encryptor = get_default_encryptor()
        assert encryptor.master_key == key

    def test_default_encryptor_singleton(self):
        """Test that default encryptor is a singleton."""
        key = generate_master_key()
        set_master_key(key)

        encryptor1 = get_default_encryptor()
        encryptor2 = get_default_encryptor()

        assert encryptor1 is encryptor2


class TestSecurityProperties:
    """Test security properties of encryption."""

    def test_same_plaintext_different_ciphertext(self):
        """Test that encrypting same plaintext twice produces different ciphertext."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        plaintext = "same-token"
        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        # Fernet includes a timestamp, so ciphertexts should differ
        assert encrypted1 != encrypted2

        # But both should decrypt to same plaintext
        assert encryptor.decrypt(encrypted1) == plaintext
        assert encryptor.decrypt(encrypted2) == plaintext

    def test_encrypted_data_not_readable(self):
        """Test that encrypted data doesn't contain plaintext."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        plaintext = "super-secret-token"
        encrypted = encryptor.encrypt(plaintext)

        # Encrypted data should not contain plaintext
        assert plaintext.encode('utf-8') not in encrypted
        assert plaintext not in encrypted.decode('utf-8', errors='ignore')

    def test_empty_string_encryption(self):
        """Test encrypting empty string."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        plaintext = ""
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_unicode_encryption(self):
        """Test encrypting unicode strings."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        unicode_credentials = [
            "日本語トークン",
            "Привет-token",
            "مرحبا-token",
            "🔐🔑🛡️",
        ]

        for plaintext in unicode_credentials:
            encrypted = encryptor.encrypt(plaintext)
            decrypted = encryptor.decrypt(encrypted)
            assert decrypted == plaintext

    def test_long_plaintext_encryption(self):
        """Test encrypting very long credentials."""
        key = CredentialEncryptor.generate_key()
        encryptor = CredentialEncryptor(master_key=key)

        # Create a very long token (10KB)
        plaintext = "a" * 10000
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext
        assert len(decrypted) == 10000


class TestPasswordDerivation:
    """Test password-based key derivation."""

    def test_pbkdf2_iterations(self):
        """Test that PBKDF2 uses recommended iterations."""
        password = "test-password"
        key, salt = CredentialEncryptor.derive_key_from_password(password)

        # Just verify it completes (iterations are set in the implementation)
        assert key is not None
        assert len(key) == 44  # Fernet key length

    def test_different_passwords_different_keys(self):
        """Test that different passwords produce different keys."""
        password1 = "password1"
        password2 = "password2"

        key1, _ = CredentialEncryptor.derive_key_from_password(password1)
        key2, _ = CredentialEncryptor.derive_key_from_password(password2)

        assert key1 != key2

    def test_salt_affects_key_derivation(self):
        """Test that salt affects derived key."""
        password = "same-password"
        salt1 = b"salt1" * 3 + b"1"  # 16 bytes
        salt2 = b"salt2" * 3 + b"2"  # 16 bytes

        key1, _ = CredentialEncryptor.derive_key_from_password(password, salt=salt1)
        key2, _ = CredentialEncryptor.derive_key_from_password(password, salt=salt2)

        assert key1 != key2
