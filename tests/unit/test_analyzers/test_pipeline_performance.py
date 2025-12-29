"""
Unit tests for PipelinePerformanceAnalyzer.

Tests pipeline function performance analysis, regex complexity detection,
JavaScript anti-patterns, and function ordering recommendations.
"""

import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.pipeline_performance import PipelinePerformanceAnalyzer


class TestPipelinePerformanceAnalyzer:
    """Tests for PipelinePerformanceAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create PipelinePerformanceAnalyzer instance."""
        return PipelinePerformanceAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock()
        client.get_pipelines = AsyncMock(return_value=[])
        client.get_metrics = AsyncMock(return_value={})
        return client

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "pipeline_performance"

    def test_get_description(self, analyzer):
        """Test analyzer description."""
        desc = analyzer.get_description()
        assert "pipeline" in desc.lower()
        assert "performance" in desc.lower()

    def test_get_estimated_api_calls(self, analyzer):
        """Test estimated API calls."""
        assert analyzer.get_estimated_api_calls() == 2

    def test_get_required_permissions(self, analyzer):
        """Test required permissions."""
        perms = analyzer.get_required_permissions()
        assert "read:pipelines" in perms
        assert "read:metrics" in perms

    @pytest.mark.asyncio
    async def test_analyze_no_pipelines(self, analyzer, mock_client):
        """Test analysis with no pipelines configured."""
        mock_client.get_pipelines.return_value = []
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_pipelines"] == 0
        assert len(result.findings) == 1
        assert result.findings[0].id == "pipeline-perf-no-pipelines"

    @pytest.mark.asyncio
    async def test_analyze_healthy_pipelines(self, analyzer, mock_client):
        """Test analysis with healthy pipelines."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "main-pipeline",
                "functions": [
                    {"id": "func-1", "type": "mask"},
                    {"id": "func-2", "type": "rename"}
                ]
            }
        ]
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "main-pipeline": {
                    "in": {"events": 10000},
                    "out": {"events": 10000},
                    "processing_time_ms": 500  # 0.05ms per event - fast
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_pipelines"] == 1
        assert result.metadata["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_analyze_detects_slow_pipeline(self, analyzer, mock_client):
        """Test analyzer detects slow pipelines."""
        mock_client.get_pipelines.return_value = [
            {"id": "slow-pipeline", "functions": [{"id": "func-1", "type": "eval"}]}
        ]
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "slow-pipeline": {
                    "in": {"events": 1000},
                    "out": {"events": 1000},
                    "processing_time_ms": 6000  # 6ms per event - very slow
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["slow_pipelines"] == 1

        slow_findings = [f for f in result.findings if "slow" in f.id]
        assert len(slow_findings) == 1
        assert slow_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_analyze_detects_complex_regex(self, analyzer, mock_client):
        """Test analyzer detects complex regex patterns."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "regex-pipeline",
                "functions": [
                    {
                        "id": "regex-func",
                        "type": "regex_extract",
                        "conf": {
                            "regex": "(a+)+b"  # Nested quantifiers - backtracking risk
                        }
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata.get("regex_issues", 0) >= 1

        regex_findings = [f for f in result.findings if "regex" in f.id]
        assert len(regex_findings) >= 1

    @pytest.mark.asyncio
    async def test_analyze_detects_unbounded_regex(self, analyzer, mock_client):
        """Test analyzer detects unbounded .* patterns."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "unbounded-regex",
                "functions": [
                    {
                        "id": "regex-func",
                        "type": "regex_extract",
                        "conf": {
                            "regex": ".*error.*"  # Unbounded without anchors
                        }
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        regex_findings = [f for f in result.findings if "regex" in f.id]
        assert len(regex_findings) >= 1
        assert "unbounded" in regex_findings[0].metadata.get("issues", [""])[0].lower() or \
               "anchor" in str(regex_findings[0].metadata.get("issues", [])).lower()

    @pytest.mark.asyncio
    async def test_analyze_detects_js_antipatterns(self, analyzer, mock_client):
        """Test analyzer detects JavaScript anti-patterns."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "js-pipeline",
                "functions": [
                    {
                        "id": "eval-func",
                        "type": "eval",
                        "conf": {
                            "expression": "myField.test(/simple/)"  # .test() for simple check
                        }
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata.get("js_antipatterns", 0) >= 1

    @pytest.mark.asyncio
    async def test_analyze_detects_eval_usage(self, analyzer, mock_client):
        """Test analyzer detects eval() usage in code."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "eval-danger",
                "functions": [
                    {
                        "id": "code-func",
                        "type": "code",
                        "conf": {
                            "code": "eval(userInput)"  # Dangerous eval
                        }
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        js_findings = [f for f in result.findings if "js" in f.id]
        assert len(js_findings) >= 1
        assert "eval" in str(js_findings[0].metadata.get("anti_patterns", []))

    @pytest.mark.asyncio
    async def test_analyze_detects_function_ordering_issue(self, analyzer, mock_client):
        """Test analyzer detects suboptimal function ordering."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "bad-order-pipeline",
                "functions": [
                    {"id": "lookup-func", "type": "lookup"},  # Heavy first
                    {"id": "geoip-func", "type": "geoip"},    # Heavy second
                    {"id": "filter-func", "type": "filter"}   # Filter last (should be first)
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        ordering_findings = [f for f in result.findings if "ordering" in f.id]
        assert len(ordering_findings) == 1

        # Should have recommendation
        ordering_recs = [r for r in result.recommendations if "ordering" in r.id]
        assert len(ordering_recs) == 1

    @pytest.mark.asyncio
    async def test_analyze_good_function_ordering(self, analyzer, mock_client):
        """Test analyzer doesn't flag good function ordering."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "good-order-pipeline",
                "functions": [
                    {"id": "filter-func", "type": "filter"},  # Filter first - good!
                    {"id": "drop-func", "type": "drop"},
                    {"id": "lookup-func", "type": "lookup"},  # Heavy after filter
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        ordering_findings = [f for f in result.findings if "ordering" in f.id]
        assert len(ordering_findings) == 0

    @pytest.mark.asyncio
    async def test_analyze_regex_lookup(self, analyzer, mock_client):
        """Test analyzer flags regex lookup mode."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "lookup-pipeline",
                "functions": [
                    {
                        "id": "lookup-func",
                        "type": "lookup",
                        "conf": {
                            "matchMode": "regex"  # Slower than exact
                        }
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        lookup_findings = [f for f in result.findings if "lookup-regex" in f.id]
        assert len(lookup_findings) == 1

    @pytest.mark.asyncio
    async def test_analyze_skips_disabled_functions(self, analyzer, mock_client):
        """Test analyzer skips disabled functions."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "disabled-pipeline",
                "functions": [
                    {
                        "id": "disabled-regex",
                        "type": "regex_extract",
                        "disabled": True,
                        "conf": {"regex": "(a+)+b"}  # Would be flagged if enabled
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata.get("regex_issues", 0) == 0

    @pytest.mark.asyncio
    async def test_analyze_handles_api_error(self, analyzer, mock_client):
        """Test analyzer handles API errors gracefully."""
        mock_client.get_pipelines.side_effect = Exception("API connection failed")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "error" in result.metadata

        error_findings = [f for f in result.findings if "error" in f.id]
        assert len(error_findings) == 1

    @pytest.mark.asyncio
    async def test_analyze_multiple_pipelines(self, analyzer, mock_client):
        """Test analyzer handles multiple pipelines."""
        mock_client.get_pipelines.return_value = [
            {
                "id": "pipeline-1",
                "functions": [{"id": "f1", "type": "mask"}]
            },
            {
                "id": "pipeline-2",
                "functions": [{"id": "f2", "type": "rename"}, {"id": "f3", "type": "drop"}]
            },
            {
                "id": "pipeline-3",
                "functions": []
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_pipelines"] == 3
        assert result.metadata["total_functions"] == 3

    @pytest.mark.asyncio
    async def test_performance_score_calculation(self, analyzer, mock_client):
        """Test pipeline performance score is calculated correctly."""
        mock_client.get_pipelines.return_value = [
            {"id": "p1", "functions": []},
            {"id": "p2", "functions": []},
            {"id": "p3", "functions": []}
        ]
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "p1": {"in": {"events": 1000}, "processing_time_ms": 100},  # 0.1ms - ok
                "p2": {"in": {"events": 1000}, "processing_time_ms": 6000},  # 6ms - slow
                "p3": {"in": {"events": 1000}, "processing_time_ms": 200}   # 0.2ms - ok
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["slow_pipelines"] == 1
        # Score should be less than 100 due to 1 slow pipeline
        assert result.metadata["pipeline_performance_score"] < 100

    @pytest.mark.asyncio
    async def test_analyze_very_long_regex(self, analyzer, mock_client):
        """Test analyzer flags very long regex patterns."""
        long_regex = "a" * 600  # Over 500 char threshold
        mock_client.get_pipelines.return_value = [
            {
                "id": "long-regex",
                "functions": [
                    {
                        "id": "regex-func",
                        "type": "regex_extract",
                        "conf": {"regex": long_regex}
                    }
                ]
            }
        ]
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata.get("regex_issues", 0) >= 1

        regex_findings = [f for f in result.findings if "regex" in f.id]
        assert len(regex_findings) >= 1
        assert "long" in str(regex_findings[0].metadata.get("issues", [])).lower()
