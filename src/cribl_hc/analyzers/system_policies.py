from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemPoliciesAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "system_policies"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:system"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            policies = await client.get_system_policies()
            items = policies.get("items", []) if isinstance(policies, dict) else policies

            result.metadata.update(
                {
                    "policy_count": len(items),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not items:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-policies-none",
                        category="system",
                        severity="info",
                        title="No System Policies",
                        description="No system policies were returned from the API.",
                        affected_components=["system"],
                        confidence_level="medium",
                    )
                )

            result.success = True
        except Exception as exc:
            log.error("system_policies_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-policies-error",
                    category="system",
                    severity="critical",
                    title="System Policy Analysis Failed",
                    description=f"Failed to analyze system policies: {str(exc)}",
                    affected_components=["system"],
                    remediation_steps=["Verify API connectivity"],
                    confidence_level="high",
                    estimated_impact="Cannot verify system policies",
                )
            )

        return result
