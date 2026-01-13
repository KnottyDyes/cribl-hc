from datetime import datetime
from typing import List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemCertificatesAnalyzer(BaseAnalyzer):
    EXPIRING_SOON_DAYS = 30
    EXPIRING_URGENT_DAYS = 7

    @property
    def objective_name(self) -> str:
        return "system_certificates"

    @property
    def supported_products(self) -> List[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> List[str]:
        return ["read:certificates"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            certificates = await client.get_certificates()
            now = datetime.utcnow()

            result.metadata.update(
                {
                    "certificate_count": len(certificates),
                    "analysis_timestamp": now.isoformat(),
                }
            )

            if not certificates:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-certificates-none",
                        category="system",
                        severity="info",
                        title="No Certificates Found",
                        description="No system certificates are configured.",
                        affected_components=["system"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            for cert in certificates:
                cert_id = cert.get("id", "unknown")
                expires_at_str = cert.get("expiresAt") or cert.get("notAfter")
                if not expires_at_str:
                    continue

                try:
                    expires_at = datetime.fromisoformat(
                        expires_at_str.replace("Z", "+00:00").split("+")[0]
                    )
                except Exception:
                    log.warning("certificate_expiry_parse_failed", cert_id=cert_id)
                    continue

                days_until = (expires_at - now).days
                if days_until < 0:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"system-cert-expired-{cert_id}",
                            category="system",
                            severity="critical",
                            title=f"Certificate Expired: {cert_id}",
                            description=f"Certificate '{cert_id}' expired {abs(days_until)} days ago.",
                            affected_components=[cert_id],
                            confidence_level="high",
                            remediation_steps=[f"Renew certificate '{cert_id}' immediately"],
                            metadata={"expires_at": expires_at_str},
                        )
                    )
                elif days_until <= self.EXPIRING_SOON_DAYS:
                    severity = "high" if days_until <= self.EXPIRING_URGENT_DAYS else "medium"
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"system-cert-expiring-{cert_id}",
                            category="system",
                            severity=severity,
                            title=f"Certificate Expiring Soon: {cert_id}",
                            description=f"Certificate '{cert_id}' expires in {days_until} days.",
                            affected_components=[cert_id],
                            confidence_level="high",
                            remediation_steps=[f"Renew certificate '{cert_id}'"],
                            metadata={"expires_at": expires_at_str},
                        )
                    )

            result.success = True
        except Exception as exc:
            log.error("system_certificates_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-certificates-error",
                    category="system",
                    severity="critical",
                    title="System Certificates Analysis Failed",
                    description=f"Failed to analyze certificates: {str(exc)}",
                    affected_components=["system"],
                    remediation_steps=["Verify API connectivity"],
                    confidence_level="high",
                )
            )

        return result
