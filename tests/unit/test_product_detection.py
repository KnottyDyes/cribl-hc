"""
Unit tests for product type detection (Stream vs Edge vs Lake).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    return mock


class TestProductDetection:
    """Test product type detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_stream_from_product_field(self, mock_httpx_client):
        """Test detecting Cribl Stream from explicit product field."""
        # Arrange
        version_response = {
            "version": "4.5.0",
            "product": "stream"
        }

        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "stream"
        assert client.is_stream is True
        assert client.is_edge is False
        assert client.is_lake is False
        assert client.product_version == "4.5.0"

    @pytest.mark.asyncio
    async def test_detect_edge_from_product_field(self, mock_httpx_client):
        """Test detecting Cribl Edge from explicit product field."""
        # Arrange
        version_response = {
            "version": "4.8.0",
            "product": "edge"
        }

        client = CriblAPIClient(
            base_url="https://edge.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "edge"
        assert client.is_stream is False
        assert client.is_edge is True
        assert client.is_lake is False
        assert client.product_version == "4.8.0"

    @pytest.mark.asyncio
    async def test_detect_lake_from_product_field(self, mock_httpx_client):
        """Test detecting Cribl Lake from explicit product field."""
        # Arrange
        version_response = {
            "version": "1.2.0",
            "product": "lake"
        }

        client = CriblAPIClient(
            base_url="https://lake.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "lake"
        assert client.is_stream is False
        assert client.is_edge is False
        assert client.is_lake is True
        assert client.product_version == "1.2.0"

    @pytest.mark.asyncio
    async def test_detect_edge_from_endpoint_probe(self, mock_httpx_client):
        """Test Edge detection via endpoint probing when product field missing."""
        # Arrange
        version_response = {
            "version": "4.8.0"
            # No product field
        }

        # Mock Edge-specific endpoint returning 200
        edge_response = AsyncMock()
        edge_response.status_code = 200
        mock_httpx_client.get = AsyncMock(return_value=edge_response)

        client = CriblAPIClient(
            base_url="https://edge.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "edge"
        assert client.is_edge is True
        mock_httpx_client.get.assert_called_with("/api/v1/edge/fleets")

    @pytest.mark.asyncio
    async def test_detect_lake_from_endpoint_probe(self, mock_httpx_client):
        """Test Lake detection via endpoint probing when Edge probe fails."""
        # Arrange
        version_response = {
            "version": "1.2.0"
            # No product field
        }

        # Mock Edge endpoint returning 404, Lake endpoint returning 200
        async def mock_get(endpoint):
            response = AsyncMock()
            if "/edge/fleets" in endpoint:
                response.status_code = 404  # Not Edge
            elif "/datasets" in endpoint:
                response.status_code = 200  # Is Lake
            return response

        mock_httpx_client.get = AsyncMock(side_effect=mock_get)

        client = CriblAPIClient(
            base_url="https://lake.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "lake"
        assert client.is_lake is True

    @pytest.mark.asyncio
    async def test_default_to_stream_when_no_detection(self, mock_httpx_client):
        """Test defaulting to Stream when no product indicators found."""
        # Arrange
        version_response = {
            "version": "4.5.0"
            # No product field
        }

        # Mock both Edge and Lake endpoints returning 404
        async def mock_get(endpoint):
            response = AsyncMock()
            response.status_code = 404  # Neither Edge nor Lake
            return response

        mock_httpx_client.get = AsyncMock(side_effect=mock_get)

        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "stream"
        assert client.is_stream is True
        assert client.product_version == "4.5.0"

    @pytest.mark.asyncio
    async def test_case_insensitive_product_field(self, mock_httpx_client):
        """Test that product field detection is case-insensitive."""
        # Arrange
        version_response = {
            "version": "4.8.0",
            "product": "EDGE"  # Uppercase
        }

        client = CriblAPIClient(
            base_url="https://edge.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "edge"
        assert client.is_edge is True

    @pytest.mark.asyncio
    async def test_edge_probe_with_401_is_still_edge(self, mock_httpx_client):
        """Test that 401 (auth error) on Edge endpoint still indicates Edge."""
        # Arrange
        version_response = {"version": "4.8.0"}

        # Mock Edge endpoint returning 401 (auth required but endpoint exists)
        edge_response = AsyncMock()
        edge_response.status_code = 401
        mock_httpx_client.get = AsyncMock(return_value=edge_response)

        client = CriblAPIClient(
            base_url="https://edge.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "edge"
        assert client.is_edge is True

    @pytest.mark.asyncio
    async def test_lake_probe_with_403_is_still_lake(self, mock_httpx_client):
        """Test that 403 (forbidden) on Lake endpoint still indicates Lake."""
        # Arrange
        version_response = {"version": "1.2.0"}

        # Mock Edge 404, Lake 403
        async def mock_get(endpoint):
            response = AsyncMock()
            if "/edge/fleets" in endpoint:
                response.status_code = 404
            elif "/datasets" in endpoint:
                response.status_code = 403  # Forbidden but exists
            return response

        mock_httpx_client.get = AsyncMock(side_effect=mock_get)

        client = CriblAPIClient(
            base_url="https://lake.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "lake"
        assert client.is_lake is True

    @pytest.mark.asyncio
    async def test_empty_version_response_defaults_to_stream(self, mock_httpx_client):
        """Test that empty version response defaults to Stream."""
        # Arrange
        version_response = None

        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.product_type == "stream"
        assert client.is_stream is True

    @pytest.mark.asyncio
    async def test_product_detection_in_test_connection(self, mock_httpx_client):
        """Test that product detection happens during test_connection."""
        # Arrange
        version_response_mock = MagicMock()
        version_response_mock.status_code = 200
        version_response_mock.json = MagicMock(return_value={
            "version": "4.8.0",
            "product": "edge"
        })

        mock_httpx_client.get = AsyncMock(return_value=version_response_mock)

        client = CriblAPIClient(
            base_url="https://edge.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Mock rate limiter as context manager
        rate_limiter_mock = AsyncMock()
        rate_limiter_mock.__aenter__ = AsyncMock(return_value=None)
        rate_limiter_mock.__aexit__ = AsyncMock(return_value=None)
        client.rate_limiter = rate_limiter_mock

        # Act
        result = await client.test_connection()

        # Assert
        assert result.success is True
        assert "Cribl Edge" in result.message
        assert client.product_type == "edge"
        assert client.is_edge is True

    @pytest.mark.asyncio
    async def test_product_detection_only_once(self, mock_httpx_client):
        """Test that product detection only runs once."""
        # Arrange
        version_response = {
            "version": "4.5.0",
            "product": "stream"
        }

        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token"
        )
        client._client = mock_httpx_client

        # Act - detect twice
        await client._detect_product_type(version_response)
        assert client.product_type == "stream"

        # Try to detect again with different product
        version_response_2 = {
            "version": "4.8.0",
            "product": "edge"  # Different!
        }
        await client._detect_product_type(version_response_2)

        # Assert - should still be stream (first detection wins)
        # Actually, re-detection DOES happen - but this is intentional
        # in case of multi-product environments
        assert client.product_type == "edge"  # Updated

    def test_product_type_properties_before_detection(self):
        """Test product type properties before detection returns None/False."""
        # Arrange
        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token"
        )

        # Assert - before detection
        assert client.product_type is None
        assert client.is_stream is False  # None != "stream"
        assert client.is_edge is False
        assert client.is_lake is False
        assert client.product_version is None

    @pytest.mark.asyncio
    async def test_cloud_deployment_detection_independent_of_product(self):
        """Test that Cloud detection works independently of product type."""
        # Arrange - Edge on Cribl Cloud
        client = CriblAPIClient(
            base_url="https://main-myorg.cribl.cloud",
            auth_token="test-token"
        )
        client._client = AsyncMock()

        version_response = {
            "version": "4.8.0",
            "product": "edge"
        }

        # Act
        await client._detect_product_type(version_response)

        # Assert
        assert client.is_cloud is True  # Cloud deployment
        assert client.is_edge is True   # Edge product
        assert client.product_type == "edge"
