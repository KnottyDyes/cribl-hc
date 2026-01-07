"""
Fleet & Multi-Tenancy Management Analyzer for Cribl Health Check.

Analyzes multiple deployments, compares environments, detects patterns,
and provides fleet-wide insights.

Priority: P6 (Fleet management and multi-environment operations)
"""

from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class FleetAnalyzer(BaseAnalyzer):
    """
    Analyzer for fleet and multi-tenancy management.

    Identifies:
    - Configuration drift across environments
    - Common issues affecting multiple deployments
    - Fleet-wide patterns and trends
    """

    def __init__(self):
        """Initialize FleetAnalyzer."""
        super().__init__()
        self._deployment_results: dict[str, dict[str, Any]] = {}

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "fleet"

    @property
    def supported_products(self) -> list[str]:
        """Fleet analyzer supports all products."""
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls per deployment."""
        return 5

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:system", "read:pipelines", "read:workers", "read:master"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze single deployment for fleet health and config drift.
        """
        result = self.create_result()
        log.info("fleet_single_deployment_analysis_started")

        try:
            worker_groups = await client.get_worker_groups()
            master_summary = await client.get_master_summary()
            workers = await client.get_workers()

            result.metadata.update(
                {
                    "worker_group_count": len(worker_groups),
                    "total_workers": len(workers),
                    "master_summary": master_summary,
                }
            )

            await self._analyze_config_drift(client, worker_groups, workers, master_summary, result)
            self._analyze_worker_group_health(worker_groups, master_summary, result)

            result.success = True

        except Exception as e:
            log.error("fleet_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)

        return result

    async def _analyze_config_drift(
        self,
        client: CriblAPIClient,
        worker_groups: list[dict[str, Any]],
        workers: list[dict[str, Any]],
        master_summary: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Analyze configuration drift."""
        if not worker_groups:
            return

        group_config_versions: dict[str, str] = {}
        groups_deploying: list[dict[str, Any]] = []

        for group in worker_groups:
            group_id = group.get("id", "unknown")
            config_version = group.get("configVersion", "unknown")
            deploying_count = group.get("deployingWorkerCount", 0)
            group_config_versions[group_id] = config_version

            if deploying_count > 0:
                groups_deploying.append(
                    {
                        "group": group_id,
                        "deploying_count": deploying_count,
                        "config_version": config_version,
                    }
                )

        leader_version = master_summary.get("currentVersion") if master_summary else None
        if leader_version:
            for group in worker_groups:
                group_id = group.get("id", "unknown")
                group_version = group.get("configVersion", "unknown")
                worker_count = group.get("workerCount", 0)

                if group_version == "unknown" or group_version == leader_version:
                    continue

                try:
                    version_diff = int(leader_version) - int(group_version)
                except ValueError:
                    version_diff = 1

                if version_diff > 0:
                    severity = "critical" if version_diff >= 3 else "high"
                    result.add_finding(
                        self.create_finding(
                            id=f"fleet-leader-drift-{group_id}",
                            category="fleet",
                            severity=severity,
                            title=f"Worker Group Behind Leader: {group_id}",
                            description=f"Worker group '{group_id}' is running config v{group_version}, but leader is at v{leader_version}.",
                            confidence_level="high",
                            affected_components=[group_id],
                            metadata={
                                "group_id": group_id,
                                "versions_behind": version_diff,
                                "worker_count": worker_count,
                            },
                        )
                    )

        if groups_deploying:
            for deploying in groups_deploying:
                result.add_finding(
                    self.create_finding(
                        id=f"fleet-deployment-in-progress-{deploying['group']}",
                        category="fleet",
                        severity="low",
                        title=f"Config Deployment In Progress: {deploying['group']}",
                        description=f"Worker group '{deploying['group']}' has {deploying['deploying_count']} worker(s) still deploying config.",
                        confidence_level="high",
                        metadata=deploying,
                    )
                )

        result.metadata["config_drift"] = {
            "groups_deploying": len(groups_deploying),
            "group_config_versions": group_config_versions,
        }

    def _analyze_worker_group_health(
        self,
        worker_groups: list[dict[str, Any]],
        master_summary: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Analyze health metrics across worker groups."""
        if not master_summary:
            return

        total_workers = master_summary.get("workerCount", 0)
        healthy_workers = master_summary.get("healthyWorkerCount", 0)
        unhealthy_workers = total_workers - healthy_workers

        result.metadata["fleet_health"] = {
            "total_workers": total_workers,
            "healthy_workers": healthy_workers,
            "unhealthy_workers": unhealthy_workers,
            "health_pct": round((healthy_workers / total_workers * 100), 1)
            if total_workers > 0
            else 0,
        }

        if total_workers > 0:
            unhealthy_pct = (unhealthy_workers / total_workers) * 100
            if unhealthy_pct >= 25:
                result.add_finding(
                    self.create_finding(
                        id="fleet-health-critical",
                        category="fleet",
                        severity="critical",
                        title="Critical Fleet Health Issue",
                        description=f"{unhealthy_workers} of {total_workers} workers are unhealthy.",
                        confidence_level="high",
                        metadata={"unhealthy_pct": round(unhealthy_pct, 1)},
                    )
                )
