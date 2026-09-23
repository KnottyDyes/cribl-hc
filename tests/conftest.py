"""
Pytest configuration and shared fixtures for Cribl Health Check tests.
"""

import asyncio
import os
from pathlib import Path

import pytest

# Set before importing anything that builds a rich Console. Rich colourises
# when it thinks a terminal is attached, which differs between a local run and
# CI, so assertions on help text passed locally and failed in CI with
# "--verbose" split by escape sequences. Consoles read this at construction,
# so a fixture would run too late.
os.environ.setdefault("NO_COLOR", "1")
os.environ.setdefault("TERM", "dumb")
# Typer renders help through rich and forces a terminal unless told otherwise.
os.environ.setdefault("_TYPER_FORCE_DISABLE_TERMINAL", "1")


@pytest.fixture(autouse=True, scope="session")
def isolate_credential_store(tmp_path_factory):
    """Keep every test out of the real credential store.

    The API tests create credentials through the live router, which writes to
    the configured store. Without this the suite appended to
    ~/.cribl-hc/credentials.enc on every run and never cleaned up - a real
    machine accumulated 1,617 stray entries that way. Redirecting the whole
    session means no test can reach the developer's own credentials, whether
    or not it remembers to patch anything.
    """
    import os

    from cribl_hc.core.credential_store import ENV_CONFIG_DIR

    store_dir = tmp_path_factory.mktemp("cribl-hc-config")
    previous = os.environ.get(ENV_CONFIG_DIR)
    os.environ[ENV_CONFIG_DIR] = str(store_dir)

    # config.py resolved its paths at import time, so repoint those too.
    from cribl_hc.cli.commands import config as config_module

    saved = (
        config_module.CONFIG_DIR,
        config_module.CREDENTIALS_FILE,
        config_module.KEY_FILE,
    )
    config_module.CONFIG_DIR = store_dir
    config_module.CREDENTIALS_FILE = store_dir / "credentials.enc"
    config_module.KEY_FILE = store_dir / ".key"

    yield store_dir

    (
        config_module.CONFIG_DIR,
        config_module.CREDENTIALS_FILE,
        config_module.KEY_FILE,
    ) = saved
    if previous is None:
        os.environ.pop(ENV_CONFIG_DIR, None)
    else:
        os.environ[ENV_CONFIG_DIR] = previous


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_deployment():
    """Create a sample Deployment model for testing."""
    from pydantic import HttpUrl, SecretStr

    from cribl_hc.models.deployment import Deployment

    return Deployment(
        id="test-deployment",
        name="Test Deployment",
        url=HttpUrl("https://cribl.example.com"),
        environment_type="self-hosted",
        auth_token=SecretStr("test-token-123"),
        cribl_version="4.5.2",
    )


@pytest.fixture
def mock_cribl_api(respx_mock):
    """Set up mock Cribl API responses."""

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
