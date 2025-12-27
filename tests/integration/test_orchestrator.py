"""
Integration tests for analyzer orchestrator.

Tests the workflow coordination, API budget tracking, progress reporting,
and error handling for multi-analyzer execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from cribl_hc.core.orchestrator import AnalyzerOrchestrator, AnalysisProgress
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation


@pytest.fixture
def mock_api_client():
    """Create mock Cribl API client."""
    client = AsyncMock(spec=CriblAPIClient)
    client.get_api_calls_used = MagicMock(return_value=0)
    client.get_remaining_calls = MagicMock(return_value=100)
    return client


@pytest.fixture
def mock_analyzer():
    """Create mock analyzer."""
    analyzer = AsyncMock()
    analyzer.__class__.__name__ = "MockAnalyzer"
    analyzer.get_estimated_api_calls = MagicMock(return_value=5)
    analyzer.pre_analyze_check = AsyncMock(return_value=True)
    analyzer.analyze = AsyncMock(return_value=AnalyzerResult(
        objective="test",
        success=True,
        findings=[],
        recommendations=[],
        metadata={"test_key": "test_value"}
    ))
    return analyzer


class TestAnalysisProgress:
    """Test AnalysisProgress tracker."""

    def test_initialization(self):
        """Test progress tracker initialization."""
        progress = AnalysisProgress(total_objectives=3, api_call_budget=100)

        assert progress.total_objectives == 3
        assert progress.completed_objectives == 0
        assert progress.current_objective is None
        assert progress.api_calls_used == 0
        assert progress.api_calls_remaining == 100

    def test_start_objective(self):
        """Test starting an objective."""
        progress = AnalysisProgress(total_objectives=3)
        progress.start_objective("health")

        assert progress.current_objective == "health"

    def test_complete_objective(self):
        """Test completing an objective."""
        progress = AnalysisProgress(total_objectives=3)
        progress.start_objective("health")
        progress.complete_objective()

        assert progress.completed_objectives == 1
        assert progress.current_objective is None

    def test_update_api_calls(self):
        """Test updating API call tracking."""
        progress = AnalysisProgress(total_objectives=3, api_call_budget=100)
        progress.update_api_calls(used=25, remaining=75)

        assert progress.api_calls_used == 25
        assert progress.api_calls_remaining == 75

    def test_get_percentage(self):
        """Test completion percentage calculation."""
        progress = AnalysisProgress(total_objectives=4)

        assert progress.get_percentage() == 0.0

        progress.complete_objective()
        assert progress.get_percentage() == 25.0

        progress.complete_objective()
        assert progress.get_percentage() == 50.0

        progress.complete_objective()
        progress.complete_objective()
        assert progress.get_percentage() == 100.0

    def test_get_percentage_zero_objectives(self):
        """Test percentage with zero objectives."""
        progress = AnalysisProgress(total_objectives=0)
        assert progress.get_percentage() == 100.0

    def test_repr(self):
        """Test string representation."""
        progress = AnalysisProgress(total_objectives=5)
        progress.complete_objective()
        progress.update_api_calls(10, 90)

        repr_str = repr(progress)
        assert "1/5" in repr_str
        assert "10 API calls" in repr_str


class TestOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_initialization(self, mock_api_client):
        """Test orchestrator initialization."""
        orchestrator = AnalyzerOrchestrator(
            client=mock_api_client,
            max_api_calls=100,
            continue_on_error=True
        )

        assert orchestrator.client == mock_api_client
        assert orchestrator.max_api_calls == 100
        assert orchestrator.continue_on_error is True
        assert orchestrator.progress is None
        assert orchestrator.start_time is None
        assert orchestrator.end_time is None

    def test_initialization_defaults(self, mock_api_client):
        """Test orchestrator with default parameters."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        assert orchestrator.max_api_calls == 100
        assert orchestrator.continue_on_error is True


class TestOrchestratorWorkflow:
    """Test orchestrator analysis workflow."""

    @pytest.mark.asyncio
    async def test_run_analysis_single_objective(self, mock_api_client, mock_analyzer):
        """Test running analysis with single objective."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(objectives=["health"])

        assert len(results) == 1
        assert "health" in results
        assert results["health"].success is True
        assert orchestrator.start_time is not None
        assert orchestrator.end_time is not None

    @pytest.mark.asyncio
    async def test_run_analysis_multiple_objectives(self, mock_api_client, mock_analyzer):
        """Test running analysis with multiple objectives."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(
                    objectives=["health", "config", "resource"]
                )

        assert len(results) == 3
        assert "health" in results
        assert "config" in results
        assert "resource" in results

        # Should have run sequentially
        assert mock_analyzer.analyze.call_count == 3

    @pytest.mark.asyncio
    async def test_run_analysis_invalid_objective(self, mock_api_client):
        """Test running analysis with invalid objective."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
            mock_registry.return_value.has_analyzer = MagicMock(return_value=False)
            with patch('cribl_hc.core.orchestrator.list_objectives', return_value=["health", "config"]):

                with pytest.raises(ValueError, match="Unknown objective"):
                    await orchestrator.run_analysis(objectives=["invalid"])

    @pytest.mark.asyncio
    async def test_run_analysis_no_objectives(self, mock_api_client):
        """Test running analysis with no objectives."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        with patch('cribl_hc.core.orchestrator.list_objectives', return_value=[]):
            results = await orchestrator.run_analysis(objectives=None)

        assert results == {}

    @pytest.mark.asyncio
    async def test_run_analysis_with_progress_callback(self, mock_api_client, mock_analyzer):
        """Test progress callback is called during analysis."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)
        progress_updates = []

        def progress_callback(progress):
            progress_updates.append({
                "completed": progress.completed_objectives,
                "total": progress.total_objectives,
                "percentage": progress.get_percentage()
            })

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                await orchestrator.run_analysis(
                    objectives=["health", "config"],
                    progress_callback=progress_callback
                )

        # Should have received 2 progress updates (one per objective)
        assert len(progress_updates) == 2
        assert progress_updates[0]["completed"] == 1
        assert progress_updates[1]["completed"] == 2


class TestOrchestratorAPIBudget:
    """Test API call budget tracking and enforcement."""

    @pytest.mark.asyncio
    async def test_api_budget_tracking(self, mock_api_client, mock_analyzer):
        """Test API call budget is tracked during analysis."""
        # Simulate API calls being used
        api_calls_sequence = [0, 10, 25]
        mock_api_client.get_api_calls_used = MagicMock(side_effect=api_calls_sequence)

        orchestrator = AnalyzerOrchestrator(client=mock_api_client, max_api_calls=100)

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                await orchestrator.run_analysis(objectives=["health"])

        # Should have checked API calls multiple times
        assert mock_api_client.get_api_calls_used.call_count >= 2

    @pytest.mark.asyncio
    async def test_api_budget_exceeded(self, mock_api_client, mock_analyzer):
        """Test behavior when API budget is exceeded."""
        # Simulate budget exceeded on second objective
        mock_api_client.get_api_calls_used = MagicMock(side_effect=[0, 0, 100, 100])

        orchestrator = AnalyzerOrchestrator(
            client=mock_api_client,
            max_api_calls=100,
            continue_on_error=True
        )

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(objectives=["health", "config"])

        # First should succeed, second should fail
        assert results["health"].success is True
        assert results["config"].success is False
        assert "budget exceeded" in results["config"].error.lower()

    @pytest.mark.asyncio
    async def test_api_budget_exceeded_stop_on_error(self, mock_api_client, mock_analyzer):
        """Test stopping analysis when budget exceeded and continue_on_error=False."""
        mock_api_client.get_api_calls_used = MagicMock(side_effect=[0, 0, 100, 100])

        orchestrator = AnalyzerOrchestrator(
            client=mock_api_client,
            max_api_calls=100,
            continue_on_error=False
        )

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(
                    objectives=["health", "config", "resource"]
                )

        # Should have stopped after config failed
        assert "health" in results
        assert "config" in results
        assert "resource" not in results


class TestOrchestratorErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_analyzer_failure_continue_on_error(self, mock_api_client, mock_analyzer):
        """Test continuing analysis when an analyzer fails."""
        # First analyzer succeeds, second fails, third succeeds
        mock_analyzer.analyze = AsyncMock(side_effect=[
            AnalyzerResult(objective="health", success=True, findings=[], recommendations=[]),
            Exception("Test error"),
            AnalyzerResult(objective="resource", success=True, findings=[], recommendations=[])
        ])

        orchestrator = AnalyzerOrchestrator(
            client=mock_api_client,
            continue_on_error=True
        )

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(
                    objectives=["health", "config", "resource"]
                )

        # All three should have results
        assert len(results) == 3
        assert results["health"].success is True
        assert results["config"].success is False  # Failed
        assert results["resource"].success is True

    @pytest.mark.asyncio
    async def test_analyzer_failure_stop_on_error(self, mock_api_client, mock_analyzer):
        """Test stopping analysis when an analyzer fails."""
        mock_analyzer.analyze = AsyncMock(side_effect=Exception("Test error"))

        orchestrator = AnalyzerOrchestrator(
            client=mock_api_client,
            continue_on_error=False
        )

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(
                    objectives=["health", "config", "resource"]
                )

        # Should have stopped after first failure
        assert len(results) == 1
        assert results["health"].success is False

    @pytest.mark.asyncio
    async def test_preflight_check_failure(self, mock_api_client, mock_analyzer):
        """Test handling of pre-flight check failure."""
        mock_analyzer.pre_analyze_check = AsyncMock(return_value=False)

        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                results = await orchestrator.run_analysis(objectives=["health"])

        # Should have result but marked as failed
        assert results["health"].success is False
        assert "pre-flight check failed" in results["health"].error.lower()

    @pytest.mark.asyncio
    async def test_progress_callback_exception(self, mock_api_client, mock_analyzer):
        """Test that progress callback exceptions don't break analysis."""
        def failing_callback(progress):
            raise Exception("Callback failed")

        orchestrator = AnalyzerOrchestrator(client=mock_api_client)

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                # Should not raise exception
                results = await orchestrator.run_analysis(
                    objectives=["health"],
                    progress_callback=failing_callback
                )

        # Analysis should still complete
        assert len(results) == 1
        assert results["health"].success is True


class TestOrchestratorProgressTracking:
    """Test progress tracking throughout analysis."""

    @pytest.mark.asyncio
    async def test_progress_initialization(self, mock_api_client, mock_analyzer):
        """Test progress is initialized correctly."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client, max_api_calls=100)

        assert orchestrator.progress is None

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                await orchestrator.run_analysis(objectives=["health", "config"])

        assert orchestrator.progress is not None
        assert orchestrator.progress.total_objectives == 2
        assert orchestrator.progress.completed_objectives == 2

    @pytest.mark.asyncio
    async def test_progress_updates_during_analysis(self, mock_api_client, mock_analyzer):
        """Test progress is updated correctly during analysis."""
        orchestrator = AnalyzerOrchestrator(client=mock_api_client)
        captured_progress = []

        def capture_progress(progress):
            captured_progress.append({
                "completed": progress.completed_objectives,
                "current": progress.current_objective,
                "percentage": progress.get_percentage()
            })

        with patch('cribl_hc.core.orchestrator.get_analyzer', return_value=mock_analyzer):
            with patch('cribl_hc.core.orchestrator.get_global_registry') as mock_registry:
                mock_registry.return_value.has_analyzer = MagicMock(return_value=True)

                await orchestrator.run_analysis(
                    objectives=["health", "config", "resource"],
                    progress_callback=capture_progress
                )

        # Verify progressive completion
        assert len(captured_progress) == 3
        assert captured_progress[0]["completed"] == 1
        assert captured_progress[1]["completed"] == 2
        assert captured_progress[2]["completed"] == 3
        assert captured_progress[2]["percentage"] == 100.0
