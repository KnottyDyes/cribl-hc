"""
Integration tests for ConfigAnalyzer.

These tests verify the ConfigAnalyzer works correctly with realistic Cribl API
responses and produces meaningful findings and recommendations.
"""

import pytest
import httpx
import respx

from cribl_hc.analyzers.config import ConfigAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def mock_valid_config(respx_mock):
    """Mock Cribl API with valid configuration data."""
    base_url = "https://cribl.example.com"

    # Mock pipelines endpoint - valid configuration
    respx_mock.get(f"{base_url}/api/v1/master/pipelines").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "main",
                        "description": "Main processing pipeline",
                        "functions": [
                            {
                                "id": "eval-1",
                                "filter": "true",
                                "conf": {
                                    "add": [{"name": "processed", "value": "'true'"}]
                                },
                            }
                        ],
                    },
                    {
                        "id": "backup",
                        "description": "Backup pipeline",
                        "functions": [
                            {
                                "id": "regex_extract-1",
                                "filter": "sourcetype=='access'",
                                "conf": {"regex": r"(?<ip>\d+\.\d+\.\d+\.\d+)"},
                            }
                        ],
                    },
                ]
            },
        )
    )

    # Mock routes endpoint
    respx_mock.get(f"{base_url}/api/v1/master/routes").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "route-main",
                        "filter": "source=='production'",
                        "pipeline": "main",
                        "output": "default",
                    },
                    {
                        "id": "route-backup",
                        "filter": "source=='backup'",
                        "pipeline": "backup",
                        "output": "s3",
                    },
                ]
            },
        )
    )

    # Mock inputs endpoint
    respx_mock.get(f"{base_url}/api/v1/master/inputs").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "http-input-1",
                        "type": "http",
                        "conf": {"port": 8088},
                    }
                ]
            },
        )
    )

    # Mock outputs endpoint
    respx_mock.get(f"{base_url}/api/v1/master/outputs").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "default",
                        "type": "splunk",
                        "conf": {"host": "${env:SPLUNK_HOST}", "token": "${env:SPLUNK_TOKEN}"},
                    },
                    {
                        "id": "s3",
                        "type": "s3",
                        "conf": {"bucket": "my-bucket", "region": "us-east-1"},
                    },
                ]
            },
        )
    )

    return respx_mock


@pytest.fixture
def mock_config_with_syntax_errors(respx_mock):
    """Mock Cribl API with configuration containing syntax errors."""
    base_url = "https://cribl.example.com"

    # Pipeline with missing required fields
    respx_mock.get(f"{base_url}/api/v1/master/pipelines").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "broken-pipeline",
                        # Missing 'functions' field - syntax error
                    }
                ]
            },
        )
    )

    respx_mock.get(f"{base_url}/api/v1/master/routes").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    respx_mock.get(f"{base_url}/api/v1/master/inputs").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    respx_mock.get(f"{base_url}/api/v1/master/outputs").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    return respx_mock


@pytest.fixture
def mock_config_with_deprecated_functions(respx_mock):
    """Mock Cribl API with configuration using deprecated functions."""
    base_url = "https://cribl.example.com"

    respx_mock.get(f"{base_url}/api/v1/master/pipelines").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "legacy-pipeline",
                        "description": "Pipeline with deprecated functions",
                        "functions": [
                            {
                                "id": "regex",  # Deprecated function type
                                "filter": "true",
                                "conf": {"pattern": r"\d+"},
                            },
                            {
                                "id": "code",  # Deprecated function type
                                "filter": "true",
                                "conf": {"code": "event.field = 'value';"},
                            },
                        ],
                    }
                ]
            },
        )
    )

    respx_mock.get(f"{base_url}/api/v1/master/routes").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    respx_mock.get(f"{base_url}/api/v1/master/inputs").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    respx_mock.get(f"{base_url}/api/v1/master/outputs").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    return respx_mock


@pytest.fixture
def mock_config_with_security_issues(respx_mock):
    """Mock Cribl API with configuration containing security issues."""
    base_url = "https://cribl.example.com"

    respx_mock.get(f"{base_url}/api/v1/master/pipelines").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    respx_mock.get(f"{base_url}/api/v1/master/routes").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    respx_mock.get(f"{base_url}/api/v1/master/inputs").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    # Output with hardcoded credentials
    respx_mock.get(f"{base_url}/api/v1/master/outputs").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "insecure-splunk",
                        "type": "splunk",
                        "conf": {
                            "host": "splunk.example.com",
                            "password": "SuperSecret123!",  # Hardcoded credential
                            "token": "hardcoded-token-abc123",  # Hardcoded credential
                        },
                    }
                ]
            },
        )
    )

    return respx_mock


@pytest.fixture
def mock_config_with_unused_components(respx_mock):
    """Mock Cribl API with unused pipelines and outputs."""
    base_url = "https://cribl.example.com"

    # Multiple pipelines, some unused
    respx_mock.get(f"{base_url}/api/v1/master/pipelines").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "used-pipeline",
                        "functions": [{"id": "eval-1", "filter": "true"}],
                    },
                    {
                        "id": "orphaned-pipeline",
                        "functions": [{"id": "eval-2", "filter": "true"}],
                    },
                ]
            },
        )
    )

    # Route only references one pipeline
    respx_mock.get(f"{base_url}/api/v1/master/routes").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "route-1",
                        "filter": "true",
                        "pipeline": "used-pipeline",
                        "output": "default",
                    }
                ]
            },
        )
    )

    respx_mock.get(f"{base_url}/api/v1/master/inputs").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    # Multiple outputs, some unused
    respx_mock.get(f"{base_url}/api/v1/master/outputs").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "default",
                        "type": "splunk",
                        "conf": {"host": "splunk.example.com"},
                    },
                    {
                        "id": "unused-s3",
                        "type": "s3",
                        "conf": {"bucket": "unused-bucket"},
                    },
                ]
            },
        )
    )

    return respx_mock


class TestConfigAnalyzerIntegration:
    """Integration tests for ConfigAnalyzer."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_valid_configuration(self, mock_valid_config):
        """Test ConfigAnalyzer with a valid configuration."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            analyzer = ConfigAnalyzer()
            result = await analyzer.analyze(client)

        # Should succeed
        assert result.success is True
        assert result.objective == "config"

        # Should have no findings for valid config
        assert len(result.findings) == 0

        # Should have metadata
        assert "compliance_score" in result.metadata
        assert result.metadata["compliance_score"] == 100.0  # Perfect score
        assert result.metadata["pipelines_analyzed"] == 2
        assert result.metadata["routes_analyzed"] == 2

        # Should have no recommendations for perfect config
        assert len(result.recommendations) == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_syntax_errors(self, mock_config_with_syntax_errors):
        """Test ConfigAnalyzer detects syntax errors."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            analyzer = ConfigAnalyzer()
            result = await analyzer.analyze(client)

        # Should succeed but have findings
        assert result.success is True

        # Should detect syntax error
        assert len(result.findings) >= 1

        # Should have high severity finding for missing functions
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 1

        # Check finding details - look for missing 'functions' finding
        missing_functions_findings = [
            f for f in high_findings
            if "functions" in f.title.lower() and "broken-pipeline" in str(f.affected_components)
        ]
        assert len(missing_functions_findings) >= 1

        syntax_finding = missing_functions_findings[0]
        assert "missing" in syntax_finding.title.lower()
        assert "broken-pipeline" in syntax_finding.affected_components[0]

        # Compliance score should be reduced
        assert result.metadata["compliance_score"] < 100.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_deprecated_functions(self, mock_config_with_deprecated_functions):
        """Test ConfigAnalyzer detects deprecated functions."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            analyzer = ConfigAnalyzer()
            result = await analyzer.analyze(client)

        assert result.success is True

        # Should detect deprecated functions (will also detect unused pipeline since no routes)
        # Expecting: 2 deprecated function findings + 1 unused pipeline finding = 3 total
        assert len(result.findings) >= 2

        # Should have medium severity findings for deprecated functions
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 2

        # Check finding details - look for deprecated function findings
        deprecated_findings = [f for f in medium_findings if "deprecated" in f.title.lower()]
        assert len(deprecated_findings) >= 2  # regex and code

        # Should have migration guidance in remediation
        for finding in deprecated_findings:
            assert len(finding.remediation_steps) > 0
            assert any("replace" in step.lower() or "migrate" in step.lower() for step in finding.remediation_steps)

        # Should have recommendations for migration
        assert len(result.recommendations) >= 1
        # Look for deprecated function or migration recommendation
        migration_recs = [r for r in result.recommendations if "deprecated" in r.title.lower() or "migrate" in r.title.lower()]
        assert len(migration_recs) >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_security_issues(self, mock_config_with_security_issues):
        """Test ConfigAnalyzer detects security misconfigurations."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            analyzer = ConfigAnalyzer()
            result = await analyzer.analyze(client)

        assert result.success is True

        # Should detect hardcoded credentials
        assert len(result.findings) >= 2  # password and token

        # Should have high severity findings
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 2

        # Check finding details
        for finding in high_findings:
            assert "credential" in finding.title.lower() or "password" in finding.title.lower() or "token" in finding.title.lower()
            assert "insecure-splunk" in finding.affected_components[0]

            # Should have remediation steps
            assert len(finding.remediation_steps) > 0
            assert any("environment" in step.lower() or "env" in step.lower() for step in finding.remediation_steps)

        # Should have security recommendation with p0 priority
        assert len(result.recommendations) >= 1

        # Find the security recommendation specifically
        security_recs = [r for r in result.recommendations if r.type == "security"]
        assert len(security_recs) >= 1

        security_rec = security_recs[0]
        assert security_rec.priority == "p0"  # Should be p0 for hardcoded credentials
        assert "security" in security_rec.title.lower() or "credential" in security_rec.title.lower()

        # Compliance score should be significantly reduced
        assert result.metadata["compliance_score"] < 80.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_unused_components(self, mock_config_with_unused_components):
        """Test ConfigAnalyzer detects unused components."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            analyzer = ConfigAnalyzer()
            result = await analyzer.analyze(client)

        assert result.success is True

        # Should detect unused pipeline and output
        assert len(result.findings) >= 2

        # Should have low severity findings
        low_findings = [f for f in result.findings if f.severity == "low"]
        assert len(low_findings) >= 2

        # Check for unused pipeline
        unused_pipeline_findings = [
            f for f in low_findings if "orphaned-pipeline" in str(f.affected_components)
        ]
        assert len(unused_pipeline_findings) == 1

        # Check for unused output
        unused_output_findings = [
            f for f in low_findings if "unused-s3" in str(f.affected_components)
        ]
        assert len(unused_output_findings) == 1

        # Should have cleanup recommendation
        assert len(result.recommendations) >= 1
        cleanup_rec = result.recommendations[0]
        assert "unused" in cleanup_rec.title.lower() or "remove" in cleanup_rec.title.lower()
        assert cleanup_rec.type == "optimization"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_compliance_score_calculation(self, mock_config_with_security_issues):
        """Test compliance score calculation logic."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            analyzer = ConfigAnalyzer()
            result = await analyzer.analyze(client)

        # Get finding counts by severity
        critical_count = len([f for f in result.findings if f.severity == "critical"])
        high_count = len([f for f in result.findings if f.severity == "high"])
        medium_count = len([f for f in result.findings if f.severity == "medium"])
        low_count = len([f for f in result.findings if f.severity == "low"])

        # Calculate expected score
        expected_score = 100.0
        expected_score -= critical_count * 20
        expected_score -= high_count * 10
        expected_score -= medium_count * 5
        expected_score -= low_count * 2
        expected_score = max(0.0, expected_score)

        # Check calculated score matches
        actual_score = result.metadata["compliance_score"]
        assert actual_score == expected_score

        # Score should be between 0 and 100
        assert 0.0 <= actual_score <= 100.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test ConfigAnalyzer handles API errors gracefully."""
        with respx.mock:
            base_url = "https://cribl.example.com"

            # Mock all endpoints to return errors
            respx.get(f"{base_url}/api/v1/master/pipelines").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            respx.get(f"{base_url}/api/v1/master/routes").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            respx.get(f"{base_url}/api/v1/master/inputs").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            respx.get(f"{base_url}/api/v1/master/outputs").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )

            async with CriblAPIClient(
                base_url=base_url,
                auth_token="test-token",
            ) as client:
                analyzer = ConfigAnalyzer()
                result = await analyzer.analyze(client)

            # Should still succeed with graceful degradation
            assert result.success is True

            # Should have metadata showing 0 components analyzed
            assert result.metadata["pipelines_analyzed"] == 0
            assert result.metadata["routes_analyzed"] == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_analysis_workflow(self, mock_valid_config):
        """Test complete end-to-end ConfigAnalyzer workflow."""
        # Create analyzer
        analyzer = ConfigAnalyzer()

        # Verify analyzer metadata
        assert analyzer.objective_name == "config"
        assert analyzer.get_estimated_api_calls() == 5
        assert len(analyzer.get_required_permissions()) > 0

        # Initialize client and run analysis
        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            # Run analysis
            result = await analyzer.analyze(client)

            # Verify result structure
            assert result is not None
            assert hasattr(result, "objective")
            assert hasattr(result, "findings")
            assert hasattr(result, "recommendations")
            assert hasattr(result, "metadata")
            assert hasattr(result, "success")

            # Verify result content
            assert result.objective == "config"
            assert isinstance(result.findings, list)
            assert isinstance(result.recommendations, list)
            assert isinstance(result.metadata, dict)
            assert result.success is True

            # Verify all expected metadata fields present
            expected_keys = [
                "compliance_score",
                "pipelines_analyzed",
                "routes_analyzed",
                "inputs_analyzed",
                "outputs_analyzed",
            ]
            for key in expected_keys:
                assert key in result.metadata

            # Verify metadata values are reasonable
            assert 0.0 <= result.metadata["compliance_score"] <= 100.0
            assert result.metadata["pipelines_analyzed"] >= 0
            assert result.metadata["routes_analyzed"] >= 0
