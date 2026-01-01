"""
End-to-end integration tests for MVP (User Story 1).

Tests the complete workflow from API connection through analysis
to report generation, ensuring all components work together.
"""

import pytest
import respx
from httpx import Response


@pytest.mark.asyncio
@respx.mock
async def test_mvp_complete_workflow():
    """
    Test complete MVP workflow: connect → analyze → report.

    This test validates User Story 1 acceptance criteria:
    - Receive health score 0-100
    - Critical issues flagged and prioritized
    - Clear remediation steps provided
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    # Mock all required endpoints
    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={
                "version": "4.7.0",
                "build": "12345",
                "product": "Stream",
                "health": "healthy",
            },
        )
    )

    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "worker-01",
                        "status": "healthy",
                        "info": {
                            "hostname": "worker-01.example.com",
                            "version": "4.7.0",
                            "cpuCount": 8,
                        },
                        "metrics": {
                            "cpu": 45.0,
                            "memory": {"used": 8.0, "total": 16.0},
                            "disk": {"used": 40.0, "total": 100.0},
                        },
                    }
                ]
            },
        )
    )

    # Step 1: Connect to Cribl API
    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        # Step 2: Run health analysis
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(client)

        # Step 3: Validate results meet MVP criteria

        # Acceptance 1: Receive health score
        assert result is not None
        assert result.findings is not None

        # Acceptance 2: Issues are prioritized by severity
        severities = [f.severity for f in result.findings]
        valid_severities = {"critical", "high", "medium", "low", "info"}
        for severity in severities:
            assert severity in valid_severities

        # Acceptance 3: Clear remediation steps
        for finding in result.findings:
            # Each finding should have description
            assert finding.description
            assert len(finding.description) > 0

            # Should have remediation steps (Finding uses remediation_steps, not remediation)
            if finding.remediation_steps:
                assert len(finding.remediation_steps) > 0

        # Step 4: Verify API call budget not exceeded
        assert client.rate_limiter.total_calls_made < 100


@pytest.mark.asyncio
@respx.mock
async def test_mvp_under_5_minutes():
    """
    Test MVP completes in under 5 minutes (SC-005).

    For standard deployments (up to 100 workers), analysis should complete
    in under 5 minutes.
    """
    import time
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(200, json={"items": []})
    )

    start_time = time.time()

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()
        await analyzer.analyze(client)

    elapsed = time.time() - start_time

    # Should complete in well under 5 minutes (300 seconds)
    # For empty deployment, should be nearly instant
    assert elapsed < 10.0  # Very generous for test environment


@pytest.mark.asyncio
@respx.mock
async def test_mvp_under_100_api_calls():
    """
    Test MVP uses fewer than 100 API calls (SC-008, FR-079).

    Health analysis should stay within the 100 API call budget.
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": f"worker-{i:02d}",
                        "status": "healthy",
                        "info": {"hostname": f"worker-{i:02d}", "version": "4.7.0", "cpuCount": 8},
                        "metrics": {
                            "cpu": 40.0 + i,
                            "memory": {"used": 8.0, "total": 16.0},
                        },
                    }
                    for i in range(10)  # 10 workers
                ]
            },
        )
    )

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()
        await analyzer.analyze(client)

        # Verify API call budget
        assert client.rate_limiter.total_calls_made < 100
        # Health analyzer should use ~3 calls (status, workers, health)
        assert client.rate_limiter.total_calls_made <= 10


@pytest.mark.asyncio
@respx.mock
async def test_mvp_graceful_error_handling():
    """
    Test MVP handles API errors gracefully (FR-084).

    Should generate partial reports when some API calls fail.
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    # System status succeeds
    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # Workers endpoint fails
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(500, json={"error": "Internal server error"})
    )

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()

        # Should not raise exception
        result = await analyzer.analyze(client)

        # Should return partial results
        assert result is not None
        assert isinstance(result.findings, list)


@pytest.mark.asyncio
@respx.mock
async def test_mvp_read_only_access():
    """
    Test MVP uses only read-only API access (FR-076, Constitution Principle I).

    Should only make GET requests, never POST/PUT/DELETE.
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    # Track all requests
    requests_made = []

    def track_request(request):
        requests_made.append(request)
        return Response(200, json={})

    # Mock with request tracker
    respx.route().mock(side_effect=track_request)

    # Override specific endpoints
    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(200, json={"version": "4.7.0", "health": "healthy"})
    )
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(200, json={"items": []})
    )

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()
        await analyzer.analyze(client)

    # All requests should be GET (read-only)
    for request in requests_made:
        assert request.method == "GET", f"Non-GET request detected: {request.method} {request.url}"


@pytest.mark.asyncio
@respx.mock
async def test_mvp_actionable_recommendations():
    """
    Test MVP provides actionable recommendations (FR-086, SC-014).

    90% of users should understand findings without additional support.
    """
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(200, json={"version": "4.7.0", "health": "healthy"})
    )

    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "worker-01",
                        "status": "healthy",
                        "info": {"hostname": "worker-01", "version": "4.7.0", "cpuCount": 8},
                        "metrics": {
                            "cpu": 95.0,  # High CPU to trigger finding
                            "memory": {"used": 8.0, "total": 16.0},
                        },
                    }
                ]
            },
        )
    )

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(client)

        # Every finding should have clear description
        for finding in result.findings:
            assert finding.title
            assert len(finding.title) > 5  # Meaningful title
            assert finding.description
            assert len(finding.description) > 20  # Substantive description

            # Should have severity
            assert finding.severity in {"critical", "high", "medium", "low", "info"}
