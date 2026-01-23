from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchJobMetricsAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "search_job_metrics"

    @property
    def supported_products(self) -> list[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:search:jobs"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            response = await client.get_search_job_metrics()

            items = []
            if isinstance(response, dict):
                items = response.get("items", []) or response.get("metrics", [])
            elif isinstance(response, list):
                items = response

            result.metadata.update(
                {
                    "metric_count": len(items),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not items:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-job-metrics-empty",
                        category="search",
                        severity="info",
                        title="No Search Job Metrics",
                        description="Search job metrics endpoint returned no data.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            error_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                status = str(item.get("status", "")).lower()
                error = item.get("error") or item.get("errors")
                if error or status in {"error", "failed"}:
                    error_items.append(item)

            if error_items:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-job-metrics-errors",
                        category="search",
                        severity="high",
                        title=f"Search Job Metrics Errors ({len(error_items)})",
                        description="Search job metrics report error states for recent jobs.",
                        affected_components=["Search"],
                        confidence_level="high",
                        remediation_steps=[
                            "Inspect failed job metrics for root cause",
                            "Review Search logs for persistent errors",
                        ],
                        estimated_impact="Search jobs may be failing or unstable",
                        metadata={"error_count": len(error_items)},
                    )
                )

            result.success = True
        except Exception as exc:
            error_str = str(exc)
            if "404" in error_str:
                log.info("search_job_metrics_404")
                result.success = True
                result.metadata["error"] = "Search not enabled or metrics endpoint not found"
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-metrics-not-enabled",
                        category="search",
                        severity="info",
                        title="Search Job Metrics Not Available",
                        description="Cribl Search appears to be disabled or job metrics unavailable.",
                        affected_components=["Search"],
                        confidence_level="high",
                        metadata={"error": error_str},
                    )
                )
            else:
                log.error("search_job_metrics_failed", error=error_str)
                result.success = False
                result.metadata["error"] = error_str
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-job-metrics-error",
                        category="search",
                        severity="critical",
                        title="Search Job Metrics Failed",
                        description=f"Failed to fetch search job metrics: {error_str}",
                        affected_components=["Search API"],
                        remediation_steps=["Verify Search API connectivity"],
                        estimated_impact="Search metrics cannot be assessed",
                        confidence_level="high",
                    )
                )

        return result
