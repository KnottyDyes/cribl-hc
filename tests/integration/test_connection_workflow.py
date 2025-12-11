"""
Integration tests for connection testing workflow.
"""

import pytest
import httpx
import respx

from cribl_hc.cli.test_connection import run_connection_test


class TestConnectionWorkflow:
    """Integration tests for end-to-end connection testing."""

    @pytest.mark.integration
    @respx.mock
    def test_successful_connection_workflow(self):
        """Test complete successful connection workflow."""
        # Mock Cribl API version endpoint
        respx.get("https://test-cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(
                200,
                json={"version": "4.5.2", "build": "12345", "product": "Stream"},
            )
        )

        # Test connection programmatically (without CLI output)
        result = run_connection_test(
            url="https://test-cribl.example.com",
            token="test-token-12345",
            show_output=False,
        )

        assert result.success is True
        assert result.cribl_version == "4.5.2"
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0
        assert result.error is None
        assert "Successfully connected" in result.message

    @pytest.mark.integration
    @respx.mock
    def test_authentication_failure_workflow(self):
        """Test connection workflow with authentication failure."""
        respx.get("https://test-cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        result = run_connection_test(
            url="https://test-cribl.example.com",
            token="invalid-token",
            show_output=False,
        )

        assert result.success is False
        assert "Authentication failed" in result.message
        assert result.cribl_version is None
        assert result.error is not None

    @pytest.mark.integration
    @respx.mock
    def test_network_error_workflow(self):
        """Test connection workflow with network connectivity issues."""
        respx.get("https://unreachable.example.com/api/v1/version").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = run_connection_test(
            url="https://unreachable.example.com",
            token="test-token",
            show_output=False,
        )

        assert result.success is False
        assert "Cannot connect to Cribl API" in result.message
        assert result.error is not None

    @pytest.mark.integration
    @respx.mock
    def test_timeout_workflow(self):
        """Test connection workflow with timeout."""
        respx.get("https://slow-cribl.example.com/api/v1/version").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        result = run_connection_test(
            url="https://slow-cribl.example.com",
            token="test-token",
            timeout=5.0,
            show_output=False,
        )

        assert result.success is False
        assert "timeout" in result.message.lower()
        assert result.error is not None

    @pytest.mark.integration
    @respx.mock
    def test_invalid_url_workflow(self):
        """Test connection workflow with malformed URL."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        result = run_connection_test(
            url="https://cribl.example.com",
            token="test-token",
            show_output=False,
        )

        assert result.success is False
        assert "endpoint not found" in result.message.lower()

    @pytest.mark.integration
    @respx.mock
    def test_cloud_deployment_connection(self):
        """Test connection to Cribl Cloud deployment."""
        respx.get("https://myorg.cribl.cloud/api/v1/version").mock(
            return_value=httpx.Response(
                200,
                json={"version": "4.6.0", "build": "67890", "product": "Cloud"},
            )
        )

        result = run_connection_test(
            url="https://myorg.cribl.cloud",
            token="cloud-token",
            show_output=False,
        )

        assert result.success is True
        assert result.cribl_version == "4.6.0"
        assert "cribl.cloud" in result.api_url.lower()

    @pytest.mark.integration
    @respx.mock
    def test_self_hosted_deployment_connection(self):
        """Test connection to self-hosted Cribl deployment."""
        respx.get("https://cribl.internal.company.com/api/v1/version").mock(
            return_value=httpx.Response(
                200,
                json={"version": "4.4.5", "build": "11111"},
            )
        )

        result = run_connection_test(
            url="https://cribl.internal.company.com",
            token="internal-token",
            show_output=False,
        )

        assert result.success is True
        assert result.cribl_version == "4.4.5"

    @pytest.mark.integration
    @respx.mock
    def test_connection_with_trailing_slash(self):
        """Test that connection works with trailing slash in URL."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(200, json={"version": "4.5.2"})
        )

        result = run_connection_test(
            url="https://cribl.example.com/",  # Note trailing slash
            token="test-token",
            show_output=False,
        )

        assert result.success is True

    @pytest.mark.integration
    @respx.mock
    def test_connection_response_time_tracking(self):
        """Test that response time is accurately tracked."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(200, json={"version": "4.5.2"})
        )

        result = run_connection_test(
            url="https://cribl.example.com",
            token="test-token",
            show_output=False,
        )

        assert result.success is True
        assert result.response_time_ms is not None
        assert result.response_time_ms >= 0
        # Response should be reasonably fast (< 5 seconds)
        assert result.response_time_ms < 5000

    @pytest.mark.integration
    @respx.mock
    def test_multiple_connection_attempts(self):
        """Test making multiple connection attempts."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(200, json={"version": "4.5.2"})
        )

        # First attempt
        result1 = run_connection_test(
            url="https://cribl.example.com",
            token="test-token",
            show_output=False,
        )

        # Second attempt
        result2 = run_connection_test(
            url="https://cribl.example.com",
            token="test-token",
            show_output=False,
        )

        # Both should succeed independently
        assert result1.success is True
        assert result2.success is True
        assert result1.tested_at <= result2.tested_at
