import asyncio
from collections import Counter, defaultdict
from typing import Any, List, Optional

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class FleetAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__()
        self._deployment_results: dict[str, dict[str, Any]] = {}

    @property
    def objective_name(self) -> str:
        return "fleet"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 5

    def get_required_permissions(self) -> list[str]:
        return ["read:system", "read:pipelines", "read:workers", "read:master"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()
        try:
            worker_groups = await client.get_worker_groups()
            worker_groups_by_type = await client.get_worker_groups_by_type()
            master_summary = await client.get_master_summary()
            workers = await client.get_workers()

            result.metadata["worker_group_count"] = len(worker_groups)
            result.metadata["total_workers"] = len(workers)
            result.metadata["master_summary"] = master_summary
            result.metadata["worker_groups_by_type"] = {
                group_type: len(groups) for group_type, groups in worker_groups_by_type.items()
            }

            await self._analyze_config_drift(client, worker_groups, workers, master_summary, result)
            self._analyze_worker_group_health(worker_groups, master_summary, result, client)
            self._analyze_worker_group_types(worker_groups_by_type, result, client)
            self._analyze_single_deployment_patterns(workers, result, client)
            result.success = True
        except Exception as e:
            self.log.error("fleet_analysis_failed", error=str(e))
            result.error = f"Fleet analysis failed: {str(e)}"
            result.success = False
        return result

    async def _analyze_config_drift(
        self,
        client: CriblAPIClient,
        worker_groups: list[dict[str, Any]],
        workers: list[dict[str, Any]],
        master_summary: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        if not worker_groups:
            return
        group_config_versions: dict[str, str] = {}
        groups_deploying: list[dict[str, Any]] = []
        for group in worker_groups:
            group_id = str(group.get("id", "unknown"))
            config_version = str(group.get("configVersion", "unknown"))
            deploying_count = int(group.get("deployingWorkerCount", 0))
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
                group_id = str(group.get("id", "unknown"))
                group_version = str(group.get("configVersion", "unknown"))
                worker_count = int(group.get("workerCount", 0))
                if group_version == "unknown" or group_version == leader_version:
                    continue
                try:
                    version_diff = int(leader_version) - int(group_version)
                except (ValueError, TypeError):
                    version_diff = 1
                if version_diff <= 0:
                    continue
                severity = "critical" if version_diff >= 3 else "high"
                result.add_finding(
                    self.create_finding(
                        client=client,
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
                group_id = str(deploying.get("group"))
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"fleet-deployment-in-progress-{group_id}",
                        category="fleet",
                        severity="low",
                        title=f"Config Deployment In Progress: {group_id}",
                        description=f"Worker group '{group_id}' has {deploying.get('deploying_count')} worker(s) deploying config.",
                        confidence_level="high",
                        metadata=deploying,
                    )
                )
        workers_with_drift: list[dict[str, Any]] = []
        for worker in workers:
            worker_id = str(worker.get("id", "unknown"))
            worker_group = str(worker.get("group", "default"))
            worker_config = str(worker.get("configVersion", "unknown"))
            expected_version = group_config_versions.get(worker_group)
            if expected_version and worker_config != expected_version:
                workers_with_drift.append(
                    {
                        "worker_id": worker_id,
                        "group": worker_group,
                        "worker_version": worker_config,
                        "expected_version": expected_version,
                    }
                )
        if workers_with_drift:
            drift_by_group: dict[str, list[str]] = defaultdict(list)
            for drift in workers_with_drift:
                drift_by_group[str(drift["group"])].append(str(drift["worker_id"]))
            for group_id, drifted_workers in drift_by_group.items():
                expected = group_config_versions.get(group_id, "unknown")
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"fleet-config-drift-{group_id}",
                        category="fleet",
                        severity="medium",
                        title=f"Config Version Drift in Worker Group: {group_id}",
                        description=f"{len(drifted_workers)} worker(s) in group '{group_id}' have version drift.",
                        confidence_level="high",
                        affected_components=drifted_workers,
                        metadata={
                            "group": group_id,
                            "expected_version": expected,
                            "drifted_worker_count": len(drifted_workers),
                        },
                    )
                )
        result.metadata["config_drift"] = {
            "groups_deploying": len(groups_deploying),
            "workers_with_drift": len(workers_with_drift),
            "group_config_versions": group_config_versions,
        }

    def _analyze_worker_group_health(
        self,
        worker_groups: list[dict[str, Any]],
        master_summary: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        if not master_summary:
            return
        total_workers = int(master_summary.get("workerCount", 0))
        healthy_workers = int(master_summary.get("healthyWorkerCount", 0))
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
                        client=client,
                        id="fleet-health-critical",
                        category="fleet",
                        severity="critical",
                        title="Critical Fleet Health Issue",
                        description=f"{unhealthy_workers} of {total_workers} workers are unhealthy.",
                        confidence_level="high",
                        metadata={"unhealthy_pct": round(unhealthy_pct, 1)},
                    )
                )
            elif unhealthy_pct >= 10:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="fleet-health-warning",
                        category="fleet",
                        severity="medium",
                        title="Fleet Health Degraded",
                        description=f"{unhealthy_workers} of {total_workers} workers are unhealthy.",
                        confidence_level="high",
                        metadata={"unhealthy_pct": round(unhealthy_pct, 1)},
                    )
                )

    def _analyze_single_deployment_patterns(
        self, workers: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        if not workers:
            return
        status_counts: dict[str, int] = Counter()
        for worker in workers:
            status = str(worker.get("status", "unknown"))
            status_counts[status] += 1
        result.metadata["worker_status_distribution"] = dict(status_counts)
        unknown_count = status_counts.get("unknown", 0)
        if unknown_count > 0:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="fleet-workers-unknown-status",
                    category="fleet",
                    severity="low",
                    title="Workers with Unknown Status",
                    description=f"{unknown_count} worker(s) are reporting unknown status.",
                    confidence_level="medium",
                    metadata={"unknown_count": unknown_count},
                )
            )

    def _analyze_worker_group_types(
        self,
        worker_groups_by_type: dict[str, list[dict[str, Any]]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        hybrid_groups = worker_groups_by_type.get("hybrid", [])
        cloud_managed_groups = worker_groups_by_type.get("cloud_managed", [])

        if hybrid_groups:
            total_hybrid_workers = sum(group.get("workerCount", 0) for group in hybrid_groups)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="fleet-hybrid-worker-groups-detected",
                    category="fleet",
                    severity="low",
                    title="Hybrid Worker Groups Detected",
                    description=f"Found {len(hybrid_groups)} hybrid worker group(s) with {total_hybrid_workers} workers. These are customer-managed workers in cloud deployments.",
                    confidence_level="high",
                    metadata={
                        "hybrid_group_count": len(hybrid_groups),
                        "hybrid_worker_count": total_hybrid_workers,
                        "hybrid_group_names": [
                            group.get("name", group.get("id", "unknown")) for group in hybrid_groups
                        ],
                    },
                )
            )

        if cloud_managed_groups:
            for group in cloud_managed_groups:
                estimated_rate = group.get("estimatedIngestRate")
                if estimated_rate and estimated_rate > 10240:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"fleet-high-throughput-cloud-group-{group.get('id', 'unknown')}",
                            category="fleet",
                            severity="low",
                            title=f"High Throughput Cloud Group: {group.get('name', group.get('id', 'Unknown'))}",
                            description=f"Cloud-managed worker group has high estimated ingest rate: {estimated_rate} KB/sec.",
                            confidence_level="medium",
                            metadata={
                                "group_id": group.get("id"),
                                "estimated_ingest_rate": estimated_rate,
                                "worker_count": group.get("workerCount", 0),
                            },
                        )
                    )

    async def analyze_fleet(self, deployments: dict[str, CriblAPIClient]) -> AnalyzerResult:
        result = AnalyzerResult(objective=self.objective_name)
        if not deployments:
            result.success = False
            result.error = "No deployments provided"
            return result
        deployment_names = list(deployments.keys())
        result.metadata.update(
            {
                "deployment_names": deployment_names,
                "deployments_analyzed": 0,
                "failed_deployments": [],
                "successful_deployments": [],
            }
        )
        await self._analyze_all_deployments(deployments, result)
        self._compare_environments(result)
        self._detect_fleet_patterns(result)
        self._generate_fleet_recommendations(result)
        result.success = result.metadata["deployments_analyzed"] > 0
        return result

    async def _analyze_all_deployments(
        self, deployments: dict[str, CriblAPIClient], result: AnalyzerResult
    ) -> None:
        tasks = []
        for name, client in deployments.items():
            tasks.append(self._analyze_single_deployment(name, client))
        deployment_results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, res in zip(deployments.keys(), deployment_results):
            if isinstance(res, dict):
                self._deployment_results[name] = res
                result.metadata["successful_deployments"].append(name)
                result.metadata["deployments_analyzed"] += 1
            else:
                result.metadata["failed_deployments"].append(name)
                log.error("deployment_analysis_failed", deployment=name, error=str(res))

    async def _analyze_single_deployment(self, name: str, client: CriblAPIClient) -> dict[str, Any]:
        deployment_data: dict[str, Any] = {
            "name": name,
            "environment": getattr(client, "environment", "unknown"),
            "base_url": getattr(client, "base_url", ""),
            "product_type": getattr(client, "product_type", "stream"),
        }
        try:
            deployment_data["system_status"] = await client.get_system_status()
        except Exception:
            deployment_data["system_status"] = {}
        try:
            deployment_data["pipelines"] = await client.get_pipelines()
            deployment_data["pipeline_count"] = len(deployment_data["pipelines"])
        except Exception:
            deployment_data["pipelines"] = []
            deployment_data["pipeline_count"] = 0
        try:
            deployment_data["workers"] = await client.get_workers()
            deployment_data["worker_count"] = len(deployment_data["workers"])
        except Exception:
            deployment_data["workers"] = []
            deployment_data["worker_count"] = 0
        return deployment_data

    def _compare_environments(self, result: AnalyzerResult) -> None:
        if len(self._deployment_results) < 2:
            return
        pipeline_counts = {
            name: int(data.get("pipeline_count", 0))
            for name, data in self._deployment_results.items()
        }
        if len(set(pipeline_counts.values())) > 1:
            max_count = max(pipeline_counts.values())
            min_count = min(pipeline_counts.values())
            if max_count > 0 and (max_count - min_count) / max_count > 0.2:
                result.add_finding(
                    self.create_finding(
                        id="fleet-config-drift-pipelines",
                        category="fleet",
                        severity="medium",
                        title="Pipeline Count Drift Across Environments",
                        description="Significant difference in pipeline counts detected.",
                        confidence_level="high",
                        metadata={"pipeline_counts": pipeline_counts},
                    )
                )

    def _detect_fleet_patterns(self, result: AnalyzerResult) -> None:
        if not self._deployment_results:
            return
        health_statuses = defaultdict(list)
        for name, data in self._deployment_results.items():
            status = str(data.get("system_status", {}).get("health", "unknown"))
            health_statuses[status].append(name)
        unhealthy_envs = health_statuses.get("yellow", []) + health_statuses.get("red", [])
        if len(unhealthy_envs) >= 2:
            result.add_finding(
                self.create_finding(
                    id="fleet-pattern-multiple-unhealthy",
                    category="fleet",
                    severity="high",
                    title="Multiple Deployments Unhealthy",
                    description="Multiple deployments are reporting unhealthy status.",
                    confidence_level="high",
                    metadata={"unhealthy_deployments": unhealthy_envs},
                )
            )

    def _generate_fleet_recommendations(self, result: AnalyzerResult) -> None:
        if len(self._deployment_results) < 2:
            return
        drift_findings = [f for f in result.findings if "drift" in f.id.lower()]
        if drift_findings:
            result.add_recommendation(
                Recommendation(
                    id="fleet-rec-gitops",
                    type="fleet",
                    priority="p1",
                    title="Implement GitOps for Configuration Management",
                    description="Configuration drift detected across environments.",
                    rationale="GitOps ensures consistency and provides audit trail.",
                    implementation_steps=["Set up Git repository"],
                    before_state="Manual management",
                    after_state="GitOps workflow",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Reduces errors",
                        cost_savings_annual=0.0,
                        storage_reduction_gb=0.0,
                        time_to_implement="1 week",
                    ),
                    implementation_effort="medium",
                )
            )
