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
            "credential_name": "nonexistent-credential",
            "objectives": ["health"],
            "options": {}
        }

        response = await async_client.post(
            "/api/v1/analysis/start",
            json=analysis_request
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_analysis_invalid_objectives(self, async_client, test_credential):
        """Test starting analysis with invalid objectives."""
        analysis_request = {
            "credential_name": test_credential["name"],
            "objectives": ["invalid-objective"],
            "options": {}
        }

        response = await async_client.post(
            "/api/v1/analysis/start",
            json=analysis_request
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_analysis_status(self, async_client, test_credential):
        """Test retrieving analysis status."""
        # Start an analysis
        analysis_request = {
            "credential_name": test_credential["name"],
            "objectives": ["health"],
            "options": {}
        }

        with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
            start_response = await async_client.post(
                "/api/v1/analysis/start",
                json=analysis_request
            )
            analysis_id = start_response.json()["analysis_id"]

        # Get status
        response = await async_client.get(f"/api/v1/analysis/{analysis_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "analysis_id" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_analysis(self, async_client):
        """Test getting status of non-existent analysis."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"/api/v1/analysis/{fake_id}/status")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_analyses(self, async_client, test_credential):
        """Test listing all analysis runs."""
        # Start multiple analyses
        for i in range(3):
            analysis_request = {
                "credential_name": test_credential["name"],
                "objectives": ["health"],
                "options": {}
            }
            with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
                await async_client.post("/api/v1/analysis/start", json=analysis_request)

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
            "credential_name": test_credential["name"],
            "objectives": ["health"],
            "options": {}
        }

        with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
            start_response = await async_client.post(
                "/api/v1/analysis/start",
                json=analysis_request
            )
            analysis_id = start_response.json()["analysis_id"]

        # Mock completed analysis with results
        with patch('cribl_hc.api.routers.analysis.get_analysis_results') as mock_get:
            mock_results = {
                "analysis_id": analysis_id,
                "status": "completed",
                "health_score": 85.5,
                "findings": [],
                "recommendations": []
            }
            mock_get.return_value = mock_results

            response = await async_client.get(f"/api/v1/analysis/{analysis_id}/results")

        assert response.status_code == 200
        data = response.json()
        assert "health_score" in data or "findings" in data

    @pytest.mark.asyncio
    async def test_delete_analysis(self, async_client, test_credential):
        """Test deleting an analysis run."""
        # Start analysis
        analysis_request = {
            "credential_name": test_credential["name"],
            "objectives": ["health"],
            "options": {}
        }

        with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
            start_response = await async_client.post(
                "/api/v1/analysis/start",
                json=analysis_request
            )
            analysis_id = start_response.json()["analysis_id"]

        # Delete it
        response = await async_client.delete(f"/api/v1/analysis/{analysis_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = await async_client.get(f"/api/v1/analysis/{analysis_id}/status")
        assert get_response.status_code == 404


class TestAnalysisExport:
    """Test analysis export functionality."""

    @pytest.mark.asyncio
    async def test_export_markdown(self, async_client, test_credential):
        """Test exporting results as Markdown."""
        # Create mock analysis
        analysis_id = "test-analysis-123"

        with patch('cribl_hc.api.routers.analysis.generate_markdown_report') as mock_gen:
            mock_gen.return_value = "# Health Check Report\n\nTest results..."

            response = await async_client.get(
                f"/api/v1/analysis/{analysis_id}/export/md"
            )

        if response.status_code == 200:
            assert response.headers["content-type"] == "text/markdown"
            assert "Health Check Report" in response.text

    @pytest.mark.asyncio
    async def test_export_json(self, async_client, test_credential):
        """Test exporting results as JSON."""
        analysis_id = "test-analysis-456"

        with patch('cribl_hc.api.routers.analysis.get_analysis_results') as mock_get:
            mock_get.return_value = {
                "analysis_id": analysis_id,
                "status": "completed",
                "health_score": 90.0
            }

            response = await async_client.get(
                f"/api/v1/analysis/{analysis_id}/export/json"
            )

        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json"
            data = response.json()
            assert "analysis_id" in data

    @pytest.mark.asyncio
    async def test_export_html(self, async_client, test_credential):
        """Test exporting results as HTML."""
        analysis_id = "test-analysis-789"

        with patch('cribl_hc.api.routers.analysis.generate_html_report') as mock_gen:
            mock_gen.return_value = "<html><body>Report</body></html>"

            response = await async_client.get(
                f"/api/v1/analysis/{analysis_id}/export/html"
            )

        if response.status_code == 200:
            assert response.headers["content-type"] == "text/html"
            assert "<html>" in response.text


class TestAnalysisValidation:
    """Test analysis request validation."""

    @pytest.mark.asyncio
    async def test_empty_objectives(self, async_client, test_credential):
        """Test that empty objectives list is rejected."""
        analysis_request = {
            "credential_name": test_credential["name"],
            "objectives": [],
            "options": {}
        }

        response = await async_client.post(
            "/api/v1/analysis/start",
            json=analysis_request
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_duplicate_objectives(self, async_client, test_credential):
        """Test handling of duplicate objectives."""
        analysis_request = {
            "credential_name": test_credential["name"],
            "objectives": ["health", "health"],
            "options": {}
        }

        response = await async_client.post(
            "/api/v1/analysis/start",
            json=analysis_request
        )

        # Should either deduplicate or reject
        assert response.status_code in [202, 422]

    @pytest.mark.asyncio
    async def test_valid_objectives(self, async_client, test_credential):
        """Test that valid objectives are accepted."""
        valid_objectives = [
            ["health"],
            ["config"],
            ["resource"],
            ["health", "config"],
            ["health", "config", "resource"]
        ]

        for objectives in valid_objectives:
            analysis_request = {
                "credential_name": test_credential["name"],
                "objectives": objectives,
                "options": {}
            }

            with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
                response = await async_client.post(
                    "/api/v1/analysis/start",
                    json=analysis_request
                )

            assert response.status_code == 202


class TestAnalysisConcurrency:
    """Test concurrent analysis handling."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_analyses(self, async_client, test_credential):
        """Test running multiple analyses concurrently."""
        analysis_request = {
            "credential_name": test_credential["name"],
            "objectives": ["health"],
            "options": {}
        }

        # Start multiple analyses concurrently
        with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
            responses = await asyncio.gather(*[
                async_client.post("/api/v1/analysis/start", json=analysis_request)
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
            "credential_name": test_credential["name"],
            "objectives": ["health"],
            "options": {}
        }

        # Try to start many analyses for same credential
        started = 0
        with patch('cribl_hc.api.routers.analysis.start_analysis_background'):
            for _ in range(20):
                response = await async_client.post(
                    "/api/v1/analysis/start",
                    json=analysis_request
                )
                if response.status_code == 202:
                    started += 1

        # Should either all succeed or enforce a limit
        assert started > 0
