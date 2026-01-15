"""
Analyzes Cribl Search workspace organization, saved search usage patterns, and dashboard efficiency.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class SavedSearchInfo(BaseModel):
    """Represents a saved search with metadata."""

    id: str
    name: str
    query: str
    dataset: str
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    avg_execution_time: Optional[float] = None
    cost_estimate: Optional[float] = None

    @property
    def is_wildcard_dataset(self) -> bool:
        """Check if search uses wildcard dataset."""
        return "*" in self.dataset or "?" in self.dataset

    @property
    def days_since_last_run(self) -> Optional[int]:
        """Calculate days since last execution."""
        if not self.last_run:
            return None
        return (datetime.now() - self.last_run).days


class DashboardInfo(BaseModel):
    """Represents a dashboard with metadata."""

    id: str
    name: str
    panels: List[Dict[str, Any]] = Field(default_factory=list)
    queries: List[str] = Field(default_factory=list)
    last_accessed: Optional[datetime] = None
    access_count: int = 0

    @property
    def total_queries(self) -> int:
        """Get total number of queries in dashboard."""
        return len(self.queries)

    @property
    def has_wildcard_queries(self) -> bool:
        """Check if dashboard contains wildcard queries."""
        return any("*" in query or "?" in query for query in self.queries)


class DatasetInfo(BaseModel):
    """Represents a dataset with usage statistics."""

    name: str
    type: str
    size_bytes: Optional[int] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    query_count: int = 0

    @property
    def is_unused(self) -> bool:
        """Check if dataset appears unused."""
        return self.access_count == 0 and (
            self.last_accessed is None or (datetime.now() - self.last_accessed).days > 30
        )


class SearchWorkspaceOptimizationAnalyzer(BaseAnalyzer):
    """
    Analyzes Cribl Search workspace organization, saved search usage patterns,
    and dashboard efficiency to identify optimization opportunities.
    """

    @property
    def objective_name(self) -> str:
        return "search-workspace-optimization"

    def get_description(self) -> str:
        return "Analyzes Search workspace organization, saved search patterns, and dashboard efficiency for optimization opportunities."

    def get_required_permissions(self) -> List[str]:
        return [
            "read:search",
            "read:datasets",
            "read:dashboards",
            "read:saved-searches",
            "read:audit",
        ]

    @property
    def supported_products(self) -> list[str]:
        return ["search"]  # Search-specific analyzer

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis on Search workspace optimization.
        """
        result = self.create_result()

        try:
            # Collect workspace data
            saved_searches = await self._get_saved_searches(client)
            dashboards = await self._get_dashboards(client)
            datasets = await self._get_datasets(client)
            workspace_audit = await self._get_workspace_audit(client)

            if not any([saved_searches, dashboards, datasets]):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="no-search-assets-found",
                        category="Configuration",
                        severity="info",
                        title="No Search Assets Found",
                        description="No saved searches, dashboards, or datasets found in the Search workspace.",
                        confidence_level="high",
                        affected_components=["search_workspace"],
                        remediation_steps=[
                            "Verify Search workspace configuration and API access.",
                            "Ensure Search service is properly configured and running.",
                        ],
                    )
                )
                return result

            # Perform various analyses
            self._analyze_saved_search_efficiency(result, saved_searches, client)
            self._analyze_dashboard_optimization(result, dashboards, client)
            self._analyze_dataset_utilization(result, datasets, client)
            self._check_workspace_organization(result, saved_searches, dashboards, client)
            self._assess_cost_efficiency(result, saved_searches, workspace_audit, client)

        except Exception as e:
            self.log.error(
                f"Error during Search workspace optimization analysis: {e}", exc_info=True
            )
            result.success = False
            result.error = str(e)

        return result

    async def _get_saved_searches(self, client: CriblAPIClient) -> List[SavedSearchInfo]:
        """Fetch saved searches with metadata."""
        searches = []

        try:
            # Get saved searches from default workspace
            response = await client.get("/api/v1/m/default/search/saved-searches")
            search_data = response.get("items", [])

            for search_item in search_data:
                # Parse timestamps
                created_at = None
                last_run = None

                if created_str := search_item.get("createdAt"):
                    try:
                        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                if last_run_str := search_item.get("lastExecuted"):
                    try:
                        last_run = datetime.fromisoformat(last_run_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                search = SavedSearchInfo(
                    id=search_item.get("id", ""),
                    name=search_item.get("name", ""),
                    query=search_item.get("query", ""),
                    dataset=search_item.get("dataset", ""),
                    created_at=created_at,
                    last_run=last_run,
                    run_count=search_item.get("executionCount", 0),
                    avg_execution_time=search_item.get("avgExecutionTimeMs"),
                    cost_estimate=search_item.get("estimatedCostPerMonth"),
                )
                searches.append(search)

        except Exception as e:
            self.log.debug(f"Could not fetch saved searches: {e}")

        return searches

    async def _get_dashboards(self, client: CriblAPIClient) -> List[DashboardInfo]:
        """Fetch dashboards with panel and query analysis."""
        dashboards = []

        try:
            response = await client.get("/api/v1/m/default/search/dashboards")
            dashboard_data = response.get("items", [])

            for dash_item in dashboard_data:
                # Extract queries from dashboard panels
                panels = dash_item.get("panels", [])
                queries = []

                for panel in panels:
                    if panel_query := panel.get("query"):
                        queries.append(panel_query)

                # Parse last accessed timestamp
                last_accessed = None
                if accessed_str := dash_item.get("lastAccessed"):
                    try:
                        last_accessed = datetime.fromisoformat(accessed_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                dashboard = DashboardInfo(
                    id=dash_item.get("id", ""),
                    name=dash_item.get("name", ""),
                    panels=panels,
                    queries=queries,
                    last_accessed=last_accessed,
                    access_count=dash_item.get("accessCount", 0),
                )
                dashboards.append(dashboard)

        except Exception as e:
            self.log.debug(f"Could not fetch dashboards: {e}")

        return dashboards

    async def _get_datasets(self, client: CriblAPIClient) -> List[DatasetInfo]:
        """Fetch datasets with usage statistics."""
        datasets = []

        try:
            response = await client.get("/api/v1/m/default/search/datasets")
            dataset_data = response.get("items", [])

            for ds_item in dataset_data:
                # Parse last accessed timestamp
                last_accessed = None
                if accessed_str := ds_item.get("lastAccessed"):
                    try:
                        last_accessed = datetime.fromisoformat(accessed_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                dataset = DatasetInfo(
                    name=ds_item.get("name", ""),
                    type=ds_item.get("type", "unknown"),
                    size_bytes=ds_item.get("sizeBytes"),
                    last_accessed=last_accessed,
                    access_count=ds_item.get("accessCount", 0),
                    query_count=ds_item.get("queryCount", 0),
                )
                datasets.append(dataset)

        except Exception as e:
            self.log.debug(f"Could not fetch datasets: {e}")

        return datasets

    async def _get_workspace_audit(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch workspace audit logs for usage analysis."""
        audit_data = {}

        try:
            response = await client.get("/api/v1/m/default/system/audit", params={"limit": 1000})
            audit_data = response.get("items", [])
        except Exception as e:
            self.log.debug(f"Could not fetch workspace audit logs: {e}")

        return {"entries": audit_data}

    def _analyze_saved_search_efficiency(
        self, result: AnalyzerResult, searches: List[SavedSearchInfo], client: CriblAPIClient
    ) -> None:
        """Analyze saved search efficiency and optimization opportunities."""
        for search in searches:
            # Check for wildcard dataset usage
            if search.is_wildcard_dataset:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"wildcard-dataset-search-{search.id}",
                        category="Performance",
                        severity="high",
                        title="Inefficient Wildcard Dataset Search",
                        description=f"Saved search '{search.name}' uses wildcard dataset '{search.dataset}', which can impact performance.",
                        confidence_level="high",
                        affected_components=["search_performance"],
                        remediation_steps=[
                            "Replace wildcard dataset with specific dataset names.",
                            f"Consider using dataset filters instead of '{search.dataset}'.",
                            "Test query performance after dataset specification.",
                        ],
                    )
                )

            # Check for unused expensive searches
            days_unused = search.days_since_last_run
            if days_unused and days_unused > 30:
                cost_indicator = ""
                if search.cost_estimate and search.cost_estimate > 50:
                    cost_indicator = f" (estimated ${search.cost_estimate:.0f}/month)"

                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"unused-expensive-search-{search.id}",
                        category="Cost",
                        severity="medium",
                        title="Unused Costly Saved Search",
                        description=f"Saved search '{search.name}' hasn't been run for {days_unused} days{cost_indicator}.",
                        confidence_level="high",
                        affected_components=["search_costs"],
                        remediation_steps=[
                            "Review if this saved search is still needed.",
                            "Consider archiving or deleting unused searches.",
                            "Document business justification for expensive unused searches.",
                        ],
                    )
                )

            # Check for high-cost searches with low usage
            if search.cost_estimate and search.cost_estimate > 100 and search.run_count < 10:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"high-cost-low-usage-search-{search.id}",
                        category="Cost",
                        severity="high",
                        title="High-Cost, Low-Usage Search",
                        description=f"Saved search '{search.name}' costs ~${search.cost_estimate:.0f}/month but only runs {search.run_count} times.",
                        confidence_level="high",
                        affected_components=["search_costs", "search_performance"],
                        remediation_steps=[
                            "Evaluate if the search provides sufficient business value.",
                            "Consider optimizing the query to reduce execution costs.",
                            "Review execution frequency vs. business requirements.",
                        ],
                    )
                )

    def _analyze_dashboard_optimization(
        self, result: AnalyzerResult, dashboards: List[DashboardInfo], client: CriblAPIClient
    ) -> None:
        """Analyze dashboard efficiency and optimization opportunities."""
        for dashboard in dashboards:
            # Check for dashboards with wildcard queries
            if dashboard.has_wildcard_queries:
                wildcard_count = sum(1 for q in dashboard.queries if "*" in q or "?" in q)
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"dashboard-wildcard-queries-{dashboard.id}",
                        category="Performance",
                        severity="medium",
                        title="Dashboard with Wildcard Queries",
                        description=f"Dashboard '{dashboard.name}' contains {wildcard_count} wildcard queries out of {dashboard.total_queries} total.",
                        confidence_level="high",
                        affected_components=["dashboard_performance"],
                        remediation_steps=[
                            "Replace wildcard queries with specific dataset references.",
                            "Use dataset filters to narrow query scope.",
                            "Consider creating targeted dashboards for specific datasets.",
                        ],
                    )
                )

            # Check for unused dashboards
            days_unused = None
            if dashboard.last_accessed:
                days_unused = (datetime.now() - dashboard.last_accessed).days

            if days_unused and days_unused > 60 and dashboard.access_count < 5:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"unused-dashboard-{dashboard.id}",
                        category="Maintenance",
                        severity="low",
                        title="Unused Dashboard",
                        description=f"Dashboard '{dashboard.name}' hasn't been accessed for {days_unused} days (only {dashboard.access_count} accesses).",
                        confidence_level="high",
                        affected_components=["dashboard_maintenance"],
                        remediation_steps=[
                            "Review if dashboard is still needed.",
                            "Consider archiving or deleting unused dashboards.",
                            "Communicate with dashboard users before removal.",
                        ],
                    )
                )

    def _analyze_dataset_utilization(
        self, result: AnalyzerResult, datasets: List[DatasetInfo], client: CriblAPIClient
    ) -> None:
        """Analyze dataset utilization and identify unused datasets."""
        for dataset in datasets:
            if dataset.is_unused:
                size_info = ""
                if dataset.size_bytes:
                    size_info = f" ({dataset.size_bytes / (1024 * 1024):.1f}MB)"

                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"unused-dataset-{dataset.name.replace('/', '-')}",
                        category="Storage",
                        severity="medium",
                        title="Unused Dataset",
                        description=f"Dataset '{dataset.name}' appears unused{size_info} - no recent access or queries.",
                        confidence_level="medium",
                        affected_components=["dataset_storage", "search_workspace"],
                        remediation_steps=[
                            "Verify dataset is not used by automated processes.",
                            "Consider archiving or deleting unused datasets.",
                            "Review dataset retention policies.",
                        ],
                    )
                )

    def _check_workspace_organization(
        self,
        result: AnalyzerResult,
        searches: List[SavedSearchInfo],
        dashboards: List[DashboardInfo],
        client: CriblAPIClient,
    ) -> None:
        """Check workspace organization and naming consistency."""
        # Check for naming consistency issues
        all_names = [s.name for s in searches] + [d.name for d in dashboards]

        # Look for inconsistent naming patterns
        prefixes = {}
        for name in all_names:
            if "_" in name:
                prefix = name.split("_")[0].lower()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
            elif name.startswith(("prod", "dev", "test", "staging")):
                prefix = name[:4].lower()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1

        # Flag inconsistent naming if we have mixed patterns
        if len(prefixes) > 3 and max(prefixes.values()) < len(all_names) * 0.6:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="inconsistent-naming-conventions",
                    category="Organization",
                    severity="low",
                    title="Inconsistent Naming Conventions",
                    description=f"Workspace contains {len(all_names)} assets with inconsistent naming patterns.",
                    confidence_level="medium",
                    affected_components=["workspace_organization"],
                    remediation_steps=[
                        "Establish consistent naming conventions for searches and dashboards.",
                        "Document naming standards in workspace guidelines.",
                        "Consider renaming existing assets to follow standards.",
                    ],
                )
            )

        # Check for duplicate names
        name_counts = {}
        for name in all_names:
            name_counts[name] = name_counts.get(name, 0) + 1

        duplicates = [(name, count) for name, count in name_counts.items() if count > 1]
        if duplicates:
            duplicate_info = ", ".join([f"'{name}' ({count}x)" for name, count in duplicates[:3]])
            if len(duplicates) > 3:
                duplicate_info += f" (+{len(duplicates) - 3} more)"

            result.add_finding(
                self.create_finding(
                    client=client,
                    id="duplicate-asset-names",
                    category="Organization",
                    severity="medium",
                    title="Duplicate Asset Names",
                    description=f"Found duplicate names in workspace: {duplicate_info}.",
                    confidence_level="high",
                    affected_components=["workspace_organization"],
                    remediation_steps=[
                        "Rename duplicate assets to have unique names.",
                        "Establish naming conventions to prevent future duplicates.",
                        "Review if duplicates serve different purposes.",
                    ],
                )
            )

    def _assess_cost_efficiency(
        self,
        result: AnalyzerResult,
        searches: List[SavedSearchInfo],
        audit_data: Dict[str, Any],
        client: CriblAPIClient,
    ) -> None:
        """Assess overall cost efficiency of the Search workspace."""
        # Calculate total estimated monthly cost
        total_cost = sum(s.cost_estimate or 0 for s in searches if s.cost_estimate)
        high_cost_searches = [s for s in searches if s.cost_estimate and s.cost_estimate > 100]

        if total_cost > 1000:  # High cost threshold
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="high-search-cost-workspace",
                    category="Cost",
                    severity="high",
                    title="High Search Cost Workspace",
                    description=f"Workspace has estimated monthly search costs of ${total_cost:.0f} across {len(searches)} saved searches.",
                    confidence_level="high",
                    affected_components=["search_costs", "workspace_budget"],
                    remediation_steps=[
                        "Review and optimize high-cost saved searches.",
                        f"Found {len(high_cost_searches)} searches costing >$100/month each.",
                        "Consider dataset partitioning to reduce query scope.",
                        "Implement query result caching where appropriate.",
                    ],
                )
            )

        # Check for cost optimization opportunities
        inefficient_searches = [
            s for s in searches if s.is_wildcard_dataset and (s.cost_estimate or 0) > 50
        ]
        if inefficient_searches:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="cost-optimization-opportunities",
                    category="Cost",
                    severity="medium",
                    title="Search Cost Optimization Opportunities",
                    description=f"Found {len(inefficient_searches)} inefficient searches using wildcards with high costs.",
                    confidence_level="high",
                    affected_components=["search_costs", "search_performance"],
                    remediation_steps=[
                        "Replace wildcard datasets with specific dataset references.",
                        "Implement dataset filters to reduce query scope.",
                        "Review query patterns for optimization opportunities.",
                    ],
                )
            )
