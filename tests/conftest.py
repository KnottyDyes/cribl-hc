"""
Pytest configuration and shared fixtures for Cribl Health Check tests.
"""

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
