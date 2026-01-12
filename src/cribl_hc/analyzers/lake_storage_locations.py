"""
Lake Storage Locations Analyzer for Cribl Health Check.

Analyzes Lake storage location status, inventory health, and usage.

Priority: P2 (Important)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class LakeStorageLocationsAnalyzer(BaseAnalyzer):
    """Analyzer for Cribl Lake storage locations (BYOS)."""

    STALE_INVENTORY_DAYS = 14

    @property
    def objective_name(self) -> str:
        return "lake_storage_locations"

    @property
    def supported_products(self) -> List[str]:
        return ["lake"]

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: lakes(1) + storage-locations per lake(N) + datasets per lake(N).
        Assuming average 2 lakes: ~5 calls.
        """
        return 5

    def get_required_permissions(self) -> List[str]:
        return [
            "read:lake:datasets",
            "read:lake:storage_locations",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            lakes_response = await client.get_lake_groups()
            lakes = lakes_response.get("items", [])

            if not lakes:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="lake-storage-no-lakes",
                        category="lake",
                        severity="info",
                        title="No Lakes Configured",
                        description="No Lake instances are configured in this deployment.",
                        confidence_level="high",
                        affected_components=["Lake"],
                    )
                )
                result.success = True
                return result

            all_locations: List[Dict[str, Any]] = []
            all_datasets: List[Dict[str, Any]] = []

            for lake in lakes:
                lake_id = lake.get("id")
                if not lake_id:
                    continue

                try:
                    locations_response = await client.get_lake_storage_locations(lake_id)
                    all_locations.extend(locations_response.get("items", []))
                except Exception as exc:
                    log.warning(
                        "lake_storage_locations_fetch_failed", lake_id=lake_id, error=str(exc)
                    )

                try:
                    datasets_response = await client.get_lake_datasets(
                        lake_id, include_metrics=False
                    )
                    all_datasets.extend(datasets_response.get("items", []))
                except Exception as exc:
                    log.warning("lake_datasets_fetch_failed", lake_id=lake_id, error=str(exc))

            if not all_locations:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="lake-storage-none",
                        category="lake",
                        severity="high",
                        title="No Storage Locations Configured",
                        description="No Lake storage locations are configured.",
                        confidence_level="high",
                        affected_components=["Lake"],
                        remediation_steps=["Configure at least one storage location for Lake."],
                    )
                )
                result.success = True
                return result

            usage_by_location: Dict[str, int] = {}
            for dataset in all_datasets:
                loc_id = dataset.get("storageLocationId") or dataset.get("storage_location")
                if loc_id:
                    usage_by_location[str(loc_id)] = usage_by_location.get(str(loc_id), 0) + 1

            now = datetime.now(timezone.utc)
            stale_threshold_days = self.STALE_INVENTORY_DAYS

            for location in all_locations:
                location_id = str(location.get("id", "unknown"))
                status = str(location.get("status", "unknown")).lower()

                if status in {"failed", "blocked"}:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"lake-storage-status-{location_id}",
                            category="lake",
                            severity="high",
                            title=f"Storage Location Error: {location_id}",
                            description=f"Storage location '{location_id}' is in '{status}' state.",
                            confidence_level="high",
                            affected_components=[location_id],
                            remediation_steps=[
                                f"Review storage location '{location_id}' configuration",
                                "Check cloud credentials and bucket accessibility",
                            ],
                            metadata={"status": status},
                        )
                    )
                elif status in {"delayed", "provisioning"}:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"lake-storage-status-{location_id}",
                            category="lake",
                            severity="medium",
                            title=f"Storage Location Provisioning: {location_id}",
                            description=f"Storage location '{location_id}' is in '{status}' state.",
                            confidence_level="medium",
                            affected_components=[location_id],
                            metadata={"status": status},
                        )
                    )

                metrics_last_generated = location.get("metricsLastGenerated")
                if isinstance(metrics_last_generated, (int, float)):
                    generated_at = datetime.fromtimestamp(
                        metrics_last_generated / 1000, tz=timezone.utc
                    )
                    stale_days = (now - generated_at).days
                    if stale_days >= stale_threshold_days:
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"lake-storage-stale-metrics-{location_id}",
                                category="lake",
                                severity="medium",
                                title=f"Stale Storage Metrics: {location_id}",
                                description=(
                                    f"Storage location '{location_id}' metrics have not refreshed in {stale_days} days."
                                ),
                                confidence_level="medium",
                                affected_components=[location_id],
                                remediation_steps=[
                                    "Verify inventory jobs are running",
                                    "Check storage location health",
                                ],
                                metadata={"stale_days": stale_days},
                            )
                        )

                usage_count = usage_by_location.get(location_id, 0)
                if usage_count == 0:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"lake-storage-orphaned-{location_id}",
                            category="lake",
                            severity="low",
                            title=f"Unused Storage Location: {location_id}",
                            description=f"Storage location '{location_id}' is not used by any dataset.",
                            confidence_level="medium",
                            affected_components=[location_id],
                            remediation_steps=[
                                f"Remove unused storage location '{location_id}' if not needed",
                            ],
                            metadata={"usage_count": usage_count},
                        )
                    )

            result.metadata.update(
                {
                    "lake_count": len(lakes),
                    "storage_location_count": len(all_locations),
                    "dataset_count": len(all_datasets),
                }
            )

            result.success = True
        except Exception as exc:
            log.warning("lake_storage_locations_analysis_failed", error=str(exc))
            result.metadata["error"] = str(exc)
            result.success = False

        return result
