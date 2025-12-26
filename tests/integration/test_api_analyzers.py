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
        assert isinstance(data, list)
        assert len(data) > 0

        # Check analyzer structure
        for analyzer in data:
            assert "name" in analyzer
            assert "objective" in analyzer
            assert "description" in analyzer

    @pytest.mark.asyncio
    async def test_get_analyzer_by_name(self, async_client):
        """Test getting specific analyzer information."""
        # First get list to find a valid analyzer name
        list_response = await async_client.get("/api/v1/analyzers")
        analyzers = list_response.json()

        if len(analyzers) > 0:
            analyzer_name = analyzers[0]["name"]

            response = await async_client.get(f"/api/v1/analyzers/{analyzer_name}")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == analyzer_name
            assert "objective" in data
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
        analyzers = response.json()

        required_fields = ["name", "objective", "description"]

        for analyzer in analyzers:
            for field in required_fields:
                assert field in analyzer
                assert analyzer[field] is not None
                assert len(str(analyzer[field])) > 0

    @pytest.mark.asyncio
    async def test_analyzers_by_objective(self, async_client):
        """Test filtering analyzers by objective."""
        response = await async_client.get("/api/v1/analyzers?objective=health")

        assert response.status_code == 200
        data = response.json()

        # All returned analyzers should be for health objective
        for analyzer in data:
            assert analyzer["objective"] == "health"

    @pytest.mark.asyncio
    async def test_analyzer_objectives(self, async_client):
        """Test that known objectives are present."""
        response = await async_client.get("/api/v1/analyzers")
        analyzers = response.json()

        objectives = {analyzer["objective"] for analyzer in analyzers}

        # Should have at least these core objectives
        expected_objectives = {"health", "config", "resource"}
        assert expected_objectives.issubset(objectives)


class TestAnalyzerMetadata:
    """Test analyzer metadata and capabilities."""

    @pytest.mark.asyncio
    async def test_analyzer_version_compatibility(self, async_client):
        """Test that analyzers expose version compatibility info."""
        list_response = await async_client.get("/api/v1/analyzers")
        analyzers = list_response.json()

        if len(analyzers) > 0:
            analyzer_name = analyzers[0]["name"]
            response = await async_client.get(f"/api/v1/analyzers/{analyzer_name}")
            data = response.json()

            # Should have version compatibility info (optional)
            if "version_compatibility" in data:
                assert isinstance(data["version_compatibility"], dict)

    @pytest.mark.asyncio
    async def test_analyzer_capabilities(self, async_client):
        """Test that analyzers expose their capabilities."""
        list_response = await async_client.get("/api/v1/analyzers")
        analyzers = list_response.json()

        for analyzer in analyzers:
            # Each analyzer should declare what it analyzes
            assert "objective" in analyzer
            assert analyzer["objective"] in [
                "health",
                "config",
                "resource",
                "security",
                "performance"
            ]
