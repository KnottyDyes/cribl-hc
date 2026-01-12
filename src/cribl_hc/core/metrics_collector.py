"""
Metrics Collector utility for Cribl Health Check.

Provides normalization, enrichment, and trend analysis of metrics from Cribl API.
Handles:
- Raw metrics normalization to standard format
- Event ratio calculations (in/out/drop/error)
- Trend detection using linear regression
- Edge case handling (division by zero, missing data, insufficient historical data)

Priority: P2 (Medium Impact - Metrics Processing Infrastructure)
"""

from typing import Any, Optional

from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class MetricsCollector:
    """
    Normalize and enrich metrics from Cribl API.

    Converts raw API responses into standardized metric structures,
    calculates derived metrics like ratios and trends, and provides
    actionable insights for health analysis.

    Example:
        >>> collector = MetricsCollector()
        >>> raw = {
        ...     "pipelines": {
        ...         "my-pipeline": {
        ...             "in": 1000,
        ...             "out": 950,
        ...             "drop": 50,
        ...             "error": 10,
        ...             "processingTime": 500.5
        ...         }
        ...     }
        ... }
        >>> normalized = collector.normalize_metrics(raw)
        >>> ratios = collector.calculate_event_ratios(normalized)
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.log = get_logger(self.__class__.__name__)

    def normalize_metrics(self, raw_metrics: Optional[dict[str, Any]]) -> dict[str, Any]:
        """
        Convert raw API metrics to standard format.

        Handles nested dict structures, extracts metric values with fallback defaults,
        converts % values to 0-100 range, and returns empty dict structure if input
        is None/empty.

        Args:
            raw_metrics: Raw metrics dict from Cribl API (may be None or empty)

        Returns:
            Normalized metrics with structure:
            {
                'pipelines': {
                    'pipeline-id': {
                        'in_events': int,
                        'out_events': int,
                        'drop_events': int,
                        'error_events': int,
                        'processing_time_ms': float,
                    }
                },
                'routes': {
                    'route-id': {
                        'throughput': float,  # events/sec
                        'latency_p50_ms': float,
                        'latency_p99_ms': float,
                        'error_rate_percent': float,
                    }
                },
                'workers': {
                    'worker-id': {
                        'cpu_percent': float,
                        'memory_percent': float,
                        'events_per_sec': float,
                        'queue_depth': int,
                    }
                },
                'outputs': {
                    'output-id': {
                        'backpressure_time_ms': float,
                        'backpressure_percent': float,
                        'queue_depth': int,
                        'queue_depth_percent': float,
                    }
                }
            }

        Example:
            >>> collector = MetricsCollector()
            >>> result = collector.normalize_metrics(None)
            >>> result['pipelines']
            {}
            >>> result = collector.normalize_metrics({
            ...     "pipelines": {
            ...         "pipe1": {
            ...             "in": {"events": 1000},
            ...             "out": {"events": 950},
            ...             "drop": {"events": 50},
            ...             "error": {"events": 10},
            ...             "processingTime": 500.5
            ...         }
            ...     }
            ... })
            >>> result['pipelines']['pipe1']['in_events']
            1000
        """
        # Return empty structure if input is None/empty
        if not raw_metrics:
            return {
                "pipelines": {},
                "routes": {},
                "workers": {},
                "outputs": {},
            }

        normalized = {
            "pipelines": self._normalize_pipelines(raw_metrics),
            "routes": self._normalize_routes(raw_metrics),
            "workers": self._normalize_workers(raw_metrics),
            "outputs": self._normalize_outputs(raw_metrics),
        }

        return normalized

    def _normalize_pipelines(self, raw_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract and normalize pipeline metrics.

        Handles various metric structure formats from different Cribl API versions.
        Extracts: in_events, out_events, drop_events, error_events, processing_time_ms
        """
        pipelines = {}
        pipelines_data = raw_metrics.get("pipelines", {})

        for pipeline_id, data in pipelines_data.items():
            if not isinstance(data, dict):
                continue

            pipelines[pipeline_id] = {
                "in_events": self._extract_nested_int(data, ["in", "events"], 0),
                "out_events": self._extract_nested_int(data, ["out", "events"], 0),
                "drop_events": self._extract_nested_int(data, ["drop", "events"], 0),
                "error_events": self._extract_nested_int(data, ["error", "events"], 0),
                "processing_time_ms": self._extract_nested_float(data, ["processingTime"], 0.0),
            }

        return pipelines

    def _normalize_routes(self, raw_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract and normalize route metrics.

        Extracts: throughput (events/sec), latency percentiles, error_rate_percent
        """
        routes = {}
        routes_data = raw_metrics.get("routes", {})

        for route_id, data in routes_data.items():
            if not isinstance(data, dict):
                continue

            # Calculate throughput (events per second)
            events_in = self._extract_nested_int(data, ["in", "events"], 0)
            throughput = events_in / 3600.0  # Assuming hourly metrics window

            # Extract latencies (may be in various formats)
            latencies = data.get("latencies", [])
            latency_p50 = self._calculate_percentile(latencies, 50)
            latency_p99 = self._calculate_percentile(latencies, 99)

            # Calculate error rate
            errors = self._extract_nested_int(data, ["errors"], 0)
            error_rate = (errors / events_in * 100) if events_in > 0 else 0.0

            routes[route_id] = {
                "throughput": throughput,
                "latency_p50_ms": latency_p50,
                "latency_p99_ms": latency_p99,
                "error_rate_percent": min(100.0, error_rate),  # Clamp to 0-100
            }

        return routes

    def _normalize_workers(self, raw_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract and normalize worker metrics.

        Extracts: cpu_percent, memory_percent, events_per_sec, queue_depth
        """
        workers = {}
        workers_data = raw_metrics.get("workers", {})

        for worker_id, data in workers_data.items():
            if not isinstance(data, dict):
                continue

            workers[worker_id] = {
                "cpu_percent": self._clamp_percent(self._extract_nested_float(data, ["cpu"], 0.0)),
                "memory_percent": self._clamp_percent(
                    self._extract_nested_float(data, ["memory"], 0.0)
                ),
                "events_per_sec": self._extract_nested_float(data, ["eventsPerSec"], 0.0),
                "queue_depth": self._extract_nested_int(data, ["queueDepth"], 0),
            }

        return workers

    def _normalize_outputs(self, raw_metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract and normalize output/destination metrics.

        Extracts: backpressure_time_ms, backpressure_percent, queue_depth, queue_depth_percent
        """
        outputs = {}
        outputs_data = raw_metrics.get("outputs", {})

        for output_id, data in outputs_data.items():
            if not isinstance(data, dict):
                continue

            outputs[output_id] = {
                "backpressure_time_ms": self._extract_nested_float(
                    data, ["backpressure", "time_ms"], 0.0
                ),
                "backpressure_percent": self._clamp_percent(
                    self._extract_nested_float(data, ["backpressure", "percent"], 0.0)
                ),
                "queue_depth": self._extract_nested_int(data, ["queue", "depth"], 0),
                "queue_depth_percent": self._clamp_percent(
                    self._extract_nested_float(data, ["queue", "percentFull"], 0.0)
                ),
            }

        return outputs

    def _extract_nested_int(self, data: dict[str, Any], path: list[str], default: int = 0) -> int:
        """
        Safely extract nested integer value from dict.

        Args:
            data: Dict to extract from
            path: List of keys to follow (e.g., ["in", "events"])
            default: Value to return if path not found

        Returns:
            Extracted int value or default
        """
        try:
            current: Any = data
            for key in path:
                if isinstance(current, dict):
                    next_val: Any = current.get(key)
                    if next_val is None:
                        return default
                    current = next_val
                else:
                    return default

            if current is None:
                return default
            result: int = int(current)
            return result
        except (ValueError, TypeError):
            return default

    def _extract_nested_float(
        self, data: dict[str, Any], path: list[str], default: float = 0.0
    ) -> float:
        """
        Safely extract nested float value from dict.

        Args:
            data: Dict to extract from
            path: List of keys to follow
            default: Value to return if path not found

        Returns:
            Extracted float value or default
        """
        try:
            current: Any = data
            for key in path:
                if isinstance(current, dict):
                    next_val: Any = current.get(key)
                    if next_val is None:
                        return default
                    current = next_val
                else:
                    return default

            if current is None:
                return default
            result: float = float(current)
            return result
        except (ValueError, TypeError):
            return default

    def _calculate_percentile(self, data: list[float], percentile: float) -> float:
        """
        Calculate percentile from a list of values.

        Args:
            data: List of float values
            percentile: Percentile to calculate (0-100)

        Returns:
            Calculated percentile value, or 0 if no data
        """
        if not data or not isinstance(data, list):
            return 0.0

        try:
            sorted_data = sorted(data)
            if not sorted_data:
                return 0.0

            # Linear interpolation method
            index = (percentile / 100.0) * (len(sorted_data) - 1)
            lower_index = int(index)
            upper_index = min(lower_index + 1, len(sorted_data) - 1)
            fraction = index - lower_index

            lower_value = sorted_data[lower_index]
            upper_value = sorted_data[upper_index]

            return lower_value + fraction * (upper_value - lower_value)
        except (ValueError, TypeError, IndexError):
            return 0.0

    def _clamp_percent(self, value: float) -> float:
        """
        Clamp percentage value to [0, 100] range.

        Args:
            value: Percentage value

        Returns:
            Value clamped to [0, 100]
        """
        return max(0.0, min(100.0, value))

    def calculate_event_ratios(self, metrics: Optional[dict[str, Any]]) -> dict[str, dict[str, float]]:
        """
        Calculate in/out/drop/error ratios per pipeline.

        Handles division by zero by returning 0 if in_events=0.
        Clamps ratios to [0, 1] range.

        Args:
            metrics: Normalized metrics dict (output from normalize_metrics)

        Returns:
            Dict keyed by pipeline ID with ratios:
            {
                'pipeline-id': {
                    'drop_ratio': float,  # drop_events / in_events
                    'retention_ratio': float,  # out_events / in_events
                    'error_ratio': float,  # error_events / in_events
                }
            }

        Example:
            >>> collector = MetricsCollector()
            >>> normalized = collector.normalize_metrics({
            ...     "pipelines": {
            ...         "pipe1": {
            ...             "in": {"events": 100},
            ...             "out": {"events": 90},
            ...             "drop": {"events": 10},
            ...             "error": {"events": 5}
            ...         }
            ...     }
            ... })
            >>> ratios = collector.calculate_event_ratios(normalized)
            >>> ratios['pipe1']['drop_ratio']
            0.1
            >>> ratios['pipe1']['retention_ratio']
            0.9
        """
        if not metrics:
            return {}

        ratios = {}
        pipelines = metrics.get("pipelines", {})

        for pipeline_id, data in pipelines.items():
            in_events = data.get("in_events", 0)

            # Handle division by zero: return 0 if no input events
            if in_events == 0:
                ratios[pipeline_id] = {
                    "drop_ratio": 0.0,
                    "retention_ratio": 0.0,
                    "error_ratio": 0.0,
                }
                continue

            # Calculate ratios
            drop_events = data.get("drop_events", 0)
            out_events = data.get("out_events", 0)
            error_events = data.get("error_events", 0)

            # Formula: ratio = events / in_events
            drop_ratio = drop_events / in_events
            retention_ratio = out_events / in_events
            error_ratio = error_events / in_events

            # Clamp ratios to [0, 1]
            ratios[pipeline_id] = {
                "drop_ratio": max(0.0, min(1.0, drop_ratio)),
                "retention_ratio": max(0.0, min(1.0, retention_ratio)),
                "error_ratio": max(0.0, min(1.0, error_ratio)),
            }

        return ratios

    def detect_trends(
        self,
        current: Optional[dict[str, Any]],
        historical: Optional[list[dict[str, Any]]],
        window_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Detect trends in metrics over time using linear regression.

        Uses simple linear regression (polyfit) to detect trends in:
        - Pipeline throughput and error rates
        - Output backpressure and failure rates

        Handles edge cases:
        - Insufficient data points (< 2): returns empty trend
        - Constant values: R² = 0, slope = 0
        - NaN values: skipped in calculation

        Args:
            current: Current normalized metrics dict
            historical: List of historical normalized metrics dicts (in chronological order)
            window_hours: Analysis window in hours (default 24)

        Returns:
            Dict with trend analysis:
            {
                'pipelines': {
                    'pipeline-id': {
                        'throughput': {
                            'slope': float,  # events/sec/hour
                            'r_squared': float,  # goodness of fit (0-1)
                            'forecast_next_hour': float  # predicted value
                        },
                        'error_rate': {...}
                        'drop_rate': {...}
                    }
                },
                'outputs': {
                    'output-id': {
                        'backpressure': {...},
                        'failure_rate': {...}
                    }
                }
            }

        Example:
            >>> collector = MetricsCollector()
            >>> current = collector.normalize_metrics(current_raw)
            >>> historical_normalized = [
            ...     collector.normalize_metrics(h) for h in historical_raw
            ... ]
            >>> trends = collector.detect_trends(current, historical_normalized)
            >>> if trends['pipelines'].get('pipe1'):
            ...     slope = trends['pipelines']['pipe1']['throughput']['slope']
            ...     print(f"Throughput increasing: {slope > 0}")
        """
        if not current or not historical:
            return {
                "pipelines": {},
                "outputs": {},
            }

        # Ensure we have at least 2 points for regression
        if len(historical) < 2:
            return {
                "pipelines": {},
                "outputs": {},
            }

        trends = {
            "pipelines": self._detect_pipeline_trends(current, historical, window_hours),
            "outputs": self._detect_output_trends(current, historical, window_hours),
        }

        return trends

    def _detect_pipeline_trends(
        self, current: dict[str, Any], historical: list[dict[str, Any]], window_hours: int
    ) -> dict[str, dict[str, Any]]:
        """
        Detect trends for pipelines.

        Tracks: throughput, error_rate, drop_rate
        """
        trends = {}
        current_pipelines = current.get("pipelines", {})

        for pipeline_id in current_pipelines.keys():
            # Collect historical throughput values
            throughputs = []
            error_rates = []
            drop_rates = []

            for hist_metrics in historical:
                hist_pipelines = hist_metrics.get("pipelines", {})
                if pipeline_id not in hist_pipelines:
                    continue

                hist_data = hist_pipelines[pipeline_id]
                in_events = hist_data.get("in_events", 0)

                # Throughput
                throughput = in_events / 3600.0  # events/sec
                if throughput > 0:
                    throughputs.append(throughput)

                # Error rate
                if in_events > 0:
                    error_events = hist_data.get("error_events", 0)
                    error_rate = (error_events / in_events) * 100
                    error_rates.append(error_rate)

                # Drop rate
                if in_events > 0:
                    drop_events = hist_data.get("drop_events", 0)
                    drop_rate = (drop_events / in_events) * 100
                    drop_rates.append(drop_rate)

            # Calculate trends for each metric
            pipeline_trends = {}

            if throughputs and len(throughputs) >= 2:
                pipeline_trends["throughput"] = self._calculate_trend(throughputs)
            if error_rates and len(error_rates) >= 2:
                pipeline_trends["error_rate"] = self._calculate_trend(error_rates)
            if drop_rates and len(drop_rates) >= 2:
                pipeline_trends["drop_rate"] = self._calculate_trend(drop_rates)

            if pipeline_trends:
                trends[pipeline_id] = pipeline_trends

        return trends

    def _detect_output_trends(
        self, current: dict[str, Any], historical: list[dict[str, Any]], window_hours: int
    ) -> dict[str, dict[str, Any]]:
        """
        Detect trends for outputs.

        Tracks: backpressure, failure_rate
        """
        trends = {}
        current_outputs = current.get("outputs", {})

        for output_id in current_outputs.keys():
            backpressures = []
            failure_rates = []

            for hist_metrics in historical:
                hist_outputs = hist_metrics.get("outputs", {})
                if output_id not in hist_outputs:
                    continue

                hist_data = hist_outputs[output_id]

                # Backpressure percent
                bp = hist_data.get("backpressure_percent", 0.0)
                if bp >= 0:
                    backpressures.append(bp)

                # Failure rate (queue depth as proxy)
                queue_depth = hist_data.get("queue_depth", 0)
                if queue_depth >= 0:
                    failure_rates.append(float(queue_depth))

            # Calculate trends
            output_trends = {}

            if backpressures and len(backpressures) >= 2:
                output_trends["backpressure"] = self._calculate_trend(backpressures)
            if failure_rates and len(failure_rates) >= 2:
                output_trends["failure_rate"] = self._calculate_trend(failure_rates)

            if output_trends:
                trends[output_id] = output_trends

        return trends

    def _calculate_trend(self, values: list[float]) -> dict[str, float]:
        """
        Calculate trend using simple linear regression.

        Returns dict with:
        - slope: change per unit time
        - r_squared: goodness of fit (0-1)
        - forecast_next_hour: predicted value at next time point

        Args:
            values: List of values in chronological order

        Returns:
            Dict with slope, r_squared, forecast_next_hour
        """
        if not values or len(values) < 2:
            return {"slope": 0.0, "r_squared": 0.0, "forecast_next_hour": 0.0}

        # Filter out NaN values
        valid_values = [v for v in values if v == v]  # NaN check: v != v is True for NaN

        if len(valid_values) < 2:
            return {"slope": 0.0, "r_squared": 0.0, "forecast_next_hour": 0.0}

        try:
            # Create x values (0, 1, 2, ...)
            x = list(range(len(valid_values)))
            y = valid_values

            # Calculate slope and intercept using least squares
            n = len(x)
            mean_x = sum(x) / n
            mean_y = sum(y) / n

            numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
            denominator = sum((x[i] - mean_x) ** 2 for i in range(n))

            if denominator == 0:
                # Constant values
                return {
                    "slope": 0.0,
                    "r_squared": 0.0,
                    "forecast_next_hour": mean_y,
                }

            slope = numerator / denominator
            intercept = mean_y - slope * mean_x

            # Calculate R²
            ss_res = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
            ss_tot = sum((y[i] - mean_y) ** 2 for i in range(n))

            if ss_tot == 0:
                r_squared = 0.0
            else:
                r_squared = max(0.0, min(1.0, 1 - (ss_res / ss_tot)))

            # Forecast next hour (at x = n)
            forecast = slope * n + intercept

            return {
                "slope": round(slope, 4),
                "r_squared": round(r_squared, 4),
                "forecast_next_hour": round(max(0.0, forecast), 4),
            }

        except (ValueError, ZeroDivisionError):
            return {"slope": 0.0, "r_squared": 0.0, "forecast_next_hour": 0.0}
