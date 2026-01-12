from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemBannersAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "system_banners"

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
            banners = await client.get_banners()
            result.metadata.update(
                {
                    "banner_count": len(banners),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not banners:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-banners-none",
                        category="system",
                        severity="info",
                        title="No System Banners",
                        description="No system banners are configured.",
                        affected_components=["system"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            enabled = [b for b in banners if b.get("enabled")]
            for banner in enabled:
                banner_id = banner.get("id", "unknown")
                message = banner.get("message") or "System banner enabled"
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"system-banner-enabled-{banner_id}",
                        category="system",
                        severity="info",
                        title=f"System Banner Enabled: {banner_id}",
                        description=message,
                        affected_components=["system"],
                        confidence_level="medium",
                        metadata={"banner_id": banner_id},
                    )
                )

            result.success = True
        except Exception as exc:
            log.error("system_banners_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-banners-error",
                    category="system",
                    severity="critical",
                    title="System Banner Analysis Failed",
                    description=f"Failed to analyze system banners: {str(exc)}",
                    affected_components=["system"],
                    remediation_steps=["Verify API connectivity"],
                    confidence_level="high",
                )
            )

        return result
