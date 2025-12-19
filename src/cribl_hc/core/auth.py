"""
OAuth authentication helpers for Cribl API.

Handles OAuth 2.0 client credentials flow for Cribl.Cloud API authentication.
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class OAuthTokenManager:
    """
    Manages OAuth access tokens for Cribl.Cloud API authentication.

    Handles token exchange using client credentials (client_id + client_secret)
    and caches tokens until expiration.
    """

    # Cribl.Cloud OAuth endpoint
    OAUTH_TOKEN_URL = "https://login.cribl.cloud/oauth/token"
    OAUTH_AUDIENCE = "https://api.cribl.cloud"

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize OAuth token manager.

        Args:
            client_id: Cribl API Client ID
            client_secret: Cribl API Client Secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._cached_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def get_access_token(self) -> str:
        """
        Get a valid access token, using cached token if available.

        Automatically requests a new token if:
        - No cached token exists
        - Cached token has expired (with 5 minute safety buffer)

        Returns:
            Valid Bearer token for API authentication

        Raises:
            httpx.HTTPStatusError: If token request fails
            ValueError: If response doesn't contain access_token
        """
        # Check if we have a valid cached token
        if self._cached_token and self._token_expires_at:
            # Add 5 minute safety buffer before expiration
            if datetime.utcnow() < (self._token_expires_at - timedelta(minutes=5)):
                log.debug("using_cached_oauth_token", expires_at=self._token_expires_at)
                return self._cached_token

        # Request new token
        log.debug("requesting_new_oauth_token", client_id=self.client_id)
        token_data = await self._request_token()

        # Cache the token
        self._cached_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 86400)  # Default 24 hours
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        log.info(
            "oauth_token_obtained",
            expires_in=expires_in,
            expires_at=self._token_expires_at,
        )

        return self._cached_token

    async def _request_token(self) -> Dict[str, Any]:
        """
        Request a new access token from Cribl OAuth endpoint.

        Returns:
            Token response containing access_token and expires_in

        Raises:
            httpx.HTTPStatusError: If token request fails
            ValueError: If response is invalid
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.OAUTH_AUDIENCE,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )

            response.raise_for_status()
            token_data = response.json()

            if "access_token" not in token_data:
                log.error("invalid_token_response", response=token_data)
                raise ValueError("OAuth response missing access_token")

            return token_data

    def invalidate_cache(self) -> None:
        """
        Invalidate cached token, forcing a new token request on next call.

        Use this if you receive a 401 Unauthorized with a cached token.
        """
        log.debug("invalidating_cached_oauth_token")
        self._cached_token = None
        self._token_expires_at = None
