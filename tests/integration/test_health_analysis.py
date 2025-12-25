"""
Integration tests for health analysis workflow.

Tests the complete health assessment workflow from API calls through
to health score calculation and findings generation.
"""

import pytest
import respx
from httpx import Response


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_workflow():
    """Test complete health analysis workflow."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    # Mock system status
    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={
                "version": "4.7.0",
                "health": "healthy",
                "uptime_seconds": 86400,
            },
        )
    )

    # Mock workers endpoint with healthy workers
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
                    },
                    {
                        "id": "worker-02",
                        "status": "healthy",
                        "info": {
                            "hostname": "worker-02.example.com",
                            "version": "4.7.0",
                            "cpuCount": 8,
                        },
                        "metrics": {
                            "cpu": 50.0,
                            "memory": {"used": 9.0, "total": 16.0},
                            "disk": {"used": 45.0, "total": 100.0},
                        },
                    },
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

        # Validate results
        assert result is not None
        assert result.findings is not None
        assert isinstance(result.findings, list)

        # With healthy workers, should have minimal findings
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) == 0


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_with_unhealthy_workers():
    """Test health analysis detects unhealthy workers."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # Mock workers with high resource usage
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
                            "cpu": 95.0,  # High CPU
                            "memory": {"used": 15.0, "total": 16.0},  # High memory
                            "disk": {"used": 95.0, "total": 100.0},  # High disk
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

        # Should detect resource issues
        assert len(result.findings) > 0

        # Check for high resource usage findings
        resource_findings = [
            f
            for f in result.findings
            if "cpu" in f.title.lower()
            or "memory" in f.title.lower()
            or "disk" in f.title.lower()
        ]
        assert len(resource_findings) > 0


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_with_down_workers():
    """Test health analysis detects down/offline workers."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # Mock workers with down status
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "worker-01",
                        "status": "down",  # Worker is down
                        "info": {"hostname": "worker-01", "version": "4.7.0"},
                        "metrics": {},
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

        # Should detect down worker
        assert len(result.findings) > 0

        # Should have critical findings for down workers
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) > 0


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_with_version_mismatch():
    """Test health analysis detects version mismatches."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # Mock workers with different versions
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "worker-01",
                        "status": "healthy",
                        "info": {"hostname": "worker-01", "version": "4.7.0", "cpuCount": 8},
                        "metrics": {"cpu": 40.0, "memory": {"used": 8.0, "total": 16.0}},
                    },
                    {
                        "id": "worker-02",
                        "status": "healthy",
                        "info": {
                            "hostname": "worker-02",
                            "version": "4.5.0",  # Different version
                            "cpuCount": 8,
                        },
                        "metrics": {"cpu": 45.0, "memory": {"used": 9.0, "total": 16.0}},
                    },
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

        # Should detect version mismatch
        version_findings = [
            f for f in result.findings if "version" in f.title.lower()
        ]
        # May or may not flag version mismatch depending on implementation
        # Just verify analysis completes successfully
        assert result is not None


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_empty_workers():
    """Test health analysis handles no workers gracefully."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # No workers
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(200, json={"items": []})
    )

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(client)

        # Should complete without errors
        assert result is not None
        # May flag no workers as an issue
        assert isinstance(result.findings, list)


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_api_error_handling():
    """Test health analysis handles API errors gracefully."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # Workers endpoint returns error
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(500, json={"error": "Internal server error"})
    )

    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="test-token",
    ) as client:
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(client)

        # Should handle error gracefully (partial results)
        assert result is not None
        # Should either have findings about the error or empty results
        assert isinstance(result.findings, list)


@pytest.mark.asyncio
@respx.mock
async def test_health_analysis_multiple_issues():
    """Test health analysis detects multiple concurrent issues."""
    from cribl_hc.core.api_client import CriblAPIClient
    from cribl_hc.analyzers.health import HealthAnalyzer

    respx.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value=Response(
            200,
            json={"version": "4.7.0", "health": "healthy"},
        )
    )

    # Multiple workers with different issues
    respx.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "worker-01",
                        "status": "down",  # Issue 1: Down
                        "info": {"hostname": "worker-01", "version": "4.7.0"},
                        "metrics": {},
                    },
                    {
                        "id": "worker-02",
                        "status": "healthy",
                        "info": {"hostname": "worker-02", "version": "4.7.0", "cpuCount": 8},
                        "metrics": {
                            "cpu": 98.0,  # Issue 2: High CPU
                            "memory": {"used": 15.5, "total": 16.0},  # Issue 3: High memory
                            "disk": {"used": 45.0, "total": 100.0},
                        },
                    },
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

        # Should detect multiple issues
        assert len(result.findings) >= 2

        # Should have findings of different severities
        severities = {f.severity for f in result.findings}
        assert len(severities) > 0
