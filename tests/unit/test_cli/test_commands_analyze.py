"""
Unit tests for analyze CLI command.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from cribl_hc.cli.commands.analyze import app, run_analysis_async
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.models.analysis import AnalysisRun, Finding, Recommendation


runner = CliRunner()


@pytest.fixture
def mock_api_client():
    """Mock CriblAPIClient."""
    client = AsyncMock()
    client.get_api_calls_used.return_value = 25
    client.test_connection = AsyncMock(
        return_value=MagicMock(
            success=True,
            response_time_ms=150.0,
            cribl_version="4.0.0",
            error=None,
        )
    )
    return client


@pytest.fixture
def mock_orchestrator():
    """Mock AnalyzerOrchestrator."""
    orchestrator = MagicMock()

    # Mock results
    result = AnalyzerResult(objective="health")
    result.add_finding(
        Finding(
            id="finding-test-001",
            title="Test Finding",
            description="Test description",
            severity="high",
            category="health",
            affected_components=["worker-1"],
            remediation_steps=["Fix the issue"],
            estimated_impact="Test impact",
            confidence_level="high",
        )
    )
    from cribl_hc.models.recommendation import ImpactEstimate

    result.add_recommendation(
        Recommendation(
            id="rec-test-001",
            type="health",
            title="Test Recommendation",
            description="Fix the issue",
            rationale="Test rationale",
            priority="p1",
            implementation_steps=["Step 1", "Step 2"],
            impact_estimate=ImpactEstimate(performance_improvement="Test"),
            implementation_effort="low",
        )
    )

    orchestrator.run_analysis = AsyncMock(return_value={"health": result})
    orchestrator.create_analysis_run = MagicMock(
        return_value=AnalysisRun(
            deployment_id="test-deployment",
            status="completed",
            objectives_analyzed=["health"],
            api_calls_used=25,
            duration_seconds=5.5,
            findings=[result.findings[0]],
            recommendations=[result.recommendations[0]],
        )
    )

    return orchestrator


class TestAnalyzeCommand:
    """Test suite for analyze command."""

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_minimal_args(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator
    ):
        """Test run command with minimal required arguments."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client
        mock_orch_class.return_value = mock_orchestrator

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
            ],
        )

        # Command should succeed
        assert result.exit_code == 0
        assert "Analysis completed successfully" in result.stdout

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_with_objectives(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator
    ):
        """Test run command with specific objectives."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client
        mock_orch_class.return_value = mock_orchestrator

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
                "--objective",
                "health",
                "--objective",
                "config",
            ],
        )

        assert result.exit_code == 0

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    def test_run_command_connection_failure(self, mock_client_class):
        """Test run command with connection failure."""
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(
            return_value=MagicMock(
                success=False,
                error="Connection refused",
            )
        )
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
            ],
        )

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Connection failed" in result.stdout

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_with_output_file(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator, tmp_path
    ):
        """Test run command with JSON output file."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client
        mock_orch_class.return_value = mock_orchestrator

        output_file = tmp_path / "report.json"

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert "JSON report saved" in result.stdout

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_with_markdown(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator, tmp_path
    ):
        """Test run command with Markdown output."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client
        mock_orch_class.return_value = mock_orchestrator

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
                "--markdown",
            ],
        )

        assert result.exit_code == 0
        assert "Markdown report saved" in result.stdout

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_partial_completion(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator
    ):
        """Test run command with partial completion status."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client

        # Override analysis run to return partial status
        partial_run = AnalysisRun(
            deployment_id="test-deployment",
            status="partial",
            objectives_analyzed=["health"],
            api_calls_used=25,
            duration_seconds=5.5,
            findings=[],
            recommendations=[],
            partial_completion=True,
        )
        mock_orchestrator.create_analysis_run = MagicMock(return_value=partial_run)
        mock_orch_class.return_value = mock_orchestrator

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
            ],
        )

        # Should exit with code 2 for partial completion
        assert result.exit_code == 2
        assert "partially completed" in result.stdout

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_failed_status(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator
    ):
        """Test run command with failed status."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client

        # Override analysis run to return failed status
        failed_run = AnalysisRun(
            deployment_id="test-deployment",
            status="failed",
            objectives_analyzed=[],
            api_calls_used=10,
            duration_seconds=1.0,
            findings=[],
            recommendations=[],
        )
        mock_orchestrator.create_analysis_run = MagicMock(return_value=failed_run)
        mock_orch_class.return_value = mock_orchestrator

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
            ],
        )

        # Should exit with code 1 for failure
        assert result.exit_code == 1
        assert "Analysis failed" in result.stdout

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_custom_deployment_id(
        self, mock_orch_class, mock_client_class, mock_api_client, mock_orchestrator
    ):
        """Test run command with custom deployment ID."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client
        mock_orch_class.return_value = mock_orchestrator

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
                "--deployment-id",
                "production",
            ],
        )

        assert result.exit_code == 0
        # Verify deployment ID was passed to create_analysis_run
        mock_orchestrator.create_analysis_run.assert_called_once()
        call_args = mock_orchestrator.create_analysis_run.call_args
        assert call_args[0][1] == "production"

    @patch("cribl_hc.cli.commands.analyze.CriblAPIClient")
    @patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator")
    def test_run_command_custom_max_api_calls(
        self, mock_orch_class, mock_client_class, mock_api_client
    ):
        """Test run command with custom max API calls."""
        mock_client_class.return_value.__aenter__.return_value = mock_api_client

        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
                "--token",
                "test-token",
                "--max-api-calls",
                "50",
            ],
        )

        # Verify AnalyzerOrchestrator was initialized with custom max_api_calls
        mock_orch_class.assert_called_once()
        call_kwargs = mock_orch_class.call_args[1]
        assert call_kwargs["max_api_calls"] == 50

    def test_run_command_missing_url(self):
        """Test run command with missing required URL."""
        result = runner.invoke(
            app,
            [
                "run",
                "--token",
                "test-token",
            ],
        )

        # Should fail due to missing required argument
        assert result.exit_code != 0
        assert "Missing option" in result.stdout or "required" in result.stdout.lower()

    def test_run_command_missing_token(self):
        """Test run command with missing required token."""
        result = runner.invoke(
            app,
            [
                "run",
                "--url",
                "https://cribl.example.com",
            ],
        )

        # Should fail due to missing required argument
        assert result.exit_code != 0


@pytest.mark.asyncio
class TestRunAnalysisAsync:
    """Test suite for run_analysis_async function."""

    async def test_progress_callback_invoked(self, mock_api_client, mock_orchestrator):
        """Test that progress callback is invoked during analysis."""
        with patch("cribl_hc.cli.commands.analyze.CriblAPIClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_api_client

            with patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator") as mock_orch_class:
                mock_orch_class.return_value = mock_orchestrator

                # Run analysis
                await run_analysis_async(
                    url="https://cribl.example.com",
                    token="test-token",
                    objectives=["health"],
                    output_file=None,
                    markdown=False,
                    deployment_id="test",
                    max_api_calls=100,
                )

                # Verify run_analysis was called with a progress callback
                mock_orchestrator.run_analysis.assert_called_once()
                call_kwargs = mock_orchestrator.run_analysis.call_args[1]
                assert "progress_callback" in call_kwargs
                assert callable(call_kwargs["progress_callback"])

    async def test_json_report_creation(self, mock_api_client, mock_orchestrator, tmp_path):
        """Test JSON report file creation."""
        output_file = tmp_path / "test_report.json"

        with patch("cribl_hc.cli.commands.analyze.CriblAPIClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_api_client

            with patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator") as mock_orch_class:
                mock_orch_class.return_value = mock_orchestrator

                await run_analysis_async(
                    url="https://cribl.example.com",
                    token="test-token",
                    objectives=None,
                    output_file=output_file,
                    markdown=False,
                    deployment_id="test",
                    max_api_calls=100,
                )

                # Verify JSON file was created
                assert output_file.exists()

                # Verify it contains valid JSON
                import json
                with open(output_file) as f:
                    data = json.load(f)
                    assert "deployment_id" in data
                    assert data["deployment_id"] == "test-deployment"

    async def test_markdown_report_creation(self, mock_api_client, mock_orchestrator, tmp_path):
        """Test Markdown report file creation."""
        with patch("cribl_hc.cli.commands.analyze.CriblAPIClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_api_client

            with patch("cribl_hc.cli.commands.analyze.AnalyzerOrchestrator") as mock_orch_class:
                mock_orch_class.return_value = mock_orchestrator

                # Change to tmp_path directory for markdown file creation
                import os
                original_cwd = os.getcwd()
                os.chdir(tmp_path)

                try:
                    await run_analysis_async(
                        url="https://cribl.example.com",
                        token="test-token",
                        objectives=None,
                        output_file=None,
                        markdown=True,
                        deployment_id="test",
                        max_api_calls=100,
                    )

                    # Verify Markdown file was created
                    md_file = tmp_path / "test_report.md"
                    assert md_file.exists()

                    # Verify it contains expected content
                    content = md_file.read_text()
                    assert "# Cribl Stream Health Check Report" in content
                    assert "test-deployment" in content
                finally:
                    os.chdir(original_cwd)
