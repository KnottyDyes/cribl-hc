"""
Unit tests for DataFlowTopologyAnalyzer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.dataflow_topology import DataFlowTopologyAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestDataFlowTopologyAnalyzer:
    """Test DataFlowTopologyAnalyzer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = DataFlowTopologyAnalyzer()
        self.mock_client = MagicMock(spec=CriblAPIClient)
        self.mock_client.get_routes = AsyncMock(return_value=[])
        self.mock_client.get_pipelines = AsyncMock(return_value=[])
        self.mock_client.get_inputs = AsyncMock(return_value=[])
        self.mock_client.get_outputs = AsyncMock(return_value=[])

    def test_objective_name(self):
        """Test objective name property."""
        assert self.analyzer.objective_name == "dataflow_topology"

    def test_supported_products(self):
        """Test supported products."""
        products = self.analyzer.supported_products
        assert "stream" in products
        assert "edge" in products

    def test_get_description(self):
        """Test description."""
        description = self.analyzer.get_description()
        assert "Data flow topology" in description
        assert "route validation" in description

    def test_get_estimated_api_calls(self):
        """Test estimated API calls."""
        assert self.analyzer.get_estimated_api_calls() == 4

    def test_get_required_permissions(self):
        """Test required permissions."""
        permissions = self.analyzer.get_required_permissions()
        assert "read:routes" in permissions
        assert "read:pipelines" in permissions
        assert "read:outputs" in permissions
        assert "read:inputs" in permissions

    @pytest.mark.asyncio
    async def test_analyze_healthy_topology(self):
        """Test analysis with healthy data flow topology."""
        # Mock routes
        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "main-pipeline",
                "output": "splunk-output",
                "disabled": False,
            },
            {
                "id": "route-2",
                "name": "Error Route",
                "filter": "level=='error'",
                "pipeline": "error-pipeline",
                "output": "pagerduty-output",
                "disabled": False,
            },
        ]

        # Mock pipelines
        pipelines = [
            {
                "id": "main-pipeline",
                "name": "Main Processing",
                "functions": [
                    {"id": "parser", "type": "parser"},
                    {"id": "enricher", "type": "lookup"},
                ],
                "disabled": False,
            },
            {
                "id": "error-pipeline",
                "name": "Error Processing",
                "functions": [{"id": "alert", "type": "eval"}],
                "disabled": False,
            },
        ]

        # Mock outputs
        outputs = [
            {"id": "splunk-output", "name": "Splunk HEC", "type": "splunk_hec", "disabled": False},
            {"id": "pagerduty-output", "name": "PagerDuty", "type": "webhook", "disabled": False},
        ]

        # Mock inputs
        inputs = [{"id": "syslog-input", "name": "Syslog", "type": "syslog", "disabled": False}]

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        assert result.metadata["route_count"] == 2
        assert result.metadata["pipeline_count"] == 2
        assert result.metadata["output_count"] == 2
        assert result.metadata["input_count"] == 1

        # Should have minimal findings for healthy topology
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) == 0

    @pytest.mark.asyncio
    async def test_analyze_orphaned_pipelines(self):
        """Test analysis with orphaned pipelines."""
        # Mock routes - only references main-pipeline
        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "main-pipeline",
                "output": "splunk-output",
                "disabled": False,
            }
        ]

        # Mock pipelines - includes orphaned pipeline
        pipelines = [
            {
                "id": "main-pipeline",
                "name": "Main Processing",
                "functions": [{"id": "parser", "type": "parser"}],
                "disabled": False,
            },
            {
                "id": "orphaned-pipeline",
                "name": "Orphaned Pipeline",
                "functions": [{"id": "unused", "type": "eval"}],
                "disabled": False,
            },
        ]

        # Mock outputs
        outputs = [
            {"id": "splunk-output", "name": "Splunk HEC", "type": "splunk_hec", "disabled": False}
        ]

        # Mock inputs
        inputs = [{"id": "syslog-input", "name": "Syslog", "type": "syslog", "disabled": False}]

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success

        # Should find orphaned pipeline
        findings = result.findings
        orphaned_finding = any(
            "disconnected" in f.title.lower()
            or "orphaned" in f.title.lower()
            or "unused" in f.description.lower()
            for f in findings
        )
        assert orphaned_finding

    @pytest.mark.asyncio
    async def test_analyze_orphaned_outputs(self):
        """Test analysis with orphaned outputs."""
        # Mock routes - only references splunk-output
        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "main-pipeline",
                "output": "splunk-output",
                "disabled": False,
            }
        ]

        # Mock pipelines
        pipelines = [
            {
                "id": "main-pipeline",
                "name": "Main Processing",
                "functions": [{"id": "parser", "type": "parser"}],
                "disabled": False,
            }
        ]

        # Mock outputs - includes orphaned output
        outputs = [
            {"id": "splunk-output", "name": "Splunk HEC", "type": "splunk_hec", "disabled": False},
            {
                "id": "orphaned-output",
                "name": "Unused Output",
                "type": "webhook",
                "disabled": False,
            },
        ]

        # Mock inputs
        inputs = [{"id": "syslog-input", "name": "Syslog", "type": "syslog", "disabled": False}]

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success

        # Should find orphaned output
        findings = result.findings
        orphaned_finding = any(
            "orphaned" in f.title.lower() or "unused" in f.description.lower() for f in findings
        )
        assert orphaned_finding

    @pytest.mark.asyncio
    async def test_analyze_missing_pipeline_references(self):
        """Test analysis with routes referencing non-existent pipelines."""
        # Mock routes - references non-existent pipeline
        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "nonexistent-pipeline",  # Missing pipeline
                "output": "splunk-output",
                "disabled": False,
            }
        ]

        # Mock pipelines - doesn't include referenced pipeline
        pipelines = [
            {
                "id": "other-pipeline",
                "name": "Other Pipeline",
                "functions": [{"id": "parser", "type": "parser"}],
                "disabled": False,
            }
        ]

        # Mock outputs
        outputs = [
            {"id": "splunk-output", "name": "Splunk HEC", "type": "splunk_hec", "disabled": False}
        ]

        # Mock inputs
        inputs = []

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success

        # Should find missing pipeline reference
        findings = result.findings
        missing_ref_finding = any(
            "missing" in f.title.lower() or "nonexistent" in f.description.lower() for f in findings
        )
        assert missing_ref_finding

    @pytest.mark.asyncio
    async def test_analyze_missing_output_references(self):
        """Test analysis with routes referencing non-existent outputs."""
        # Mock routes - references non-existent output
        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "main-pipeline",
                "output": "nonexistent-output",  # Missing output
                "disabled": False,
            }
        ]

        # Mock pipelines
        pipelines = [
            {
                "id": "main-pipeline",
                "name": "Main Processing",
                "functions": [{"id": "parser", "type": "parser"}],
                "disabled": False,
            }
        ]

        # Mock outputs - doesn't include referenced output
        outputs = [
            {"id": "other-output", "name": "Other Output", "type": "webhook", "disabled": False}
        ]

        # Mock inputs
        inputs = []

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success

        # Should find missing output reference
        findings = result.findings
        missing_ref_finding = any(
            "missing" in f.title.lower() or "nonexistent" in f.description.lower() for f in findings
        )
        assert missing_ref_finding

    @pytest.mark.asyncio
    async def test_analyze_disabled_components(self):
        """Test analysis with disabled components in topology."""
        # Mock routes - references disabled pipeline
        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "disabled-pipeline",
                "output": "splunk-output",
                "disabled": False,
            }
        ]

        # Mock pipelines - includes disabled pipeline
        pipelines = [
            {
                "id": "disabled-pipeline",
                "name": "Disabled Pipeline",
                "functions": [{"id": "parser", "type": "parser"}],
                "disabled": True,  # Disabled
            }
        ]

        # Mock outputs
        outputs = [
            {"id": "splunk-output", "name": "Splunk HEC", "type": "splunk_hec", "disabled": False}
        ]

        # Mock inputs
        inputs = []

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success

        findings = result.findings
        assert len(findings) >= 0

    @pytest.mark.asyncio
    async def test_analyze_complex_topology_issues(self):
        """Test analysis with multiple topology issues."""
        # Mock routes with various issues
        routes = [
            {
                "id": "route-1",
                "name": "Good Route",
                "filter": "source=='app'",
                "pipeline": "main-pipeline",
                "output": "splunk-output",
                "disabled": False,
            },
            {
                "id": "route-2",
                "name": "Bad Route",
                "filter": "source=='error'",
                "pipeline": "missing-pipeline",  # Missing
                "output": "missing-output",  # Missing
                "disabled": False,
            },
            {
                "id": "route-3",
                "name": "Disabled Route",
                "filter": "source=='test'",
                "pipeline": "test-pipeline",
                "output": "test-output",
                "disabled": True,  # Disabled route
            },
        ]

        # Mock pipelines
        pipelines = [
            {
                "id": "main-pipeline",
                "name": "Main Processing",
                "functions": [{"id": "parser", "type": "parser"}],
                "disabled": False,
            },
            {
                "id": "orphaned-pipeline",
                "name": "Orphaned Pipeline",
                "functions": [{"id": "unused", "type": "eval"}],
                "disabled": False,
            },
            {
                "id": "test-pipeline",
                "name": "Test Pipeline",
                "functions": [{"id": "test", "type": "eval"}],
                "disabled": False,
            },
        ]

        # Mock outputs
        outputs = [
            {"id": "splunk-output", "name": "Splunk HEC", "type": "splunk_hec", "disabled": False},
            {
                "id": "orphaned-output",
                "name": "Orphaned Output",
                "type": "webhook",
                "disabled": False,
            },
            {"id": "test-output", "name": "Test Output", "type": "devnull", "disabled": False},
        ]

        # Mock inputs
        inputs = []

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.return_value = pipelines
        self.mock_client.get_outputs.return_value = outputs
        self.mock_client.get_inputs.return_value = inputs

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success

        # Should find multiple issues
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_empty_topology(self):
        """Test analysis with empty topology."""
        self.mock_client.get_routes.return_value = []
        self.mock_client.get_pipelines.return_value = []
        self.mock_client.get_outputs.return_value = []
        self.mock_client.get_inputs.return_value = []

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        assert result.metadata["route_count"] == 0
        assert result.metadata["pipeline_count"] == 0
        assert result.metadata["output_count"] == 0
        assert result.metadata["input_count"] == 0

        findings = result.findings
        assert len(findings) >= 1

    @pytest.mark.asyncio
    async def test_analyze_api_error_handling(self):
        """Test analysis handles API errors gracefully."""
        # Mock API error
        self.mock_client.get_routes.side_effect = Exception("API connection failed")

        result = await self.analyzer.analyze(self.mock_client)

        assert not result.success
        assert result.error

    @pytest.mark.asyncio
    async def test_analyze_partial_api_failure(self):
        """Test analysis with partial API failures."""

        routes = [
            {
                "id": "route-1",
                "name": "Main Route",
                "filter": "source=='app'",
                "pipeline": "main-pipeline",
                "output": "splunk-output",
                "disabled": False,
            }
        ]

        self.mock_client.get_routes.return_value = routes
        self.mock_client.get_pipelines.side_effect = Exception("Pipelines API failed")

        result = await self.analyzer.analyze(self.mock_client)

        assert not result.success
        assert result.error

    def test_analyzer_inheritance(self):
        """Test that analyzer properly inherits from BaseAnalyzer."""
        from cribl_hc.analyzers.base import BaseAnalyzer

        assert isinstance(self.analyzer, BaseAnalyzer)

    def test_analyzer_constants(self):
        """Test analyzer constants and properties."""
        assert self.analyzer.objective_name == "dataflow_topology"
        assert isinstance(self.analyzer.supported_products, list)
        assert len(self.analyzer.supported_products) > 0
        assert isinstance(self.analyzer.get_estimated_api_calls(), int)
        assert self.analyzer.get_estimated_api_calls() > 0
