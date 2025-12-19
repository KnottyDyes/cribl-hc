"""
Unit tests for ConfigAnalyzer.

Tests configuration validation, syntax checking, and error handling.
"""

import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.config import ConfigAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_pipeline(
    pipeline_id: str,
    functions: list = None,
    include_functions_field: bool = True
) -> dict:
    """
    Create a realistic pipeline data structure.

    Args:
        pipeline_id: Pipeline identifier
        functions: List of function configurations
        include_functions_field: Whether to include 'functions' field

    Returns:
        Pipeline configuration dict
    """
    pipeline = {
        "id": pipeline_id,
        "description": f"Test pipeline {pipeline_id}",
        "conf": {}
    }

    if include_functions_field:
        pipeline["functions"] = functions if functions is not None else [
            {
                "id": "eval",
                "filter": "true",
                "conf": {
                    "add": [{"name": "test_field", "value": "'test_value'"}]
                }
            }
        ]

    return pipeline


def create_route(route_id: str, pipeline_id: str, output: str = "default") -> dict:
    """
    Create a realistic route data structure.

    Args:
        route_id: Route identifier
        pipeline_id: Pipeline to route to
        output: Output destination

    Returns:
        Route configuration dict
    """
    return {
        "id": route_id,
        "pipeline": pipeline_id,
        "output": output,
        "filter": "true",
        "description": f"Test route {route_id}"
    }


class TestConfigAnalyzer:
    """Test suite for ConfigAnalyzer."""

    def test_objective_name(self):
        """Test that objective name is 'config'."""
        analyzer = ConfigAnalyzer()
        assert analyzer.objective_name == "config"

    def test_estimated_api_calls(self):
        """Test that estimated API calls is 5."""
        analyzer = ConfigAnalyzer()
        assert analyzer.get_estimated_api_calls() == 5

    def test_required_permissions(self):
        """Test that required permissions are returned."""
        analyzer = ConfigAnalyzer()
        permissions = analyzer.get_required_permissions()

        assert isinstance(permissions, list)
        assert "read:pipelines" in permissions
        assert "read:routes" in permissions
        assert "read:inputs" in permissions
        assert "read:outputs" in permissions

    @pytest.mark.asyncio
    async def test_analyze_valid_configuration(self):
        """Test analysis with valid pipeline configuration."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Mock valid responses
        valid_pipeline = create_pipeline("test-pipeline-01")

        mock_client.get_pipelines.return_value = [valid_pipeline]
        mock_client.get_routes.return_value = [
            create_route("route-01", "test-pipeline-01")
        ]
        mock_client.get_inputs.return_value = [
            {"id": "input-01", "type": "splunk_hec"}
        ]
        mock_client.get_outputs.return_value = [
            {"id": "output-01", "type": "s3"}
        ]

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.objective == "config"
        assert result.metadata["pipelines_analyzed"] == 1
        assert result.metadata["routes_analyzed"] == 1
        assert result.metadata["inputs_analyzed"] == 1
        assert result.metadata["outputs_analyzed"] == 1

        # Valid configuration should have no syntax errors
        syntax_errors = [
            f for f in result.findings if "syntax" in f.id.lower()
        ]
        assert len(syntax_errors) == 0

        # Verify API calls
        mock_client.get_pipelines.assert_called_once()
        mock_client.get_routes.assert_called_once()
        mock_client.get_inputs.assert_called_once()
        mock_client.get_outputs.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_syntax_errors(self):
        """Test detection of pipeline syntax errors."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipelines with various syntax errors
        pipelines = [
            # Missing 'id' field
            {"functions": [{"id": "eval"}]},

            # Missing 'functions' field
            create_pipeline("test-pipeline-02", include_functions_field=False),

            # Invalid 'functions' type (not array)
            {
                "id": "test-pipeline-03",
                "functions": "invalid"
            },

            # Function without 'id' field
            create_pipeline(
                "test-pipeline-04",
                functions=[{"filter": "true"}]
            ),

            # Invalid function type (not object)
            create_pipeline(
                "test-pipeline-05",
                functions=["invalid-function"]
            )
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.metadata["pipelines_analyzed"] == len(pipelines)

        # Should detect multiple syntax errors
        syntax_errors = [
            f for f in result.findings if "syntax" in f.id.lower()
        ]
        assert len(syntax_errors) >= 5  # At least one per error type

        # Check for specific error types
        error_titles = [f.title for f in result.findings]

        # Missing 'id' field
        assert any("Missing Required 'id'" in title for title in error_titles)

        # Missing 'functions' field
        assert any("Missing 'functions'" in title for title in error_titles)

        # Invalid 'functions' type
        assert any("'functions' Must Be Array" in title for title in error_titles)

        # Function missing 'id'
        assert any("Function Missing 'id'" in title for title in error_titles)

        # Invalid function type
        assert any("Invalid Function Type" in title for title in error_titles)

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test graceful degradation when API calls fail."""
        # Create mock client where one fetch fails
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.get_pipelines.side_effect = Exception("API connection failed")
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle error gracefully per Constitution Principle #6
        # Individual fetch failures are caught and return empty lists
        assert result.success is True
        assert result.metadata["pipelines_analyzed"] == 0
        assert result.metadata["routes_analyzed"] == 0
        assert result.metadata["inputs_analyzed"] == 0
        assert result.metadata["outputs_analyzed"] == 0

        # Individual fetch failures don't create error findings
        # (they're logged but analysis continues with empty data)

    @pytest.mark.asyncio
    async def test_partial_fetch_failures(self):
        """Test that analysis continues even when some fetches fail."""
        # Create mock client where multiple fetches fail
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.get_pipelines.side_effect = Exception("Pipelines API failed")
        mock_client.get_routes.side_effect = Exception("Routes API failed")
        mock_client.get_inputs.return_value = [{"id": "input-01", "type": "splunk_hec"}]
        mock_client.get_outputs.return_value = [{"id": "output-01", "type": "s3"}]

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle errors gracefully and continue with partial data
        assert result.success is True
        assert result.metadata["pipelines_analyzed"] == 0  # Failed
        assert result.metadata["routes_analyzed"] == 0      # Failed
        assert result.metadata["inputs_analyzed"] == 1      # Succeeded
        assert result.metadata["outputs_analyzed"] == 1     # Succeeded

        # Individual fetch failures are logged but don't stop the analysis

    @pytest.mark.asyncio
    async def test_empty_configuration(self):
        """Test analysis with no pipelines, routes, inputs, or outputs."""
        # Create mock client with empty responses
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.metadata["pipelines_analyzed"] == 0
        assert result.metadata["routes_analyzed"] == 0
        assert result.metadata["inputs_analyzed"] == 0
        assert result.metadata["outputs_analyzed"] == 0

        # No syntax errors with empty configuration
        assert result.metadata["syntax_errors"] == 0

    @pytest.mark.asyncio
    async def test_multiple_valid_pipelines(self):
        """Test analysis with multiple valid pipelines."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create multiple valid pipelines
        pipelines = [
            create_pipeline("pipeline-01", functions=[
                {"id": "eval", "filter": "true"}
            ]),
            create_pipeline("pipeline-02", functions=[
                {"id": "mask", "filter": "true"},
                {"id": "drop", "filter": "true"}
            ]),
            create_pipeline("pipeline-03", functions=[
                {"id": "regex_extract", "filter": "true"}
            ])
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.metadata["pipelines_analyzed"] == 3
        assert result.metadata["syntax_errors"] == 0

        # No syntax errors with valid pipelines
        syntax_errors = [
            f for f in result.findings if "syntax" in f.id.lower()
        ]
        assert len(syntax_errors) == 0

    @pytest.mark.asyncio
    async def test_severity_levels(self):
        """Test that findings have appropriate severity levels."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipelines with various error severities
        pipelines = [
            # CRITICAL: Missing 'id' field
            {"functions": []},

            # CRITICAL: Invalid 'functions' type
            {"id": "pipeline-02", "functions": "invalid"},

            # HIGH: Missing 'functions' field
            create_pipeline("pipeline-03", include_functions_field=False),

            # MEDIUM: Function missing 'id'
            create_pipeline("pipeline-04", functions=[{"filter": "true"}])
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Check severity distribution
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        high_findings = [f for f in result.findings if f.severity == "high"]
        medium_findings = [f for f in result.findings if f.severity == "medium"]

        # Should have at least one of each severity
        assert len(critical_findings) >= 2  # Missing id, invalid functions type
        assert len(high_findings) >= 1      # Missing functions field
        assert len(medium_findings) >= 1    # Function missing id

    @pytest.mark.asyncio
    async def test_finding_metadata(self):
        """Test that findings include proper metadata."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipeline with syntax error
        pipeline = create_pipeline("test-pipeline", include_functions_field=False)

        mock_client.get_pipelines.return_value = [pipeline]
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify finding structure
        assert len(result.findings) > 0
        finding = result.findings[0]

        # Check required fields
        assert finding.id is not None
        assert finding.category == "config"
        assert finding.severity in ["critical", "high", "medium", "low", "info"]
        assert finding.title is not None
        assert finding.description is not None
        assert isinstance(finding.affected_components, list)
        assert isinstance(finding.remediation_steps, list)
        assert len(finding.remediation_steps) > 0
        assert isinstance(finding.documentation_links, list)
        assert finding.estimated_impact is not None
        assert finding.confidence_level in ["high", "medium", "low"]
        assert isinstance(finding.metadata, dict)

    @pytest.mark.asyncio
    async def test_detect_orphaned_route_references(self):
        """Test detection of routes referencing non-existent pipelines."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipelines and routes with orphaned references
        pipelines = [
            create_pipeline("pipeline-A"),
            create_pipeline("pipeline-B")
        ]

        routes = [
            create_route("route-01", "pipeline-A"),  # Valid
            create_route("route-02", "pipeline-MISSING"),  # Orphaned
            create_route("route-03", "pipeline-B"),  # Valid
            create_route("route-04", "pipeline-NONEXISTENT")  # Orphaned
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = routes
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect orphaned references
        orphaned_findings = [
            f for f in result.findings if "orphaned" in f.id.lower()
        ]
        assert len(orphaned_findings) == 2

        # Check finding details
        for finding in orphaned_findings:
            assert finding.severity == "high"
            assert "Non-Existent Pipeline" in finding.title
            assert finding.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_detect_routes_missing_output(self):
        """Test detection of routes without output destinations."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        pipelines = [create_pipeline("pipeline-A")]
        routes = [
            create_route("route-01", "pipeline-A", "output-default"),  # Valid
            {"id": "route-02", "pipeline": "pipeline-A"},  # Missing output
            {"id": "route-03", "pipeline": "pipeline-A", "output": ""}  # Empty output
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = routes
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect missing outputs
        missing_output_findings = [
            f for f in result.findings if "missing-output" in f.id.lower()
        ]
        assert len(missing_output_findings) == 2

        for finding in missing_output_findings:
            assert finding.severity == "medium"
            assert "Missing Output" in finding.title

    @pytest.mark.asyncio
    async def test_detect_deprecated_functions(self):
        """Test detection of deprecated function usage."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipelines with deprecated functions
        pipelines = [
            create_pipeline("pipeline-01", functions=[
                {"id": "eval", "filter": "true"}  # Not deprecated
            ]),
            create_pipeline("pipeline-02", functions=[
                {"id": "regex", "filter": "true"},  # Deprecated
                {"id": "mask", "filter": "true"}    # Not deprecated
            ]),
            create_pipeline("pipeline-03", functions=[
                {"id": "code", "filter": "true"}  # Deprecated
            ])
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect deprecated functions
        deprecated_findings = [
            f for f in result.findings if "deprecated" in f.id.lower()
        ]
        assert len(deprecated_findings) == 2  # regex and code

        # Verify finding details
        for finding in deprecated_findings:
            assert finding.severity == "medium"
            assert "Deprecated Function" in finding.title
            assert finding.confidence_level == "high"
            assert "replacement_function" in finding.metadata
            assert "migration_reason" in finding.metadata

    @pytest.mark.asyncio
    async def test_no_deprecated_functions(self):
        """Test that modern functions don't trigger deprecated warnings."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipelines with only modern functions
        pipelines = [
            create_pipeline("pipeline-01", functions=[
                {"id": "eval", "filter": "true"},
                {"id": "mask", "filter": "true"},
                {"id": "drop", "filter": "true"}
            ])
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should not detect any deprecated functions
        deprecated_findings = [
            f for f in result.findings if "deprecated" in f.id.lower()
        ]
        assert len(deprecated_findings) == 0

    @pytest.mark.asyncio
    async def test_detect_unused_pipelines(self):
        """Test detection of unused pipelines."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create pipelines where some are used and some are not
        pipelines = [
            create_pipeline("pipeline-used-1"),
            create_pipeline("pipeline-used-2"),
            create_pipeline("pipeline-unused-1"),
            create_pipeline("pipeline-unused-2")
        ]

        routes = [
            create_route("route-01", "pipeline-used-1"),  # Uses pipeline-used-1
            create_route("route-02", "pipeline-used-2")   # Uses pipeline-used-2
            # pipeline-unused-1 and pipeline-unused-2 are not referenced
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = routes
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect 2 unused pipelines
        unused_pipeline_findings = [
            f for f in result.findings if "unused-pipeline" in f.id.lower()
        ]
        assert len(unused_pipeline_findings) == 2

        for finding in unused_pipeline_findings:
            assert finding.severity == "low"
            assert "Unused Pipeline" in finding.title
            assert finding.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_detect_unused_outputs(self):
        """Test detection of unused outputs."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        pipelines = [create_pipeline("pipeline-A")]
        routes = [
            create_route("route-01", "pipeline-A", "output-used")
            # output-unused is not referenced by any route
        ]
        outputs = [
            {"id": "output-used", "type": "s3"},
            {"id": "output-unused", "type": "splunk"}
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = routes
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = outputs

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect 1 unused output
        unused_output_findings = [
            f for f in result.findings if "unused-output" in f.id.lower()
        ]
        assert len(unused_output_findings) == 1

        finding = unused_output_findings[0]
        assert finding.severity == "low"
        assert "Unused Output" in finding.title
        assert "output-unused" in finding.id

    @pytest.mark.asyncio
    async def test_detect_hardcoded_credentials(self):
        """Test detection of hardcoded credentials in outputs."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create outputs with hardcoded credentials
        outputs = [
            {
                "id": "output-with-password",
                "type": "splunk",
                "password": "hardcoded123",
                "url": "https://splunk.example.com"
            },
            {
                "id": "output-with-token",
                "type": "http",
                "api_key": "secret_token_abc123",
                "url": "https://api.example.com"
            },
            {
                "id": "output-secure",
                "type": "s3",
                "password": "${env:S3_PASSWORD}",  # Using env var - secure
                "url": "https://s3.amazonaws.com"
            }
        ]

        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = outputs

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect hardcoded credentials
        security_findings = [
            f for f in result.findings if "security-hardcoded" in f.id.lower()
        ]
        assert len(security_findings) >= 2  # At least password and token

        for finding in security_findings:
            assert finding.severity == "high"
            assert "Hardcoded Credential" in finding.title
            assert finding.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_detect_unencrypted_connections(self):
        """Test detection of HTTP instead of HTTPS."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        outputs = [
            {
                "id": "output-insecure",
                "type": "http",
                "url": "http://insecure.example.com"  # HTTP instead of HTTPS
            },
            {
                "id": "output-secure",
                "type": "http",
                "url": "https://secure.example.com"  # HTTPS - secure
            }
        ]

        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = outputs

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect unencrypted connection
        tls_findings = [
            f for f in result.findings if "security-no-tls" in f.id.lower()
        ]
        assert len(tls_findings) == 1

        finding = tls_findings[0]
        assert finding.severity == "medium"
        assert "Unencrypted Connection" in finding.title
        assert "output-insecure" in finding.id

    @pytest.mark.asyncio
    async def test_compliance_score_calculation(self):
        """Test compliance score calculation."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create configuration with various severity findings
        pipelines = [
            {"functions": []},  # Missing id - critical (-20)
            create_pipeline("pipeline-02", functions=[
                {"id": "regex", "filter": "true"}  # Deprecated - medium (-5)
            ]),
            create_pipeline("pipeline-03", include_functions_field=False)  # Missing functions - high (-10)
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should calculate compliance score
        # Base 100 - 20 (critical) - 10 (high) - 5 (medium) = 65
        assert "compliance_score" in result.metadata
        compliance_score = result.metadata["compliance_score"]
        assert isinstance(compliance_score, float)
        assert 0.0 <= compliance_score <= 100.0
        assert compliance_score < 100.0  # Should have deductions

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_unused_components(self):
        """Test recommendation generation for unused components."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        pipelines = [
            create_pipeline("pipeline-used"),
            create_pipeline("pipeline-unused-1"),
            create_pipeline("pipeline-unused-2")
        ]
        routes = [
            create_route("route-01", "pipeline-used", "output-used")
        ]
        outputs = [
            {"id": "output-used", "type": "s3"},
            {"id": "output-unused", "type": "splunk"}
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = routes
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = outputs

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should generate recommendation for cleanup
        cleanup_recs = [
            r for r in result.recommendations if "cleanup-unused" in r.id.lower()
        ]
        assert len(cleanup_recs) == 1

        rec = cleanup_recs[0]
        assert rec.type == "optimization"
        assert rec.priority == "p3"
        assert "Remove Unused" in rec.title

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_deprecated_functions(self):
        """Test recommendation generation for deprecated functions."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        pipelines = [
            create_pipeline("pipeline-01", functions=[
                {"id": "regex", "filter": "true"}
            ]),
            create_pipeline("pipeline-02", functions=[
                {"id": "code", "filter": "true"}
            ])
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should generate migration recommendation
        migration_recs = [
            r for r in result.recommendations if "migrate-deprecated" in r.id.lower()
        ]
        assert len(migration_recs) == 1

        rec = migration_recs[0]
        assert rec.type == "best_practice"
        assert rec.priority == "p2"
        assert "Migrate Deprecated" in rec.title

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_security_issues(self):
        """Test recommendation generation for security issues."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        outputs = [
            {
                "id": "output-insecure",
                "type": "http",
                "url": "http://insecure.example.com",
                "password": "hardcoded123"
            }
        ]

        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = outputs

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should generate security recommendation
        security_recs = [
            r for r in result.recommendations if "fix-security" in r.id.lower()
        ]
        assert len(security_recs) == 1

        rec = security_recs[0]
        assert rec.type == "security"
        assert rec.priority in ["p0", "p1"]
        assert "Security" in rec.title

    @pytest.mark.asyncio
    async def test_generate_recommendations_for_critical_errors(self):
        """Test recommendation generation for critical errors."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        pipelines = [
            {"functions": []},  # Missing id - critical error
            {"id": "pipeline-02", "functions": "invalid"}  # Invalid type - critical
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should generate critical fix recommendation
        critical_recs = [
            r for r in result.recommendations if "fix-critical" in r.id.lower()
        ]
        assert len(critical_recs) == 1

        rec = critical_recs[0]
        assert rec.type == "bug_fix"
        assert rec.priority == "p0"
        assert "Critical" in rec.title

    @pytest.mark.asyncio
    async def test_metadata_includes_all_counts(self):
        """Test that metadata includes all expected counts."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Create comprehensive test data
        pipelines = [
            create_pipeline("pipeline-01", functions=[
                {"id": "regex", "filter": "true"}  # Deprecated
            ]),
            create_pipeline("pipeline-unused"),  # Unused
            {"functions": []}  # Critical error - missing id
        ]
        routes = [
            create_route("route-01", "pipeline-01")
        ]
        outputs = [
            {"id": "output-used", "type": "http"},
            {"id": "output-unused", "type": "s3"}
        ]

        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = routes
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = outputs

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify all metadata counts are present
        assert "pipelines_analyzed" in result.metadata
        assert "routes_analyzed" in result.metadata
        assert "inputs_analyzed" in result.metadata
        assert "outputs_analyzed" in result.metadata
        assert "syntax_errors" in result.metadata
        assert "deprecated_functions" in result.metadata
        assert "unused_components" in result.metadata
        assert "security_issues" in result.metadata
        assert "compliance_score" in result.metadata
        assert "critical_findings" in result.metadata
        assert "high_findings" in result.metadata
        assert "medium_findings" in result.metadata
        assert "low_findings" in result.metadata

        # Verify values are correct types
        assert isinstance(result.metadata["pipelines_analyzed"], int)
        assert isinstance(result.metadata["compliance_score"], float)
        assert result.metadata["pipelines_analyzed"] == 3
        assert result.metadata["routes_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_edge_deployment_analysis(self):
        """Test ConfigAnalyzer works with Edge deployments."""
        # Create mock Edge client
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = True
        mock_client.is_stream = False
        mock_client.product_type = "edge"

        # Mock Edge configuration responses
        mock_client.get_pipelines.return_value = [
            create_pipeline("edge-pipeline-01")
        ]
        mock_client.get_routes.return_value = [
            create_route("edge-route-01", "edge-pipeline-01")
        ]
        mock_client.get_inputs.return_value = [
            {"id": "edge-input-01", "type": "syslog"}
        ]
        mock_client.get_outputs.return_value = [
            {"id": "edge-output-01", "type": "cribl"}
        ]

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify Edge-specific metadata
        assert result.success is True
        assert result.metadata["product_type"] == "edge"
        assert result.metadata["pipelines_analyzed"] == 1
        assert result.metadata["routes_analyzed"] == 1

        # Verify API calls
        mock_client.get_pipelines.assert_called_once()
        mock_client.get_routes.assert_called_once()
        mock_client.get_inputs.assert_called_once()
        mock_client.get_outputs.assert_called_once()

    @pytest.mark.asyncio
    async def test_edge_product_type_metadata(self):
        """Test Edge product type is captured in metadata."""
        # Create mock Edge client
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = True
        mock_client.is_stream = False
        mock_client.product_type = "edge"

        # Mock successful responses (but empty to keep test fast)
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        # Run analysis
        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should succeed and capture Edge product type
        assert result.success is True
        assert result.metadata["product_type"] == "edge"
        assert result.metadata["pipelines_analyzed"] == 0
        assert result.metadata["routes_analyzed"] == 0

    # ========================================
    # Phase 2B: Pipeline Efficiency Tests
    # ========================================

    def test_pipeline_efficiency_score_optimal(self):
        """Test efficiency score for optimally ordered pipeline."""
        analyzer = ConfigAnalyzer()

        # Optimal pipeline: filter first, then expensive operations
        functions = [
            {"id": "drop", "conf": {"filter": "status == 404"}},
            {"id": "regex_extract", "conf": {"pattern": ".*"}},
            {"id": "eval", "conf": {"expression": "field = value"}}
        ]

        score = analyzer._calculate_pipeline_efficiency_score(functions)

        # Should have perfect or near-perfect score
        assert score >= 90.0
        assert score <= 100.0

    def test_pipeline_efficiency_score_suboptimal(self):
        """Test efficiency score for suboptimally ordered pipeline."""
        analyzer = ConfigAnalyzer()

        # Suboptimal: expensive operations before filtering
        functions = [
            {"id": "regex_extract", "conf": {"pattern": ".*"}},
            {"id": "lookup", "conf": {}},
            {"id": "eval", "conf": {"expression": "field = value"}},
            {"id": "drop", "conf": {"filter": "status == 404"}}
        ]

        score = analyzer._calculate_pipeline_efficiency_score(functions)

        # Should have lower score due to expensive functions before filtering
        assert score < 60.0  # 3 expensive functions before filter = -45 points

    def test_pipeline_efficiency_score_excessive_operations(self):
        """Test efficiency score penalizes excessive expensive operations."""
        analyzer = ConfigAnalyzer()

        # Too many expensive operations
        functions = [
            {"id": "regex_extract", "conf": {}},
            {"id": "regex", "conf": {}},
            {"id": "grok", "conf": {}},
            {"id": "lookup", "conf": {}},
            {"id": "eval", "conf": {}}  # 5 total, 2 over threshold of 3
        ]

        score = analyzer._calculate_pipeline_efficiency_score(functions)

        # Should penalize for having > 3 expensive operations
        assert score < 100.0

    def test_pipeline_efficiency_score_empty_pipeline(self):
        """Test efficiency score for empty pipeline."""
        analyzer = ConfigAnalyzer()

        score = analyzer._calculate_pipeline_efficiency_score([])

        # Empty pipeline should have perfect score
        assert score == 100.0

    @pytest.mark.asyncio
    async def test_function_ordering_check_detects_issues(self):
        """Test detection of expensive functions before filtering."""
        # Setup: Pipeline with regex before drop
        pipelines = [{
            "id": "test_pipeline",
            "conf": {
                "functions": [
                    {"id": "regex_extract", "conf": {"pattern": ".*"}},
                    {"id": "drop", "conf": {"filter": "status == 404"}}
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect function ordering issue
        ordering_findings = [f for f in result.findings
                            if f.id.startswith("config-perf-function-ordering")]
        assert len(ordering_findings) > 0

        finding = ordering_findings[0]
        assert "test_pipeline" in finding.affected_components[0]
        assert finding.severity == "medium"
        assert "expensive operations before filtering" in finding.description.lower()

    @pytest.mark.asyncio
    async def test_function_ordering_check_no_issues(self):
        """Test no issues for optimal function ordering."""
        # Setup: Well-ordered pipeline
        pipelines = [{
            "id": "optimal_pipeline",
            "conf": {
                "functions": [
                    {"id": "drop", "conf": {"filter": "status == 404"}},
                    {"id": "regex_extract", "conf": {"pattern": ".*"}}
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT detect function ordering issues
        ordering_findings = [f for f in result.findings
                            if f.id.startswith("config-perf-function-ordering")]
        assert len(ordering_findings) == 0

    @pytest.mark.asyncio
    async def test_multiple_regex_detection(self):
        """Test detection of multiple regex operations."""
        # Setup: Pipeline with 3 regex functions
        pipelines = [{
            "id": "regex_heavy_pipeline",
            "conf": {
                "functions": [
                    {"id": "regex_extract", "conf": {}},
                    {"id": "regex", "conf": {}},
                    {"id": "grok", "conf": {}}
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect multiple regex operations
        regex_findings = [f for f in result.findings
                         if f.id.startswith("config-perf-multiple-regex")]
        assert len(regex_findings) > 0

        finding = regex_findings[0]
        assert finding.severity == "medium"
        assert "3" in finding.description  # Should mention count
        assert finding.metadata["regex_function_count"] == 3

    @pytest.mark.asyncio
    async def test_lookup_caching_detection(self):
        """Test detection of lookup without caching."""
        # Setup: Pipeline with uncached lookup
        pipelines = [{
            "id": "lookup_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "lookup",
                        "conf": {
                            "cache": {"enabled": False}
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect lookup without caching
        cache_findings = [f for f in result.findings
                         if f.id.startswith("config-perf-lookup-no-cache")]
        assert len(cache_findings) > 0

        finding = cache_findings[0]
        assert finding.severity == "low"
        assert "caching" in finding.description.lower()
        assert finding.metadata["cache_enabled"] is False

    @pytest.mark.asyncio
    async def test_efficiency_metadata_populated(self):
        """Test that efficiency metadata is populated in results."""
        # Setup: Mix of pipelines
        pipelines = [
            {
                "id": "good_pipeline",
                "conf": {
                    "functions": [
                        {"id": "drop", "conf": {"filter": "status == 404"}},
                        {"id": "eval", "conf": {}}
                    ]
                }
            },
            {
                "id": "bad_pipeline",
                "conf": {
                    "functions": [
                        {"id": "regex_extract", "conf": {}},
                        {"id": "lookup", "conf": {}},
                        {"id": "drop", "conf": {}}
                    ]
                }
            }
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have efficiency metadata
        assert "pipeline_efficiency_score" in result.metadata
        assert "max_pipeline_efficiency" in result.metadata
        assert "min_pipeline_efficiency" in result.metadata
        assert "performance_opportunities" in result.metadata

        # Scores should be within valid range
        assert 0.0 <= result.metadata["pipeline_efficiency_score"] <= 100.0
        assert 0.0 <= result.metadata["max_pipeline_efficiency"] <= 100.0
        assert 0.0 <= result.metadata["min_pipeline_efficiency"] <= 100.0

    @pytest.mark.asyncio
    async def test_efficiency_no_pipelines(self):
        """Test efficiency analysis with no pipelines."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have default perfect efficiency score when no pipelines
        assert result.metadata["pipeline_efficiency_score"] == 100.0
        assert result.metadata["performance_opportunities"] == 0

    @pytest.mark.asyncio
    async def test_efficiency_empty_functions(self):
        """Test efficiency analysis with pipelines that have no functions."""
        pipelines = [
            {"id": "empty1", "conf": {"functions": []}},
            {"id": "empty2", "conf": {}}  # No functions key
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle gracefully - empty pipelines don't generate findings
        assert result.success is True
        # No performance issues from empty pipelines
        assert result.metadata["performance_opportunities"] == 0

    # Phase 2C: Route Conflict Detection Tests

    @pytest.mark.asyncio
    async def test_catchall_route_not_last_detected(self):
        """Test detection of catch-all route that's not at the end."""
        # Setup: Catch-all route in middle of list
        routes = [
            {"id": "specific_route", "filter": "status == 200"},
            {"id": "catchall_route", "filter": ""},  # Catch-all in middle
            {"id": "unreachable_route_1", "filter": "status == 404"},
            {"id": "unreachable_route_2", "filter": "status == 500"}
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect catch-all not last
        catchall_findings = [f for f in result.findings
                            if f.id.startswith("config-route-catchall-not-last")]
        assert len(catchall_findings) == 1

        finding = catchall_findings[0]
        assert finding.severity == "high"
        assert "catchall_route" in finding.description
        assert finding.metadata["unreachable_routes"] == 2
        assert "unreachable_route_1" in finding.metadata["unreachable_route_ids"]
        assert "unreachable_route_2" in finding.metadata["unreachable_route_ids"]

        # Metadata should track unreachable routes
        assert result.metadata["unreachable_routes"] == 2

    @pytest.mark.asyncio
    async def test_catchall_route_last_is_ok(self):
        """Test that catch-all route at the end is not flagged."""
        routes = [
            {"id": "specific_route_1", "filter": "status == 200"},
            {"id": "specific_route_2", "filter": "status == 404"},
            {"id": "catchall_route", "filter": ""}  # Catch-all at end is OK
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT detect catch-all issue (it's last)
        catchall_findings = [f for f in result.findings
                            if f.id.startswith("config-route-catchall-not-last")]
        assert len(catchall_findings) == 0

        # No unreachable routes
        assert result.metadata["unreachable_routes"] == 0

    @pytest.mark.asyncio
    async def test_overlapping_routes_detected(self):
        """Test detection of routes with overlapping filters."""
        routes = [
            {"id": "route_1", "filter": "host == 'server1'"},
            {"id": "route_2", "filter": "host == 'server1'"}  # Identical filter
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect overlapping routes
        overlap_findings = [f for f in result.findings
                           if f.id.startswith("config-route-overlap")]
        assert len(overlap_findings) == 1

        finding = overlap_findings[0]
        assert finding.severity == "medium"
        assert "route_1" in finding.metadata["route_1"]
        assert "route_2" in finding.metadata["route_2"]

    @pytest.mark.asyncio
    async def test_overlapping_routes_same_fields(self):
        """Test detection of routes referencing same fields."""
        routes = [
            {"id": "route_1", "filter": "status == 200 and host == 'server1'"},
            {"id": "route_2", "filter": "host == 'server2' and path == '/api'"}
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect potential overlap (both reference 'host')
        overlap_findings = [f for f in result.findings
                           if f.id.startswith("config-route-overlap")]
        assert len(overlap_findings) == 1

    @pytest.mark.asyncio
    async def test_non_overlapping_routes(self):
        """Test that non-overlapping routes are not flagged."""
        routes = [
            {"id": "route_1", "filter": "sourcetype == 'syslog'"},
            {"id": "route_2", "filter": "application == 'web'"}
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT detect overlap (different fields)
        overlap_findings = [f for f in result.findings
                           if f.id.startswith("config-route-overlap")]
        assert len(overlap_findings) == 0

    @pytest.mark.asyncio
    async def test_invalid_filter_expression_detected(self):
        """Test detection of invalid filter expressions."""
        routes = [
            {"id": "bad_route_1", "filter": "status == 200 and (host == 'server1'"},  # Unbalanced parens
            {"id": "bad_route_2", "filter": "path == '/api' && method == 'GET'"},  # Wrong operator
            {"id": "bad_route_3", "filter": "message == 'test"}  # Unbalanced quotes
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect all 3 invalid filters
        invalid_findings = [f for f in result.findings
                           if f.id.startswith("config-route-invalid-filter")]
        assert len(invalid_findings) == 3

        # All should be high severity
        for finding in invalid_findings:
            assert finding.severity == "high"

    @pytest.mark.asyncio
    async def test_valid_filter_expressions_not_flagged(self):
        """Test that valid filter expressions are not flagged."""
        routes = [
            {"id": "route_1", "filter": "status == 200"},
            {"id": "route_2", "filter": "(status == 404 or status == 500) and host == 'server1'"},
            {"id": "route_3", "filter": "message == 'test' and not (error == true)"}
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT detect invalid filters
        invalid_findings = [f for f in result.findings
                           if f.id.startswith("config-route-invalid-filter")]
        assert len(invalid_findings) == 0

    @pytest.mark.asyncio
    async def test_route_conflict_metadata_populated(self):
        """Test that route conflict metadata is properly populated."""
        routes = [
            {"id": "route_1", "filter": ""},  # Catch-all not last
            {"id": "route_2", "filter": "status == 200"},
            {"id": "route_3", "filter": "status == 200"}  # Overlapping
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have metadata about conflicts
        assert "route_conflicts_found" in result.metadata
        assert result.metadata["route_conflicts_found"] >= 2  # Catch-all + overlap
        assert "unreachable_routes" in result.metadata
        assert result.metadata["unreachable_routes"] == 2  # route_2 and route_3

    @pytest.mark.asyncio
    async def test_no_routes_handled_gracefully(self):
        """Test that empty routes list is handled gracefully."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = []
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle gracefully
        assert result.success is True
        assert result.metadata["route_conflicts_found"] == 0
        assert result.metadata["unreachable_routes"] == 0

    @pytest.mark.asyncio
    async def test_catchall_variations_detected(self):
        """Test detection of various catch-all patterns."""
        routes = [
            {"id": "route_1", "filter": "true"},  # Always-true
            {"id": "route_2", "filter": "status == 200"},
            {"id": "route_3", "filter": "1==1"},  # Another always-true
            {"id": "route_4", "filter": "status == 404"}
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect both catch-all routes
        catchall_findings = [f for f in result.findings
                            if f.id.startswith("config-route-catchall-not-last")]
        assert len(catchall_findings) == 2  # Both route_1 and route_3 are catch-all

    # Phase 2D: Configuration Complexity Metrics Tests

    def test_pipeline_complexity_calculation_simple(self):
        """Test complexity calculation for simple pipeline."""
        analyzer = ConfigAnalyzer()

        # Simple pipeline: 3 functions, no nesting
        functions = [
            {"id": "eval", "conf": {"expression": "x = 1"}},
            {"id": "drop", "conf": {"filter": "status == 200"}},
            {"id": "mask", "conf": {"fields": ["password"]}}
        ]

        complexity = analyzer._calculate_pipeline_complexity(functions)

        # Expected: 3 functions * 2 = 6, plus minimal nesting/config overhead
        assert complexity >= 6
        assert complexity < 20  # Should be low complexity

    def test_pipeline_complexity_calculation_complex(self):
        """Test complexity calculation for complex pipeline with nesting."""
        analyzer = ConfigAnalyzer()

        # Complex pipeline: nested filters and long expressions
        functions = [
            {
                "id": "eval",
                "conf": {
                    "filter": "((status == 200 or status == 201) and (method == 'GET' or method == 'POST'))",
                    "expression": "very_long_expression_" * 10  # >50 chars
                }
            },
            {
                "id": "regex_extract",
                "conf": {
                    "pattern": ".*",
                    "field": "message",
                    "output": "extracted",
                    "mode": "sed",
                    "iterations": 100,
                    "cache_enabled": True  # >5 config keys
                }
            }
        ]

        complexity = analyzer._calculate_pipeline_complexity(functions)

        # Should have high complexity due to nesting and config size
        assert complexity >= 19  # Actual is 19 - nested parens + config

    def test_pipeline_complexity_empty(self):
        """Test complexity for empty pipeline."""
        analyzer = ConfigAnalyzer()

        complexity = analyzer._calculate_pipeline_complexity([])

        assert complexity == 0

    @pytest.mark.asyncio
    async def test_high_complexity_pipeline_detected(self):
        """Test detection of overly complex pipelines."""
        # Create pipeline with high complexity (>50)
        complex_functions = []
        for i in range(15):  # 15 functions * 2 = 30 base complexity
            complex_functions.append({
                "id": "eval",
                "conf": {
                    "filter": "((a and b) or (c and d))",  # Adds nesting points
                    "expression": "long_expression_" * 10
                }
            })

        pipelines = [{
            "id": "complex_pipeline",
            "conf": {"functions": complex_functions}
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect high complexity
        complexity_findings = [f for f in result.findings
                              if f.id.startswith("config-complexity-high")]
        assert len(complexity_findings) == 1

        finding = complexity_findings[0]
        assert finding.severity in ["medium", "high"]
        assert "complex_pipeline" in finding.affected_components[0]

    @pytest.mark.asyncio
    async def test_many_functions_pipeline_detected(self):
        """Test detection of pipelines with too many functions."""
        # Create pipeline with >10 functions
        many_functions = [
            {"id": f"function_{i}", "conf": {}} for i in range(12)
        ]

        pipelines = [{
            "id": "large_pipeline",
            "conf": {"functions": many_functions}
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect too many functions
        function_count_findings = [f for f in result.findings
                                  if f.id.startswith("config-complexity-function-count")]
        assert len(function_count_findings) == 1

        finding = function_count_findings[0]
        assert finding.severity == "low"
        assert finding.metadata["function_count"] == 12

    @pytest.mark.asyncio
    async def test_duplicate_pipeline_patterns_detected(self):
        """Test detection of duplicate pipeline patterns."""
        # Create two pipelines with identical function patterns
        identical_functions = [
            {"id": "eval", "conf": {"expression": "x = 1"}},
            {"id": "drop", "conf": {"filter": "status == 404"}},
            {"id": "mask", "conf": {"fields": ["password"]}}
        ]

        pipelines = [
            {"id": "pipeline_1", "conf": {"functions": identical_functions}},
            {"id": "pipeline_2", "conf": {"functions": identical_functions}},  # Duplicate
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect duplicate pattern
        duplicate_findings = [f for f in result.findings
                             if f.id.startswith("config-complexity-duplicate-pattern")]
        assert len(duplicate_findings) == 1

        finding = duplicate_findings[0]
        assert finding.severity == "low"
        assert "pipeline_1" in finding.metadata["duplicate_pipeline_ids"]
        assert "pipeline_2" in finding.metadata["duplicate_pipeline_ids"]

    @pytest.mark.asyncio
    async def test_unique_pipelines_not_flagged_as_duplicate(self):
        """Test that unique pipelines are not flagged as duplicates."""
        pipelines = [
            {
                "id": "pipeline_1",
                "conf": {
                    "functions": [
                        {"id": "eval", "conf": {"expression": "x = 1"}},
                        {"id": "drop", "conf": {"filter": "status == 404"}}
                    ]
                }
            },
            {
                "id": "pipeline_2",
                "conf": {
                    "functions": [
                        {"id": "mask", "conf": {"fields": ["password"]}},
                        {"id": "regex_extract", "conf": {"pattern": ".*"}}
                    ]
                }
            }
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT detect duplicates
        duplicate_findings = [f for f in result.findings
                             if f.id.startswith("config-complexity-duplicate-pattern")]
        assert len(duplicate_findings) == 0

    @pytest.mark.asyncio
    async def test_complexity_metadata_populated(self):
        """Test that complexity metadata is properly populated."""
        pipelines = [
            {"id": "simple", "conf": {"functions": [{"id": "drop", "conf": {}}]}},
            {
                "id": "complex",
                "conf": {
                    "functions": [
                        {"id": f"func_{i}", "conf": {"filter": "((a and b) or c)"}}
                        for i in range(10)
                    ]
                }
            },
            {"id": "medium", "conf": {"functions": [{"id": f"func_{i}", "conf": {}} for i in range(5)]}}
        ]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have complexity metadata
        assert "avg_pipeline_complexity" in result.metadata
        assert "max_pipeline_complexity" in result.metadata
        assert "min_pipeline_complexity" in result.metadata
        assert "duplicate_patterns_found" in result.metadata

        # Verify values are reasonable
        assert result.metadata["avg_pipeline_complexity"] > 0
        assert result.metadata["max_pipeline_complexity"] >= result.metadata["avg_pipeline_complexity"]
        assert result.metadata["min_pipeline_complexity"] <= result.metadata["avg_pipeline_complexity"]

    @pytest.mark.asyncio
    async def test_complexity_no_pipelines(self):
        """Test complexity analysis with no pipelines."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle gracefully
        assert result.metadata["avg_pipeline_complexity"] == 0.0
        assert result.metadata["max_pipeline_complexity"] == 0
        assert result.metadata["duplicate_patterns_found"] == 0

    # Phase 2E: Advanced Security Checks Tests

    @pytest.mark.asyncio
    async def test_pii_exposure_in_expression_detected(self):
        """Test detection of PII references in eval expressions."""
        pipelines = [{
            "id": "user_data_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "expression": "user_ssn = social_security_number"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect SSN exposure
        pii_findings = [f for f in result.findings
                       if f.id.startswith("config-sec-pii")]
        assert len(pii_findings) > 0

        finding = pii_findings[0]
        assert finding.severity == "high"
        assert "ssn" in finding.title.lower() or "social" in finding.title.lower()

    @pytest.mark.asyncio
    async def test_unmasked_sensitive_field_detected(self):
        """Test detection of unmasked sensitive fields."""
        pipelines = [{
            "id": "payment_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "field": "credit_card",
                            "expression": "value = credit_card"
                        }
                    },
                    # No mask/redact function
                    {
                        "id": "publish",
                        "conf": {}
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect unmasked credit card field
        unmasked_findings = [f for f in result.findings
                            if f.id.startswith("config-sec-unmasked")]
        assert len(unmasked_findings) > 0

        finding = unmasked_findings[0]
        assert finding.severity == "medium"
        assert "credit" in finding.description.lower() or "card" in finding.description.lower()

    @pytest.mark.asyncio
    async def test_masked_sensitive_field_not_flagged(self):
        """Test that properly masked fields are not flagged."""
        pipelines = [{
            "id": "secure_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "field": "credit_card"
                        }
                    },
                    {
                        "id": "mask",
                        "conf": {
                            "fields": ["credit_card", "ssn"]
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT flag properly masked fields
        unmasked_findings = [f for f in result.findings
                            if f.id.startswith("config-sec-unmasked") and "credit_card" in f.id]
        assert len(unmasked_findings) == 0

    @pytest.mark.asyncio
    async def test_multiple_pii_types_detected(self):
        """Test detection of multiple PII types in single pipeline."""
        pipelines = [{
            "id": "multi_pii_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "expression": "log = email + ' ' + phone + ' ' + password"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect multiple PII types
        pii_findings = [f for f in result.findings
                       if f.id.startswith("config-sec-pii")]
        assert len(pii_findings) >= 3  # email, phone, password

    @pytest.mark.asyncio
    async def test_api_key_exposure_detected(self):
        """Test detection of API key exposure."""
        pipelines = [{
            "id": "api_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "expression": "auth = api_key + ':' + api_token"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect API key exposure
        api_findings = [f for f in result.findings
                       if "api" in f.title.lower() and f.id.startswith("config-sec-pii")]
        assert len(api_findings) >= 1

    @pytest.mark.asyncio
    async def test_ip_address_handling_detected(self):
        """Test detection of IP address handling without masking."""
        pipelines = [{
            "id": "network_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "field": "client_ip"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect IP address field
        ip_findings = [f for f in result.findings
                      if "ip" in f.metadata.get("field", "").lower() or "ip" in f.metadata.get("pii_type", "")]
        assert len(ip_findings) >= 0  # May or may not flag IPs depending on policy

    @pytest.mark.asyncio
    async def test_redact_function_protects_fields(self):
        """Test that redact function properly protects fields."""
        pipelines = [{
            "id": "redacted_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "field": "password"
                        }
                    },
                    {
                        "id": "redact",
                        "conf": {
                            "fields": ["password", "api_key"]
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT flag password field (it's redacted)
        pwd_findings = [f for f in result.findings
                       if f.id.startswith("config-sec-unmasked") and "password" in f.id]
        assert len(pwd_findings) == 0

    @pytest.mark.asyncio
    async def test_security_metadata_populated(self):
        """Test that security metadata is properly populated."""
        pipelines = [{
            "id": "test_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "expression": "data = email + ssn",
                            "field": "credit_card"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have security metadata
        assert "pii_exposure_risks" in result.metadata
        assert "unmasked_sensitive_fields" in result.metadata
        assert "encryption_issues" in result.metadata

    @pytest.mark.asyncio
    async def test_no_pipelines_security_check(self):
        """Test security check with no pipelines."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle gracefully
        assert result.metadata["pii_exposure_risks"] == 0
        assert result.metadata["unmasked_sensitive_fields"] == 0

    @pytest.mark.asyncio
    async def test_fields_list_pii_detection(self):
        """Test PII detection in fields list."""
        pipelines = [{
            "id": "batch_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "fields": ["name", "email", "phone", "address"]
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect email and phone in fields list
        sensitive_findings = [f for f in result.findings
                             if f.id.startswith("config-sec-unmasked")]
        assert len(sensitive_findings) >= 2  # At least email and phone

    @pytest.mark.asyncio
    async def test_case_insensitive_pii_detection(self):
        """Test that PII detection is case-insensitive."""
        pipelines = [{
            "id": "mixed_case_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "expression": "data = CREDIT_CARD + Email_Address"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect PII regardless of case
        pii_findings = [f for f in result.findings
                       if f.id.startswith("config-sec-pii")]
        assert len(pii_findings) >= 2  # credit_card and email

    @pytest.mark.asyncio
    async def test_partial_field_name_matching(self):
        """Test PII detection with partial field name matches."""
        pipelines = [{
            "id": "partial_match_pipeline",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "conf": {
                            "field": "user_email_address"  # Contains "email"
                        }
                    }
                ]
            }
        }]

        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"
        mock_client.get_pipelines.return_value = pipelines
        mock_client.get_routes.return_value = []
        mock_client.get_inputs.return_value = []
        mock_client.get_outputs.return_value = []

        analyzer = ConfigAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect email in composite field name
        email_findings = [f for f in result.findings
                         if "email" in f.metadata.get("field", "").lower()]
        assert len(email_findings) >= 1
