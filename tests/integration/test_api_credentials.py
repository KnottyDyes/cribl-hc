"""
Integration tests for credentials API router.

Tests the full credential management workflow including:
- Creating credentials
- Testing connections
- Listing credentials
- Updating credentials
- Deleting credentials
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from cribl_hc.api.app import app
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
async def async_client():
    """Create async test client for the API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_cribl_client():
    """Mock Cribl API client for testing."""
    mock = AsyncMock(spec=CriblAPIClient)
    mock.test_connection = AsyncMock(return_value=MagicMock(
        success=True,
        cribl_version="5.0.0",
        response_time_ms=123.45,
        message="Connection successful",
        error=None
    ))
    return mock


class TestCredentialsAPI:
    """Test credentials API endpoints."""

    @pytest.mark.asyncio
    async def test_create_credential_success(self, async_client):
        """Test creating a new credential."""
        credential_data = {
            "name": "test-prod",
            "url": "https://cribl.example.com:9000",
            "token": "test-bearer-token-12345",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret"
        }

        response = await async_client.post(
            "/api/v1/credentials",
            json=credential_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-prod"
        assert data["url"] == "https://cribl.example.com:9000"
        assert "token" not in data  # Token should not be returned
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_credential_missing_fields(self, async_client):
        """Test creating credential with missing required fields."""
        incomplete_data = {
            "name": "test-prod"
            # Missing url and token
        }

        response = await async_client.post(
            "/api/v1/credentials",
            json=incomplete_data
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_credential_duplicate_name(self, async_client):
        """Test creating credential with duplicate name."""
        credential_data = {
            "name": "duplicate-test",
            "url": "https://cribl.example.com:9000",
            "token": "test-token"
        }

        # Create first credential
        response1 = await async_client.post(
            "/api/v1/credentials",
            json=credential_data
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = await async_client.post(
            "/api/v1/credentials",
            json=credential_data
        )
        assert response2.status_code == 409  # Conflict

    @pytest.mark.asyncio
    async def test_list_credentials(self, async_client):
        """Test listing all credentials."""
        # Create some test credentials
        for i in range(3):
            credential_data = {
                "name": f"test-cred-{i}",
                "url": f"https://cribl{i}.example.com:9000",
                "token": f"token-{i}"
            }
            await async_client.post("/api/v1/credentials", json=credential_data)

        # List credentials
        response = await async_client.get("/api/v1/credentials")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

        # Verify tokens are not included
        for cred in data:
            assert "token" not in cred
            assert "name" in cred
            assert "url" in cred

    @pytest.mark.asyncio
    async def test_get_credential_by_name(self, async_client):
        """Test getting a specific credential by name."""
        credential_data = {
            "name": "get-test",
            "url": "https://cribl.example.com:9000",
            "token": "test-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get("/api/v1/credentials/get-test")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "get-test"
        assert "token" not in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_credential(self, async_client):
        """Test getting a credential that doesn't exist."""
        response = await async_client.get("/api/v1/credentials/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_credential(self, async_client):
        """Test updating an existing credential."""
        # Create credential
        original_data = {
            "name": "update-test",
            "url": "https://cribl.example.com:9000",
            "token": "original-token"
        }
        await async_client.post("/api/v1/credentials", json=original_data)

        # Update it
        updated_data = {
            "url": "https://cribl-new.example.com:9000",
            "token": "new-token"
        }
        response = await async_client.put(
            "/api/v1/credentials/update-test",
            json=updated_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://cribl-new.example.com:9000"

    @pytest.mark.asyncio
    async def test_delete_credential(self, async_client):
        """Test deleting a credential."""
        # Create credential
        credential_data = {
            "name": "delete-test",
            "url": "https://cribl.example.com:9000",
            "token": "test-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        # Delete it
        response = await async_client.delete("/api/v1/credentials/delete-test")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await async_client.get("/api/v1/credentials/delete-test")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_test_connection_success(self, async_client, mock_cribl_client):
        """Test connection testing endpoint with successful connection."""
        # Create credential
        credential_data = {
            "name": "connection-test",
            "url": "https://cribl.example.com:9000",
            "token": "test-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        # Mock the CriblAPIClient
        with patch('cribl_hc.api.routers.credentials.CriblAPIClient', return_value=mock_cribl_client):
            response = await async_client.post("/api/v1/credentials/connection-test/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "cribl_version" in data

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, async_client):
        """Test connection testing with invalid credentials."""
        # Create credential with invalid URL
        credential_data = {
            "name": "connection-fail-test",
            "url": "https://invalid-url-that-does-not-exist.local:9000",
            "token": "invalid-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.post("/api/v1/credentials/connection-fail-test/test")

        assert response.status_code == 200
        data = response.json()
        # Connection should fail but not return 500
        assert "success" in data

    @pytest.mark.asyncio
    async def test_credential_name_validation(self, async_client):
        """Test credential name validation rules."""
        invalid_names = [
            "",  # Empty
            "a" * 101,  # Too long
            "test name",  # Spaces
            "test@name",  # Special chars
        ]

        for invalid_name in invalid_names:
            credential_data = {
                "name": invalid_name,
                "url": "https://cribl.example.com:9000",
                "token": "test-token"
            }
            response = await async_client.post(
                "/api/v1/credentials",
                json=credential_data
            )
            # Should get validation error
            assert response.status_code in [422, 400]

    @pytest.mark.asyncio
    async def test_url_validation(self, async_client):
        """Test URL validation for credentials."""
        invalid_urls = [
            "not-a-url",
            "ftp://cribl.example.com",  # Wrong protocol
            "http://",  # Incomplete
        ]

        for invalid_url in invalid_urls:
            credential_data = {
                "name": f"test-{invalid_urls.index(invalid_url)}",
                "url": invalid_url,
                "token": "test-token"
            }
            response = await async_client.post(
                "/api/v1/credentials",
                json=credential_data
            )
            # Should get validation error
            assert response.status_code in [422, 400]


class TestCredentialSecurity:
    """Test security aspects of credential management."""

    @pytest.mark.asyncio
    async def test_tokens_not_exposed_in_list(self, async_client):
        """Test that bearer tokens are never exposed in list endpoint."""
        credential_data = {
            "name": "security-test-1",
            "url": "https://cribl.example.com:9000",
            "token": "super-secret-token-12345"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get("/api/v1/credentials")
        data = response.json()

        for cred in data:
            assert "token" not in cred
            assert "super-secret-token" not in str(cred)

    @pytest.mark.asyncio
    async def test_tokens_not_exposed_in_get(self, async_client):
        """Test that bearer tokens are never exposed in get endpoint."""
        credential_data = {
            "name": "security-test-2",
            "url": "https://cribl.example.com:9000",
            "token": "another-secret-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get("/api/v1/credentials/security-test-2")
        data = response.json()

        assert "token" not in data
        assert "another-secret-token" not in str(data)

    @pytest.mark.asyncio
    async def test_client_secret_not_exposed(self, async_client):
        """Test that OAuth client secrets are not exposed."""
        credential_data = {
            "name": "oauth-test",
            "url": "https://cribl.example.com:9000",
            "token": "test-token",
            "client_id": "test-client-id",
            "client_secret": "super-secret-client-secret"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get("/api/v1/credentials/oauth-test")
        data = response.json()

        assert "client_secret" not in data
        assert "super-secret-client-secret" not in str(data)
