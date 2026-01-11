from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemLicenseUsageAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "system_license_usage"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 2

    def get_required_permissions(self) -> list[str]:
        return ["read:system", "read:license"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            licenses = await client.get_licenses()
            usage = await client.get_license_usage()

            summary = usage.get("summary", {}) if isinstance(usage, dict) else {}
            result.metadata.update(
                {
                    "license_count": len(licenses),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "usage_summary": summary,
                }
            )

            used = summary.get("used") or summary.get("usedGb") or summary.get("consumedGb")
            limit = summary.get("limit") or summary.get("limitGb") or summary.get("allocatedGb")
            if isinstance(used, (int, float)) and isinstance(limit, (int, float)) and limit > 0:
                usage_pct = (used / limit) * 100
                result.metadata["usage_percent"] = usage_pct
                if usage_pct >= 95:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id="system-license-usage-critical",
                            category="system",
                            severity="critical",
                            title="License Usage Near Limit",
                            description=f"License usage is at {usage_pct:.1f}% of limit.",
                            affected_components=["license"],
                            confidence_level="high",
                            remediation_steps=["Reduce ingestion or increase license allocation"],
                            metadata={"usage_percent": usage_pct},
                        )
                    )
                elif usage_pct >= 80:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id="system-license-usage-high",
                            category="system",
                            severity="high",
                            title="High License Usage",
                            description=f"License usage is at {usage_pct:.1f}% of limit.",
                            affected_components=["license"],
                            confidence_level="high",
                            remediation_steps=["Monitor usage and plan license adjustments"],
                            metadata={"usage_percent": usage_pct},
                        )
                    )

            if not licenses:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-license-missing",
                        category="system",
                        severity="critical",
                        title="No License Found",
                        description="No licenses are installed on the system.",
                        affected_components=["license"],
                        confidence_level="high",
                        remediation_steps=["Install a valid license key"],
                        estimated_impact="System functionality restricted",
                    )
                )

            now = datetime.utcnow()
            valid_license_found = False

            for lic in licenses:
                lic_id = lic.get("id", "unknown")
                exp_date_ts = lic.get("expirationDate")

                if exp_date_ts:
                    try:
                        if exp_date_ts > 10000000000:
                            exp_date_ts = exp_date_ts / 1000

                        exp_date = datetime.fromtimestamp(exp_date_ts)
                        days_left = (exp_date - now).days

                        result.metadata[f"license_{lic_id}_days_left"] = days_left

                        if days_left < 0:
                            result.add_finding(
                                self.create_finding(
                                    client=client,
                                    id=f"system-license-expired-{lic_id}",
                                    category="system",
                                    severity="critical",
                                    title=f"License Expired: {lic_id}",
                                    description=f"License {lic_id} expired on {exp_date.isoformat()}.",
                                    affected_components=["license"],
                                    confidence_level="high",
                                    remediation_steps=["Renew and update license immediately"],
                                    estimated_impact="System functionality may be restricted or stopped",
                                    metadata={"expiration_date": exp_date.isoformat()},
                                )
                            )
                        elif days_left < 14:
                            result.add_finding(
                                self.create_finding(
                                    client=client,
                                    id=f"system-license-expiring-critical-{lic_id}",
                                    category="system",
                                    severity="high",
                                    title=f"License Expiring Soon: {lic_id}",
                                    description=f"License {lic_id} expires in {days_left} days.",
                                    affected_components=["license"],
                                    confidence_level="high",
                                    remediation_steps=["Plan license renewal"],
                                    metadata={
                                        "expiration_date": exp_date.isoformat(),
                                        "days_left": days_left,
                                    },
                                )
                            )
                        elif days_left < 30:
                            result.add_finding(
                                self.create_finding(
                                    client=client,
                                    id=f"system-license-expiring-warning-{lic_id}",
                                    category="system",
                                    severity="medium",
                                    title=f"License Expiring: {lic_id}",
                                    description=f"License {lic_id} expires in {days_left} days.",
                                    affected_components=["license"],
                                    confidence_level="high",
                                    remediation_steps=["Plan license renewal"],
                                    metadata={
                                        "expiration_date": exp_date.isoformat(),
                                        "days_left": days_left,
                                    },
                                )
                            )
                        else:
                            valid_license_found = True
                    except Exception as e:
                        log.warning(f"failed_to_parse_license_date: {e}")

            if licenses and not valid_license_found:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-no-valid-license",
                        category="system",
                        severity="critical",
                        title="No Valid License",
                        description="All installed licenses are expired or invalid.",
                        affected_components=["license"],
                        confidence_level="high",
                        remediation_steps=["Install a valid license key"],
                        estimated_impact="System functionality restricted or stopped",
                    )
                )

            result.success = True
        except Exception as exc:
            log.error("system_license_usage_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-license-usage-error",
                    category="system",
                    severity="critical",
                    title="License Analysis Failed",
                    description=f"Failed to analyze license usage: {str(exc)}",
                    affected_components=["license"],
                    remediation_steps=["Verify API connectivity"],
                    confidence_level="high",
                    estimated_impact="Cannot verify license status",
                )
            )

        return result
