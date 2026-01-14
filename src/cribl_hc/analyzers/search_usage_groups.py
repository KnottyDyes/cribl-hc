
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

    async def analyze(
        self, client: CriblAPIClient, workspace: str = "default_search"
    ) -> AnalyzerResult:
        result = self.create_result()

        try:
            groups_response = await client.get_search_groups(workspace)
            if isinstance(groups_response, dict) and "count" not in groups_response:
                groups_response = {
                    **groups_response,
                    "count": len(groups_response.get("items", [])),
                }
            group_list = SearchGroupList(**groups_response)
            groups = group_list.items

            result.metadata.update(
                {
                    "workspace": workspace,
                    "total_groups": len(groups),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not groups:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-groups-none",
                        category="search",
                        severity="info",
                        title="No Search Usage Groups Found",
                        description=f"No usage groups configured in workspace '{workspace}'.",
                        affected_components=["Search"],
                        confidence_level="high",
                        metadata={"workspace": workspace},
                    )
                )
                result.success = True
                return result

            self._analyze_group_allocations(groups, result, client)
            result.success = True
        except Exception as exc:
            log.error("search_usage_groups_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-groups-analysis-error",
                    category="search",
                    severity="critical",
                    title="Search Usage Group Analysis Failed",
                    description=f"Failed to analyze usage groups: {str(exc)}",
                    affected_components=["Search API"],
                    remediation_steps=["Verify Search API connectivity"],
                    estimated_impact="Search usage group analysis unavailable",
                    confidence_level="high",
                )
            )

        return result

    def _analyze_group_allocations(
        self, groups: list[SearchGroup], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        empty_groups = [g for g in groups if not g.datasets and not g.dashboards]
        if empty_groups:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-groups-empty",
                    category="search",
                    severity="info",
                    title=f"{len(empty_groups)} Empty Usage Group(s)",
                    description="Found usage group(s) without datasets or dashboards.",
                    affected_components=["Search"] + [g.id for g in empty_groups[:5]],
                    confidence_level="high",
                    metadata={
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
                    id="search-groups-large",
                    category="search",
                    severity="low",
                    title=f"{len(large_groups)} Large Usage Group(s)",
                    description="Some usage groups reference 25+ datasets/dashboards. Consider splitting for clarity.",
                    affected_components=["Search"] + [g.id for g in large_groups[:5]],
                    confidence_level="medium",
                    metadata={
                        "large_count": len(large_groups),
                        "large_ids": [g.id for g in large_groups],
                    },
                )
            )
