from datetime import datetime
from typing import List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.search import SearchHealthCheckList
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchHealthcheckAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "search_healthcheck"

    @property
    def supported_products(self) -> List[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> List[str]:
        return ["read:search:healthcheck"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            response = await client.get_search_healthcheck()
            status_list = SearchHealthCheckList(**response)
            statuses = status_list.items

            result.metadata.update(
                {
                    "status_count": len(statuses),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not statuses:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-healthcheck-empty",
                        category="search",
                        severity="info",
                        title="No Search Healthcheck Data",
                        description="Search healthcheck endpoint returned no data.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            for status in statuses:
                if str(status.status).lower() == "red":
                    reason = status.reason or "unknown"
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id="search-healthcheck-red",
                            category="search",
                            severity="critical",
                            title="Search Healthcheck Red",
                            description=f"Search healthcheck reported red status ({reason}).",
                            affected_components=["Search"],
                            confidence_level="high",
                            remediation_steps=[
                                "Check Search service health",
                                "Review recent Search errors",
                            ],
                            estimated_impact="Search may be unavailable or degraded",
                            metadata={
                                "reason": reason,
                                "reported_at": status.reported_at,
                            },
                        )
                    )

            result.success = True
        except Exception as exc:
            log.error("search_healthcheck_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-healthcheck-error",
                    category="search",
                    severity="critical",
                    title="Search Healthcheck Failed",
                    description=f"Failed to fetch search healthcheck data: {str(exc)}",
                    affected_components=["Search API"],
                    remediation_steps=["Verify Search API connectivity"],
                    estimated_impact="Search health cannot be assessed",
                    confidence_level="high",
                )
            )

        return result
