"""
Tests for OAuth client-credentials authentication against Cribl.Cloud.
"""

import json
from datetime import datetime, timedelta

import httpx
import pytest
import respx

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.exceptions import APIAuthenticationError

TOKEN_URL = CriblAPIClient.DEFAULT_OAUTH_TOKEN_URL
BASE_URL = "https://main-acme.cribl.cloud"


def oauth_client(**overrides):
    kwargs = {
        "base_url": BASE_URL,
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
    }
    kwargs.update(overrides)
    return CriblAPIClient(**kwargs)


class TestConstruction:
    def test_requires_some_form_of_credential(self):
        with pytest.raises(ValueError, match="auth_token.*client_id|client_id"):
            CriblAPIClient(base_url=BASE_URL)

    def test_bearer_token_alone_is_accepted(self):
        client = CriblAPIClient(base_url=BASE_URL, auth_token="tok")
        assert client.uses_oauth is False

    def test_client_credentials_alone_are_accepted(self):
        assert oauth_client().uses_oauth is True

    def test_client_id_without_secret_is_rejected(self):
        with pytest.raises(ValueError):
            CriblAPIClient(base_url=BASE_URL, client_id="only-id")

    def test_endpoints_are_overridable_for_government_cloud(self):
        client = oauth_client(
            oauth_token_url="https://login.cribl-gov.cloud/oauth/token",
            oauth_audience="https://api.cribl-gov.cloud",
        )
        assert client.oauth_token_url == "https://login.cribl-gov.cloud/oauth/token"
        assert client.oauth_audience == "https://api.cribl-gov.cloud"


class TestTokenExchange:
    @pytest.mark.asyncio
    @respx.mock
    async def test_exchanges_credentials_for_a_bearer_token(self):
        route = respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "issued-token", "expires_in": 86400})
        )

        client = oauth_client()
        async with client:
            assert client.auth_token == "issued-token"

        assert route.called
        sent = json.loads(route.calls.last.request.read())
        assert sent == {
            "grant_type": "client_credentials",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "audience": "https://api.cribl.cloud",
        }

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_is_used_on_subsequent_requests(self):
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "issued-token", "expires_in": 86400})
        )
        endpoint = respx.get(f"{BASE_URL}/api/v1/system/info").mock(
            return_value=httpx.Response(200, json={"items": []})
        )

        async with oauth_client() as client:
            await client.get("/api/v1/system/info")

        assert endpoint.calls.last.request.headers["Authorization"] == "Bearer issued-token"

    @pytest.mark.asyncio
    @respx.mock
    async def test_expiry_is_recorded_from_expires_in(self):
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        )

        client = oauth_client()
        async with client:
            assert client._token_expires_at is not None
            remaining = client._token_expires_at - datetime.utcnow()
            assert timedelta(minutes=55) < remaining <= timedelta(hours=1)

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_bearer_token_client_never_calls_the_token_endpoint(self):
        route = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={}))
        respx.get(f"{BASE_URL}/api/v1/system/info").mock(
            return_value=httpx.Response(200, json={"items": []})
        )

        async with CriblAPIClient(base_url=BASE_URL, auth_token="static") as client:
            await client.get("/api/v1/system/info")

        assert not route.called


class TestTokenRefresh:
    @pytest.mark.asyncio
    @respx.mock
    async def test_a_fresh_token_is_reused(self):
        route = respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "t1", "expires_in": 86400})
        )

        async with oauth_client() as client:
            await client._ensure_access_token()
            await client._ensure_access_token()

        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_token_near_expiry_is_replaced(self):
        respx.post(TOKEN_URL).mock(
            side_effect=[
                httpx.Response(200, json={"access_token": "first", "expires_in": 86400}),
                httpx.Response(200, json={"access_token": "second", "expires_in": 86400}),
            ]
        )

        async with oauth_client() as client:
            assert client.auth_token == "first"

            # Inside the refresh margin, so the next use must re-exchange.
            client._token_expires_at = datetime.utcnow() + timedelta(seconds=30)
            await client._ensure_access_token()

            assert client.auth_token == "second"
            assert client._client.headers["Authorization"] == "Bearer second"


class TestFailures:
    @pytest.mark.asyncio
    @respx.mock
    async def test_rejected_credentials_raise_authentication_error(self):
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(401, json={"error": "access_denied"})
        )

        with pytest.raises(APIAuthenticationError, match="OAuth token request failed"):
            async with oauth_client():
                pass

    @pytest.mark.asyncio
    @respx.mock
    async def test_the_error_does_not_echo_the_secret_back(self):
        # A token endpoint can reflect submitted parameters; the raised message
        # must not carry the secret onwards into a log or an API response.
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                400, json={"error": "invalid_client", "client_secret": "test-client-secret"}
            )
        )

        with pytest.raises(APIAuthenticationError) as exc_info:
            async with oauth_client():
                pass

        assert "test-client-secret" not in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_response_without_a_token_is_rejected(self):
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"expires_in": 3600}))

        with pytest.raises(APIAuthenticationError, match="no access_token"):
            async with oauth_client():
                pass
