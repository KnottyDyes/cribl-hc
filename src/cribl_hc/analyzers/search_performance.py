"""
Search Performance Analyzer for Cribl Health Check.

Analyzes Cribl Search query performance, CPU costs, and optimization opportunities.

Priority: P2 (Important - cost optimization)
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
    SearchJob,
    SearchJobList,
)
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchPerformanceAnalyzer(BaseAnalyzer):
    """
    Analyzer for Cribl Search performance and cost optimization.

    Identifies:
    - Expensive queries consuming high CPU
    - Inefficient query patterns
    - Queries that could benefit from Lakehouse
    - Cost optimization opportunities

    Priority: P2 (Important - reduces search costs)
    """

    # CPU cost thresholds (billable CPU seconds)
    MODERATE_CPU_THRESHOLD = 30.0  # 30 seconds billable CPU
    HIGH_CPU_THRESHOLD = 60.0  # 1 minute billable CPU
    VERY_HIGH_CPU_THRESHOLD = 300.0  # 5 minutes billable CPU

    # Efficiency thresholds
    LOW_EFFICIENCY_RATIO = 0.5  # billable/total < 50% is inefficient
    VERY_LOW_EFFICIENCY_RATIO = 0.3  # billable/total < 30% is very inefficient

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "search"

    @property
    def supported_products(self) -> List[str]:
        """Search performance analyzer is specific to Cribl Search."""
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: jobs(1) + dashboards(1) = 2."""
        return 2

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return ["read:search:jobs", "read:search:dashboards"]

    async def analyze(self, client: CriblAPIClient, workspace: str = "default_search") -> AnalyzerResult:
        """
        Analyze Cribl Search performance and cost patterns.

        Args:
            client: Authenticated Cribl API client
            workspace: Search workspace name (default: "default_search")

        Returns:
            AnalyzerResult with Search performance findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("search_performance_analysis_started", workspace=workspace)

            # Fetch Search jobs and dashboards
            jobs_response = await client.get_search_jobs(workspace)
            dashboards_response = await client.get_search_dashboards(workspace)

            job_list = SearchJobList(**jobs_response)
            dashboard_list = DashboardList(**dashboards_response)

            jobs = job_list.items
            dashboards = dashboard_list.items

            # Filter to completed jobs with metrics
            completed_jobs = [
                j for j in jobs
                if j.status == "completed" and j.cpu_metrics
            ]

            # Calculate aggregate metrics
            total_billable_cpu = sum(
                j.cpu_metrics.billable_cpu_seconds or 0
                for j in completed_jobs
                if j.cpu_metrics
            )
            total_cpu = sum(
                j.cpu_metrics.total_cpu_seconds or 0
                for j in completed_jobs
                if j.cpu_metrics
            )

            # Initialize metadata
            result.metadata.update({
                "workspace": workspace,
                "total_jobs_analyzed": len(jobs),
                "completed_jobs_with_metrics": len(completed_jobs),
                "total_billable_cpu_seconds": round(total_billable_cpu, 2),
                "total_cpu_seconds": round(total_cpu, 2),
                "efficiency_ratio": round(total_billable_cpu / total_cpu, 2) if total_cpu > 0 else 1.0,
                "total_dashboards": len(dashboards),
                "analysis_timestamp": datetime.utcnow().isoformat()
            })

            # Handle empty state
            if not completed_jobs and not dashboards:
                result.add_finding(
                    Finding(
                        id="search-perf-no-jobs",
                        category="search",
                        severity="info",
                        title="No Completed Jobs for Performance Analysis",
                        description=f"No completed jobs with metrics found in workspace '{workspace}'.",
                        affected_components=["Search"],
                        confidence_level="high",
                        metadata={"workspace": workspace}
                    )
                )
                result.success = True
                return result

            # Analyze job performance patterns
            if completed_jobs:
                self._analyze_cpu_costs(completed_jobs, result)
                self._analyze_efficiency(completed_jobs, result)
                self._identify_optimization_opportunities(completed_jobs, result)

            # Analyze dashboard query patterns
            if dashboards:
                self._analyze_dashboard_queries(dashboards, result)

            # Add summary recommendations if significant costs found
            if total_billable_cpu > 600:  # More than 10 minutes total
                self._add_cost_summary_recommendation(total_billable_cpu, completed_jobs, result)

            result.success = True
            log.info(
                "search_performance_analysis_completed",
                workspace=workspace,
                jobs_analyzed=len(completed_jobs),
                total_billable_cpu=round(total_billable_cpu, 2),
                findings=len(result.findings),
                recommendations=len(result.recommendations)
            )

        except Exception as e:
            log.error("search_performance_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="search-perf-analysis-error",
                    category="search",
                    severity="critical",
                    title="Search Performance Analysis Failed",
                    description=f"Failed to analyze Search performance: {str(e)}",
                    affected_components=["Search API"],
                    remediation_steps=["Check API connectivity", "Verify Search workspace exists"],
                    estimated_impact="Cannot assess Search performance",
                    confidence_level="high",
                    metadata={"error": str(e)}
                )
            )

        return result

    def _analyze_cpu_costs(self, jobs: List[SearchJob], result: AnalyzerResult) -> None:
        """Analyze CPU costs across jobs."""
        high_cpu_jobs = []
        very_high_cpu_jobs = []

        for job in jobs:
            if not job.cpu_metrics:
                continue

            billable = job.cpu_metrics.billable_cpu_seconds or 0

            if billable >= self.VERY_HIGH_CPU_THRESHOLD:
                very_high_cpu_jobs.append((job, billable))
            elif billable >= self.HIGH_CPU_THRESHOLD:
                high_cpu_jobs.append((job, billable))

        # Report very high CPU jobs
        if very_high_cpu_jobs:
            result.metadata["very_high_cpu_jobs"] = len(very_high_cpu_jobs)
            for job, billable in very_high_cpu_jobs[:5]:  # Limit to top 5
                result.add_finding(
                    Finding(
                        id=f"search-perf-very-high-cpu-{job.id}",
                        category="search",
                        severity="high",
                        title=f"Very High CPU Query: {job.id}",
                        description=(
                            f"Query consumed {round(billable, 1)} billable CPU seconds. "
                            "This is significantly above normal and should be optimized."
                        ),
                        affected_components=["Search", job.id],
                        remediation_steps=[
                            "Review query for optimization opportunities",
                            "Add time filters to reduce data scanned",
                            "Use more specific dataset filters",
                            "Consider Lakehouse for frequently queried datasets"
                        ],
                        estimated_impact=f"{round(billable, 1)} CPU seconds per execution",
                        confidence_level="high",
                        metadata={
                            "job_id": job.id,
                            "query": job.query,
                            "billable_cpu_seconds": round(billable, 2)
                        }
                    )
                )

        # Report high CPU jobs
        if high_cpu_jobs:
            result.metadata["high_cpu_jobs"] = len(high_cpu_jobs)
            for job, billable in high_cpu_jobs[:5]:  # Limit to top 5
                result.add_finding(
                    Finding(
                        id=f"search-perf-high-cpu-{job.id}",
                        category="search",
                        severity="medium",
                        title=f"High CPU Query: {job.id}",
                        description=(
                            f"Query consumed {round(billable, 1)} billable CPU seconds."
                        ),
                        affected_components=["Search", job.id],
                        remediation_steps=[
                            "Review query complexity",
                            "Consider adding filters to reduce scan scope",
                            "Use indexed fields when available"
                        ],
                        estimated_impact=f"{round(billable, 1)} CPU seconds per execution",
                        confidence_level="high",
                        metadata={
                            "job_id": job.id,
                            "query": job.query,
                            "billable_cpu_seconds": round(billable, 2)
                        }
                    )
                )

    def _analyze_efficiency(self, jobs: List[SearchJob], result: AnalyzerResult) -> None:
        """Analyze query efficiency (billable vs total CPU)."""
        inefficient_jobs = []

        for job in jobs:
            if not job.cpu_metrics:
                continue

            total = job.cpu_metrics.total_cpu_seconds or 0
            billable = job.cpu_metrics.billable_cpu_seconds or 0

            if total <= 0:
                continue

            efficiency = billable / total

            if efficiency < self.VERY_LOW_EFFICIENCY_RATIO:
                inefficient_jobs.append((job, efficiency, billable, total))

        if inefficient_jobs:
            result.metadata["inefficient_jobs"] = len(inefficient_jobs)

            # Report top inefficient jobs
            for job, efficiency, billable, total in inefficient_jobs[:3]:
                result.add_finding(
                    Finding(
                        id=f"search-perf-inefficient-{job.id}",
                        category="search",
                        severity="medium",
                        title=f"Inefficient Query: {job.id}",
                        description=(
                            f"Query has {round(efficiency * 100)}% efficiency ratio "
                            f"(billable: {round(billable, 1)}s, total: {round(total, 1)}s). "
                            "High overhead may indicate query optimization opportunities."
                        ),
                        affected_components=["Search", job.id],
                        remediation_steps=[
                            "Review query structure for inefficiencies",
                            "Check if query is scanning unnecessary data",
                            "Consider using more selective filters"
                        ],
                        estimated_impact="Reduced query efficiency",
                        confidence_level="medium",
                        metadata={
                            "job_id": job.id,
                            "query": job.query,
                            "efficiency_ratio": round(efficiency, 2),
                            "billable_cpu": round(billable, 2),
                            "total_cpu": round(total, 2)
                        }
                    )
                )

    def _identify_optimization_opportunities(
        self, jobs: List[SearchJob], result: AnalyzerResult
    ) -> None:
        """Identify query optimization opportunities."""
        # Analyze query patterns for common anti-patterns
        wildcard_queries = []
        no_time_filter_queries = []

        for job in jobs:
            if not job.query:
                continue

            query = job.query.lower()

            # Check for wildcard dataset usage
            if "dataset='*'" in query or 'dataset="*"' in query:
                wildcard_queries.append(job)

            # Check for missing time filters (common issue)
            if "earliest" not in query and "latest" not in query:
                if job.earliest is None and job.latest is None:
                    no_time_filter_queries.append(job)

        # Report wildcard dataset usage
        if wildcard_queries:
            result.add_finding(
                Finding(
                    id="search-perf-wildcard-datasets",
                    category="search",
                    severity="medium",
                    title=f"{len(wildcard_queries)} Query/Queries Using Wildcard Datasets",
                    description=(
                        "Queries using dataset='*' scan all datasets, "
                        "increasing CPU costs and query time."
                    ),
                    affected_components=["Search"] + [j.id for j in wildcard_queries[:5]],
                    remediation_steps=[
                        "Specify exact dataset names in queries",
                        "Use dataset filters to limit scope",
                        "Create saved searches with specific datasets"
                    ],
                    estimated_impact="Increased CPU usage and costs",
                    confidence_level="high",
                    metadata={
                        "wildcard_query_count": len(wildcard_queries),
                        "example_queries": [j.query for j in wildcard_queries[:3]]
                    }
                )
            )

            result.add_recommendation(
                Recommendation(
                    id="rec-search-perf-avoid-wildcards",
                    type="optimization",
                    priority="p2",
                    title="Replace Wildcard Dataset Queries",
                    description=(
                        f"Found {len(wildcard_queries)} queries using dataset='*'. "
                        "Specifying datasets reduces CPU costs."
                    ),
                    rationale="Wildcard queries scan all datasets, consuming more resources.",
                    implementation_steps=[
                        "Identify specific datasets needed for each query",
                        "Update queries to use explicit dataset names",
                        "Create saved searches for common query patterns"
                    ],
                    before_state=f"{len(wildcard_queries)} queries with wildcard datasets",
                    after_state="All queries with specific dataset filters",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Reduced query CPU usage"
                    ),
                    implementation_effort="low",
                    product_tags=["search"]
                )
            )

    def _add_cost_summary_recommendation(
        self,
        total_billable_cpu: float,
        jobs: List[SearchJob],
        result: AnalyzerResult
    ) -> None:
        """Add summary recommendation for overall cost optimization."""
        # Find top CPU consumers
        sorted_jobs = sorted(
            [j for j in jobs if j.cpu_metrics],
            key=lambda j: j.cpu_metrics.billable_cpu_seconds or 0,
            reverse=True
        )

        top_consumers = sorted_jobs[:5]
        top_cpu = sum(
            j.cpu_metrics.billable_cpu_seconds or 0
            for j in top_consumers
            if j.cpu_metrics
        )

        result.add_recommendation(
            Recommendation(
                id="rec-search-perf-cost-optimization",
                type="optimization",
                priority="p1",
                title="Optimize Top CPU-Consuming Queries",
                description=(
                    f"Total billable CPU: {round(total_billable_cpu, 1)} seconds. "
                    f"Top 5 queries account for {round(top_cpu, 1)} seconds "
                    f"({round(top_cpu / total_billable_cpu * 100, 1)}% of total)."
                ),
                rationale="Optimizing high-CPU queries provides the best cost reduction ROI.",
                implementation_steps=[
                    "Review the top CPU-consuming queries identified in findings",
                    "Add time range filters to limit data scanned",
                    "Use specific dataset names instead of wildcards",
                    "Consider creating Lakehouse indexes for frequently queried data",
                    "Schedule resource-intensive queries during off-peak hours"
                ],
                before_state=f"{round(total_billable_cpu, 1)} CPU seconds across {len(jobs)} queries",
                after_state="Optimized queries with reduced CPU consumption",
                impact_estimate=ImpactEstimate(
                    cost_savings_monthly=round(total_billable_cpu * 0.001 * 30, 2),
                    performance_improvement="Faster query execution, reduced costs"
                ),
                implementation_effort="medium",
                product_tags=["search"]
            )
        )

    def _analyze_dashboard_queries(
        self, dashboards: List[Dashboard], result: AnalyzerResult
    ) -> None:
        """Analyze dashboard element queries for efficiency issues."""
        dashboards_with_wildcards = []
        dashboards_without_time_filters = []
        total_elements_analyzed = 0

        for dashboard in dashboards:
            if not dashboard.elements:
                continue

            dashboard_has_wildcard = False
            dashboard_missing_time_filter = False

            for element in dashboard.elements:
                if not element.query:
                    continue

                total_elements_analyzed += 1
                query = element.query.lower()

                # Check for wildcard dataset usage
                if "dataset='*'" in query or 'dataset="*"' in query:
                    dashboard_has_wildcard = True

                # Check for missing time filters in query
                if "earliest" not in query and "latest" not in query:
                    dashboard_missing_time_filter = True

            if dashboard_has_wildcard:
                dashboards_with_wildcards.append(dashboard)
            if dashboard_missing_time_filter:
                dashboards_without_time_filters.append(dashboard)

        result.metadata["dashboard_elements_analyzed"] = total_elements_analyzed

        # Report dashboards with wildcard queries
        if dashboards_with_wildcards:
            result.metadata["dashboards_with_wildcards"] = len(dashboards_with_wildcards)
            result.add_finding(
                Finding(
                    id="search-perf-dashboard-wildcards",
                    category="search",
                    severity="medium",
                    title=f"{len(dashboards_with_wildcards)} Dashboard(s) Using Wildcard Datasets",
                    description=(
                        "Dashboard queries using dataset='*' scan all datasets on every refresh, "
                        "significantly increasing CPU costs for scheduled dashboards."
                    ),
                    affected_components=["Search"] + [d.id for d in dashboards_with_wildcards[:5]],
                    remediation_steps=[
                        "Edit dashboard elements to use specific dataset names",
                        "Review scheduled dashboards for cost impact",
                        "Consider splitting dashboards by dataset"
                    ],
                    estimated_impact="High CPU usage on dashboard refresh",
                    confidence_level="high",
                    metadata={
                        "dashboard_count": len(dashboards_with_wildcards),
                        "dashboard_ids": [d.id for d in dashboards_with_wildcards]
                    }
                )
            )

            result.add_recommendation(
                Recommendation(
                    id="rec-search-perf-dashboard-wildcards",
                    type="optimization",
                    priority="p2",
                    title="Optimize Dashboard Queries",
                    description=(
                        f"Found {len(dashboards_with_wildcards)} dashboards with wildcard dataset queries. "
                        "Scheduled dashboards with wildcards can be very expensive."
                    ),
                    rationale="Dashboard queries run on every refresh; optimizing reduces ongoing costs.",
                    implementation_steps=[
                        "Navigate to Search > Dashboards",
                        "Edit each dashboard element's query to use specific datasets",
                        "Test dashboard after changes to verify data is still correct",
                        "Monitor CPU usage after optimization"
                    ],
                    before_state=f"{len(dashboards_with_wildcards)} dashboards with wildcard queries",
                    after_state="Dashboards with specific dataset filters",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Reduced CPU usage per dashboard refresh"
                    ),
                    implementation_effort="medium",
                    product_tags=["search"]
                )
            )
