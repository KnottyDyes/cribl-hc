"""
Lake Health Analyzer for Cribl Health Check.

Analyzes Lake dataset health, retention policies, storage formats,
and lakehouse availability.

Priority: P2 (Important)
"""

from datetime import datetime
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.lake import LakeDataset, LakeDatasetList, LakehouseList
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class LakeHealthAnalyzer(BaseAnalyzer):
    """
    Analyzer for Cribl Lake dataset health and optimization.

    Identifies:
    - Datasets with very short retention periods (potential data loss)
    - Datasets using inefficient formats (JSON vs Parquet)
    - Lakehouse availability for query optimization
    - Retention policy optimization opportunities
    - Storage location health and organization

    Priority: P2 (Important - prevents data loss, optimizes storage)
    """

    # Retention thresholds (days)
    VERY_SHORT_RETENTION = 7
    SHORT_RETENTION = 14
    RECOMMENDED_MIN_RETENTION = 30

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "lake"

    @property
    def supported_products(self) -> list[str]:
        """Lake analyzer is specific to Cribl Lake."""
        return ["lake"]

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: lakes(1) + datasets per lake(N) + storage_locations per lake(N) = 1+2N.
        Assuming average 2 lakes: ~5 calls.
        """
        return 5

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return [
            "read:lake:datasets",
            "read:lake:lakehouses",
            "read:lake:stats",
            "read:lake:storage_locations",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze Lake dataset health and configuration.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with Lake health findings and recommendations
        """
        result = self.create_result()

        try:
            log.info("lake_health_analysis_started")

            try:
                lakes_response = await client.get_lake_groups()
                lakes = lakes_response.get("items", [])
            except Exception as e:
                log.warning("lake_groups_fetch_failed", error=str(e))
                result.add_finding(
                    self.create_finding(
                        id="lake-unavailable",
                        category="lake",
                        severity="warning",
                        title="Lake Service Unavailable",
                        description="Lake API is not available in this deployment. Skipping Lake health analysis.",
                        remediation_steps=["Ensure Lake product is installed and configured."],
                        confidence_level="high",
                        metadata={"error": str(e)},
                    )
                )
                return result

            if not lakes:
                result.add_finding(
                    self.create_finding(
                        id="lake-no-lakes",
                        category="lake",
                        severity="info",
                        title="No Lakes Configured",
                        description="No Lake instances are configured in this deployment.",
                        remediation_steps=[
                            "Configure a Lake instance to enable Lake health monitoring."
                        ],
                        confidence_level="high",
                    )
                )
                return result

            datasets_list_all = []
            storage_locations_all = []

            for lake in lakes:
                lake_id = lake.get("id")
                if not lake_id:
                    continue

                try:
                    datasets_response = await client.get_lake_datasets(
                        lake_id, include_metrics=True
                    )
                    dataset_list = LakeDatasetList(**datasets_response)
                    datasets_list_all.extend(dataset_list.items)
                except Exception as e:
                    log.warning("lake_datasets_fetch_failed", lake_id=lake_id, error=str(e))

                try:
                    storage_locations_response = await client.get_lake_storage_locations(lake_id)
                    storage_locations_all.extend(storage_locations_response.get("items", []))
                except Exception as e:
                    log.warning("lake_storage_fetch_failed", lake_id=lake_id, error=str(e))

            dataset_list = LakeDatasetList(items=datasets_list_all, count=len(datasets_list_all))
            storage_locations = storage_locations_all

            datasets = dataset_list.items

            result.metadata.update(
                {
                    "total_datasets": len(datasets),
                    "lake_count": len(lakes),
                    "storage_location_count": len(storage_locations),
                    "json_datasets": sum(1 for d in datasets if d.format == "json"),
                    "parquet_datasets": sum(1 for d in datasets if d.format == "parquet"),
                    "datasets_with_short_retention": sum(
                        1 for d in datasets if d.retention_period_in_days < self.SHORT_RETENTION
                    ),
                    "datasets_with_very_short_retention": sum(
                        1
                        for d in datasets
                        if d.retention_period_in_days < self.VERY_SHORT_RETENTION
                    ),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Handle empty datasets
            if not datasets:
                result.add_finding(
                    self.create_finding(
                        id="lake-no-datasets",
                        category="lake",
                        severity="info",
                        title="No Lake Datasets Found",
                        description="No datasets are currently configured in Cribl Lake.",
                        affected_components=["Lake"],
                        confidence_level="high",
                        metadata={"message": "Consider creating datasets to store data in Lake."},
                    )
                )
                result.success = True
                return result

            # Analyze each dataset
            for dataset in datasets:
                self._analyze_retention_policy(dataset, result)
                self._analyze_storage_format(dataset, result)

            # Analyze storage locations
            self._analyze_storage_locations(storage_locations, datasets, result)

            result.success = True
            log.info(
                "lake_health_analysis_completed",
                datasets=len(datasets),
                lakes=len(lakes),
                findings=len(result.findings),
                recommendations=len(result.recommendations),
            )

        except Exception as e:
            log.error("lake_health_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                self.create_finding(
                    id="lake-analysis-error",
                    category="lake",
                    severity="critical",
                    title="Lake Health Analysis Failed",
                    description=f"Failed to analyze Lake health: {str(e)}",
                    affected_components=["Lake API"],
                    remediation_steps=["Check API connectivity", "Verify Lake is provisioned"],
                    estimated_impact="Cannot assess Lake health",
                    confidence_level="high",
                    metadata={"error": str(e)},
                )
            )

        return result

    def _analyze_retention_policy(self, dataset: LakeDataset, result: AnalyzerResult) -> None:
        """Analyze dataset retention policy."""
        retention_days = dataset.retention_period_in_days

        if retention_days < self.VERY_SHORT_RETENTION:
            result.add_finding(
                self.create_finding(
                    id=f"lake-short-retention-{dataset.id}",
                    category="lake",
                    severity="high",
                    title=f"Very Short Retention Period: {dataset.id}",
                    description=(
                        f"Dataset '{dataset.id}' has a very short retention period "
                        f"of {retention_days} days. This may lead to data loss."
                    ),
                    affected_components=["Lake", dataset.id],
                    remediation_steps=[
                        f"Navigate to Lake > Datasets > {dataset.id}",
                        "Edit dataset configuration",
                        f"Update 'Retention Period' to at least {self.RECOMMENDED_MIN_RETENTION} days",
                    ],
                    estimated_impact="Potential data loss for historical queries",
                    confidence_level="high",
                    metadata={
                        "dataset_id": dataset.id,
                        "retention_days": retention_days,
                        "recommended_min": self.RECOMMENDED_MIN_RETENTION,
                    },
                )
            )
            self._add_retention_recommendation(dataset, result)

    def _analyze_storage_format(self, dataset: LakeDataset, result: AnalyzerResult) -> None:
        """Analyze dataset storage format efficiency."""
        if dataset.format == "json":
            result.add_finding(
                self.create_finding(
                    id=f"lake-json-format-{dataset.id}",
                    category="lake",
                    severity="info",
                    title=f"Inefficient Storage Format: {dataset.id}",
                    description=(
                        f"Dataset '{dataset.id}' uses JSON format. Parquet format "
                        "offers better compression and faster queries."
                    ),
                    affected_components=["Lake", dataset.id],
                    confidence_level="high",
                    metadata={
                        "dataset_id": dataset.id,
                        "current_format": "json",
                        "recommended_format": "parquet",
                    },
                )
            )
            self._add_parquet_recommendation(dataset, result)

    def _add_retention_recommendation(self, dataset: LakeDataset, result: AnalyzerResult) -> None:
        """Add recommendation to increase retention period."""
        current_retention = dataset.retention_period_in_days
        recommended_retention = max(self.RECOMMENDED_MIN_RETENTION, current_retention * 2)

        result.add_recommendation(
            Recommendation(
                id=f"rec-lake-retention-{dataset.id}",
                type="configuration",
                priority="p1" if current_retention < self.VERY_SHORT_RETENTION else "p2",
                title=f"Increase Retention for {dataset.id}",
                description=(
                    f"Increase retention period from {current_retention} to "
                    f"{recommended_retention} days to prevent data loss."
                ),
                rationale="Current retention is short. Standard practice is 30+ days.",
                implementation_steps=[
                    f"Navigate to Lake > Datasets > {dataset.id}",
                    "Edit dataset configuration",
                    f"Update 'Retention Period' to {recommended_retention} days",
                ],
                before_state=f"{dataset.id} retention: {current_retention} days",
                after_state=f"{dataset.id} retention: {recommended_retention} days",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Prevents accidental data loss for historical queries",
                    cost_savings_annual=0.0,
                    storage_reduction_gb=0.0,
                    time_to_implement="10 minutes",
                ),
                implementation_effort="low",
                product_tags=["lake"],
            )
        )

    def _add_parquet_recommendation(self, dataset: LakeDataset, result: AnalyzerResult) -> None:
        """Add recommendation to convert to Parquet format."""
        result.add_recommendation(
            Recommendation(
                id=f"rec-lake-parquet-{dataset.id}",
                type="optimization",
                priority="p2",
                title=f"Convert {dataset.id} to Parquet Format",
                description="Convert dataset from JSON to Parquet for storage reduction and faster queries.",
                rationale="Parquet is optimized for analytics workloads.",
                implementation_steps=[
                    f"Create new Parquet dataset: {dataset.id}_parquet",
                    "Configure pipeline to route data to new dataset",
                ],
                before_state=f"{dataset.id} using JSON format",
                after_state=f"{dataset.id} using Parquet format",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Faster query performance",
                    cost_savings_annual=0.0,
                    storage_reduction_gb=0.0,
                    time_to_implement="2-4 hours",
                ),
                implementation_effort="medium",
                product_tags=["lake"],
            )
        )

    def _analyze_storage_locations(
        self,
        storage_locations: list[dict[str, Any]],
        datasets: list[LakeDataset],
        result: AnalyzerResult,
    ) -> None:
        """Analyze Lake storage locations for issues."""
        if not storage_locations:
            return

        for location in storage_locations:
            location_id = location.get("id", "unknown")
            location_type = location.get("type", "unknown")

            datasets_using = [d.id for d in datasets if d.storage_location == location_id]
            if not datasets_using:
                result.add_finding(
                    self.create_finding(
                        id=f"lake-storage-orphaned-{location_id}",
                        category="lake",
                        severity="low",
                        title=f"Unused Storage Location: {location_id}",
                        description=f"Storage location '{location_id}' is not used by any dataset.",
                        affected_components=["Lake", f"storage:{location_id}"],
                        confidence_level="medium",
                        remediation_steps=[
                            f"Verify if storage location '{location_id}' is no longer needed",
                            "Remove unused storage locations",
                        ],
                        metadata={"location_id": location_id, "location_type": location_type},
                    )
                )

        location_usage = {}
        for d in datasets:
            if d.storage_location:
                loc_id = d.storage_location
                location_usage[loc_id] = location_usage.get(loc_id, 0) + 1

        for loc_id, count in location_usage.items():
            if count > 10:
                result.add_finding(
                    self.create_finding(
                        id=f"lake-storage-heavy-{loc_id}",
                        category="lake",
                        severity="medium",
                        title=f"Heavily Used Storage: {loc_id}",
                        description=f"Storage location '{loc_id}' is used by {count} datasets.",
                        affected_components=["Lake", f"storage:{loc_id}"],
                        confidence_level="high",
                        remediation_steps=[
                            "Review distribution of datasets across storage locations",
                        ],
                        metadata={"location_id": loc_id, "dataset_count": count},
                    )
                )
