"""
Integration tests for analyzers API router.

Tests analyzer listing and information endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from cribl_hc.api.app import app


@pytest.fixture
async def async_client():
    """Create async test client for the API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestAnalyzersAPI:
    """Test analyzers API endpoints."""

    @pytest.mark.asyncio
    async def test_list_analyzers(self, async_client):
        """Test listing available analyzers."""
        response = await async_client.get("/api/v1/analyzers")

        assert response.status_code == 200
        data = response.json()
        assert "analyzers" in data
        assert "total_count" in data
        assert isinstance(data["analyzers"], list)
        assert len(data["analyzers"]) > 0

        # Check analyzer structure
        for analyzer in data["analyzers"]:
            assert "name" in analyzer
            assert "description" in analyzer

    @pytest.mark.asyncio
    async def test_get_analyzer_by_name(self, async_client):
        """Test getting specific analyzer information."""
        # First get list to find a valid analyzer name
        list_response = await async_client.get("/api/v1/analyzers")
        data = list_response.json()
        analyzers = data["analyzers"]

        if len(analyzers) > 0:
            analyzer_name = analyzers[0]["name"]

            response = await async_client.get(f"/api/v1/analyzers/{analyzer_name}")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == analyzer_name
            assert "description" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_analyzer(self, async_client):
        """Test getting analyzer that doesn't exist."""
        response = await async_client.get("/api/v1/analyzers/nonexistent-analyzer")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analyzers_have_required_fields(self, async_client):
        """Test that all analyzers have required fields."""
        response = await async_client.get("/api/v1/analyzers")
        data = response.json()
        analyzers = data["analyzers"]

        required_fields = ["name", "description", "api_calls", "permissions"]

        for analyzer in analyzers:
            for field in required_fields:
                assert field in analyzer
                assert analyzer[field] is not None

    @pytest.mark.asyncio
    async def test_analyzer_objectives(self, async_client):
        """Test that known objectives are present."""
        response = await async_client.get("/api/v1/analyzers")
        data = response.json()
        analyzers = data["analyzers"]

        names = {analyzer["name"] for analyzer in analyzers}

        # Should have at least these core objectives
        expected_names = {"health", "config", "resource"}
        assert expected_names.issubset(names)


class TestAnalyzerMetadata:
    """Test analyzer metadata and capabilities."""

    @pytest.mark.asyncio
    async def test_analyzer_api_calls(self, async_client):
        """Test that analyzers expose API call estimates."""
        response = await async_client.get("/api/v1/analyzers")
        data = response.json()

        assert "total_api_calls" in data
        assert data["total_api_calls"] > 0

        for analyzer in data["analyzers"]:
            assert "api_calls" in analyzer
            assert isinstance(analyzer["api_calls"], int)
            assert analyzer["api_calls"] > 0

    @pytest.mark.asyncio
    async def test_analyzer_permissions(self, async_client):
        """Test that analyzers expose their required permissions."""
        response = await async_client.get("/api/v1/analyzers")
        data = response.json()

        for analyzer in data["analyzers"]:
            assert "permissions" in analyzer
            assert isinstance(analyzer["permissions"], list)
            # All analyzers should require at least one permission
            assert len(analyzer["permissions"]) > 0
