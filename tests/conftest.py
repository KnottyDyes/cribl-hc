"""
Pytest configuration and shared fixtures for Cribl Health Check tests.
"""

import asyncio
import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_deployment():
    """Create a sample Deployment model for testing."""
    from cribl_hc.models.deployment import Deployment

    return Deployment(
        id="test-deployment",
        name="Test Deployment",
        url="https://cribl.example.com",
        environment_type="self-hosted",
        auth_token="test-token-123",
        cribl_version="4.5.2",
    )


@pytest.fixture
def mock_cribl_api(respx_mock):
    """Set up mock Cribl API responses."""
    import respx

    # Mock system status endpoint
    respx_mock.get("https://cribl.example.com/api/v1/system/status").mock(
        return_value={
            "version": "4.5.2",
            "health": "healthy",
            "uptime_seconds": 86400,
        }
    )

    # Mock workers endpoint
    respx_mock.get("https://cribl.example.com/api/v1/master/workers").mock(
        return_value={
            "items": [
                {
                    "id": "worker-01",
                    "info": {
                        "hostname": "worker-01.example.com",
                        "ipAddress": "10.0.1.10",
                        "version": "4.5.2",
                    },
                    "metrics": {
                        "cpu": 45.2,
                        "memory": {"used": 8.5, "total": 16.0},
                        "disk": {"used": 45.0, "total": 100.0},
                    },
                }
            ]
        }
    )

    return respx_mock


@pytest.fixture(scope="function", autouse=True)
def reset_analyzer_registry():
    """
    Reset the global analyzer registry after each test.

    Some tests mock or modify the registry, so we need to restore it
    to prevent contamination between tests.
    """
    # Store the original analyzers
    from cribl_hc.analyzers import get_global_registry
    registry = get_global_registry()
    original_analyzers = dict(registry._analyzers)

    yield

    # Restore the original analyzers
    registry._analyzers.clear()
    registry._analyzers.update(original_analyzers)


@pytest.fixture(scope="function", autouse=True)
def reset_event_loop():
    """
    Reset event loop after each test to prevent contamination.

    This fixture ensures that async tests don't leave event loops in a bad state
    that affects subsequent tests. It runs automatically for all tests.
    """
    yield

    # Clean up any existing event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
        if not loop.is_closed():
            loop.close()
    except RuntimeError:
        # No event loop exists, which is fine
        pass

    # Set a new event loop for the next test
    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
    except RuntimeError:
        # If we can't set a new loop, that's okay
        pass
