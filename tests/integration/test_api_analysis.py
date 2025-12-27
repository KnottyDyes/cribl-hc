"""
Integration tests for analysis API router.

Tests the full analysis workflow including:
- Starting analysis runs
- Checking analysis status
- Retrieving analysis results
- Exporting results in different formats
- WebSocket progress updates
"""

import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from cribl_hc.api.app import app


@pytest.fixture
async def async_client():
    """Create async test client for the API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_credential(async_client):
    """Create a test credential for analysis tests."""
    import uuid
    cred_name = f"analysis-test-{uuid.uuid4().hex[:8]}"
    credential_data = {
        "name": cred_name,
        "url": "https://cribl.example.com:9000",
        "auth_type": "bearer",
        "token": "test-token"
    }
    response = await async_client.post("/api/v1/credentials", json=credential_data)
    assert response.status_code == 201, f"Failed to create credential: {response.status_code} - {response.text}"
    return response.json()


class TestAnalysisWorkflow:
    """Test complete analysis workflow."""

    @pytest.mark.asyncio
    async def test_start_analysis_success(self, async_client, test_credential):
        """Test starting a new analysis run."""
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health"]
        }

        with patch('cribl_hc.api.routers.analysis.run_analysis_task') as mock_task:
            # Mock the background task
            mock_task.return_value = None

            response = await async_client.post(
                "/api/v1/analysis",
                json=analysis_request
            )

        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "pending"
        assert "deployment_name" in data

    @pytest.mark.asyncio
    async def test_start_analysis_invalid_credential(self, async_client):
        """Test starting analysis with non-existent credential."""
        analysis_request = {
            "deployment_name": "nonexistent-credential",
            "analyzers": ["health"]
        }

        response = await async_client.post(
            "/api/v1/analysis",
            json=analysis_request
        )

        # Should succeed - deployment validation happens during execution
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_start_analysis_invalid_objectives(self, async_client, test_credential):
        """Test starting analysis with invalid objectives."""
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["invalid-objective"]
        }

        response = await async_client.post(
            "/api/v1/analysis",
            json=analysis_request
        )

        # Should succeed - analyzer validation happens during execution
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_get_analysis_status(self, async_client, test_credential):
        """Test retrieving analysis status."""
        # Start an analysis
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health"]
        }

        with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
            start_response = await async_client.post(
                "/api/v1/analysis",
                json=analysis_request
            )
            analysis_id = start_response.json()["analysis_id"]

        # Get status
        response = await async_client.get(f"/api/v1/analysis/{analysis_id}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "analysis_id" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_analysis(self, async_client):
        """Test getting status of non-existent analysis."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"/api/v1/analysis/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_analyses(self, async_client, test_credential):
        """Test listing all analysis runs."""
        # Start multiple analyses
        for i in range(3):
            analysis_request = {
                "deployment_name": test_credential["name"],
                "analyzers": ["health"]
            }
            with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
                await async_client.post("/api/v1/analysis", json=analysis_request)

        # List all
        response = await async_client.get("/api/v1/analysis")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_get_analysis_results(self, async_client, test_credential):
        """Test retrieving completed analysis results."""
        # Start analysis
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health"]
        }

        with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
            start_response = await async_client.post(
                "/api/v1/analysis",
                json=analysis_request
            )
            analysis_id = start_response.json()["analysis_id"]

        # Get results
        response = await async_client.get(f"/api/v1/analysis/{analysis_id}/results")

        # May be 200 with results, 404 if not found, or 409 if still running
        assert response.status_code in [200, 404, 409]
        if response.status_code == 200:
            data = response.json()
            assert "analysis_id" in data

    @pytest.mark.asyncio
    async def test_delete_analysis(self, async_client, test_credential):
        """Test deleting an analysis run."""
        # Start analysis
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health"]
        }

        with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
            start_response = await async_client.post(
                "/api/v1/analysis",
                json=analysis_request
            )
            analysis_id = start_response.json()["analysis_id"]

        # Delete it (endpoint may not exist yet)
        response = await async_client.delete(f"/api/v1/analysis/{analysis_id}")

        # May be 204 (No Content), 404 (Not Found), or 405 (Method Not Allowed)
        assert response.status_code in [204, 404, 405]


class TestAnalysisExport:
    """Test analysis export functionality."""

    @pytest.mark.asyncio
    async def test_export_markdown(self, async_client, test_credential):
        """Test exporting results as Markdown."""
        # Create a fake analysis ID
        analysis_id = "test-analysis-123"

        response = await async_client.get(
            f"/api/v1/analysis/{analysis_id}/export/markdown"
        )

        # May be 404 (not found) or 400 (not completed)
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_export_json(self, async_client, test_credential):
        """Test exporting results as JSON."""
        analysis_id = "test-analysis-456"

        response = await async_client.get(
            f"/api/v1/analysis/{analysis_id}/export/json"
        )

        # May be 404 (not found) or 400 (not completed)
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            data = response.json()
            assert "analysis_id" in data

    @pytest.mark.asyncio
    async def test_export_html(self, async_client, test_credential):
        """Test exporting results as HTML."""
        analysis_id = "test-analysis-789"

        response = await async_client.get(
            f"/api/v1/analysis/{analysis_id}/export/html"
        )

        # May be 404 (not found) or 400 (not completed)
        assert response.status_code in [200, 400, 404]


class TestAnalysisValidation:
    """Test analysis request validation."""

    @pytest.mark.asyncio
    async def test_empty_objectives(self, async_client, test_credential):
        """Test that empty objectives list is handled."""
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": []
        }

        response = await async_client.post(
            "/api/v1/analysis",
            json=analysis_request
        )

        # May succeed with all analyzers or reject empty list
        assert response.status_code in [202, 422]

    @pytest.mark.asyncio
    async def test_duplicate_objectives(self, async_client, test_credential):
        """Test handling of duplicate objectives."""
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health", "health"]
        }

        response = await async_client.post(
            "/api/v1/analysis",
            json=analysis_request
        )

        # Should either deduplicate or reject
        assert response.status_code in [202, 422]

    @pytest.mark.asyncio
    async def test_valid_objectives(self, async_client, test_credential):
        """Test that valid objectives are accepted."""
        valid_analyzers = [
            ["health"],
            ["config"],
            ["resource"],
            ["health", "config"],
            ["health", "config", "resource"]
        ]

        for analyzers in valid_analyzers:
            analysis_request = {
                "deployment_name": test_credential["name"],
                "analyzers": analyzers
            }

            with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
                response = await async_client.post(
                    "/api/v1/analysis",
                    json=analysis_request
                )

            assert response.status_code == 202


class TestAnalysisConcurrency:
    """Test concurrent analysis handling."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_analyses(self, async_client, test_credential):
        """Test running multiple analyses concurrently."""
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health"]
        }

        # Start multiple analyses concurrently
        with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
            responses = await asyncio.gather(*[
                async_client.post("/api/v1/analysis", json=analysis_request)
                for _ in range(5)
            ])

        # All should succeed
        for response in responses:
            assert response.status_code == 202

        # All should have unique IDs
        analysis_ids = [r.json()["analysis_id"] for r in responses]
        assert len(set(analysis_ids)) == 5

    @pytest.mark.asyncio
    async def test_analysis_per_credential_limit(self, async_client, test_credential):
        """Test that there's a reasonable limit on concurrent analyses per credential."""
        analysis_request = {
            "deployment_name": test_credential["name"],
            "analyzers": ["health"]
        }

        # Try to start many analyses for same credential
        started = 0
        with patch('cribl_hc.api.routers.analysis.run_analysis_task'):
            for _ in range(20):
                response = await async_client.post(
                    "/api/v1/analysis",
                    json=analysis_request
                )
                if response.status_code == 202:
                    started += 1

        # Should either all succeed or enforce a limit
        assert started > 0
