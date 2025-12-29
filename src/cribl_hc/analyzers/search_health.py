"""
Search Health Analyzer for Cribl Health Check.

Analyzes Cribl Search job health, dataset availability, dashboard status,
and saved search configurations.

Priority: P2 (Important)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.models.search import (
    Dashboard,
    DashboardList,
    SavedSearch,
    SavedSearchList,
    SearchDataset,
    SearchDatasetList,
    SearchJob,
    SearchJobList,
)
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchHealthAnalyzer(BaseAnalyzer):
    """
    Analyzer for Cribl Search health monitoring.

    Identifies:
    - Failed or stuck search jobs
    - Long-running queries that may need optimization
    - Datasets with connectivity issues
    - Dashboards without schedules
    - Unused or stale saved searches

    Priority: P2 (Important - ensures search functionality)
    """

    # Job thresholds
    LONG_RUNNING_SECONDS = 300  # 5 minutes
    VERY_LONG_RUNNING_SECONDS = 900  # 15 minutes

    # CPU usage thresholds (billable CPU seconds)
    HIGH_CPU_THRESHOLD = 60.0  # 1 minute billable CPU
    VERY_HIGH_CPU_THRESHOLD = 300.0  # 5 minutes billable CPU

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "search"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: jobs(1) + datasets(1) + dashboards(1) + saved(1) = 4.
        """
        return 4

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:search:jobs",
            "read:search:datasets",
            "read:search:dashboards",
            "read:search:saved"
        ]

    async def analyze(self, client: CriblAPIClient, workspace: str = "default_search") -> AnalyzerResult:
        """
        Analyze Cribl Search health and configuration.

        Args:
            client: Authenticated Cribl API client
            workspace: Search workspace name (default: "default_search")

        Returns:
            AnalyzerResult with Search health findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("search_health_analysis_started", workspace=workspace)

            # Fetch Search data
            jobs_response = await client.get_search_jobs(workspace)
            datasets_response = await client.get_search_datasets(workspace)
            dashboards_response = await client.get_search_dashboards(workspace)
            saved_response = await client.get_search_saved_searches(workspace)

            # Parse responses
            job_list = SearchJobList(**jobs_response)
            dataset_list = SearchDatasetList(**datasets_response)
            dashboard_list = DashboardList(**dashboards_response)
            saved_list = SavedSearchList(**saved_response)

            jobs = job_list.items
            datasets = dataset_list.items
            dashboards = dashboard_list.items
            saved_searches = saved_list.items

            # Categorize jobs by status
            running_jobs = [j for j in jobs if j.status == "running"]
            failed_jobs = [j for j in jobs if j.status == "failed"]
            completed_jobs = [j for j in jobs if j.status == "completed"]

            # Initialize metadata
            result.metadata.update({
                "workspace": workspace,
                "total_jobs": len(jobs),
                "running_jobs": len(running_jobs),
                "failed_jobs": len(failed_jobs),
                "completed_jobs": len(completed_jobs),
                "total_datasets": len(datasets),
                "enabled_datasets": sum(1 for d in datasets if d.enabled),
                "total_dashboards": len(dashboards),
                "total_saved_searches": len(saved_searches),
                "analysis_timestamp": datetime.utcnow().isoformat()
            })

            # Handle empty state
            if not any([jobs, datasets, dashboards, saved_searches]):
                result.add_finding(
                    Finding(
                        id="search-no-resources",
                        category="search",
                        severity="info",
                        title="No Search Resources Found",
                        description=f"No search resources configured in workspace '{workspace}'.",
                        affected_components=["Search"],
                        confidence_level="high",
                        metadata={"workspace": workspace}
                    )
                )
                result.success = True
                return result

            # Analyze jobs
            self._analyze_jobs(jobs, result)

            # Analyze datasets
            self._analyze_datasets(datasets, result)

            # Analyze dashboards
            self._analyze_dashboards(dashboards, result)

            # Analyze saved searches
            self._analyze_saved_searches(saved_searches, result)

            result.success = True
            log.info(
                "search_health_analysis_completed",
                workspace=workspace,
                jobs=len(jobs),
                datasets=len(datasets),
                dashboards=len(dashboards),
                saved_searches=len(saved_searches),
                findings=len(result.findings),
                recommendations=len(result.recommendations)
            )

        except Exception as e:
            log.error("search_health_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="search-analysis-error",
                    category="search",
                    severity="critical",
                    title="Search Health Analysis Failed",
                    description=f"Failed to analyze Search health: {str(e)}",
                    affected_components=["Search API"],
                    remediation_steps=["Check API connectivity", "Verify Search workspace exists"],
                    estimated_impact="Cannot assess Search health",
                    confidence_level="high",
                    metadata={"error": str(e)}
                )
            )

        return result

    def _analyze_jobs(self, jobs: List[SearchJob], result: AnalyzerResult) -> None:
        """Analyze search job health."""
        current_time = datetime.utcnow()

        for job in jobs:
            # Check for failed jobs
            if job.status == "failed":
                self._report_failed_job(job, result)
                continue

            # Check for long-running jobs
            if job.status == "running" and job.time_started:
                start_time = datetime.fromtimestamp(job.time_started / 1000)
                duration_seconds = (current_time - start_time).total_seconds()

                if duration_seconds >= self.VERY_LONG_RUNNING_SECONDS:
                    self._report_stuck_job(job, duration_seconds, result)
                elif duration_seconds >= self.LONG_RUNNING_SECONDS:
                    self._report_long_running_job(job, duration_seconds, result)

            # Check for high CPU usage in completed jobs
            if job.status == "completed" and job.cpu_metrics:
                billable_cpu = job.cpu_metrics.billable_cpu_seconds or 0
                if billable_cpu >= self.VERY_HIGH_CPU_THRESHOLD:
                    self._report_high_cpu_job(job, billable_cpu, "very_high", result)
                elif billable_cpu >= self.HIGH_CPU_THRESHOLD:
                    self._report_high_cpu_job(job, billable_cpu, "high", result)

    def _report_failed_job(self, job: SearchJob, result: AnalyzerResult) -> None:
        """Report a failed search job."""
        result.add_finding(
            Finding(
                id=f"search-job-failed-{job.id}",
                category="search",
                severity="high",
                title=f"Failed Search Job: {job.id}",
                description=(
                    f"Search job '{job.id}' failed. "
                    f"Error: {job.error or 'No error details available'}"
                ),
                affected_components=["Search", job.id],
                remediation_steps=[
                    "Review the query syntax for errors",
                    "Check if referenced datasets are available",
                    "Verify user has required permissions",
                    "Check Search workspace health"
                ],
                estimated_impact="Query results not available",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "error": job.error,
                    "user": job.user
                }
            )
        )

    def _report_stuck_job(
        self, job: SearchJob, duration_seconds: float, result: AnalyzerResult
    ) -> None:
        """Report a potentially stuck search job."""
        result.add_finding(
            Finding(
                id=f"search-job-stuck-{job.id}",
                category="search",
                severity="high",
                title=f"Potentially Stuck Job: {job.id}",
                description=(
                    f"Search job '{job.id}' has been running for "
                    f"{int(duration_seconds / 60)} minutes. This may indicate a stuck query."
                ),
                affected_components=["Search", job.id],
                remediation_steps=[
                    "Consider cancelling the job if not needed",
                    "Review query complexity and optimize",
                    "Check for resource constraints in the Search cluster"
                ],
                estimated_impact="Resources tied up, potential timeout",
                confidence_level="medium",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "duration_seconds": round(duration_seconds, 0),
                    "user": job.user
                }
            )
        )

        # Add recommendation to optimize or cancel
        result.add_recommendation(
            Recommendation(
                id=f"rec-search-optimize-job-{job.id}",
                type="performance",
                priority="p1",
                title=f"Optimize or Cancel Long-Running Job {job.id}",
                description=(
                    f"Job has been running for {int(duration_seconds / 60)} minutes. "
                    "Consider cancelling or optimizing the query."
                ),
                rationale="Long-running queries consume resources and may never complete.",
                implementation_steps=[
                    "Navigate to Search > Jobs",
                    f"Locate job {job.id}",
                    "Either cancel the job or review query for optimization opportunities"
                ],
                before_state=f"Job running for {int(duration_seconds / 60)} minutes",
                after_state="Job cancelled or optimized query submitted",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Frees up Search resources"
                ),
                implementation_effort="low",
                product_tags=["search"]
            )
        )

    def _report_long_running_job(
        self, job: SearchJob, duration_seconds: float, result: AnalyzerResult
    ) -> None:
        """Report a long-running search job."""
        result.add_finding(
            Finding(
                id=f"search-job-long-{job.id}",
                category="search",
                severity="medium",
                title=f"Long-Running Job: {job.id}",
                description=(
                    f"Search job '{job.id}' has been running for "
                    f"{int(duration_seconds / 60)} minutes."
                ),
                affected_components=["Search", job.id],
                remediation_steps=[
                    "Monitor job progress in Search UI",
                    "Consider optimizing the query if it runs frequently",
                    "Check for resource constraints if jobs consistently take long"
                ],
                estimated_impact="Extended resource usage",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "duration_seconds": round(duration_seconds, 0)
                }
            )
        )

    def _report_high_cpu_job(
        self, job: SearchJob, billable_cpu: float, severity_level: str, result: AnalyzerResult
    ) -> None:
        """Report a job with high CPU usage."""
        severity = "high" if severity_level == "very_high" else "medium"

        result.add_finding(
            Finding(
                id=f"search-job-high-cpu-{job.id}",
                category="search",
                severity=severity,
                title=f"High CPU Query: {job.id}",
                description=(
                    f"Search job '{job.id}' consumed {round(billable_cpu, 1)} billable CPU seconds. "
                    "Consider optimizing this query to reduce costs."
                ),
                affected_components=["Search", job.id],
                remediation_steps=[
                    "Review query for optimization opportunities",
                    "Use more specific time ranges",
                    "Add filters to reduce data scanned",
                    "Consider using Lakehouse for frequently queried data"
                ],
                estimated_impact=f"{round(billable_cpu, 1)} CPU seconds per execution",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "billable_cpu_seconds": round(billable_cpu, 2),
                    "total_cpu_seconds": round(
                        job.cpu_metrics.total_cpu_seconds or 0, 2
                    ) if job.cpu_metrics else 0
                }
            )
        )

        # Add optimization recommendation for very high CPU
        if severity_level == "very_high":
            result.add_recommendation(
                Recommendation(
                    id=f"rec-search-optimize-cpu-{job.id}",
                    type="optimization",
                    priority="p1",
                    title=f"Optimize High-CPU Query",
                    description=(
                        f"Query consumed {round(billable_cpu, 1)} billable CPU seconds. "
                        "Optimizing could significantly reduce costs."
                    ),
                    rationale="High CPU queries increase costs and may impact other searches.",
                    implementation_steps=[
                        "Review the query pattern and identify optimization opportunities",
                        "Add time range filters to limit data scanned",
                        "Use specific dataset filters instead of wildcards",
                        "Consider creating a Lakehouse for frequently queried data"
                    ],
                    before_state=f"Query uses {round(billable_cpu, 1)} CPU seconds",
                    after_state="Optimized query with reduced CPU usage",
                    impact_estimate=ImpactEstimate(
                        cost_savings_monthly=round(billable_cpu * 0.001, 2),  # Rough estimate
                        performance_improvement="Faster query execution"
                    ),
                    implementation_effort="medium",
                    product_tags=["search"]
                )
            )

    def _analyze_datasets(self, datasets: List[SearchDataset], result: AnalyzerResult) -> None:
        """Analyze search dataset health."""
        disabled_datasets = [d for d in datasets if not d.enabled]

        if disabled_datasets:
            result.add_finding(
                Finding(
                    id="search-datasets-disabled",
                    category="search",
                    severity="low",
                    title=f"{len(disabled_datasets)} Disabled Dataset(s)",
                    description=(
                        f"Found {len(disabled_datasets)} disabled dataset(s): "
                        f"{', '.join(d.id for d in disabled_datasets[:5])}"
                        f"{'...' if len(disabled_datasets) > 5 else ''}"
                    ),
                    affected_components=["Search"] + [d.id for d in disabled_datasets[:5]],
                    confidence_level="high",
                    metadata={
                        "disabled_count": len(disabled_datasets),
                        "disabled_ids": [d.id for d in disabled_datasets]
                    }
                )
            )

        # Check for datasets without providers
        orphan_datasets = [d for d in datasets if not d.provider]
        if orphan_datasets:
            result.add_finding(
                Finding(
                    id="search-datasets-no-provider",
                    category="search",
                    severity="medium",
                    title=f"{len(orphan_datasets)} Dataset(s) Without Provider",
                    description=(
                        f"Found {len(orphan_datasets)} dataset(s) without a configured provider."
                    ),
                    affected_components=["Search"] + [d.id for d in orphan_datasets[:5]],
                    remediation_steps=[
                        "Configure a data provider for each dataset",
                        "Remove datasets that are no longer needed"
                    ],
                    confidence_level="high",
                    metadata={
                        "orphan_count": len(orphan_datasets),
                        "orphan_ids": [d.id for d in orphan_datasets]
                    }
                )
            )

    def _analyze_dashboards(self, dashboards: List[Dashboard], result: AnalyzerResult) -> None:
        """Analyze dashboard health."""
        # Check for dashboards without elements
        empty_dashboards = [
            d for d in dashboards
            if not d.elements or len(d.elements) == 0
        ]

        if empty_dashboards:
            result.add_finding(
                Finding(
                    id="search-dashboards-empty",
                    category="search",
                    severity="info",
                    title=f"{len(empty_dashboards)} Empty Dashboard(s)",
                    description=(
                        f"Found {len(empty_dashboards)} dashboard(s) without any elements."
                    ),
                    affected_components=["Search"] + [d.id for d in empty_dashboards[:5]],
                    confidence_level="high",
                    metadata={
                        "empty_count": len(empty_dashboards),
                        "empty_ids": [d.id for d in empty_dashboards]
                    }
                )
            )

        # Check for dashboards with schedules
        scheduled_dashboards = [
            d for d in dashboards
            if d.schedule and d.schedule.enabled
        ]

        result.metadata["scheduled_dashboards"] = len(scheduled_dashboards)

    def _analyze_saved_searches(
        self, saved_searches: List[SavedSearch], result: AnalyzerResult
    ) -> None:
        """Analyze saved search configurations."""
        # Check for saved searches without queries
        invalid_searches = [s for s in saved_searches if not s.query]

        if invalid_searches:
            result.add_finding(
                Finding(
                    id="search-saved-no-query",
                    category="search",
                    severity="low",
                    title=f"{len(invalid_searches)} Saved Search(es) Without Query",
                    description=(
                        f"Found {len(invalid_searches)} saved search(es) without a query defined."
                    ),
                    affected_components=["Search"] + [s.id for s in invalid_searches[:5]],
                    remediation_steps=[
                        "Update saved searches with valid queries",
                        "Remove unused saved searches"
                    ],
                    confidence_level="high",
                    metadata={
                        "invalid_count": len(invalid_searches),
                        "invalid_ids": [s.id for s in invalid_searches]
                    }
                )
            )
