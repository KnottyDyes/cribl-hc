from typing import List

"""
Script Inventory Analyzer for Cribl Health Check.

Surfaces visibility into custom scripts and basic validation signals.

Priority: P3 (Operational visibility)
"""

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class ScriptsAnalyzer(BaseAnalyzer):
    """Analyzer for system script inventory and validation."""

    @property
    def objective_name(self) -> str:
        return "scripts"

    @property
    def supported_products(self) -> List[str]:
        return ["stream"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> List[str]:
        return ["read:system"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            scripts = await client.get_scripts()
            result.metadata["script_count"] = len(scripts)

            if not scripts:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="scripts-none",
                        category="scripts",
                        severity="info",
                        title="No Custom Scripts Found",
                        description="No custom scripts are configured in the system.",
                        confidence_level="high",
                        affected_components=["system"],
                    )
                )
                result.success = True
                return result

            disabled_scripts = []
            error_scripts = []

            for script in scripts:
                script_id = script.get("id") or script.get("name") or "unknown"
                enabled = script.get("enabled")
                disabled = script.get("disabled")
                status = str(script.get("status", "")).lower()
                errors = script.get("errors") or script.get("validationErrors")

                if disabled is True or enabled is False:
                    disabled_scripts.append(script_id)
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"scripts-disabled-{script_id}",
                            category="scripts",
                            severity="low",
                            title=f"Script Disabled: {script_id}",
                            description=f"Script '{script_id}' is disabled.",
                            confidence_level="medium",
                            affected_components=[script_id],
                            metadata={"script_id": script_id},
                        )
                    )

                if status in {"error", "invalid", "failed"} or errors:
                    error_scripts.append(script_id)
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"scripts-error-{script_id}",
                            category="scripts",
                            severity="high",
                            title=f"Script Validation Error: {script_id}",
                            description=f"Script '{script_id}' reports validation errors.",
                            confidence_level="high",
                            affected_components=[script_id],
                            remediation_steps=[
                                f"Review script '{script_id}' for syntax or runtime errors",
                                "Fix validation errors and redeploy the script",
                            ],
                            metadata={"script_id": script_id, "status": status},
                        )
                    )

            result.metadata.update(
                {
                    "disabled_scripts": len(disabled_scripts),
                    "error_scripts": len(error_scripts),
                }
            )

            result.success = True
        except Exception as exc:
            log.warning("scripts_analysis_failed", error=str(exc))
            result.metadata["error"] = str(exc)
            result.success = False

        return result
