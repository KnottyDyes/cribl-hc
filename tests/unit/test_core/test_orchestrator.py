"""
Unit tests for AnalyzerOrchestrator.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalyzerOrchestrator, AnalysisProgress
from cribl_hc.models.finding import Finding
from tests.helpers import create_test_finding


class TestAnalysisProgress:
    """Test suite for AnalysisProgress."""

    def test_init(self):
        """Test AnalysisProgress initialization."""
        progress = AnalysisProgress(total_objectives=3, api_call_budget=100)

        assert progress.total_objectives == 3
        assert progress.completed_objectives == 0
        assert progress.current_objective is None
        assert progress.api_calls_used == 0
        assert progress.api_calls_remaining == 100

    def test_start_objective(self):
        """Test starting an objective."""
        progress = AnalysisProgress(total_objectives=2)
        progress.start_objective("health")

        assert progress.current_objective == "health"

    def test_complete_objective(self):
        """Test completing an objective."""
        progress = AnalysisProgress(total_objectives=2)
        progress.start_objective("health")
        progress.complete_objective()

        assert progress.completed_objectives == 1
        assert progress.current_objective is None

    def test_update_api_calls(self):
        """Test updating API call tracking."""
        progress = AnalysisProgress(total_objectives=1)
        progress.update_api_calls(used=25, remaining=75)

        assert progress.api_calls_used == 25
        assert progress.api_calls_remaining == 75

    def test_get_percentage(self):
        """Test percentage calculation."""
        progress = AnalysisProgress(total_objectives=4)

        assert progress.get_percentage() == 0.0

        progress.completed_objectives = 2
        assert progress.get_percentage() == 50.0

        progress.completed_objectives = 4
        assert progress.get_percentage() == 100.0

    def test_get_percentage_no_objectives(self):
        """Test percentage with zero objectives."""
        progress = AnalysisProgress(total_objectives=0)
        assert progress.get_percentage() == 100.0

    def test_repr(self):
        """Test string representation."""
        progress = AnalysisProgress(total_objectives=3)
        progress.completed_objectives = 1
        progress.api_calls_used = 10

        repr_str = repr(progress)
        assert "1/3" in repr_str
        assert "10" in repr_str


class MockHealthAnalyzer(BaseAnalyzer):
    """Mock health analyzer for testing."""

    @property
    def objective_name(self) -> str:
        return "health"

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = AnalyzerResult(objective="health")
        result.add_finding(
            create_test_finding(
                id="test-finding-1",
                title="Test finding",
                description="Test",
                severity="medium",
                category="test",
            )
        )
        result.metadata["health_score"] = 85.0
        return result


class TestAnalyzerOrchestrator:
    """Test suite for AnalyzerOrchestrator."""

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        client.get_api_calls_used.return_value = 0
        client.get_api_calls_remaining.return_value = 100
        return client

    @pytest.fixture
    def orchestrator(self, mock_client):
        """Create orchestrator instance."""
        return AnalyzerOrchestrator(
            client=mock_client,
            max_api_calls=100,
            continue_on_error=True,
        )

    def test_init(self, mock_client):
        """Test orchestrator initialization."""
        orch = AnalyzerOrchestrator(
            client=mock_client,
            max_api_calls=50,
            continue_on_error=False,
        )

        assert orch.client == mock_client
        assert orch.max_api_calls == 50
        assert orch.continue_on_error is False

    @pytest.mark.asyncio
    async def test_run_analysis_no_objectives(self, orchestrator):
        """Test running analysis with no objectives."""
        # Mock empty registry
        with patch("cribl_hc.core.orchestrator.list_objectives", return_value=[]):
            results = await orchestrator.run_analysis()

            assert results == {}

    @pytest.mark.asyncio
    async def test_run_analysis_unknown_objective(self, orchestrator):
        """Test running analysis with unknown objective."""
        with pytest.raises(ValueError, match="Unknown objective"):
            await orchestrator.run_analysis(["nonexistent"])

    @pytest.mark.asyncio
    async def test_run_analysis_single_analyzer(self, orchestrator, mock_client):
        """Test running single analyzer."""
        # Mock registry to return our mock analyzer
        mock_analyzer = MockHealthAnalyzer()

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=mock_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(["health"])

                assert "health" in results
                assert results["health"].success is True
                assert len(results["health"].findings) == 1
                assert results["health"].metadata["health_score"] == 85.0

    @pytest.mark.asyncio
    async def test_run_analysis_progress_tracking(self, orchestrator, mock_client):
        """Test progress tracking during analysis."""
        mock_analyzer = MockHealthAnalyzer()

        progress_updates = []

        def progress_callback(progress: AnalysisProgress):
            progress_updates.append({
                "completed": progress.completed_objectives,
                "total": progress.total_objectives,
                "percentage": progress.get_percentage(),
            })

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=mock_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(
                    ["health"],
                    progress_callback=progress_callback,
                )

                assert len(progress_updates) == 1
                assert progress_updates[0]["completed"] == 1
                assert progress_updates[0]["total"] == 1
                assert progress_updates[0]["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_run_analysis_api_budget_tracking(self, orchestrator, mock_client):
        """Test API call budget tracking."""
        mock_analyzer = MockHealthAnalyzer()

        # Simulate API calls being made
        call_count = [0]

        def get_api_calls_used():
            call_count[0] += 5
            return call_count[0]

        mock_client.get_api_calls_used = get_api_calls_used

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=mock_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(["health"])

                # Check that API usage was tracked
                usage = orchestrator.get_api_usage_summary()
                assert usage["used"] > 0
                assert usage["remaining"] < 100
                assert usage["budget"] == 100

    @pytest.mark.asyncio
    async def test_run_analysis_api_budget_exceeded(self, orchestrator, mock_client):
        """Test behavior when API budget is exceeded."""
        mock_analyzer = MockHealthAnalyzer()

        # Simulate API budget exceeded
        mock_client.get_api_calls_used.return_value = 101

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=mock_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(["health"])

                # Should get a failure result
                assert "health" in results
                assert results["health"].success is False
                assert "budget exceeded" in results["health"].error.lower()

    @pytest.mark.asyncio
    async def test_run_analysis_analyzer_error_continue(self, orchestrator, mock_client):
        """Test continuing analysis when analyzer fails."""
        # Create failing analyzer
        class FailingAnalyzer(BaseAnalyzer):
            @property
            def objective_name(self) -> str:
                return "health"

            async def analyze(self, client):
                raise RuntimeError("Analyzer failed!")

        failing_analyzer = FailingAnalyzer()

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=failing_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(["health"])

                # Should get failure result but not raise exception
                assert "health" in results
                assert results["health"].success is False
                assert "failed" in results["health"].error.lower()

    @pytest.mark.asyncio
    async def test_run_analysis_analyzer_error_stop(self, mock_client):
        """Test stopping analysis when analyzer fails and continue_on_error=False."""
        orchestrator = AnalyzerOrchestrator(
            client=mock_client,
            continue_on_error=False,
        )

        class FailingAnalyzer(BaseAnalyzer):
            @property
            def objective_name(self) -> str:
                return "health"

            async def analyze(self, client):
                raise RuntimeError("Analyzer failed!")

        failing_analyzer = FailingAnalyzer()

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=failing_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health", "config"]):
                results = await orchestrator.run_analysis(["health", "config"])

                # Should only have health result (failed), config should not run
                assert len(results) == 1
                assert "health" in results
                assert "config" not in results

    @pytest.mark.asyncio
    async def test_run_analysis_preflight_check_failed(self, orchestrator, mock_client):
        """Test analyzer that fails pre-flight check."""
        class PreflightFailAnalyzer(BaseAnalyzer):
            @property
            def objective_name(self) -> str:
                return "health"

            async def pre_analyze_check(self, client):
                return False

            async def analyze(self, client):
                # Should not be called
                raise RuntimeError("Should not reach here!")

        analyzer = PreflightFailAnalyzer()

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(["health"])

                assert results["health"].success is False
                assert "pre-flight" in results["health"].error.lower()

    @pytest.mark.asyncio
    async def test_create_analysis_run(self, orchestrator, mock_client):
        """Test creating AnalysisRun from results."""
        mock_analyzer = MockHealthAnalyzer()

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=mock_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                results = await orchestrator.run_analysis(["health"])

                analysis_run = orchestrator.create_analysis_run(
                    results,
                    deployment_id="test-deployment",
                )

                assert analysis_run.deployment_id == "test-deployment"
                assert "health" in analysis_run.objectives_analyzed
                assert len(analysis_run.findings) == 1
                assert analysis_run.findings[0].severity == "medium"

    def test_get_progress(self, orchestrator):
        """Test getting progress."""
        # Before running analysis
        assert orchestrator.get_progress() is None

    def test_get_api_usage_summary(self, orchestrator, mock_client):
        """Test API usage summary."""
        mock_client.get_api_calls_used.return_value = 25

        summary = orchestrator.get_api_usage_summary()

        assert summary["used"] == 25
        assert summary["remaining"] == 75
        assert summary["budget"] == 100

    @pytest.mark.asyncio
    async def test_progress_callback_error_handling(self, orchestrator, mock_client):
        """Test that errors in progress callback don't crash analysis."""
        mock_analyzer = MockHealthAnalyzer()

        def failing_callback(progress):
            raise RuntimeError("Callback failed!")

        with patch("cribl_hc.core.orchestrator.get_analyzer", return_value=mock_analyzer):
            with patch("cribl_hc.core.orchestrator.list_objectives", return_value=["health"]):
                # Should not raise exception
                results = await orchestrator.run_analysis(
                    ["health"],
                    progress_callback=failing_callback,
                )

                assert "health" in results
                assert results["health"].success is True
