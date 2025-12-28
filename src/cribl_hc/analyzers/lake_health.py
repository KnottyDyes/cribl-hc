"""
Lake Health Analyzer for Cribl Health Check.

Analyzes Lake dataset health, retention policies, storage formats,
and lakehouse availability.

Priority: P2 (Important)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.lake import LakeDataset, LakeDatasetList, Lakehouse, LakehouseList
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

    Priority: P2 (Important - prevents data loss, optimizes storage)
    """

    # Retention thresholds (days)
    VERY_SHORT_RETENTION = 7  # Less than 1 week is concerning
    SHORT_RETENTION = 14  # Less than 2 weeks is worth noting
    RECOMMENDED_MIN_RETENTION = 30  # Industry standard minimum

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "lake"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: datasets(1) + stats(1) + lakehouses(1) = 3.
        """
        return 3

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:lake:datasets",
            "read:lake:lakehouses",
            "read:lake:stats"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze Lake dataset health and configuration.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with Lake health findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("lake_health_analysis_started")

            # Fetch Lake data
            datasets_response = await client.get_lake_datasets(include_metrics=True)
            stats_response = await client.get_lake_dataset_stats()
            lakehouses_response = await client.get_lake_lakehouses()

            # Parse responses
            dataset_list = LakeDatasetList(**datasets_response)
            lakehouse_list = LakehouseList(**lakehouses_response)

            datasets = dataset_list.items
            lakehouses = lakehouse_list.items

            # Initialize metadata
            result.metadata.update({
                "total_datasets": len(datasets),
                "lakehouse_count": len(lakehouses),
                "json_datasets": sum(1 for d in datasets if d.format == "json"),
                "parquet_datasets": sum(1 for d in datasets if d.format == "parquet"),
                "datasets_with_short_retention": sum(1 for d in datasets if d.retention_period_in_days < self.SHORT_RETENTION),
                "datasets_with_very_short_retention": sum(1 for d in datasets if d.retention_period_in_days < self.VERY_SHORT_RETENTION),
                "analysis_timestamp": datetime.utcnow().isoformat()
            })

            # Handle empty datasets
            if not datasets:
                result.add_finding(
                    Finding(
                        id="lake-no-datasets",
                        category="lake",
                        severity="info",
                        title="No Lake Datasets Found",
                        description="No datasets are currently configured in Cribl Lake.",
                        affected_components=["Lake"],
                        confidence_level="high",
                        metadata={"message": "Consider creating datasets to store data in Lake."}
                    )
                )
                result.success = True
                return result

            # Analyze each dataset
            for dataset in datasets:
                self._analyze_retention_policy(dataset, result)
                self._analyze_storage_format(dataset, result)

            result.success = True
            log.info(
                "lake_health_analysis_completed",
                datasets=len(datasets),
                lakehouses=len(lakehouses),
                findings=len(result.findings),
                recommendations=len(result.recommendations)
            )

        except Exception as e:
            log.error("lake_health_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="lake-analysis-error",
                    category="lake",
                    severity="critical",
                    title="Lake Health Analysis Failed",
                    description=f"Failed to analyze Lake health: {str(e)}",
                    affected_components=["Lake API"],
                    remediation_steps=["Check API connectivity", "Verify Lake is provisioned"],
                    estimated_impact="Cannot assess Lake health",
                    confidence_level="high",
                    metadata={"error": str(e)}
                )
            )

        return result

    def _analyze_retention_policy(self, dataset: LakeDataset, result: AnalyzerResult) -> None:
        """Analyze dataset retention policy."""
        retention_days = dataset.retention_period_in_days

        # Check for very short retention (< 1 week)
        if retention_days < self.VERY_SHORT_RETENTION:
            result.add_finding(
                Finding(
                    id=f"lake-short-retention-{dataset.id}",
                    category="lake",
                    severity="high",
                    title=f"Very Short Retention Period: {dataset.id}",
                    description=(
                        f"Dataset '{dataset.id}' has a very short retention period "
                        f"of {retention_days} days (< {self.VERY_SHORT_RETENTION} days). "
                        "This may lead to data loss."
                    ),
                    affected_components=["Lake", dataset.id],
                    remediation_steps=[
                        f"Navigate to Lake > Datasets > {dataset.id}",
                        "Edit dataset configuration",
                        f"Update 'Retention Period' to at least {self.RECOMMENDED_MIN_RETENTION} days"
                    ],
                    estimated_impact="Potential data loss for historical queries",
                    confidence_level="high",
                    metadata={
                        "dataset_id": dataset.id,
                        "retention_days": retention_days,
                        "recommended_min": self.RECOMMENDED_MIN_RETENTION
                    }
                )
            )

            # Add recommendation
            self._add_retention_recommendation(dataset, result)

    def _analyze_storage_format(self, dataset: LakeDataset, result: AnalyzerResult) -> None:
        """Analyze dataset storage format efficiency."""
        if dataset.format == "json":
            result.add_finding(
                Finding(
                    id=f"lake-json-format-{dataset.id}",
                    category="lake",
                    severity="info",
                    title=f"Inefficient Storage Format: {dataset.id}",
                    description=(
                        f"Dataset '{dataset.id}' uses JSON format. Parquet format "
                        "offers better compression (60-80% smaller) and faster queries."
                    ),
                    affected_components=["Lake", dataset.id],
                    confidence_level="high",
                    metadata={
                        "dataset_id": dataset.id,
                        "current_format": "json",
                        "recommended_format": "parquet"
                    }
                )
            )

            # Add Parquet recommendation
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
                rationale=(
                    f"Current {current_retention}-day retention is very short. "
                    "Standard practice is 30+ days for operational data."
                ),
                implementation_steps=[
                    f"Navigate to Lake > Datasets > {dataset.id}",
                    "Edit dataset configuration",
                    f"Update 'Retention Period' to {recommended_retention} days",
                    "Save changes"
                ],
                before_state=f"{dataset.id} retention: {current_retention} days",
                after_state=f"{dataset.id} retention: {recommended_retention} days",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Prevents accidental data loss for historical queries"
                ),
                implementation_effort="low",
                product_tags=["lake"]
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
                description=(
                    "Convert dataset from JSON to Parquet for 60-80% storage reduction "
                    "and faster query performance."
                ),
                rationale=(
                    "Parquet is a columnar format optimized for analytics workloads. "
                    "It provides better compression, faster queries, and lower costs."
                ),
                implementation_steps=[
                    f"Create new Parquet dataset: {dataset.id}_parquet",
                    "Configure pipeline to route data to new dataset",
                    "Monitor both datasets during transition",
                    "Update queries to use new dataset"
                ],
                before_state=f"{dataset.id} using JSON format (inefficient compression)",
                after_state=f"{dataset.id} using Parquet format (60-80% storage reduction)",
                impact_estimate=ImpactEstimate(
                    storage_reduction_gb=None,  # Unknown without actual size data
                    performance_improvement="Faster query performance with columnar storage",
                    time_to_implement="2-4 hours"
                ),
                implementation_effort="medium",
                product_tags=["lake"]
            )
        )
