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
