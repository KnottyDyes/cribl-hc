"""
Freshness Analyzer for Cribl Stream Health Check.

Analyzes event timestamps to detect pipeline lag and latency issues.
"""

import time
from typing import Any, List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.utils.logger import get_logger


class FreshnessAnalyzer(BaseAnalyzer):
    """
    Analyzer for monitoring data freshness and pipeline latency.

    Phase 8 - Runtime Health

    Checks:
    - Event Lag (difference between _time and now)
    - Future timestamps (clock skew detection)
    """

    # Thresholds in seconds
    LAG_WARNING_THRESHOLD = 60 * 5  # 5 minutes
    LAG_CRITICAL_THRESHOLD = 60 * 15  # 15 minutes
    FUTURE_THRESHOLD = 60 * 5  # 5 minutes in future

    def __init__(self):
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        return "freshness"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return "Detects pipeline lag and data freshness issues by analyzing event timestamps"

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:system", "execute:capture"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            # Capture events to check timestamps
            events = await client.capture_events(
                filter_expr="true", max_events=50, duration=5, level=1
            )

            result.metadata["events_scanned"] = len(events)

            if not events:
                self.log.info("no_events_captured_for_freshness")
                return result

            current_time = time.time()
            lags = []
            future_events = 0

            for event in events:
                # Cribl _time is usually a float timestamp
                event_time = event.get("_time")

                if event_time is None:
                    continue

                try:
                    event_time = float(event_time)
                except (ValueError, TypeError):
                    continue

                lag = current_time - event_time
                lags.append(lag)

                if lag < -self.FUTURE_THRESHOLD:
                    future_events += 1

            if not lags:
                return result

            avg_lag = sum(lags) / len(lags)
            max_lag = max(lags)

            result.metadata["avg_lag_seconds"] = round(avg_lag, 2)
            result.metadata["max_lag_seconds"] = round(max_lag, 2)

            # Check for high lag
            if max_lag > self.LAG_WARNING_THRESHOLD:
                severity = "critical" if max_lag > self.LAG_CRITICAL_THRESHOLD else "high"

                result.add_finding(
                    Finding(
                        id="freshness-high-lag",
                        title=f"High Data Latency Detected ({round(max_lag / 60)} min)",
                        description=f"Detected events with significant lag. Max lag: {round(max_lag / 60, 1)} minutes. "
                        f"Average lag: {round(avg_lag / 60, 1)} minutes.",
                        severity=severity,
                        category="runtime_health",
                        confidence_level="high",
                        affected_components=["pipeline:processing"],
                        estimated_impact="Delayed insights, SLA breaches, Alerting delays",
                        remediation_steps=[
                            "Check input sources for delay",
                            "Verify pipeline performance (backpressure)",
                            "Check worker resource utilization",
                        ],
                        metadata={
                            "max_lag_seconds": max_lag,
                            "avg_lag_seconds": avg_lag,
                            "threshold": self.LAG_WARNING_THRESHOLD,
                        },
                    )
                )

            # Check for future timestamps
            if future_events > 0:
                result.add_finding(
                    Finding(
                        id="freshness-future-timestamps",
                        title="Future Timestamps Detected",
                        description=f"Found {future_events} events with timestamps significantly in the future. "
                        f"This indicates clock skew or parsing issues.",
                        severity="medium",
                        category="data_quality",
                        confidence_level="high",
                        affected_components=["input:parsing"],
                        estimated_impact="Incorrect time-based analysis, Search ordering issues",
                        remediation_steps=[
                            "Check source system clocks",
                            "Verify Event Breaker / Timestamp parsing configuration",
                        ],
                        metadata={"future_event_count": future_events},
                    )
                )

            if max_lag <= self.LAG_WARNING_THRESHOLD and future_events == 0:
                result.add_finding(
                    Finding(
                        id="freshness-healthy",
                        title="Data Freshness Healthy",
                        description=f"All {len(events)} scanned events are within freshness thresholds. "
                        f"Max lag: {round(max_lag, 2)}s",
                        severity="info",
                        category="runtime_health",
                        confidence_level="high",
                        affected_components=["pipeline:processing"],
                        estimated_impact="None",
                        remediation_steps=[],
                        metadata={"max_lag_seconds": max_lag},
                    )
                )

        except Exception as e:
            self.log.error("freshness_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result
