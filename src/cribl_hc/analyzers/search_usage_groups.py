"""
Search Usage Groups Analyzer for Cribl Health Check.

Analyzes Search usage groups for allocation and configuration hygiene.

Priority: P3 (Cost allocation and access hygiene)
"""

from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.search import SearchGroup, SearchGroupList
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchUsageGroupsAnalyzer(BaseAnalyzer):
    """Analyzer for Search usage group configuration."""

    @property
    def objective_name(self) -> str:
        return "search_usage_groups"

    @property
    def supported_products(self) -> list[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:search:groups"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            workspaces = await client.get_search_workspaces()
            if not workspaces:
                result.success = True
                result.metadata["message"] = "No search workspaces found or Search is disabled."
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-not-enabled-or-no-workspaces",
                        category="search",
                        severity="info",
                        title="Search Not Enabled or No Workspaces Found",
                        description="Cribl Search appears to be disabled or no search workspaces are configured.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )
                return result

            total_groups_found = 0
            for workspace in workspaces:
                groups_response = await client.get_search_groups(workspace)
                groups_list = SearchGroupList(**groups_response)
                workspace_groups = groups_list.items
                total_groups_found += len(workspace_groups)

                if not workspace_groups:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"search-groups-none-{workspace}",
                            category="search",
                            severity="info",
                            title=f"No Search Usage Groups Found in '{workspace}'",
                            description=f"No usage groups configured in workspace '{workspace}'.",
                            affected_components=["Search"],
                            confidence_level="high",
                            metadata={"workspace": workspace},
                        )
                    )
                else:
                    self._analyze_group_allocations(workspace_groups, result, client, workspace)

            result.metadata.update(
                {
                    "workspaces_analyzed": workspaces,
                    "total_groups": total_groups_found,
                }
            )
            result.success = True

        except Exception as exc:
            error_str = str(exc)
            if "404" in error_str:
                log.info("search_usage_groups_404", error=error_str)
                result.success = True
                result.metadata["error"] = "Search not enabled or workspace not found"
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-not-enabled",
                        category="search",
                        severity="info",
                        title="Search Not Enabled",
                        description="Cribl Search appears to be disabled or workspace not found.",
                        affected_components=["Search"],
                        confidence_level="high",
                        metadata={"error": error_str},
                    )
                )
            else:
                log.error("search_usage_groups_failed", error=error_str)
                result.success = False
                result.metadata["error"] = error_str
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-groups-analysis-error",
                        category="search",
                        severity="critical",
                        title="Search Usage Group Analysis Failed",
                        description=f"Failed to analyze usage groups: {error_str}",
                        affected_components=["Search API"],
                        remediation_steps=["Verify Search API connectivity"],
                        estimated_impact="Search usage group analysis unavailable",
                        confidence_level="high",
                    )
                )

        return result

    def _analyze_group_allocations(
        self,
        groups: list[SearchGroup],
        result: AnalyzerResult,
        client: CriblAPIClient,
        workspace: str,
    ) -> None:
        empty_groups = [g for g in groups if not g.datasets and not g.dashboards]
        if empty_groups:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"search-groups-empty-{workspace}",
                    category="search",
                    severity="info",
                    title=f"{len(empty_groups)} Empty Usage Group(s) in '{workspace}'",
                    description=f"Found usage group(s) in workspace '{workspace}' without datasets or dashboards.",
                    affected_components=["Search"] + [g.id for g in empty_groups[:5]],
                    confidence_level="high",
                    metadata={
                        "workspace": workspace,
                        "empty_count": len(empty_groups),
                        "empty_ids": [g.id for g in empty_groups],
                    },
                )
            )

        large_groups = [g for g in groups if (len(g.datasets or []) + len(g.dashboards or [])) > 25]
        if large_groups:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"search-groups-large-{workspace}",
                    category="search",
                    severity="low",
                    title=f"{len(large_groups)} Large Usage Group(s) in '{workspace}'",
                    description=f"Some usage groups in workspace '{workspace}' reference 25+ datasets/dashboards. Consider splitting for clarity.",
                    affected_components=["Search"] + [g.id for g in large_groups[:5]],
                    confidence_level="medium",
                    metadata={
                        "workspace": workspace,
                        "large_count": len(large_groups),
                        "large_ids": [g.id for g in large_groups],
                    },
                )
            )
