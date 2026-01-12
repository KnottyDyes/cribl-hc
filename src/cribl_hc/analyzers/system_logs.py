from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemLogsAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "system_logs"

    @property
    def supported_products(self) -> List[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 2

    def get_required_permissions(self) -> List[str]:
        return ["read:system"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            logs = await client.get_system_logs()
            result.metadata.update(
                {
                    "log_count": len(logs),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not logs:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-logs-none",
                        category="system",
                        severity="info",
                        title="No System Logs Available",
                        description="System logs endpoint returned no log files.",
                        affected_components=["system"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            error_items = await client.search_system_logs(
                log_type="single",
                limit=200,
                filter_expr="error",
            )

            if error_items:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-logs-errors",
                        category="system",
                        severity="high",
                        title="System Logs Contain Errors",
                        description=f"Found {len(error_items)} error log entries in system logs.",
                        affected_components=["system"],
                        confidence_level="medium",
                        remediation_steps=[
                            "Review system logs for recurring errors",
                            "Investigate configuration or connectivity issues",
                        ],
                        estimated_impact="System errors are present in logs",
                        metadata={"error_count": len(error_items)},
                    )
                )

            result.success = True
        except Exception as exc:
            log.error("system_logs_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-logs-error",
                    category="system",
                    severity="critical",
                    title="System Logs Analysis Failed",
                    description=f"Failed to analyze system logs: {str(exc)}",
                    affected_components=["system"],
                    remediation_steps=["Verify API connectivity"],
                    estimated_impact="System log visibility unavailable",
                    confidence_level="high",
                )
            )

        return result
