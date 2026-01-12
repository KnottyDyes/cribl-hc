"""
System Messages Analyzer for Cribl Health Check.

Surfaces operational system messages for Core deployments.

Priority: P2 (Operational visibility)
"""

from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemMessagesAnalyzer(BaseAnalyzer):
    """Analyzer for system messages from Core API."""

    @property
    def objective_name(self) -> str:
        return "system_messages"

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
            messages = await client.get_system_messages()
            result.metadata.update(
                {
                    "message_count": len(messages),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not messages:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-messages-none",
                        category="system",
                        severity="info",
                        title="No System Messages",
                        description="No system messages are currently present.",
                        confidence_level="high",
                        affected_components=["system"],
                    )
                )
                result.success = True
                return result

            for msg in messages:
                message_id = msg.get("id") or msg.get("_id") or "unknown"
                message_text = msg.get("message") or msg.get("text") or "System message"
                severity = self._map_severity(msg)

                remediation_steps = ["Review system message details", "Address underlying issue"]
                estimated_impact = (
                    "System warnings or errors are present"
                    if severity in {"high", "critical"}
                    else "Informational system notice"
                )

                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"system-message-{message_id}",
                        category="system",
                        severity=severity,
                        title=f"System Message: {message_id}",
                        description=message_text,
                        confidence_level="medium",
                        affected_components=["system"],
                        remediation_steps=remediation_steps,
                        estimated_impact=estimated_impact,
                        metadata={"severity": severity, "raw": msg},
                    )
                )

            result.success = True
        except Exception as exc:
            log.error("system_messages_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-messages-error",
                    category="system",
                    severity="critical",
                    title="System Messages Analysis Failed",
                    description=f"Failed to analyze system messages: {str(exc)}",
                    affected_components=["system"],
                    remediation_steps=["Verify API connectivity"],
                    estimated_impact="System message visibility unavailable",
                    confidence_level="high",
                )
            )

        return result

    def _map_severity(self, msg: dict) -> str:
        level = str(
            msg.get("severity")
            or msg.get("level")
            or msg.get("type")
            or msg.get("status")
            or "info"
        ).lower()

        if "critical" in level or "fatal" in level:
            return "critical"
        if "error" in level:
            return "high"
        if "warn" in level:
            return "medium"
        return "info"
