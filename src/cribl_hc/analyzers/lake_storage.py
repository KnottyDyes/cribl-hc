"""
Lake Storage Analyzer for Cribl Health Check.

Analyzes Lake storage efficiency, data format optimization, and
dataset utilization patterns.

Priority: P2 (Important - cost optimization)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.lake import DatasetStats, DatasetStatsList, LakeDataset, LakeDatasetList
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class LakeStorageAnalyzer(BaseAnalyzer):
    """
    Analyzer for Cribl Lake storage optimization and cost efficiency.

    Identifies:
    - Datasets using inefficient JSON format (recommend Parquet)
    - Low-activity or unused datasets
    - Storage cost optimization opportunities
    - Dataset consolidation opportunities

    Priority: P2 (Important - reduces storage costs)
    """

    # Storage thresholds
    LARGE_DATASET_GB = 100  # Datasets over 100GB are worth optimizing
    JSON_TO_PARQUET_SAVINGS = 0.70  # 70% average storage reduction
    LOW_ACTIVITY_DAYS = 30  # No activity in 30+ days

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "lake"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: datasets(1) + stats(1) = 2.
        """
        return 2

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:lake:datasets",
            "read:lake:stats"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze Lake storage efficiency and optimization opportunities.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with Lake storage findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("lake_storage_analysis_started")

            # Fetch Lake data
            datasets_response = await client.get_lake_datasets(include_metrics=True)
            stats_response = await client.get_lake_dataset_stats()

            # Parse responses
            dataset_list = LakeDatasetList(**datasets_response)
            stats_list = DatasetStatsList(**stats_response)

            datasets = dataset_list.items
            stats_map = {s.dataset_id: s for s in stats_list.items}

            # Calculate total storage
            total_storage_bytes = sum(
                stats_map.get(d.id, DatasetStats(dataset_id=d.id)).size_bytes or 0
                for d in datasets
            )
            total_storage_gb = total_storage_bytes / (1024 ** 3)

            # Initialize metadata
            result.metadata.update({
                "total_datasets": len(datasets),
                "total_storage_gb": round(total_storage_gb, 2),
                "json_datasets": sum(1 for d in datasets if d.format == "json"),
                "parquet_datasets": sum(1 for d in datasets if d.format == "parquet"),
                "datasets_with_stats": len(stats_map),
                "analysis_timestamp": datetime.utcnow().isoformat()
            })

            # Handle empty datasets
            if not datasets:
                result.add_finding(
                    Finding(
                        id="lake-storage-no-datasets",
                        category="lake",
                        severity="info",
                        title="No Lake Datasets for Storage Analysis",
                        description="No datasets are currently configured in Cribl Lake.",
                        affected_components=["Lake"],
                        confidence_level="high",
                        metadata={"message": "No storage analysis needed."}
                    )
                )
                result.success = True
                return result

            # Analyze each dataset
            potential_savings_gb = 0.0
            for dataset in datasets:
                stats = stats_map.get(dataset.id)
                savings = self._analyze_dataset_storage(dataset, stats, result)
                if savings:
                    potential_savings_gb += savings

            # Add summary metadata
            result.metadata["potential_savings_gb"] = round(potential_savings_gb, 2)
            result.metadata["potential_savings_percent"] = (
                round((potential_savings_gb / total_storage_gb * 100), 1)
                if total_storage_gb > 0 else 0
            )

            result.success = True
            log.info(
                "lake_storage_analysis_completed",
                datasets=len(datasets),
                total_storage_gb=round(total_storage_gb, 2),
                potential_savings_gb=round(potential_savings_gb, 2),
                findings=len(result.findings),
                recommendations=len(result.recommendations)
            )

        except Exception as e:
            log.error("lake_storage_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="lake-storage-analysis-error",
                    category="lake",
                    severity="critical",
                    title="Lake Storage Analysis Failed",
                    description=f"Failed to analyze Lake storage: {str(e)}",
                    affected_components=["Lake API"],
                    remediation_steps=["Check API connectivity", "Verify Lake is provisioned"],
                    estimated_impact="Cannot assess Lake storage optimization",
                    confidence_level="high",
                    metadata={"error": str(e)}
                )
            )

        return result

    def _analyze_dataset_storage(
        self,
        dataset: LakeDataset,
        stats: Optional[DatasetStats],
        result: AnalyzerResult
    ) -> float:
        """
        Analyze storage efficiency for a single dataset.

        Returns:
            Estimated storage savings in GB (if applicable)
        """
        potential_savings = 0.0

        # Check for JSON format inefficiency with size data
        if dataset.format == "json" and stats and stats.size_bytes:
            size_gb = stats.size_bytes / (1024 ** 3)

            # Only flag large datasets (>10GB) for Parquet conversion
            if size_gb >= 10:
                estimated_savings_gb = size_gb * self.JSON_TO_PARQUET_SAVINGS
                potential_savings = estimated_savings_gb

                result.add_finding(
                    Finding(
                        id=f"lake-storage-json-large-{dataset.id}",
                        category="lake",
                        severity="medium",
                        title=f"Large JSON Dataset: {dataset.id}",
                        description=(
                            f"Dataset '{dataset.id}' stores {round(size_gb, 1)}GB in JSON format. "
                            f"Converting to Parquet could save ~{round(estimated_savings_gb, 1)}GB "
                            f"({round(self.JSON_TO_PARQUET_SAVINGS * 100)}% reduction)."
                        ),
                        affected_components=["Lake", dataset.id],
                        remediation_steps=[
                            f"Create new Parquet dataset: {dataset.id}_parquet",
                            "Configure pipeline to route data to new dataset",
                            "Monitor both datasets during transition",
                            "Delete old JSON dataset after validation"
                        ],
                        estimated_impact=f"~{round(estimated_savings_gb, 1)}GB storage reduction",
                        confidence_level="high",
                        metadata={
                            "dataset_id": dataset.id,
                            "current_size_gb": round(size_gb, 2),
                            "current_format": "json",
                            "recommended_format": "parquet",
                            "estimated_savings_gb": round(estimated_savings_gb, 2)
                        }
                    )
                )

                # Add optimization recommendation
                self._add_format_optimization_recommendation(
                    dataset, size_gb, estimated_savings_gb, result
                )

        # Check for inactive datasets
        if stats and stats.last_updated:
            self._analyze_dataset_activity(dataset, stats, result)

        return potential_savings

    def _analyze_dataset_activity(
        self,
        dataset: LakeDataset,
        stats: DatasetStats,
        result: AnalyzerResult
    ) -> None:
        """Analyze dataset activity patterns."""
        if not stats.last_updated:
            return

        # Calculate days since last update
        current_time = datetime.utcnow()
        last_update_time = datetime.fromtimestamp(stats.last_updated / 1000)
        days_inactive = (current_time - last_update_time).days

        # Flag inactive datasets
        if days_inactive >= self.LOW_ACTIVITY_DAYS:
            result.add_finding(
                Finding(
                    id=f"lake-storage-inactive-{dataset.id}",
                    category="lake",
                    severity="low",
                    title=f"Inactive Dataset: {dataset.id}",
                    description=(
                        f"Dataset '{dataset.id}' has not been updated in {days_inactive} days. "
                        "Consider archiving or deleting if no longer needed."
                    ),
                    affected_components=["Lake", dataset.id],
                    confidence_level="high",
                    metadata={
                        "dataset_id": dataset.id,
                        "days_inactive": days_inactive,
                        "last_updated": last_update_time.isoformat()
                    }
                )
            )

    def _add_format_optimization_recommendation(
        self,
        dataset: LakeDataset,
        current_size_gb: float,
        savings_gb: float,
        result: AnalyzerResult
    ) -> None:
        """Add recommendation for format optimization."""
        result.add_recommendation(
            Recommendation(
                id=f"rec-lake-storage-parquet-{dataset.id}",
                type="optimization",
                priority="p2",
                title=f"Convert {dataset.id} to Parquet for Storage Savings",
                description=(
                    f"Convert {round(current_size_gb, 1)}GB JSON dataset to Parquet format "
                    f"to save ~{round(savings_gb, 1)}GB ({round(self.JSON_TO_PARQUET_SAVINGS * 100)}% reduction)."
                ),
                rationale=(
                    "Parquet uses columnar compression optimized for analytics, "
                    "achieving 60-80% storage reduction vs JSON while improving query performance."
                ),
                implementation_steps=[
                    f"Create new Parquet dataset: {dataset.id}_parquet",
                    "Update pipeline routing to send data to new dataset",
                    "Monitor data ingestion for 24-48 hours",
                    "Validate query compatibility with Parquet format",
                    f"Delete old JSON dataset: {dataset.id}"
                ],
                before_state=f"{dataset.id}: {round(current_size_gb, 1)}GB JSON format",
                after_state=f"{dataset.id}: ~{round(current_size_gb - savings_gb, 1)}GB Parquet format",
                impact_estimate=ImpactEstimate(
                    storage_reduction_gb=round(savings_gb, 2),
                    performance_improvement="Faster query execution with columnar storage",
                    time_to_implement="2-4 hours"
                ),
                implementation_effort="medium",
                product_tags=["lake"]
            )
        )
