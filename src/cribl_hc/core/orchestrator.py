from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Dict, List, Optional

from cribl_hc.analyzers import get_analyzer, get_global_registry, list_objectives
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.analysis import AnalysisRun, ComponentVersion, VersionInfo
from cribl_hc.models.finding import Finding
from cribl_hc.models.health import ComponentScore, HealthScore
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class AnalysisProgress:
    """
    Progress tracker for analysis execution.
    """

    def __init__(self, total_objectives: int, api_call_budget: int = 100):
        self.total_objectives = total_objectives
        self.completed_objectives = 0
        self.current_objective: Optional[str] = None
        self.api_calls_used = 0
        self.api_calls_remaining = api_call_budget

    def start_objective(self, objective: str) -> None:
        self.current_objective = objective

    def complete_objective(self) -> None:
        self.completed_objectives += 1
        self.current_objective = None

    def update_api_calls(self, used: int, remaining: int) -> None:
        self.api_calls_used = used
        self.api_calls_remaining = remaining

    def get_percentage(self) -> float:
        if self.total_objectives == 0:
            return 100.0
        return (self.completed_objectives / self.total_objectives) * 100

    def __repr__(self) -> str:
        return f"AnalysisProgress({self.completed_objectives}/{self.total_objectives})"


class AnalyzerOrchestrator:
    """
    Orchestrates execution of multiple analyzers and aggregates results.
    """

    def __init__(
        self,
        client: CriblAPIClient,
        max_api_calls: int = 100,
        continue_on_error: bool = True,
    ):
        self.client = client
        self.max_api_calls = max_api_calls
        self.continue_on_error = continue_on_error
        self.log = get_logger(self.__class__.__name__)
        self.registry = get_global_registry()
        self.progress: Optional[AnalysisProgress] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.version_info: VersionInfo = VersionInfo()

    async def run_analysis(
        self,
        objectives: Optional[Sequence[str]] = None,
        products: Optional[Sequence[str]] = None,
        progress_callback: Optional[Callable[[Any], None]] = None,
    ) -> dict[str, AnalyzerResult]:
        """
        Run health check analysis for specified objectives.
        """
        self.start_time = datetime.utcnow()
        if objectives is None:
            objectives = list_objectives()

        if products:
            requested_products = set(products)
            filtered_objectives: list[str] = []
            for objective in objectives:
                analyzer = get_analyzer(objective)
                if analyzer and any(p in requested_products for p in analyzer.supported_products):
                    filtered_objectives.append(objective)
            objectives = filtered_objectives

        if not objectives:
            return {}
        self.progress = AnalysisProgress(
            total_objectives=len(objectives),
            api_call_budget=self.max_api_calls,
        )

        # Pre-collect version info for the entire deployment
        self.version_info = await self._collect_version_info()

        results: dict[str, AnalyzerResult] = {}

        # Check API budget upfront for all objectives
        api_calls_used = self.client.get_api_calls_used()
        api_calls_remaining = self.max_api_calls - api_calls_used

        if api_calls_remaining <= 0:
            for objective in objectives:
                self.log.error("api_budget_exhausted", objective=objective)
                results[objective] = AnalyzerResult(
                    objective=objective, success=False, error="API budget exceeded"
                )
            self.end_time = datetime.utcnow()
            return results

        # Run all analyzers in parallel
        async def run_objective_with_tracking(objective: str) -> tuple[str, AnalyzerResult]:
            self.progress.start_objective(objective)
            try:
                result = await self._run_single_analyzer(objective)
            except Exception as e:
                self.log.error("analyzer_failed", objective=objective, error=str(e))
                result = AnalyzerResult(objective=objective, success=False, error=str(e))
            self.progress.complete_objective()
            if progress_callback:
                progress_callback(self.progress)
            return objective, result

        # Execute all objectives in parallel
        objective_tasks = [run_objective_with_tracking(obj) for obj in objectives]
        objective_results = await asyncio.gather(*objective_tasks, return_exceptions=True)

        # Process results, handling any exceptions
        for item in objective_results:
            if isinstance(item, Exception):
                self.log.error("parallel_execution_error", error=str(item))
                continue
            objective, result = item
            results[objective] = result

        self.end_time = datetime.utcnow()
        return results

    async def _collect_version_info(self) -> VersionInfo:
        """
        Collect version information for all deployment components.
        """
        info = VersionInfo()
        try:
            # 1. Get leader version
            status = await self.client.get_system_status()
            info.leader_version = status.get("version") or self.client.product_version
            info.product_type = self.client.product_type

            # 2. Get node versions
            nodes = await self.client.get_nodes()
            comp_versions = []
            prod_versions = {}

            if info.leader_version:
                prod_versions["leader"] = info.leader_version

            for node in nodes:
                node_id = str(node.get("id", "unknown"))
                version = str(node.get("info", {}).get("cribl", {}).get("version", "unknown"))
                status_str = str(node.get("status", "unknown"))
                group = str(node.get("group", "default"))

                comp_versions.append(
                    ComponentVersion(
                        name=node_id,
                        version=version,
                        status=status_str,
                        metadata={
                            "group": group,
                            "hostname": str(node.get("info", {}).get("hostname", "unknown")),
                        },
                    )
                )

                # Track product variant versions (e.g. per-group)
                if version != "unknown":
                    prod_versions[group] = version

            info.component_versions = comp_versions
            info.product_versions = prod_versions

        except Exception as e:
            self.log.warning("version_collection_failed", error=str(e))

        return info

    async def _run_single_analyzer(self, objective: str) -> AnalyzerResult:
        """
        Run a single analyzer.
        """
        analyzer = get_analyzer(objective)
        if not analyzer:
            raise ValueError(f"No analyzer found for: {objective}")

        return await analyzer.analyze(self.client)

    def create_analysis_run(
        self,
        results: dict[str, AnalyzerResult],
        deployment_id: str,
    ) -> AnalysisRun:
        """
        Aggregate results into an AnalysisRun.
        """
        all_findings = []
        all_recommendations = []
        all_errors = []

        for objective, result in results.items():
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)
            if not result.success and result.error:
                all_errors.append(f"{objective}: {result.error}")

        duration = 0.0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        failed_count = sum(1 for r in results.values() if not r.success)
        status_val = (
            "completed"
            if failed_count == 0
            else "partial"
            if failed_count < len(results)
            else "failed"
        )

        health_score = self._calculate_overall_health_score(results, all_findings)

        return AnalysisRun(
            deployment_id=deployment_id,
            status=status_val,
            objectives_analyzed=list(results.keys()),
            api_calls_used=self.client.get_api_calls_used(),
            duration_seconds=duration,
            findings=all_findings,
            recommendations=all_recommendations,
            errors=all_errors,
            partial_completion=(0 < failed_count < len(results)),
            health_score=health_score,
            version_info=self.version_info,
        )

    def _calculate_overall_health_score(
        self,
        results: dict[str, AnalyzerResult],
        findings: list[Finding],
    ) -> HealthScore:
        """
        Calculate health score with component breakdown.
        """
        severity_penalties = {"critical": 20, "high": 10, "medium": 3, "low": 0.5, "info": 0}
        component_weights = {
            "health": 0.25,
            "security": 0.20,
            "config": 0.15,
            "resource": 0.15,
            "fleet": 0.10,
            "alerting": 0.05,
            "other": 0.10,
        }

        component_scores: dict[str, ComponentScore] = {}
        components_found: dict[str, dict] = {}

        for objective, result in results.items():
            # Map objective to category
            if objective in ("health",):
                category = "health"
            elif objective in ("security",):
                category = "security"
            elif objective in ("config", "schema_quality", "dataflow_topology"):
                category = "config"
            elif objective in ("resource", "storage", "backpressure", "pipeline_performance"):
                category = "resource"
            elif objective in ("fleet",):
                category = "fleet"
            elif objective in ("alerting",):
                category = "alerting"
            else:
                category = "other"

            # Calculate score for this analyzer
            score = 100
            objective_findings = [f for f in findings if f.source_analyzer == objective]
            penalty = sum(severity_penalties.get(f.severity, 0) for f in objective_findings)
            score = max(0, 100 - penalty)

            if category not in components_found:
                components_found[category] = {
                    "scores": [],
                    "objectives": [],
                    "weight": component_weights.get(category, 0.05),
                }
            components_found[category]["scores"].append(score)
            components_found[category]["objectives"].append(objective)

        overall_weighted_sum = 0.0
        total_weight = 0.0
        raw_weight_sum = sum(data["weight"] for data in components_found.values())

        for category, data in components_found.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 100
            weight = data["weight"] / raw_weight_sum if raw_weight_sum > 0 else 1.0

            component_scores[category] = ComponentScore(
                name=category.replace("_", " ").title(),
                score=int(avg_score),
                weight=weight,
                details=f"Based on: {', '.join(data['objectives'])}",
            )
            overall_weighted_sum += avg_score * weight
            total_weight += weight

        final_score = int(overall_weighted_sum) if total_weight > 0 else 100
        return HealthScore(overall_score=final_score, components=component_scores)

    def get_progress(self) -> Optional[AnalysisProgress]:
        return self.progress

    def get_api_usage_summary(self) -> dict[str, int]:
        used = self.client.get_api_calls_used()
        return {"used": used, "remaining": self.max_api_calls - used, "budget": self.max_api_calls}
