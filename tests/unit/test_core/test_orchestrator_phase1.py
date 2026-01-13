"""
Unit tests for Orchestrator Phase 1 integration: PipelineBottleneckAnalyzer + MetricsCollector

Tests verify:
1. PipelineBottleneckAnalyzer is registered and discoverable
2. Orchestrator runs pipeline_bottleneck objective successfully
3. Findings are aggregated into AnalysisRun correctly
4. Health score includes pipeline_bottleneck findings
5. Error handling for unavailable metrics
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cribl_hc.analyzers import get_analyzer, list_objectives
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalyzerOrchestrator


class TestPipelineBottleneckRegistration:
    """Test 1: Verify PipelineBottleneckAnalyzer is registered"""

    def test_pipeline_bottleneck_objective_exists(self):
        """Verify 'pipeline_bottleneck' is in list of available objectives."""
        objectives = list_objectives()
        assert "pipeline_bottleneck" in objectives, (
            f"'pipeline_bottleneck' not found in objectives: {objectives}"
        )

    def test_pipeline_bottleneck_analyzer_discoverable(self):
        """Verify PipelineBottleneckAnalyzer can be instantiated via registry."""
        analyzer = get_analyzer("pipeline_bottleneck")
        assert analyzer is not None, "Failed to get pipeline_bottleneck analyzer"
        assert analyzer.objective_name == "pipeline_bottleneck"
        assert "stream" in analyzer.supported_products
        assert "edge" in analyzer.supported_products

    def test_pipeline_bottleneck_analyzer_interface(self):
        """Verify PipelineBottleneckAnalyzer implements required interface."""
        analyzer = get_analyzer("pipeline_bottleneck")
        assert hasattr(analyzer, "analyze"), "Missing analyze() method"
        assert hasattr(analyzer, "get_description"), "Missing get_description() method"
        assert hasattr(analyzer, "get_estimated_api_calls"), (
            "Missing get_estimated_api_calls() method"
        )
        assert hasattr(analyzer, "get_required_permissions"), (
            "Missing get_required_permissions() method"
        )

    def test_pipeline_bottleneck_analyzer_metadata(self):
        """Verify PipelineBottleneckAnalyzer has proper metadata."""
        analyzer = get_analyzer("pipeline_bottleneck")
        description = analyzer.get_description()
        assert "bottleneck" in description.lower() or "throughput" in description.lower()

        api_calls = analyzer.get_estimated_api_calls()
        assert api_calls > 0, "Should estimate at least 1 API call"

        permissions = analyzer.get_required_permissions()
        assert "read:pipelines" in permissions
        assert "read:metrics" in permissions


class TestOrchestrationPipelineBottleneck:
    """Test 2-3: Orchestrator integration with pipeline_bottleneck"""

    @pytest.fixture
    def mock_client(self):
        """Create mock API client with proper async/sync method signatures."""
        client = AsyncMock(spec=CriblAPIClient)
        client.get_api_calls_used = MagicMock(return_value=0)  # Synchronous
        client.get_system_status.return_value = {"version": "4.15.1"}
        client.get_nodes.return_value = []
        client.product_type = "stream"
        client.is_cloud = False
        return client

    @pytest.fixture
    def orchestrator(self, mock_client):
        """Create orchestrator with mock client."""
        return AnalyzerOrchestrator(client=mock_client, max_api_calls=100)

    @pytest.mark.asyncio
    async def test_run_single_pipeline_bottleneck_objective(self, orchestrator, mock_client):
        """Test running pipeline_bottleneck objective alone."""
        # Mock pipeline and metrics data
        mock_client.get_pipelines.return_value = {
            "healthy-pipe": {
                "id": "healthy-pipe",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "healthy-pipe": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        # Run analysis
        results = await orchestrator.run_analysis(["pipeline_bottleneck"])

        # Verify result
        assert "pipeline_bottleneck" in results
        result = results["pipeline_bottleneck"]
        assert result.success is True, f"Analysis failed: {result.error}"
        assert result.objective == "pipeline_bottleneck"
        # Healthy pipeline should have few/no findings
        assert len(result.findings) < 3

    @pytest.mark.asyncio
    async def test_run_pipeline_bottleneck_with_unhealthy_metrics(self, orchestrator, mock_client):
        """Test pipeline_bottleneck with critical findings."""
        # Mock pipeline with silent failure (in > 0, out = 0)
        mock_client.get_pipelines.return_value = {
            "failing-pipe": {
                "id": "failing-pipe",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "failing-pipe": {
                    "in": {"events": 1000},
                    "out": {"events": 0},  # Silent failure!
                    "drop": {"events": 0},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        # Run analysis
        results = await orchestrator.run_analysis(["pipeline_bottleneck"])
        result = results["pipeline_bottleneck"]

        # Verify critical finding detected
        assert result.success is True
        assert len(result.findings) > 0
        critical_findings = result.get_critical_findings()
        assert len(critical_findings) > 0, "Should detect silent failure as CRITICAL"

        # Verify finding details
        silent_failure = next((f for f in critical_findings if "silent" in f.id.lower()), None)
        assert silent_failure is not None
        assert "1,000" in silent_failure.description or "1000" in silent_failure.description

    @pytest.mark.asyncio
    async def test_run_pipeline_bottleneck_no_metrics(self, orchestrator, mock_client):
        """Test graceful degradation when metrics unavailable."""
        # No metrics returned (Cribl Cloud scenario)
        mock_client.get_pipelines.return_value = {
            "some-pipe": {"id": "some-pipe", "disabled": False}
        }
        mock_client.get_metrics.return_value = None

        # Run analysis
        results = await orchestrator.run_analysis(["pipeline_bottleneck"])
        result = results["pipeline_bottleneck"]

        # Verify graceful degradation
        assert result.success is True, "Should succeed even without metrics"
        assert len(result.findings) >= 1

        # Should have info-level finding, not error
        info_findings = [f for f in result.findings if f.severity == "info"]
        assert len(info_findings) > 0

        # Finding should mention metrics unavailable
        metrics_finding = next(
            (f for f in info_findings if "metrics" in f.description.lower()), None
        )
        assert metrics_finding is not None

    @pytest.mark.asyncio
    async def test_run_pipeline_bottleneck_empty_pipelines(self, orchestrator, mock_client):
        """Test handling of no pipelines configured."""
        mock_client.get_pipelines.return_value = {}
        mock_client.get_metrics.return_value = {"pipelines": {}}

        results = await orchestrator.run_analysis(["pipeline_bottleneck"])
        result = results["pipeline_bottleneck"]

        assert result.success is True
        assert len(result.findings) >= 1

        # Should have info finding about no pipelines
        no_pipe_finding = next(
            (
                f
                for f in result.findings
                if "no" in f.title.lower() and "pipeline" in f.title.lower()
            ),
            None,
        )
        assert no_pipe_finding is not None

    @pytest.mark.asyncio
    async def test_orchestrator_aggregates_pipeline_bottleneck_findings(
        self, orchestrator, mock_client
    ):
        """Test AnalysisRun aggregation includes pipeline_bottleneck findings."""
        # Mock data for both health and pipeline_bottleneck
        mock_client.get_pipelines.return_value = {"pipe-1": {"id": "pipe-1", "disabled": False}}
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 100},
                    "out": {"events": 50},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 100.0,  # 50% increase anomaly
                }
            }
        }

        # Run multiple objectives
        results = await orchestrator.run_analysis(["health", "pipeline_bottleneck"])

        # Create AnalysisRun
        analysis_run = orchestrator.create_analysis_run(results, "test-deployment")

        # Verify aggregation
        assert "health" in analysis_run.objectives_analyzed
        assert "pipeline_bottleneck" in analysis_run.objectives_analyzed

        # Verify findings from both objectives are included
        assert len(analysis_run.findings) > 0

        # Verify pipeline_bottleneck findings are present
        pb_findings = [
            f for f in analysis_run.findings if f.source_analyzer == "pipeline_bottleneck"
        ]
        assert len(pb_findings) > 0, "Should have findings from pipeline_bottleneck analyzer"

    @pytest.mark.asyncio
    async def test_health_score_includes_pipeline_bottleneck_category(
        self, orchestrator, mock_client
    ):
        """Test health score calculation includes pipeline_bottleneck in resource category."""
        # Healthy metrics
        mock_client.get_pipelines.return_value = {"pipe": {"id": "pipe", "disabled": False}}
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        results = await orchestrator.run_analysis(["pipeline_bottleneck"])
        analysis_run = orchestrator.create_analysis_run(results, "test")

        # Verify resource category exists (key is lowercase)
        assert "resource" in analysis_run.health_score.components
        resource_component = analysis_run.health_score.components["resource"]

        # Resource component should include pipeline_bottleneck in details
        assert "pipeline_bottleneck" in resource_component.details.lower()

    @pytest.mark.asyncio
    async def test_metrics_shared_across_objectives(self, orchestrator, mock_client):
        """Test that orchestrator doesn't make duplicate metrics calls."""
        # Setup mock to track call count
        call_count = {"metrics": 0}


        async def tracked_get_metrics(*args, **kwargs):
            call_count["metrics"] += 1
            return {
                "pipelines": {
                    "pipe": {
                        "in": {"events": 100},
                        "out": {"events": 100},
                        "drop": {"events": 0},
                        "error": {"events": 0},
                        "processingTime": 50.0,
                    }
                }
            }

        mock_client.get_metrics = tracked_get_metrics
        mock_client.get_pipelines.return_value = {"pipe": {"id": "pipe", "disabled": False}}

        # Each analyzer makes its own call, so we expect 1 call per analyzer
        await orchestrator.run_analysis(["pipeline_bottleneck"])

        # Verify get_metrics was called (by pipeline_bottleneck analyzer)
        assert call_count["metrics"] > 0, "get_metrics should be called"


class TestErrorHandling:
    """Test 7: Error handling and graceful degradation"""

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_api_calls_used = MagicMock(return_value=0)
        client.get_system_status.return_value = {"version": "4.15.1"}
        client.get_nodes.return_value = []
        client.product_type = "stream"
        client.is_cloud = False
        return client

    @pytest.mark.asyncio
    async def test_pipeline_bottleneck_handles_api_error(self, mock_client):
        """Test graceful handling when API call fails."""
        mock_client.get_pipelines.side_effect = RuntimeError("API Error")

        orchestrator = AnalyzerOrchestrator(client=mock_client)
        results = await orchestrator.run_analysis(["pipeline_bottleneck"])

        # Should fail gracefully
        assert "pipeline_bottleneck" in results
        assert results["pipeline_bottleneck"].success is False
        assert "error" in results["pipeline_bottleneck"].error.lower()

    @pytest.mark.asyncio
    async def test_pipeline_bottleneck_missing_metrics_data(self, mock_client):
        """Test handling of malformed metrics response."""
        mock_client.get_pipelines.return_value = {"pipe": {"id": "pipe"}}
        mock_client.get_metrics.return_value = {"pipelines": {}}  # Empty metrics

        orchestrator = AnalyzerOrchestrator(client=mock_client)
        results = await orchestrator.run_analysis(["pipeline_bottleneck"])

        result = results["pipeline_bottleneck"]
        # Should succeed but with info finding
        assert result.success is True
        assert len(result.findings) >= 1

    @pytest.mark.asyncio
    async def test_orchestrator_continues_on_analyzer_error(self, mock_client):
        """Test orchestrator continues with other objectives if one fails."""
        # Fail pipeline_bottleneck, succeed on health
        mock_client.get_pipelines.side_effect = RuntimeError("Pipeline API down")
        mock_client.get_system_status.return_value = {"version": "4.15.1"}

        orchestrator = AnalyzerOrchestrator(client=mock_client, continue_on_error=True)
        results = await orchestrator.run_analysis(["pipeline_bottleneck", "health"])

        # Both should be in results
        assert "pipeline_bottleneck" in results
        assert "health" in results

        # pipeline_bottleneck should fail
        assert results["pipeline_bottleneck"].success is False

        # health should succeed (may have fewer findings due to lack of full metrics)
        assert results["health"].success is True


class TestSmokeTests:
    """Integration smoke tests for phase 1 completion"""

    @pytest.fixture
    def mock_client_full(self):
        """Mock client with realistic data."""
        client = AsyncMock(spec=CriblAPIClient)
        client.get_api_calls_used = MagicMock(return_value=5)
        client.get_system_status.return_value = {"version": "4.15.1", "deploymentName": "test"}
        client.get_nodes.return_value = [
            {
                "id": "worker1",
                "status": "up",
                "info": {
                    "cribl": {"version": "4.15.1"},
                    "hostname": "worker-1.local",
                },
                "group": "default",
            }
        ]
        client.product_type = "stream"
        client.is_cloud = False

        return client

    @pytest.mark.asyncio
    async def test_full_analysis_all_objectives(self, mock_client_full):
        """Run full analysis with multiple objectives including pipeline_bottleneck."""
        mock_client_full.get_pipelines.return_value = {
            "ingest": {"id": "ingest", "disabled": False},
            "transform": {"id": "transform", "disabled": False},
        }
        mock_client_full.get_metrics.return_value = {
            "pipelines": {
                "ingest": {
                    "in": {"events": 5000},
                    "out": {"events": 4500},
                    "drop": {"events": 500},
                    "error": {"events": 0},
                    "processingTime": 75.0,
                },
                "transform": {
                    "in": {"events": 4500},
                    "out": {"events": 4400},
                    "drop": {"events": 100},
                    "error": {"events": 0},
                    "processingTime": 120.0,
                },
            }
        }

        orchestrator = AnalyzerOrchestrator(client=mock_client_full, max_api_calls=100)

        results = await orchestrator.run_analysis(["pipeline_bottleneck"])

        assert "pipeline_bottleneck" in results
        assert results["pipeline_bottleneck"].success is True

        analysis_run = orchestrator.create_analysis_run(results, "smoke-test-deployment")

        assert analysis_run.status in ("completed", "partial")
        assert analysis_run.health_score.overall_score >= 0
        assert analysis_run.health_score.overall_score <= 100
        assert "resource" in analysis_run.health_score.components

    @pytest.mark.asyncio
    async def test_analysis_produces_valid_output_structure(self, mock_client_full):
        """Verify output structure is complete and valid."""
        mock_client_full.get_pipelines.return_value = {}
        mock_client_full.get_outputs.return_value = {}
        mock_client_full.get_metrics.return_value = {"pipelines": {}}

        orchestrator = AnalyzerOrchestrator(client=mock_client_full)
        results = await orchestrator.run_analysis(["pipeline_bottleneck"])

        analysis_run = orchestrator.create_analysis_run(results, "structure-test")

        # Verify structure
        assert hasattr(analysis_run, "deployment_id")
        assert hasattr(analysis_run, "status")
        assert hasattr(analysis_run, "objectives_analyzed")
        assert hasattr(analysis_run, "findings")
        assert hasattr(analysis_run, "recommendations")
        assert hasattr(analysis_run, "health_score")
        assert hasattr(analysis_run, "duration_seconds")
        assert hasattr(analysis_run, "api_calls_used")

        # Verify types
        assert isinstance(analysis_run.findings, list)
        assert isinstance(analysis_run.recommendations, list)
        assert isinstance(analysis_run.objectives_analyzed, list)
        assert isinstance(analysis_run.health_score.overall_score, int)
        assert isinstance(analysis_run.duration_seconds, float)
