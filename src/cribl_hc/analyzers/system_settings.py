from datetime import datetime
from typing import List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemSettingsAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "system_settings"

    @property
    def supported_products(self) -> List[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> List[str]:
        return ["read:system"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            settings = await client.get_system_settings()
            items = settings.get("items", []) if isinstance(settings, dict) else settings

            result.metadata.update(
                {
                    "settings_count": len(items),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not items:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-settings-none",
                        category="system",
                        severity="info",
                        title="No System Settings Found",
                        description="No system settings were returned from the API.",
                        affected_components=["system"],
                        confidence_level="medium",
                    )
                )
                result.success = True
                return result

            result.success = True
        except Exception as exc:
            log.error("system_settings_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-settings-error",
                    category="system",
                    severity="critical",
                    title="System Settings Analysis Failed",
                    description=f"Failed to analyze system settings: {str(exc)}",
                    affected_components=["system"],
                    remediation_steps=["Verify API connectivity"],
                    confidence_level="high",
                    estimated_impact="Cannot verify system settings",
                )
            )

        return result
