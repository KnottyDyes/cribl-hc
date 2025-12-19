"""Unit tests for OAuth authentication module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from cribl_hc.core.auth import OAuthTokenManager


class TestOAuthTokenManager:
    """Tests for OAuthTokenManager class."""

    @pytest.fixture
    def token_manager(self):
        """Create a token manager instance for testing."""
        return OAuthTokenManager(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )

    @pytest.fixture
    def mock_token_response(self):
        """Create a mock OAuth token response."""
        return {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours
        }

    @pytest.mark.asyncio
    async def test_initialization(self, token_manager):
        """Test OAuthTokenManager initialization."""
        assert token_manager.client_id == "test_client_id"
        assert token_manager.client_secret == "test_client_secret"
        assert token_manager._cached_token is None
        assert token_manager._token_expires_at is None
        assert token_manager.OAUTH_TOKEN_URL == "https://login.cribl.cloud/oauth/token"
        assert token_manager.OAUTH_AUDIENCE == "https://api.cribl.cloud"

    @pytest.mark.asyncio
    async def test_request_token_success(self, token_manager, mock_token_response):
        """Test successful token request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            token_data = await token_manager._request_token()

        assert token_data == mock_token_response
        assert token_data["access_token"] == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert token_data["expires_in"] == 86400

        # Verify the request was made correctly
        mock_client.post.assert_called_once_with(
            "https://login.cribl.cloud/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "audience": "https://api.cribl.cloud",
            },
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_request_token_http_error(self, token_manager):
        """Test token request with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock()
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await token_manager._request_token()

    @pytest.mark.asyncio
    async def test_request_token_missing_access_token(self, token_manager):
        """Test token request with invalid response (missing access_token)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_request"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="OAuth response missing access_token"):
                await token_manager._request_token()

    @pytest.mark.asyncio
    async def test_get_access_token_first_call(self, token_manager, mock_token_response):
        """Test getting access token on first call (no cache)."""
        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            token = await token_manager.get_access_token()

        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert token_manager._cached_token == token
        assert token_manager._token_expires_at is not None
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_uses_cache(self, token_manager, mock_token_response):
        """Test that cached token is reused if still valid."""
        # Set up a cached token that won't expire for another hour
        token_manager._cached_token = "cached_token_value"
        token_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            token = await token_manager.get_access_token()

        assert token == "cached_token_value"
        mock_request.assert_not_called()  # Should not request new token

    @pytest.mark.asyncio
    async def test_get_access_token_refresh_on_expiry(self, token_manager, mock_token_response):
        """Test that token is refreshed when close to expiration."""
        # Set up a cached token that expires in 3 minutes (within 5-minute safety buffer)
        token_manager._cached_token = "old_token"
        token_manager._token_expires_at = datetime.utcnow() + timedelta(minutes=3)

        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            token = await token_manager.get_access_token()

        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert token_manager._cached_token == token
        mock_request.assert_called_once()  # Should request new token

    @pytest.mark.asyncio
    async def test_get_access_token_refresh_on_expired(self, token_manager, mock_token_response):
        """Test that token is refreshed when already expired."""
        # Set up a cached token that already expired
        token_manager._cached_token = "expired_token"
        token_manager._token_expires_at = datetime.utcnow() - timedelta(hours=1)

        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            token = await token_manager.get_access_token()

        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_access_token_no_cache_initially(self, token_manager, mock_token_response):
        """Test getting token when no cache exists."""
        assert token_manager._cached_token is None
        assert token_manager._token_expires_at is None

        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            token = await token_manager.get_access_token()

        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_caching_reduces_requests(self, token_manager, mock_token_response):
        """Test that multiple calls use cached token."""
        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            # Make multiple calls
            token1 = await token_manager.get_access_token()
            token2 = await token_manager.get_access_token()
            token3 = await token_manager.get_access_token()

        assert token1 == token2 == token3
        mock_request.assert_called_once()  # Only one request should be made

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, token_manager):
        """Test cache invalidation."""
        # Set up cached token
        token_manager._cached_token = "cached_token"
        token_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        # Invalidate cache
        token_manager.invalidate_cache()

        assert token_manager._cached_token is None
        assert token_manager._token_expires_at is None

    @pytest.mark.asyncio
    async def test_default_expiry_time(self, token_manager):
        """Test that default expiry is used when not provided."""
        mock_response = {
            "access_token": "test_token",
            "token_type": "Bearer",
            # No expires_in field
        }

        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await token_manager.get_access_token()

        # Should default to 86400 seconds (24 hours)
        expected_expiry = datetime.utcnow() + timedelta(seconds=86400)
        actual_expiry = token_manager._token_expires_at

        # Allow 5 second tolerance for test execution time
        assert abs((actual_expiry - expected_expiry).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_token_expiry_calculation(self, token_manager, mock_token_response):
        """Test that token expiry is calculated correctly."""
        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            before = datetime.utcnow()
            await token_manager.get_access_token()
            after = datetime.utcnow()

        expected_expiry = before + timedelta(seconds=86400)
        actual_expiry = token_manager._token_expires_at

        # Expiry should be within test execution time
        assert expected_expiry <= actual_expiry <= (after + timedelta(seconds=86400))

    @pytest.mark.asyncio
    async def test_safety_buffer_timing(self, token_manager, mock_token_response):
        """Test that 5-minute safety buffer is correctly applied."""
        # Token expires in exactly 5 minutes
        token_manager._cached_token = "old_token"
        token_manager._token_expires_at = datetime.utcnow() + timedelta(minutes=5)

        with patch.object(token_manager, "_request_token", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_token_response

            await token_manager.get_access_token()

        # Should request new token (at exactly 5 minutes, it's not safe)
        mock_request.assert_called_once()

        # Now test with token expiring in 5 minutes + 1 second
        token_manager._cached_token = "newer_token"
        token_manager._token_expires_at = datetime.utcnow() + timedelta(minutes=5, seconds=1)

        mock_request.reset_mock()
        token = await token_manager.get_access_token()

        # Should use cached token (more than 5 minutes remaining)
        assert token == "newer_token"
        mock_request.assert_not_called()
