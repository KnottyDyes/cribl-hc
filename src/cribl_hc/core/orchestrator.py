"""
Analyzer orchestrator for coordinating health check analysis.

The orchestrator manages multiple analyzers, tracks API usage, and
aggregates results into a comprehensive analysis report.
"""

from datetime import datetime
from typing import Dict, List, Optional

from cribl_hc.analyzers import get_analyzer, get_global_registry, list_objectives
from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.analysis import AnalysisRun
from cribl_hc.models.finding import Finding
from cribl_hc.models.health import HealthScore, ComponentScore
from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class AnalysisProgress:
    """
    Progress tracker for analysis execution.

    Attributes:
        total_objectives: Total number of objectives to analyze
        completed_objectives: Number of completed objectives
        current_objective: Currently executing objective
        api_calls_used: Total API calls made
        api_calls_remaining: Remaining API call budget
    """

    def __init__(self, total_objectives: int, api_call_budget: int = 100):
        self.total_objectives = total_objectives
        self.completed_objectives = 0
        self.current_objective: Optional[str] = None
        self.api_calls_used = 0
        self.api_calls_remaining = api_call_budget

    def start_objective(self, objective: str) -> None:
        """Mark an objective as started."""
        self.current_objective = objective

    def complete_objective(self) -> None:
        """Mark current objective as completed."""
        self.completed_objectives += 1
        self.current_objective = None

    def update_api_calls(self, used: int, remaining: int) -> None:
        """Update API call tracking."""
        self.api_calls_used = used
        self.api_calls_remaining = remaining

    def get_percentage(self) -> float:
        """Get completion percentage."""
        if self.total_objectives == 0:
            return 100.0
        return (self.completed_objectives / self.total_objectives) * 100

    def __repr__(self) -> str:
        return (
            f"AnalysisProgress({self.completed_objectives}/{self.total_objectives} "
            f"objectives, {self.api_calls_used} API calls)"
        )


class AnalyzerOrchestrator:
    """
    Orchestrates execution of multiple analyzers.

    Features:
    - Sequential analyzer execution
    - API call budget tracking (max 100 calls)
    - Partial result handling for graceful degradation
    - Progress tracking
    - Result aggregation

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     orchestrator = AnalyzerOrchestrator(client)
        ...     results = await orchestrator.run_analysis(["health", "config"])
        ...     print(f"Health score: {results['health'].metadata['health_score']}")
    """

    def __init__(
        self,
        client: CriblAPIClient,
        max_api_calls: int = 100,
        continue_on_error: bool = True,
    ):
        """
        Initialize analyzer orchestrator.

        Args:
            client: Authenticated Cribl API client
            max_api_calls: Maximum API calls allowed (default: 100)
            continue_on_error: Continue analysis if an analyzer fails (default: True)
        """
        self.client = client
        self.max_api_calls = max_api_calls
        self.continue_on_error = continue_on_error
        self.log = get_logger(self.__class__.__name__)

        # Get registry for analyzer access
        self.registry = get_global_registry()

        # Analysis state
        self.progress: Optional[AnalysisProgress] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    async def run_analysis(
        self,
        objectives: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, AnalyzerResult]:
        """
        Run health check analysis for specified objectives.

        Args:
            objectives: List of objective names to analyze (e.g., ["health", "config"])
                       If None, runs all registered analyzers
            progress_callback: Optional callback function(progress: AnalysisProgress)
                              called after each objective completes

        Returns:
            Dictionary mapping objective names to AnalyzerResult objects

        Raises:
            ValueError: If unknown objective specified
            RuntimeError: If API call budget exceeded

        Example:
            >>> results = await orchestrator.run_analysis(["health"])
            >>> health_result = results["health"]
            >>> print(f"Score: {health_result.metadata['health_score']}")
        """
        self.start_time = datetime.utcnow()

        # Determine which objectives to run
        if objectives is None:
            objectives = list_objectives()

        if not objectives:
            self.log.warning("no_objectives", message="No analyzers registered")
            return {}

        # Validate objectives
        for objective in objectives:
            if not self.registry.has_analyzer(objective):
                raise ValueError(
                    f"Unknown objective '{objective}'. "
                    f"Available: {', '.join(list_objectives())}"
                )

        # Initialize progress tracking
        self.progress = AnalysisProgress(
            total_objectives=len(objectives),
            api_call_budget=self.max_api_calls,
        )

        self.log.info(
            "analysis_started",
            objectives=objectives,
            api_call_budget=self.max_api_calls,
        )

        results: Dict[str, AnalyzerResult] = {}

        # Run each analyzer sequentially
        for objective in objectives:
            # Check API call budget before starting
            api_calls_used = self.client.get_api_calls_used()
            api_calls_remaining = self.max_api_calls - api_calls_used

            if api_calls_remaining <= 0:
                self.log.error(
                    "api_budget_exceeded",
                    objective=objective,
                    used=api_calls_used,
                    budget=self.max_api_calls,
                )

                # Add failure result for this objective
                results[objective] = AnalyzerResult(
                    objective=objective,
                    success=False,
                    error="API call budget exceeded",
                )

                if not self.continue_on_error:
                    break

                continue

            # Update progress
            self.progress.start_objective(objective)
            self.progress.update_api_calls(api_calls_used, api_calls_remaining)

            # Run analyzer
            try:
                result = await self._run_single_analyzer(objective)
                results[objective] = result

            except Exception as e:
                self.log.error(
                    "analyzer_failed",
                    objective=objective,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                # Create failure result
                results[objective] = AnalyzerResult(
                    objective=objective,
                    success=False,
                    error=f"Analyzer failed: {str(e)}",
                )

                if not self.continue_on_error:
                    break

            # Mark objective complete
            self.progress.complete_objective()

            # Update API call tracking
            api_calls_used = self.client.get_api_calls_used()
            api_calls_remaining = self.max_api_calls - api_calls_used
            self.progress.update_api_calls(api_calls_used, api_calls_remaining)

            # Notify progress callback
            if progress_callback:
                try:
                    progress_callback(self.progress)
                except Exception as e:
                    self.log.warning("progress_callback_failed", error=str(e))

        self.end_time = datetime.utcnow()
        duration = (self.end_time - self.start_time).total_seconds()

        self.log.info(
            "analysis_completed",
            objectives_completed=len(results),
            objectives_total=len(objectives),
            api_calls_used=self.client.get_api_calls_used(),
            duration_seconds=duration,
        )

        return results

    async def _run_single_analyzer(self, objective: str) -> AnalyzerResult:
        """
        Run a single analyzer for the given objective.

        Args:
            objective: Objective name

        Returns:
            AnalyzerResult from the analyzer

        Raises:
            Exception: If analyzer execution fails critically
        """
        analyzer = get_analyzer(objective)
        if not analyzer:
            raise ValueError(f"No analyzer found for objective '{objective}'")

        self.log.info(
            "analyzer_started",
            objective=objective,
            analyzer_class=analyzer.__class__.__name__,
            estimated_api_calls=analyzer.get_estimated_api_calls(),
        )

        # Check if analyzer supports pre-flight checks
        can_run = await analyzer.pre_analyze_check(self.client)
        if not can_run:
            self.log.warning(
                "analyzer_preflight_failed",
                objective=objective,
            )
            return AnalyzerResult(
                objective=objective,
                success=False,
                error="Pre-flight check failed - analyzer cannot run",
            )

        # Run the analyzer
        start_time = datetime.utcnow()
        result = await analyzer.analyze(self.client)
        end_time = datetime.utcnow()

        duration = (end_time - start_time).total_seconds()

        self.log.info(
            "analyzer_completed",
            objective=objective,
            success=result.success,
            findings=len(result.findings),
            recommendations=len(result.recommendations),
            duration_seconds=duration,
        )

        # Run cleanup
        await analyzer.post_analyze_cleanup()

        return result

    def create_analysis_run(
        self,
        results: Dict[str, AnalyzerResult],
        deployment_id: str,
    ) -> AnalysisRun:
        """
        Create an AnalysisRun model from orchestrator results.

        Args:
            results: Dictionary of analyzer results
            deployment_id: Deployment identifier

        Returns:
            AnalysisRun model with aggregated results

        Example:
            >>> results = await orchestrator.run_analysis(["health"])
            >>> analysis_run = orchestrator.create_analysis_run(
            ...     results, deployment_id="prod-cluster"
            ... )
        """
        all_findings = []
        all_recommendations = []
        all_errors = []

        for objective, result in results.items():
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)

            # Collect errors from failed analyzers
            if not result.success and result.error:
                all_errors.append(f"{objective}: {result.error}")

        # Calculate execution time
        duration_seconds = 0.0
        if self.start_time and self.end_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()

        # Determine status
        failed_count = sum(1 for r in results.values() if not r.success)
        if failed_count == 0:
            status = "completed"
        elif failed_count < len(results):
            status = "partial"
        else:
            status = "failed"

        # Calculate overall health score from findings and analyzer metadata
        health_score = self._calculate_overall_health_score(results, all_findings)

        return AnalysisRun(
            deployment_id=deployment_id,
            status=status,
            objectives_analyzed=list(results.keys()),
            api_calls_used=self.client.get_api_calls_used(),
            duration_seconds=duration_seconds,
            findings=all_findings,
            recommendations=all_recommendations,
            errors=all_errors,
            partial_completion=(failed_count > 0 and failed_count < len(results)),
            health_score=health_score,
        )

    def _calculate_overall_health_score(
        self,
        results: Dict[str, AnalyzerResult],
        findings: List[Finding],
    ) -> HealthScore:
        """
        Calculate overall health score from analyzer results and findings.

        Uses a combination of:
        1. Per-analyzer health scores from metadata (if available)
        2. Findings-based penalty calculation

        Args:
            results: Dictionary of analyzer results
            findings: List of all findings

        Returns:
            HealthScore with overall score and component breakdown
        """
        # Severity penalties for findings
        severity_penalties = {
            "critical": 20,
            "high": 10,
            "medium": 3,
            "low": 0.5,
            "info": 0,
        }

        # Component weights (sum to 1.0)
        component_weights = {
            "health": 0.25,
            "security": 0.20,
            "config": 0.15,
            "resource": 0.15,
            "fleet": 0.10,
            "alerting": 0.05,
            "other": 0.10,
        }

        # Initialize component scores
        component_scores: Dict[str, ComponentScore] = {}
        components_found: Dict[str, Dict] = {}

        # First, try to get scores from analyzer metadata
        for objective, result in results.items():
            # Map objective to component category
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

            # Get score from metadata if available
            score = None
            if result.metadata:
                # Try various common score key names
                for key in ("health_score", f"{objective}_health_score", "score", "overall_score"):
                    if key in result.metadata:
                        val = result.metadata[key]
                        if isinstance(val, (int, float)):
                            score = int(min(100, max(0, val)))
                            break

            # If no score in metadata, calculate from findings for this analyzer
            if score is None:
                objective_findings = [f for f in findings if f.source_analyzer == objective]
                penalty = sum(
                    severity_penalties.get(f.severity, 0)
                    for f in objective_findings
                )
                score = int(max(0, 100 - penalty))

            # Store component data
            if category not in components_found:
                components_found[category] = {
                    "scores": [],
                    "objectives": [],
                    "weight": component_weights.get(category, 0.05),
                }
            components_found[category]["scores"].append(score)
            components_found[category]["objectives"].append(objective)

        # Build component scores
        overall_weighted_sum = 0.0
        total_weight = 0.0

        for category, data in components_found.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 100
            weight = data["weight"]

            component_scores[category] = ComponentScore(
                name=category.replace("_", " ").title(),
                score=int(avg_score),
                weight=weight,
                details=f"Based on: {', '.join(data['objectives'])}",
            )

            overall_weighted_sum += avg_score * weight
            total_weight += weight

        # Calculate overall score
        if total_weight > 0:
            overall_score = int(overall_weighted_sum / total_weight)
        else:
            # Fallback: calculate from all findings
            total_penalty = sum(
                severity_penalties.get(f.severity, 0)
                for f in findings
            )
            overall_score = int(max(0, 100 - total_penalty))

        # Ensure score is in valid range
        overall_score = min(100, max(0, overall_score))

        return HealthScore(
            overall_score=overall_score,
            components=component_scores,
        )

    def get_progress(self) -> Optional[AnalysisProgress]:
        """
        Get current analysis progress.

        Returns:
            AnalysisProgress if analysis is running, None otherwise
        """
        return self.progress

    def get_api_usage_summary(self) -> Dict[str, int]:
        """
        Get summary of API call usage.

        Returns:
            Dictionary with 'used', 'remaining', and 'budget' counts
        """
        used = self.client.get_api_calls_used()
        return {
            "used": used,
            "remaining": self.max_api_calls - used,
            "budget": self.max_api_calls,
        }
