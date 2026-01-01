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
        """Test creating a new credential with bearer token."""
        import uuid
        unique_name = f"test-prod-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
            "token": "test-bearer-token-12345"
        }

        response = await async_client.post(
            "/api/v1/credentials",
            json=credential_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["url"] == "https://cribl.example.com:9000"
        assert data["auth_type"] == "bearer"
        assert data["has_token"] is True
        assert "token" not in data  # Token should not be returned

    @pytest.mark.asyncio
    async def test_create_credential_oauth(self, async_client):
        """Test creating a new credential with OAuth."""
        import uuid
        unique_name = f"test-oauth-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "oauth",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret"
        }

        response = await async_client.post(
            "/api/v1/credentials",
            json=credential_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["auth_type"] == "oauth"
        assert data["has_oauth"] is True
        assert "client_secret" not in data  # Secret should not be returned

    @pytest.mark.asyncio
    async def test_create_credential_missing_fields(self, async_client):
        """Test creating credential with missing required fields."""
        incomplete_data = {
            "name": "test-prod"
            # Missing url and auth_type
        }

        response = await async_client.post(
            "/api/v1/credentials",
            json=incomplete_data
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_credential_duplicate_name(self, async_client):
        """Test creating credential with duplicate name."""
        import uuid
        unique_name = f"duplicate-test-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
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
        import uuid
        batch_id = uuid.uuid4().hex[:8]
        # Create some test credentials
        for i in range(3):
            credential_data = {
                "name": f"test-cred-{batch_id}-{i}",
                "url": f"https://cribl{i}.example.com:9000",
                "auth_type": "bearer",
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
        import uuid
        unique_name = f"get-test-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
            "token": "test-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get(f"/api/v1/credentials/{unique_name}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == unique_name
        assert "token" not in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_credential(self, async_client):
        """Test getting a credential that doesn't exist."""
        response = await async_client.get("/api/v1/credentials/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_credential(self, async_client):
        """Test updating an existing credential."""
        import uuid
        unique_name = f"update-test-{uuid.uuid4().hex[:8]}"
        # Create credential
        original_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
            "token": "original-token"
        }
        await async_client.post("/api/v1/credentials", json=original_data)

        # Update it
        updated_data = {
            "url": "https://cribl-new.example.com:9000",
            "token": "new-token"
        }
        response = await async_client.put(
            f"/api/v1/credentials/{unique_name}",
            json=updated_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://cribl-new.example.com:9000"

    @pytest.mark.asyncio
    async def test_delete_credential(self, async_client):
        """Test deleting a credential."""
        import uuid
        unique_name = f"delete-test-{uuid.uuid4().hex[:8]}"
        # Create credential
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
            "token": "test-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        # Delete it
        response = await async_client.delete(f"/api/v1/credentials/{unique_name}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await async_client.get(f"/api/v1/credentials/{unique_name}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_test_connection_success(self, async_client, mock_cribl_client):
        """Test connection testing endpoint with successful connection."""
        import uuid
        unique_name = f"connection-test-{uuid.uuid4().hex[:8]}"
        # Create credential
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
            "token": "test-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        # Mock the CriblAPIClient
        with patch('cribl_hc.api.routers.credentials.CriblAPIClient', return_value=mock_cribl_client):
            response = await async_client.post(f"/api/v1/credentials/{unique_name}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "cribl_version" in data

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, async_client):
        """Test connection testing with invalid credentials."""
        import uuid
        unique_name = f"connection-fail-test-{uuid.uuid4().hex[:8]}"
        # Create credential with invalid URL
        credential_data = {
            "name": unique_name,
            "url": "https://invalid-url-that-does-not-exist.local:9000",
            "auth_type": "bearer",
            "token": "invalid-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.post(f"/api/v1/credentials/{unique_name}/test")

        assert response.status_code == 200
        data = response.json()
        # Connection should fail but not return 500
        assert "success" in data


class TestCredentialSecurity:
    """Test security aspects of credential management."""

    @pytest.mark.asyncio
    async def test_tokens_not_exposed_in_list(self, async_client):
        """Test that bearer tokens are never exposed in list endpoint."""
        import uuid
        unique_name = f"security-test-1-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
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
        import uuid
        unique_name = f"security-test-2-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "bearer",
            "token": "another-secret-token"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get(f"/api/v1/credentials/{unique_name}")
        data = response.json()

        assert "token" not in data
        assert "another-secret-token" not in str(data)

    @pytest.mark.asyncio
    async def test_client_secret_not_exposed(self, async_client):
        """Test that OAuth client secrets are not exposed."""
        import uuid
        unique_name = f"oauth-test-sec-{uuid.uuid4().hex[:8]}"
        credential_data = {
            "name": unique_name,
            "url": "https://cribl.example.com:9000",
            "auth_type": "oauth",
            "client_id": "test-client-id",
            "client_secret": "super-secret-client-secret"
        }
        await async_client.post("/api/v1/credentials", json=credential_data)

        response = await async_client.get(f"/api/v1/credentials/{unique_name}")
        data = response.json()

        assert "client_secret" not in data
        assert "super-secret-client-secret" not in str(data)
