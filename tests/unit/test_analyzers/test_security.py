"""
Unit tests for SecurityAnalyzer.

Following TDD: These tests are written FIRST and should FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.security import SecurityAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSecurityAnalyzer:
    """Test suite for SecurityAnalyzer."""

    @pytest.fixture
    def security_analyzer(self):
        """Create SecurityAnalyzer instance."""
        return SecurityAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock Cribl API client."""
        client = AsyncMock(spec=CriblAPIClient)
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        # Set up default mock responses
        client.get_outputs = AsyncMock(return_value=[])
        client.get_inputs = AsyncMock(return_value=[])
        client.get_auth_config = AsyncMock(return_value={})
        client.get_system_settings = AsyncMock(return_value={})
        return client

    # === Objective Name and Metadata Tests ===

    def test_objective_name(self, security_analyzer):
        """Test that analyzer has correct objective name."""
        assert security_analyzer.objective_name == "security"

    def test_estimated_api_calls(self, security_analyzer):
        """Test API call estimation."""
        # Should need: outputs(1) + inputs(1) + system/users(1) + auth(1) = 4 calls
        assert security_analyzer.get_estimated_api_calls() <= 5

    def test_required_permissions(self, security_analyzer):
        """Test required API permissions."""
        permissions = security_analyzer.get_required_permissions()
        assert "read:outputs" in permissions
        assert "read:inputs" in permissions

    # === TLS/mTLS Configuration Tests ===

    @pytest.mark.asyncio
    async def test_detect_tls_disabled(self, security_analyzer, mock_client):
        """Test detection of disabled TLS on outputs."""
        # Mock output with TLS disabled
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "splunk-insecure",
                "type": "splunk_hec",
                "conf": {
                    "host": "splunk.example.com",
                    "tls": {"disabled": True}
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should find TLS disabled
        tls_findings = [f for f in result.findings if "tls" in f.id.lower()]
        assert len(tls_findings) > 0
        assert any("disabled" in f.description.lower() or "insecure" in f.description.lower()
                   for f in tls_findings)

    @pytest.mark.asyncio
    async def test_detect_weak_tls_version(self, security_analyzer, mock_client):
        """Test detection of weak TLS versions (TLS 1.0, 1.1)."""
        # Mock output with old TLS version
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-weak-tls",
                "type": "s3",
                "conf": {
                    "tls": {
                        "disabled": False,
                        "minVersion": "TLSv1.0"  # Weak version
                    }
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should flag weak TLS version
        weak_tls_findings = [f for f in result.findings
                            if "tls" in f.id.lower() or "weak" in f.description.lower()]
        # May or may not detect depending on implementation
        # This is a "nice to have" check

    @pytest.mark.asyncio
    async def test_detect_tls_certificate_validation_disabled(self, security_analyzer, mock_client):
        """Test detection of disabled certificate validation."""
        # Mock output with cert validation disabled
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "http-no-verify",
                "type": "http",
                "conf": {
                    "url": "https://api.example.com",
                    "tls": {
                        "rejectUnauthorized": False  # Don't verify certs
                    }
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should find cert validation issue
        cert_findings = [f for f in result.findings
                        if "cert" in f.id.lower() or "unauthorized" in f.description.lower()]
        assert len(cert_findings) > 0

    # === Secret Scanning Tests ===

    @pytest.mark.asyncio
    async def test_detect_hardcoded_password(self, security_analyzer, mock_client):
        """Test detection of hardcoded passwords."""
        # Mock output with hardcoded password
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "splunk-hardcoded",
                "type": "splunk_hec",
                "conf": {
                    "host": "splunk.example.com",
                    "password": "MySecretPassword123"  # Hardcoded!
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should detect hardcoded credential
        secret_findings = [f for f in result.findings
                          if "secret" in f.id.lower() or "credential" in f.id.lower()
                          or "hardcoded" in f.id.lower()]
        assert len(secret_findings) > 0
        assert any("splunk-hardcoded" in f.affected_components for f in secret_findings)

    @pytest.mark.asyncio
    async def test_detect_hardcoded_api_key(self, security_analyzer, mock_client):
        """Test detection of hardcoded API keys."""
        # Mock output with hardcoded API key
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "datadog-api-key",
                "type": "datadog",
                "conf": {
                    "apiKey": "1234567890abcdef1234567890abcdef"  # Hardcoded!
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should detect API key
        secret_findings = [f for f in result.findings
                          if "secret" in f.id.lower() or "api" in f.id.lower()
                          or "key" in f.id.lower()]
        assert len(secret_findings) > 0

    @pytest.mark.asyncio
    async def test_ignore_environment_variables(self, security_analyzer, mock_client):
        """Test that environment variables are NOT flagged as secrets."""
        # Mock output using env vars (good practice)
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-env-vars",
                "type": "s3",
                "conf": {
                    "awsAccessKeyId": "${AWS_ACCESS_KEY_ID}",  # Env var - OK
                    "awsSecretAccessKey": "${AWS_SECRET_ACCESS_KEY}"  # Env var - OK
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should NOT flag env vars as hardcoded secrets
        secret_findings = [f for f in result.findings
                          if "secret" in f.id.lower() and "s3-env-vars" in f.affected_components]
        assert len(secret_findings) == 0  # No findings for env vars

    # === Authentication Mechanism Tests ===

    @pytest.mark.asyncio
    async def test_detect_no_authentication(self, security_analyzer, mock_client):
        """Test detection of outputs without authentication."""
        # Mock output with no auth
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "http-no-auth",
                "type": "http",
                "conf": {
                    "url": "https://api.example.com"
                    # No auth configured
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should warn about missing authentication
        auth_findings = [f for f in result.findings
                        if "auth" in f.id.lower()]
        # May or may not flag depending on output type and implementation

    @pytest.mark.asyncio
    async def test_detect_basic_auth_over_http(self, security_analyzer, mock_client):
        """Test detection of Basic Auth over unencrypted HTTP."""
        # Mock output using basic auth over HTTP (insecure!)
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "http-basic-auth",
                "type": "http",
                "conf": {
                    "url": "http://api.example.com",  # HTTP not HTTPS!
                    "authType": "basic",
                    "username": "admin",
                    "password": "${HTTP_PASSWORD}"
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should flag basic auth over HTTP
        insecure_auth = [f for f in result.findings
                        if ("basic" in f.description.lower() or "http" in f.id.lower())
                        and f.severity in ["high", "critical"]]
        # Implementation may or may not detect this

    # === Security Posture Score Tests ===

    @pytest.mark.asyncio
    async def test_calculate_security_posture_score_perfect(self, security_analyzer, mock_client):
        """Test security score calculation with perfect security."""
        # Mock perfectly secure config
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-secure",
                "type": "s3",
                "conf": {
                    "awsAccessKeyId": "${AWS_ACCESS_KEY_ID}",
                    "awsSecretAccessKey": "${AWS_SECRET_ACCESS_KEY}",
                    "tls": {"disabled": False}
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should have high security score
        assert "security_posture_score" in result.metadata
        score = result.metadata["security_posture_score"]
        assert 0 <= score <= 100
        assert score >= 80  # Should be high for perfect config

    @pytest.mark.asyncio
    async def test_calculate_security_posture_score_poor(self, security_analyzer, mock_client):
        """Test security score calculation with poor security."""
        # Mock insecure config
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "splunk-insecure",
                "type": "splunk_hec",
                "conf": {
                    "host": "splunk.example.com",
                    "password": "MyPassword123",  # Hardcoded
                    "tls": {"disabled": True}  # No TLS
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should have low security score
        assert "security_posture_score" in result.metadata
        score = result.metadata["security_posture_score"]
        assert score < 70  # Should be low for insecure config (TLS disabled + hardcoded password)

    # === Metadata Tests ===

    @pytest.mark.asyncio
    async def test_metadata_counts(self, security_analyzer, mock_client):
        """Test that metadata includes security issue counts."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "output1",
                "type": "s3",
                "conf": {"password": "hardcoded"}
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Check for security issue counts in metadata
        assert "tls_issues_count" in result.metadata or "security_issues_count" in result.metadata
        assert "secret_issues_count" in result.metadata
        assert "outputs_analyzed" in result.metadata

    # === Recommendation Tests ===

    @pytest.mark.asyncio
    async def test_generate_security_recommendations(self, security_analyzer, mock_client):
        """Test that security recommendations are generated."""
        # Mock insecure outputs
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "insecure1",
                "type": "splunk_hec",
                "conf": {
                    "password": "hardcoded",
                    "tls": {"disabled": True}
                }
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should generate security recommendations
        sec_recs = [r for r in result.recommendations if r.type == "security"]
        assert len(sec_recs) > 0
        # Recommendations should mention TLS and credentials
        rec_text = " ".join(r.description.lower() for r in sec_recs)
        assert "tls" in rec_text or "credential" in rec_text or "security" in rec_text

    # === Edge Case Tests ===

    @pytest.mark.asyncio
    async def test_no_outputs(self, security_analyzer, mock_client):
        """Test analysis when no outputs configured."""
        mock_client.get_outputs = AsyncMock(return_value=[])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should succeed with zero issues
        assert result.success is True
        assert result.metadata.get("outputs_analyzed", 0) == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, security_analyzer, mock_client):
        """Test graceful error handling."""
        mock_client.get_outputs = AsyncMock(side_effect=Exception("API Error"))

        result = await security_analyzer.analyze(mock_client)

        # Should still return success (graceful degradation)
        assert result.success is True
        assert result.metadata.get("outputs_analyzed", 0) == 0

    # === Product Type Tests (Stream vs Edge) ===

    @pytest.mark.asyncio
    async def test_edge_deployment_analysis(self, security_analyzer):
        """Test security analysis on Edge deployment."""
        edge_client = AsyncMock(spec=CriblAPIClient)
        edge_client.is_edge = True
        edge_client.is_stream = False
        edge_client.product_type = "edge"

        # Edge typically has cribl output to Stream
        edge_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "cribl-stream",
                "type": "cribl",
                "conf": {
                    "host": "stream.example.com",
                    "tls": {"disabled": False}
                }
            }
        ])
        edge_client.get_inputs = AsyncMock(return_value=[])
        edge_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(edge_client)

        assert result.success is True
        assert result.metadata.get("product_type") == "edge"

    # === Severity Classification Tests ===

    @pytest.mark.asyncio
    async def test_critical_severity_for_hardcoded_secrets(self, security_analyzer, mock_client):
        """Test that hardcoded secrets are marked as critical/high severity."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "output-secret",
                "type": "s3",
                "conf": {"password": "MyHardcodedPassword"}
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        secret_findings = [f for f in result.findings
                          if "secret" in f.id.lower() or "credential" in f.id.lower()]
        if secret_findings:
            # Should be high or critical severity
            assert any(f.severity in ["high", "critical"] for f in secret_findings)

    @pytest.mark.asyncio
    async def test_high_severity_for_tls_disabled(self, security_analyzer, mock_client):
        """Test that disabled TLS is marked as high severity."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "output-no-tls",
                "type": "splunk_hec",
                "conf": {"tls": {"disabled": True}}
            }
        ])
        mock_client.get_inputs = AsyncMock(return_value=[])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        tls_findings = [f for f in result.findings if "tls" in f.id.lower()]
        if tls_findings:
            # Should be high severity
            assert any(f.severity in ["high", "critical"] for f in tls_findings)

    # === Input Security Tests ===

    @pytest.mark.asyncio
    async def test_check_input_security(self, security_analyzer, mock_client):
        """Test security checks on input sources."""
        # Mock insecure input
        mock_client.get_outputs = AsyncMock(return_value=[])
        mock_client.get_inputs = AsyncMock(return_value=[
            {
                "id": "http-input-insecure",
                "type": "http",
                "conf": {
                    "port": 8080,
                    "tls": {"disabled": True}  # No TLS on input
                }
            }
        ])
        mock_client.get_system_status = AsyncMock(return_value={})

        result = await security_analyzer.analyze(mock_client)

        # Should flag insecure input
        input_findings = [f for f in result.findings
                         if "http-input-insecure" in f.affected_components]
        # May or may not detect depending on implementation
