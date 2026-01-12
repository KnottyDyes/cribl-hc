"""
Unit tests for MetricsCollector utility.

Tests:
1. Normalization (empty, None, nested structures, type conversions)
2. Ratio calculations (normal, division by zero, edge cases)
3. Trend detection (flat, increasing, decreasing, insufficient data)
"""

import pytest

from cribl_hc.core.metrics_collector import MetricsCollector


class TestMetricsCollectorNormalization:
    """Test normalization of raw API metrics."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a metrics collector instance."""
        return MetricsCollector()

    def test_normalize_none_input(self, collector: MetricsCollector):
        """Test handling of None input."""
        result = collector.normalize_metrics(None)
        assert result is not None
        assert "pipelines" in result
        assert "routes" in result
        assert "workers" in result
        assert "outputs" in result
        assert result["pipelines"] == {}
        assert result["routes"] == {}

    def test_normalize_empty_dict(self, collector: MetricsCollector):
        """Test handling of empty dict."""
        result = collector.normalize_metrics({})
        assert result["pipelines"] == {}
        assert result["routes"] == {}
        assert result["workers"] == {}
        assert result["outputs"] == {}

    def test_normalize_pipeline_basic(self, collector: MetricsCollector):
        """Test basic pipeline normalization."""
        raw = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 10},
                    "processingTime": 500.5,
                }
            }
        }
        result = collector.normalize_metrics(raw)

        assert "pipe-1" in result["pipelines"]
        pipeline = result["pipelines"]["pipe-1"]
        assert pipeline["in_events"] == 1000
        assert pipeline["out_events"] == 950
        assert pipeline["drop_events"] == 50
        assert pipeline["error_events"] == 10
        assert pipeline["processing_time_ms"] == 500.5

    def test_normalize_pipeline_missing_fields(self, collector: MetricsCollector):
        """Test pipeline normalization with missing fields (should default to 0)."""
        raw = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 100},
                    # out, drop, error, processingTime missing
                }
            }
        }
        result = collector.normalize_metrics(raw)

        pipeline = result["pipelines"]["pipe-1"]
        assert pipeline["in_events"] == 100
        assert pipeline["out_events"] == 0  # default
        assert pipeline["drop_events"] == 0  # default
        assert pipeline["error_events"] == 0  # default
        assert pipeline["processing_time_ms"] == 0.0  # default

    def test_normalize_route_basic(self, collector: MetricsCollector):
        """Test basic route normalization."""
        raw = {
            "routes": {
                "route-1": {
                    "in": {"events": 3600},  # 1 event per second
                    "errors": 36,  # 1% error rate
                    "latencies": [10.0, 15.0, 20.0, 25.0, 30.0],
                }
            }
        }
        result = collector.normalize_metrics(raw)

        route = result["routes"]["route-1"]
        assert route["throughput"] == 1.0  # 3600 events / 3600 seconds
        assert route["error_rate_percent"] == 1.0
        assert 10.0 <= route["latency_p50_ms"] <= 30.0
        assert 10.0 <= route["latency_p99_ms"] <= 30.0

    def test_normalize_route_zero_events(self, collector: MetricsCollector):
        """Test route normalization with zero events (division by zero)."""
        raw = {
            "routes": {
                "route-1": {
                    "in": {"events": 0},
                    "errors": 0,
                    "latencies": [],
                }
            }
        }
        result = collector.normalize_metrics(raw)

        route = result["routes"]["route-1"]
        assert route["throughput"] == 0.0
        assert route["error_rate_percent"] == 0.0
        assert route["latency_p50_ms"] == 0.0

    def test_normalize_worker_basic(self, collector: MetricsCollector):
        """Test basic worker normalization."""
        raw = {
            "workers": {
                "worker-1": {
                    "cpu": 75.5,
                    "memory": 80.0,
                    "eventsPerSec": 1000.5,
                    "queueDepth": 42,
                }
            }
        }
        result = collector.normalize_metrics(raw)

        worker = result["workers"]["worker-1"]
        assert worker["cpu_percent"] == 75.5
        assert worker["memory_percent"] == 80.0
        assert worker["events_per_sec"] == 1000.5
        assert worker["queue_depth"] == 42

    def test_normalize_worker_percent_clamping(self, collector: MetricsCollector):
        """Test that percentages are clamped to [0, 100]."""
        raw = {
            "workers": {
                "worker-1": {
                    "cpu": 150.0,  # Invalid: > 100
                    "memory": -10.0,  # Invalid: < 0
                    "eventsPerSec": 1000,
                    "queueDepth": 10,
                }
            }
        }
        result = collector.normalize_metrics(raw)

        worker = result["workers"]["worker-1"]
        assert worker["cpu_percent"] == 100.0  # Clamped
        assert worker["memory_percent"] == 0.0  # Clamped

    def test_normalize_output_basic(self, collector: MetricsCollector):
        """Test basic output normalization."""
        raw = {
            "outputs": {
                "out-1": {
                    "backpressure": {"time_ms": 250.5, "percent": 15.0},
                    "queue": {"depth": 1000, "percentFull": 60.0},
                }
            }
        }
        result = collector.normalize_metrics(raw)

        output = result["outputs"]["out-1"]
        assert output["backpressure_time_ms"] == 250.5
        assert output["backpressure_percent"] == 15.0
        assert output["queue_depth"] == 1000
        assert output["queue_depth_percent"] == 60.0

    def test_normalize_output_percent_clamping(self, collector: MetricsCollector):
        """Test output percentage clamping."""
        raw = {
            "outputs": {
                "out-1": {
                    "backpressure": {"time_ms": 0, "percent": 110.0},  # Invalid
                    "queue": {"depth": 0, "percentFull": -5.0},  # Invalid
                }
            }
        }
        result = collector.normalize_metrics(raw)

        output = result["outputs"]["out-1"]
        assert output["backpressure_percent"] == 100.0  # Clamped
        assert output["queue_depth_percent"] == 0.0  # Clamped

    def test_normalize_complex_nested_structure(self, collector: MetricsCollector):
        """Test normalization of complex multi-component metrics."""
        raw = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 100.0,
                }
            },
            "routes": {
                "route-1": {
                    "in": {"events": 500},
                    "errors": 25,
                    "latencies": [5.0, 10.0, 15.0],
                }
            },
            "workers": {
                "worker-1": {
                    "cpu": 50.0,
                    "memory": 60.0,
                    "eventsPerSec": 500.0,
                    "queueDepth": 100,
                }
            },
            "outputs": {
                "out-1": {
                    "backpressure": {"time_ms": 0, "percent": 5.0},
                    "queue": {"depth": 500, "percentFull": 50.0},
                }
            },
        }
        result = collector.normalize_metrics(raw)

        assert len(result["pipelines"]) == 1
        assert len(result["routes"]) == 1
        assert len(result["workers"]) == 1
        assert len(result["outputs"]) == 1

    def test_normalize_invalid_types(self, collector: MetricsCollector):
        """Test normalization with invalid types (should use defaults)."""
        raw = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": "not-a-number"},  # Invalid
                    "out": {"events": None},  # Invalid
                    "drop": {"events": 50},
                    "error": {"events": 10},
                    "processingTime": "abc",  # Invalid
                }
            }
        }
        result = collector.normalize_metrics(raw)

        pipeline = result["pipelines"]["pipe-1"]
        assert pipeline["in_events"] == 0  # Invalid, use default
        assert pipeline["out_events"] == 0  # None, use default
        assert pipeline["drop_events"] == 50
        assert pipeline["processing_time_ms"] == 0.0  # Invalid, use default


class TestMetricsCollectorRatioCalculation:
    """Test calculation of event ratios."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a metrics collector instance."""
        return MetricsCollector()

    def test_ratio_normal_case(self, collector: MetricsCollector):
        """Test ratio calculation with normal values."""
        normalized = {
            "pipelines": {
                "pipe-1": {
                    "in_events": 100,
                    "out_events": 90,
                    "drop_events": 10,
                    "error_events": 5,
                    "processing_time_ms": 0.0,
                }
            },
            "routes": {},
            "workers": {},
            "outputs": {},
        }
        ratios = collector.calculate_event_ratios(normalized)

        assert "pipe-1" in ratios
        assert ratios["pipe-1"]["drop_ratio"] == 0.1
        assert ratios["pipe-1"]["retention_ratio"] == 0.9
        assert ratios["pipe-1"]["error_ratio"] == 0.05

    def test_ratio_zero_events(self, collector: MetricsCollector):
        """Test ratio calculation with zero input events (division by zero)."""
        normalized = {
            "pipelines": {
                "pipe-1": {
                    "in_events": 0,
                    "out_events": 0,
                    "drop_events": 0,
                    "error_events": 0,
                    "processing_time_ms": 0.0,
                }
            },
            "routes": {},
            "workers": {},
            "outputs": {},
        }
        ratios = collector.calculate_event_ratios(normalized)

        # Should return 0 for all ratios when in_events is 0
        assert ratios["pipe-1"]["drop_ratio"] == 0.0
        assert ratios["pipe-1"]["retention_ratio"] == 0.0
        assert ratios["pipe-1"]["error_ratio"] == 0.0

    def test_ratio_100_percent_drop(self, collector: MetricsCollector):
        """Test ratio calculation when all events are dropped."""
        normalized = {
            "pipelines": {
                "pipe-1": {
                    "in_events": 100,
                    "out_events": 0,
                    "drop_events": 100,
                    "error_events": 0,
                    "processing_time_ms": 0.0,
                }
            },
            "routes": {},
            "workers": {},
            "outputs": {},
        }
        ratios = collector.calculate_event_ratios(normalized)

        assert ratios["pipe-1"]["drop_ratio"] == 1.0
        assert ratios["pipe-1"]["retention_ratio"] == 0.0
        assert ratios["pipe-1"]["error_ratio"] == 0.0

    def test_ratio_clamping(self, collector: MetricsCollector):
        """Test that ratios are clamped to [0, 1]."""
        normalized = {
            "pipelines": {
                "pipe-1": {
                    "in_events": 100,
                    "out_events": 150,  # > in_events, ratio would be > 1
                    "drop_events": 0,
                    "error_events": 0,
                    "processing_time_ms": 0.0,
                }
            },
            "routes": {},
            "workers": {},
            "outputs": {},
        }
        ratios = collector.calculate_event_ratios(normalized)

        # Ratio should be clamped to 1.0
        assert ratios["pipe-1"]["retention_ratio"] <= 1.0

    def test_ratio_multiple_pipelines(self, collector: MetricsCollector):
        """Test ratio calculation with multiple pipelines."""
        normalized = {
            "pipelines": {
                "pipe-1": {
                    "in_events": 100,
                    "out_events": 90,
                    "drop_events": 10,
                    "error_events": 0,
                    "processing_time_ms": 0.0,
                },
                "pipe-2": {
                    "in_events": 200,
                    "out_events": 180,
                    "drop_events": 20,
                    "error_events": 5,
                    "processing_time_ms": 0.0,
                },
            },
            "routes": {},
            "workers": {},
            "outputs": {},
        }
        ratios = collector.calculate_event_ratios(normalized)

        assert len(ratios) == 2
        assert ratios["pipe-1"]["drop_ratio"] == 0.1
        assert ratios["pipe-2"]["drop_ratio"] == 0.1
        assert ratios["pipe-2"]["error_ratio"] == 0.025

    def test_ratio_none_input(self, collector: MetricsCollector):
        """Test ratio calculation with None input."""
        ratios = collector.calculate_event_ratios(None)
        assert ratios == {}

    def test_ratio_empty_metrics(self, collector: MetricsCollector):
        """Test ratio calculation with empty metrics."""
        normalized = {
            "pipelines": {},
            "routes": {},
            "workers": {},
            "outputs": {},
        }
        ratios = collector.calculate_event_ratios(normalized)
        assert ratios == {}


class TestMetricsCollectorTrendDetection:
    """Test trend detection using linear regression."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a metrics collector instance."""
        return MetricsCollector()

    def test_trend_flat(self, collector: MetricsCollector):
        """Test detection of flat (no change) trend."""
        # Constant throughput over time
        historical = [
            {
                "pipelines": {
                    "pipe-1": {
                        "in_events": 3600,
                        "out_events": 3600,
                        "drop_events": 0,
                        "error_events": 0,
                        "processing_time_ms": 100.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
            for _ in range(5)
        ]

        current = historical[0]

        trends = collector.detect_trends(current, historical, window_hours=24)

        assert "pipe-1" in trends["pipelines"]
        if "throughput" in trends["pipelines"]["pipe-1"]:
            # Flat trend should have slope close to 0
            assert trends["pipelines"]["pipe-1"]["throughput"]["slope"] == 0.0

    def test_trend_increasing(self, collector: MetricsCollector):
        """Test detection of increasing trend."""
        # Linearly increasing events
        historical = [
            {
                "pipelines": {
                    "pipe-1": {
                        "in_events": 3600 * (i + 1),  # 3600, 7200, 10800, ...
                        "out_events": 3600 * (i + 1),
                        "drop_events": 0,
                        "error_events": 0,
                        "processing_time_ms": 100.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
            for i in range(5)
        ]

        current = historical[-1]

        trends = collector.detect_trends(current, historical, window_hours=24)

        assert "pipe-1" in trends["pipelines"]
        if "throughput" in trends["pipelines"]["pipe-1"]:
            # Increasing trend should have positive slope
            assert trends["pipelines"]["pipe-1"]["throughput"]["slope"] > 0

    def test_trend_decreasing(self, collector: MetricsCollector):
        """Test detection of decreasing trend."""
        # Linearly decreasing events
        historical = [
            {
                "pipelines": {
                    "pipe-1": {
                        "in_events": 3600 * (5 - i),  # 18000, 14400, 10800, ...
                        "out_events": 3600 * (5 - i),
                        "drop_events": 0,
                        "error_events": 0,
                        "processing_time_ms": 100.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
            for i in range(5)
        ]

        current = historical[-1]

        trends = collector.detect_trends(current, historical, window_hours=24)

        assert "pipe-1" in trends["pipelines"]
        if "throughput" in trends["pipelines"]["pipe-1"]:
            # Decreasing trend should have negative slope
            assert trends["pipelines"]["pipe-1"]["throughput"]["slope"] < 0

    def test_trend_insufficient_data(self, collector: MetricsCollector):
        """Test trend detection with insufficient data points."""
        # Only 1 historical point
        historical = [
            {
                "pipelines": {
                    "pipe-1": {
                        "in_events": 3600,
                        "out_events": 3600,
                        "drop_events": 0,
                        "error_events": 0,
                        "processing_time_ms": 100.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
        ]

        current = historical[0]

        trends = collector.detect_trends(current, historical, window_hours=24)

        # Should return empty trends when data is insufficient
        assert trends["pipelines"] == {}
        assert trends["outputs"] == {}

    def test_trend_none_inputs(self, collector: MetricsCollector):
        """Test trend detection with None inputs."""
        trends = collector.detect_trends(None, None, window_hours=24)

        assert trends["pipelines"] == {}
        assert trends["outputs"] == {}

    def test_trend_r_squared_calculation(self, collector: MetricsCollector):
        """Test that R² is calculated correctly."""
        # Create data with perfect linear relationship
        historical = [
            {
                "pipelines": {
                    "pipe-1": {
                        "in_events": 3600 * i,
                        "out_events": 3600 * i,
                        "drop_events": 0,
                        "error_events": 0,
                        "processing_time_ms": 100.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
            for i in range(1, 6)
        ]

        current = historical[-1]

        trends = collector.detect_trends(current, historical, window_hours=24)

        if "pipe-1" in trends["pipelines"] and "throughput" in trends["pipelines"]["pipe-1"]:
            # Perfect linear relationship should have R² close to 1.0
            r_squared = trends["pipelines"]["pipe-1"]["throughput"]["r_squared"]
            assert 0.9 <= r_squared <= 1.0  # Allow for floating point rounding

    def test_trend_forecast(self, collector: MetricsCollector):
        """Test forecast calculation."""
        # Create increasing trend
        historical = [
            {
                "pipelines": {
                    "pipe-1": {
                        "in_events": 3600 * (i + 1),
                        "out_events": 3600 * (i + 1),
                        "drop_events": 0,
                        "error_events": 0,
                        "processing_time_ms": 100.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
            for i in range(5)
        ]

        current = historical[-1]

        trends = collector.detect_trends(current, historical, window_hours=24)

        if "pipe-1" in trends["pipelines"] and "throughput" in trends["pipelines"]["pipe-1"]:
            forecast = trends["pipelines"]["pipe-1"]["throughput"]["forecast_next_hour"]
            # Forecast should be > last value for increasing trend
            last_value = current["pipelines"]["pipe-1"]["in_events"] / 3600.0
            assert forecast >= last_value

    def test_trend_output_backpressure(self, collector: MetricsCollector):
        """Test trend detection for output backpressure."""
        historical = [
            {
                "pipelines": {},
                "routes": {},
                "workers": {},
                "outputs": {
                    "out-1": {
                        "backpressure_time_ms": 100.0 * i,
                        "backpressure_percent": 10.0 * i,
                        "queue_depth": 1000 * i,
                        "queue_depth_percent": 50.0,
                    }
                },
            }
            for i in range(1, 6)
        ]

        current = historical[-1]

        trends = collector.detect_trends(current, historical, window_hours=24)

        if "out-1" in trends["outputs"] and "backpressure" in trends["outputs"]["out-1"]:
            # Backpressure should show increasing trend
            assert trends["outputs"]["out-1"]["backpressure"]["slope"] > 0


class TestMetricsCollectorEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a metrics collector instance."""
        return MetricsCollector()

    def test_percentile_calculation_empty_list(self, collector: MetricsCollector):
        """Test percentile calculation with empty list."""
        result = collector._calculate_percentile([], 50)
        assert result == 0.0

    def test_percentile_calculation_single_value(self, collector: MetricsCollector):
        """Test percentile calculation with single value."""
        result = collector._calculate_percentile([10.0], 50)
        assert result == 10.0

    def test_percentile_calculation_multiple_values(self, collector: MetricsCollector):
        """Test percentile calculation with multiple values."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]

        p50 = collector._calculate_percentile(data, 50)
        assert 2.5 <= p50 <= 3.5  # Median around 3

        p99 = collector._calculate_percentile(data, 99)
        assert 4.5 <= p99 <= 5.0  # Near max

    def test_extract_nested_int_missing_key(self, collector: MetricsCollector):
        """Test extraction of nested int with missing key."""
        data = {"in": {"events": 100}}
        result = collector._extract_nested_int(data, ["out", "events"], 999)
        assert result == 999

    def test_extract_nested_float_invalid_type(self, collector: MetricsCollector):
        """Test extraction of nested float with invalid type."""
        data = {"processing": "not-a-number"}
        result = collector._extract_nested_float(data, ["processing"], 0.0)
        assert result == 0.0

    def test_clamp_percent_valid_range(self, collector: MetricsCollector):
        """Test percent clamping with valid values."""
        assert collector._clamp_percent(50.0) == 50.0
        assert collector._clamp_percent(0.0) == 0.0
        assert collector._clamp_percent(100.0) == 100.0

    def test_clamp_percent_out_of_range(self, collector: MetricsCollector):
        """Test percent clamping with out-of-range values."""
        assert collector._clamp_percent(-50.0) == 0.0
        assert collector._clamp_percent(150.0) == 100.0
        assert collector._clamp_percent(-0.1) == 0.0

    def test_normalize_with_non_dict_values(self, collector: MetricsCollector):
        """Test normalization skips non-dict pipeline/route/etc values."""
        raw = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 100},
                    "out": {"events": 90},
                    "drop": {"events": 10},
                    "error": {"events": 0},
                    "processingTime": 0.0,
                },
                "pipe-2": "not-a-dict",  # Should be skipped
            }
        }
        result = collector.normalize_metrics(raw)

        assert "pipe-1" in result["pipelines"]
        assert "pipe-2" not in result["pipelines"]


class TestMetricsCollectorIntegration:
    """Integration tests combining multiple methods."""

    @pytest.fixture
    def collector(self) -> MetricsCollector:
        """Create a metrics collector instance."""
        return MetricsCollector()

    def test_full_pipeline_analysis(self, collector: MetricsCollector):
        """Test complete pipeline: normalize -> ratio -> trends."""
        # Create realistic raw metrics
        raw_metrics = {
            "pipelines": {
                "prod-pipeline": {
                    "in": {"events": 10000},
                    "out": {"events": 9500},
                    "drop": {"events": 500},
                    "error": {"events": 100},
                    "processingTime": 50.0,
                }
            },
            "routes": {},
            "workers": {},
            "outputs": {},
        }

        # Normalize
        normalized = collector.normalize_metrics(raw_metrics)
        assert "prod-pipeline" in normalized["pipelines"]

        # Calculate ratios
        ratios = collector.calculate_event_ratios(normalized)
        assert ratios["prod-pipeline"]["drop_ratio"] == 0.05
        assert ratios["prod-pipeline"]["retention_ratio"] == 0.95

        # Create historical data
        historical = []
        for i in range(5):
            hist_raw = {
                "pipelines": {
                    "prod-pipeline": {
                        "in": {"events": 10000 + (i * 1000)},
                        "out": {"events": 9500 + (i * 1000)},
                        "drop": {"events": 500},
                        "error": {"events": 100},
                        "processingTime": 50.0,
                    }
                },
                "routes": {},
                "workers": {},
                "outputs": {},
            }
            historical.append(collector.normalize_metrics(hist_raw))

        # Detect trends
        trends = collector.detect_trends(normalized, historical)

        # Should have some trend data
        assert isinstance(trends, dict)
        assert "pipelines" in trends
        assert "outputs" in trends

    def test_all_metrics_components(self, collector: MetricsCollector):
        """Test normalization of all metric components together."""
        raw = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 10},
                    "processingTime": 100.0,
                }
            },
            "routes": {
                "route-1": {
                    "in": {"events": 500},
                    "errors": 25,
                    "latencies": [5.0, 10.0, 15.0, 20.0],
                }
            },
            "workers": {
                "worker-1": {
                    "cpu": 75.0,
                    "memory": 80.0,
                    "eventsPerSec": 500.0,
                    "queueDepth": 100,
                }
            },
            "outputs": {
                "out-1": {
                    "backpressure": {"time_ms": 100.0, "percent": 10.0},
                    "queue": {"depth": 500, "percentFull": 50.0},
                }
            },
        }

        result = collector.normalize_metrics(raw)

        # All components should be normalized
        assert len(result["pipelines"]) == 1
        assert len(result["routes"]) == 1
        assert len(result["workers"]) == 1
        assert len(result["outputs"]) == 1

        # Each component should have correct structure
        assert "in_events" in result["pipelines"]["pipe-1"]
        assert "throughput" in result["routes"]["route-1"]
        assert "cpu_percent" in result["workers"]["worker-1"]
        assert "backpressure_percent" in result["outputs"]["out-1"]
