"""
Analyzes the balance of load and resource utilization across worker groups.
"""

from typing import Any, Dict, List, Optional

import numpy as np
from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from pydantic import BaseModel, Field


class WorkerMetrics(BaseModel):
    """Represents metrics for a single worker node."""

    node_id: str = Field(..., alias="id")
    cpu_util_pct: Optional[float] = Field(None, alias="cpu.usage")
    mem_util_pct: Optional[float] = Field(None, alias="mem.usage")
    events_in_per_sec: Optional[float] = Field(None, alias="total.in")
    historical_cpu: List[float] = Field(default_factory=list)
    historical_mem: List[float] = Field(default_factory=list)


class WorkerGroupMetrics(BaseModel):
    """Represents metrics for an entire worker group."""

    group_id: str
    workers: List[WorkerMetrics] = Field(default_factory=list)


class WorkerGroupBalanceAnalyzer(BaseAnalyzer):
    """
    Analyzes load distribution and resource utilization across workers in a group.
    """

    @property
    def objective_name(self) -> str:
        return "worker-group-balance"

    def get_description(self) -> str:
        return "Analyzes load balance and resource utilization variance across workers."

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis on worker group balance.
        """
        result = self.create_result()
        try:
            # Fetches system-wide metrics. We assume this contains node data.
            # The API client does not currently support time ranges for historical data.
            system_metrics = await client.get_metrics()
            worker_groups = self._parse_worker_groups(system_metrics)

            if not any(wg.workers for wg in worker_groups):
                result.add_finding(
                    self.create_finding(
                        id="no-worker-metrics-found",
                        category="Configuration",
                        severity="info",
                        title="No Worker Metrics Found",
                        description="No worker group metrics were available for analysis.",
                    )
                )
                return result

            for group in worker_groups:
                if len(group.workers) < 2:
                    continue  # Balance analysis requires at least 2 workers

                self._check_load_distribution(result, group)
                self._check_utilization_variance(result, group)
                self._check_capacity_exhaustion(result, group)

        except Exception as e:
            self.log.error(f"Error during worker group balance analysis: {e}", exc_info=True)
            result.success = False
            result.error = str(e)

        return result

    def _parse_worker_groups(self, metrics: Dict[str, Any]) -> List[WorkerGroupMetrics]:
        """Parses raw API metrics into structured WorkerGroupMetrics."""
        groups: Dict[str, WorkerGroupMetrics] = {}
        # Based on observed metrics structure, worker data is under the 'workers' key
        nodes_metrics = metrics.get("workers", [])
        if not nodes_metrics:
            return []

        for node_data in nodes_metrics:
            group_id = node_data.get("group", "default")
            if group_id not in groups:
                groups[group_id] = WorkerGroupMetrics(group_id=group_id)
            try:
                # The get_metrics call doesn't provide historical data, so we'll pass empty lists.
                # Capacity exhaustion check will be skipped if history is empty.
                worker = WorkerMetrics.model_validate(
                    {
                        "id": node_data.get("id"),
                        **node_data,  # Metrics are at the top level of each worker object
                        "historical_cpu": node_data.get("historical_cpu", []),  # Placeholder
                        "historical_mem": node_data.get("historical_mem", []),  # Placeholder
                    },
                    strict=False,
                )
                groups[group_id].workers.append(worker)
            except Exception:
                self.log.warning(f"Skipping node with malformed metrics: {node_data.get('id')}")
        return list(groups.values())

    def _check_load_distribution(self, result: AnalyzerResult, group: WorkerGroupMetrics):
        """Analyzes event load distribution using the Gini coefficient."""
        events_in = np.array(
            [w.events_in_per_sec for w in group.workers if w.events_in_per_sec is not None]
        )
        if len(events_in) < 2 or np.sum(events_in) == 0:
            return

        gini_coeff = self._calculate_gini(events_in)
        if gini_coeff > 0.4:
            result.add_finding(
                self.create_finding(
                    id=f"load-imbalance-{group.group_id}",
                    category="Performance",
                    severity="medium",
                    title=f"Uneven Load Distribution in '{group.group_id}'",
                    description=f"The distribution of incoming events is uneven, with a Gini coefficient of {gini_coeff:.2f}. "
                    "This can lead to some workers being overloaded while others are underutilized.",
                    remediation_steps=[
                        "Ensure load balancers are configured for even distribution (e.g., round-robin).",
                        "Check for Sources configured to send data to specific workers, causing imbalance.",
                        "Investigate network configurations that might favor certain routes to specific workers.",
                    ],
                    metadata={
                        "worker_group_id": group.group_id,
                        "gini_coefficient": round(gini_coeff, 2),
                    },
                )
            )

    def _check_utilization_variance(self, result: AnalyzerResult, group: WorkerGroupMetrics):
        """Analyzes CPU and memory utilization variance using Coefficient of Variation."""
        cpu_utils = np.array([w.cpu_util_pct for w in group.workers if w.cpu_util_pct is not None])
        mem_utils = np.array([w.mem_util_pct for w in group.workers if w.mem_util_pct is not None])

        if len(cpu_utils) < 2 and len(mem_utils) < 2:
            return

        cpu_cv = self._calculate_cv(cpu_utils) if len(cpu_utils) >= 2 else 0.0
        mem_cv = self._calculate_cv(mem_utils) if len(mem_utils) >= 2 else 0.0

        if cpu_cv > 0.5 or mem_cv > 0.5:
            metric, cv = ("CPU", cpu_cv) if cpu_cv > mem_cv else ("Memory", mem_cv)
            result.add_finding(
                self.create_finding(
                    id=f"utilization-variance-{group.group_id}",
                    category="Performance",
                    severity="high",
                    title=f"High {metric} Utilization Variance in '{group.group_id}'",
                    description=f"{metric} utilization is highly variable across workers, with a Coefficient of Variation of {cv:.2f}. "
                    "This indicates a significant resource imbalance.",
                    remediation_steps=[
                        "Investigate processes on high-utilization workers to identify the cause.",
                        "Review pipeline configurations; complex processing on some workers can cause skews.",
                        "Consider restarting persistently high-utilization workers if they are unresponsive.",
                    ],
                    estimated_impact="High resource utilization variance can lead to processing bottlenecks, "
                    "backpressure, and potential data loss if individual workers fail.",
                    metadata={
                        "worker_group_id": group.group_id,
                        "cpu_cv": round(cpu_cv, 2),
                        "mem_cv": round(mem_cv, 2),
                    },
                )
            )

    def _check_capacity_exhaustion(self, result: AnalyzerResult, group: WorkerGroupMetrics):
        """Predicts if any worker will hit 90% utilization within 48 hours."""
        for worker in group.workers:
            for metric, history in [
                ("CPU", worker.historical_cpu),
                ("Memory", worker.historical_mem),
            ]:
                if len(history) < 2:
                    continue
                prediction = self._predict_utilization(np.array(history))
                if prediction and prediction > 90.0:
                    result.add_finding(
                        self.create_finding(
                            id=f"capacity-exhaustion-{group.group_id}-{worker.node_id}-{metric.lower()}",
                            category="Capacity",
                            severity="medium",
                            title=f"Predicted {metric} Exhaustion for Worker '{worker.node_id}'",
                            description=f"Based on recent trends, {metric} utilization for worker '{worker.node_id}' in group '{group.group_id}' "
                            f"is predicted to exceed 90% within the next 48 hours.",
                            remediation_steps=[
                                "Proactively scale up the worker group or add more resources to the node.",
                                "Analyze the source of the increasing load and mitigate if possible.",
                                "Optimize pipelines running on the affected worker to reduce resource consumption.",
                            ],
                            metadata={
                                "worker_group_id": group.group_id,
                                "worker_id": worker.node_id,
                                "metric": metric,
                                "predicted_utilization_pct": round(prediction, 2),
                            },
                        )
                    )

    @staticmethod
    def _calculate_gini(x: np.ndarray) -> float:
        """Calculates the Gini coefficient for a 1D array."""
        if len(x) < 2 or np.sum(x) == 0:
            return 0.0
        x_sorted = np.sort(x)
        n = len(x)
        cumx = np.cumsum(x_sorted, dtype=float)
        return float((n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n)

    @staticmethod
    def _calculate_cv(x: np.ndarray) -> float:
        """Calculates the Coefficient of Variation."""
        if len(x) < 2:
            return 0.0
        mean = np.mean(x)
        if mean == 0:
            return 0.0
        return float(np.std(x, ddof=1) / mean)

    @staticmethod
    def _predict_utilization(series: np.ndarray, hours_ahead: int = 48) -> Optional[float]:
        """Predicts utilization using linear regression based on hourly data points."""
        if len(series) < 2:
            return None
        time_steps = np.arange(len(series))
        coeffs = np.polyfit(time_steps, series, 1)
        slope = coeffs[0]

        if slope <= 0:
            return None

        future_time_step = len(series) - 1 + hours_ahead
        prediction = np.poly1d(coeffs)(future_time_step)

        return float(min(prediction, 100.0))
