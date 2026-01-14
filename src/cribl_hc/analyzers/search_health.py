from typing import List

"""
Search Health Analyzer for Cribl Health Check.

Analyzes Cribl Search job health, dataset availability, dashboard status,
and saved search configurations.

Priority: P2 (Important)
"""

from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.models.search import (
    Dashboard,
    DashboardList,
    SavedSearch,
    SavedSearchList,
    SearchCost,
    SearchDataset,
    SearchDatasetList,
    SearchGroup,
    SearchGroupList,
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
    - Search cost and resource consumption
    """

    LONG_RUNNING_SECONDS = 300
    VERY_LONG_RUNNING_SECONDS = 900

    HIGH_CPU_THRESHOLD = 60.0
    VERY_HIGH_CPU_THRESHOLD = 300.0

    @property
    def supported_products(self) -> List[str]:
        """Search health analyzer is specific to Cribl Search."""
        return ["search"]

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "search"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: jobs(1) + datasets(1) + dashboards(1) + saved(1) + groups(1) + cost(1) = 6.
        """
        return 6

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:search:jobs",
            "read:search:datasets",
            "read:search:dashboards",
            "read:search:saved",
            "read:search:groups",
            "read:search:cost",
        ]

    async def analyze(
        self, client: CriblAPIClient, workspace: str = "default_search"
    ) -> AnalyzerResult:
        """
        Analyze Cribl Search health and configuration.
        """
        result = self.create_result()

        try:
            log.info("search_health_analysis_started", workspace=workspace)

            jobs_response = await client.get_search_jobs(workspace)
            datasets_response = await client.get_search_datasets(workspace)
            dashboards_response = await client.get_search_dashboards(workspace)
            saved_response = await client.get_search_saved_searches(workspace)
            groups_response = await client.get_search_groups(workspace)
            cost_response = await client.get_search_cost(workspace, days=30)

            job_list = SearchJobList(**jobs_response)
            dataset_list = SearchDatasetList(**datasets_response)
            dashboard_list = DashboardList(**dashboards_response)
            saved_list = SavedSearchList(**saved_response)
            group_list = SearchGroupList(**groups_response)
            cost_data = SearchCost(**cost_response)

            jobs = job_list.items
            datasets = dataset_list.items
            dashboards = dashboard_list.items
            saved_searches = saved_list.items
            groups = group_list.items

            running_jobs = [j for j in jobs if j.status == "running"]
            failed_jobs = [j for j in jobs if j.status == "failed"]
            completed_jobs = [j for j in jobs if j.status == "completed"]
            canceled_jobs = [j for j in jobs if j.status == "canceled"]

            result.metadata.update(
                {
                    "workspace": workspace,
                    "total_jobs": len(jobs),
                    "running_jobs": len(running_jobs),
                    "failed_jobs": len(failed_jobs),
                    "completed_jobs": len(completed_jobs),
                    "canceled_jobs": len(canceled_jobs),
                    "total_datasets": len(datasets),
                    "enabled_datasets": sum(1 for d in datasets if d.enabled),
                    "total_dashboards": len(dashboards),
                    "total_saved_searches": len(saved_searches),
                    "total_groups": len(groups),
                    "total_cost_30d": cost_data.total_cost_usd,
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not any([jobs, datasets, dashboards, saved_searches]):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-no-resources",
                        category="search",
                        severity="info",
                        title="No Search Resources Found",
                        description=f"No search resources configured in workspace '{workspace}'.",
                        affected_components=["Search"],
                        confidence_level="high",
                        metadata={"workspace": workspace},
                    )
                )
                result.success = True
                return result

            self._analyze_jobs(jobs, result, client)
            self._analyze_datasets(datasets, result, client)
            self._analyze_groups(groups, result, client)
            self._analyze_dashboards(dashboards, result, client)
            self._analyze_saved_searches(saved_searches, result, client)
            self._analyze_cost(cost_data, result, client)

            result.success = True
            log.info(
                "search_health_analysis_completed",
                workspace=workspace,
                jobs=len(jobs),
                datasets=len(datasets),
                findings=len(result.findings),
            )

        except Exception as e:
            log.error("search_health_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-analysis-error",
                    category="search",
                    severity="critical",
                    title="Search Health Analysis Failed",
                    description=f"Failed to analyze Search health: {str(e)}",
                    affected_components=["Search API"],
                    remediation_steps=["Check API connectivity", "Verify Search workspace exists"],
                    estimated_impact="Cannot assess Search health",
                    confidence_level="high",
                    metadata={"error": str(e)},
                )
            )

        return result

    def _analyze_jobs(
        self, jobs: List[SearchJob], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze search job health."""
        current_time = datetime.utcnow()

        for job in jobs:
            if job.status == "failed":
                self._report_failed_job(job, result, client)
                continue

            if job.status == "canceled":
                self._report_canceled_job(job, result, client)
                continue

            if job.status == "running" and job.time_started:
                start_time = datetime.fromtimestamp(job.time_started / 1000)
                duration_seconds = (current_time - start_time).total_seconds()

                if duration_seconds >= self.VERY_LONG_RUNNING_SECONDS:
                    self._report_stuck_job(job, duration_seconds, result, client)
                elif duration_seconds >= self.LONG_RUNNING_SECONDS:
                    self._report_long_running_job(job, duration_seconds, result, client)

            if job.status == "completed" and job.cpu_metrics:
                billable_cpu = job.cpu_metrics.billable_cpu_seconds or 0
                if billable_cpu >= self.VERY_HIGH_CPU_THRESHOLD:
                    self._report_high_cpu_job(job, billable_cpu, "very_high", result, client)
                elif billable_cpu >= self.HIGH_CPU_THRESHOLD:
                    self._report_high_cpu_job(job, billable_cpu, "high", result, client)

    def _report_failed_job(
        self, job: SearchJob, result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Report a failed search job."""
        result.add_finding(
            self.create_finding(
                client=client,
                id=f"search-job-failed-{job.id}",
                category="search",
                severity="critical",
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
                    "Check Search workspace health",
                ],
                estimated_impact="Query results not available",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "error": job.error,
                    "user": job.user,
                },
            )
        )

    def _report_canceled_job(
        self, job: SearchJob, result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Report a canceled search job."""
        result.add_finding(
            self.create_finding(
                client=client,
                id=f"search-job-canceled-{job.id}",
                category="search",
                severity="medium",
                title=f"Canceled Search Job: {job.id}",
                description=f"Search job '{job.id}' was canceled by a user.",
                affected_components=["Search", job.id],
                remediation_steps=[
                    "Investigate why the job was canceled",
                    "If the cancellation was unintentional, re-run the search.",
                ],
                estimated_impact="Potential data loss or incomplete analysis",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "user": job.user,
                },
            )
        )

    def _report_stuck_job(
        self,
        job: SearchJob,
        duration_seconds: float,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Report a potentially stuck search job."""
        result.add_finding(
            self.create_finding(
                client=client,
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
                    "Check for resource constraints in the Search cluster",
                ],
                estimated_impact="Resources tied up, potential timeout",
                confidence_level="medium",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "duration_seconds": round(duration_seconds, 0),
                    "user": job.user,
                },
            )
        )

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
                    "Either cancel the job or review query for optimization opportunities",
                ],
                before_state=f"Job running for {int(duration_seconds / 60)} minutes",
                after_state="Job cancelled or optimized query submitted",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Frees up Search resources",
                    cost_savings_annual=0.0,
                    storage_reduction_gb=0.0,
                    time_to_implement="5 minutes",
                ),
                implementation_effort="low",
                product_tags=["search"],
            )
        )

    def _report_long_running_job(
        self,
        job: SearchJob,
        duration_seconds: float,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Report a long-running search job."""
        result.add_finding(
            self.create_finding(
                client=client,
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
                    "Check for resource constraints if jobs consistently take long",
                ],
                estimated_impact="Extended resource usage",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "duration_seconds": round(duration_seconds, 0),
                },
            )
        )

    def _report_high_cpu_job(
        self,
        job: SearchJob,
        billable_cpu: float,
        severity_level: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Report a job with high CPU usage."""
        severity = "high" if severity_level == "very_high" else "medium"

        result.add_finding(
            self.create_finding(
                client=client,
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
                    "Consider using Lakehouse for frequently queried data",
                ],
                estimated_impact=f"{round(billable_cpu, 1)} CPU seconds per execution",
                confidence_level="high",
                metadata={
                    "job_id": job.id,
                    "query": job.query,
                    "billable_cpu_seconds": round(billable_cpu, 2),
                    "total_cpu_seconds": round(job.cpu_metrics.total_cpu_seconds or 0, 2)
                    if job.cpu_metrics
                    else 0,
                },
            )
        )

        if severity_level == "very_high":
            result.add_recommendation(
                Recommendation(
                    id=f"rec-search-optimize-cpu-{job.id}",
                    type="optimization",
                    priority="p1",
                    title="Optimize High-CPU Query",
                    description=(
                        f"Query consumed {round(billable_cpu, 1)} billable CPU seconds. "
                        "Optimizing could significantly reduce costs."
                    ),
                    rationale="High CPU queries increase costs and may impact other searches.",
                    implementation_steps=[
                        "Review the query pattern and identify optimization opportunities",
                        "Add time range filters to limit data scanned",
                        "Use specific dataset filters instead of wildcards",
                        "Consider creating a Lakehouse for frequently queried data",
                    ],
                    before_state=f"Query uses {round(billable_cpu, 1)} CPU seconds",
                    after_state="Optimized query with reduced CPU usage",
                    impact_estimate=ImpactEstimate(
                        cost_savings_annual=round(billable_cpu * 0.001 * 12, 2),
                        performance_improvement="Faster query execution",
                        storage_reduction_gb=0.0,
                        time_to_implement="1 hour",
                    ),
                    implementation_effort="medium",
                    product_tags=["search"],
                )
            )

    def _analyze_datasets(
        self, datasets: List[SearchDataset], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze search dataset health."""
        disabled_datasets = [d for d in datasets if not d.enabled]

        if disabled_datasets:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-datasets-disabled",
                    category="search",
                    severity="low",
                    title=f"{len(disabled_datasets)} Disabled Dataset(s)",
                    description=(
                        f"Found {len(disabled_datasets)} disabled dataset(s): "
                        f"{', '.join(d.id for d in disabled_datasets[:5])}"
                    ),
                    affected_components=["Search"] + [d.id for d in disabled_datasets[:5]],
                    confidence_level="high",
                    metadata={
                        "disabled_count": len(disabled_datasets),
                        "disabled_ids": [d.id for d in disabled_datasets],
                    },
                )
            )

        orphan_datasets = [d for d in datasets if not d.provider]
        if orphan_datasets:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-datasets-no-provider",
                    category="search",
                    severity="medium",
                    title=f"{len(orphan_datasets)} Dataset(s) Without Provider",
                    description="Found dataset(s) without a configured provider.",
                    affected_components=["Search"] + [d.id for d in orphan_datasets[:5]],
                    remediation_steps=[
                        "Configure a data provider for each dataset",
                        "Remove datasets that are no longer needed",
                    ],
                    confidence_level="high",
                    metadata={
                        "orphan_count": len(orphan_datasets),
                        "orphan_ids": [d.id for d in orphan_datasets],
                    },
                )
            )

    def _analyze_groups(
        self, groups: List[SearchGroup], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze Search groups for configuration issues."""
        if not groups:
            return

        empty_groups = [g for g in groups if not g.datasets and not g.dashboards]

        if empty_groups:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-groups-empty",
                    category="search",
                    severity="info",
                    title=f"{len(empty_groups)} Empty Group(s)",
                    description="Found group(s) without datasets or dashboards.",
                    affected_components=["Search"] + [g.id for g in empty_groups[:5]],
                    confidence_level="high",
                    metadata={
                        "empty_count": len(empty_groups),
                        "empty_ids": [g.id for g in empty_groups],
                    },
                )
            )

    def _analyze_dashboards(
        self, dashboards: List[Dashboard], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze dashboard health."""
        empty_dashboards = [d for d in dashboards if not d.elements or len(d.elements) == 0]

        if empty_dashboards:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-dashboards-empty",
                    category="search",
                    severity="info",
                    title=f"{len(empty_dashboards)} Empty Dashboard(s)",
                    description="Found dashboard(s) without any elements.",
                    affected_components=["Search"] + [d.id for d in empty_dashboards[:5]],
                    confidence_level="high",
                    metadata={
                        "empty_count": len(empty_dashboards),
                        "empty_ids": [d.id for d in empty_dashboards],
                    },
                )
            )

        complex_dashboards = [d for d in dashboards if d.elements and len(d.elements) > 10]
        if complex_dashboards:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-dashboards-complex",
                    category="search",
                    severity="low",
                    title=f"{len(complex_dashboards)} Complex Dashboard(s)",
                    description="Found dashboard(s) with more than 10 elements. Large dashboards can be slow to load.",
                    affected_components=["Search"] + [d.id for d in complex_dashboards[:5]],
                    confidence_level="medium",
                    metadata={
                        "complex_count": len(complex_dashboards),
                        "complex_ids": [d.id for d in complex_dashboards],
                    },
                )
            )

        scheduled_dashboards = [d for d in dashboards if d.schedule and d.schedule.enabled]
        result.metadata["scheduled_dashboards"] = len(scheduled_dashboards)

    def _analyze_saved_searches(
        self, saved_searches: List[SavedSearch], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze saved search configurations."""
        if not saved_searches:
            return

        for saved in saved_searches:
            if not saved.query:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"search-saved-no-query-{saved.id}",
                        category="search",
                        severity="low",
                        title=f"Saved Search Without Query: {saved.id}",
                        description=f"Saved search '{saved.id}' has no query defined.",
                        affected_components=["Search", saved.id],
                        confidence_level="high",
                        remediation_steps=[
                            f"Update saved search '{saved.id}' with a valid query",
                            "Remove unused saved searches",
                        ],
                        metadata={"saved_search_id": saved.id},
                    )
                )

    def _analyze_cost(
        self, cost_data: SearchCost, result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze Search cost and resource consumption."""
        if cost_data.total_cost_usd and cost_data.total_cost_usd > 100.0:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-cost-high",
                    category="search",
                    severity="medium",
                    title=f"High Search Cost Detected: ${cost_data.total_cost_usd:.2f}",
                    description=(
                        f"Cribl Search cost for the last {cost_data.time_period_days} days is high."
                    ),
                    affected_components=["Search"],
                    confidence_level="high",
                    remediation_steps=[
                        "Identify top-cost queries in the Search usage dashboard",
                        "Review and optimize high-CPU queries",
                    ],
                    metadata={
                        "total_cost": cost_data.total_cost_usd,
                        "period_days": cost_data.time_period_days,
                        "cpu_seconds": cost_data.total_cpu_seconds,
                    },
                )
            )
