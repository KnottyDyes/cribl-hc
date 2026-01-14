from datetime import datetime, timedelta

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.search import (
    DatasetStatsResponse,
    DatasetUsageStatsResponse,
    SearchDatasetList,
)
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchDatasetStatsAnalyzer(BaseAnalyzer):
    MAX_DATASETS = 10
    STALE_USAGE_THRESHOLD = 0

    @property
    def objective_name(self) -> str:
        return "search_dataset_stats"

    @property
    def supported_products(self) -> list[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 5

    def get_required_permissions(self) -> list[str]:
        return ["read:search:datasets"]

    async def analyze(
        self, client: CriblAPIClient, workspace: str = "default_search"
    ) -> AnalyzerResult:
        result = self.create_result()

        try:
            datasets_response = await client.get_search_datasets(workspace)
            dataset_list = SearchDatasetList(**datasets_response)
            datasets = dataset_list.items

            if not datasets:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-dataset-stats-empty",
                        category="search",
                        severity="info",
                        title="No Search Datasets",
                        description="No Search datasets found to analyze stats.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            now = datetime.utcnow()
            end_time = int(now.timestamp() * 1000)
            start_time = int((now - timedelta(hours=24)).timestamp() * 1000)
            granularity_hours = 1

            sampled_datasets = datasets[: self.MAX_DATASETS]
            analyzed = 0
            zero_event_datasets = []
            zero_query_datasets = []

            for dataset in sampled_datasets:
                dataset_id = dataset.id
                try:
                    stats_response = await client.get_search_dataset_stats(
                        dataset_id,
                        start_time=start_time,
                        end_time=end_time,
                        granularity=granularity_hours,
                    )
                    stats = DatasetStatsResponse(**stats_response)
                except Exception as exc:
                    log.warning("dataset_stats_fetch_failed", dataset_id=dataset_id, error=str(exc))
                    continue

                try:
                    usage_response = await client.get_search_dataset_usage_stats(
                        dataset_id,
                        end_time=end_time,
                        time_window=24,
                    )
                    usage = DatasetUsageStatsResponse(**usage_response)
                except Exception as exc:
                    log.warning("dataset_usage_fetch_failed", dataset_id=dataset_id, error=str(exc))
                    usage = DatasetUsageStatsResponse(**{"queryCounts": []})

                analyzed += 1
                total_events = stats.total_event_count or 0
                if total_events == 0:
                    zero_event_datasets.append(dataset_id)
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"search-dataset-no-events-{dataset_id}",
                            category="search",
                            severity="medium",
                            title=f"Dataset Has No Events: {dataset_id}",
                            description="Dataset statistics report zero events in the last 24 hours.",
                            affected_components=[dataset_id],
                            confidence_level="medium",
                            remediation_steps=[
                                "Verify dataset source connectivity",
                                "Confirm expected ingestion into this dataset",
                            ],
                            metadata={"dataset_id": dataset_id},
                        )
                    )

                query_count = sum(q.count for q in usage.query_counts)
                if query_count <= self.STALE_USAGE_THRESHOLD:
                    zero_query_datasets.append(dataset_id)
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"search-dataset-unused-{dataset_id}",
                            category="search",
                            severity="low",
                            title=f"Dataset Not Queried: {dataset_id}",
                            description="Dataset has no recorded queries in the last 24 hours.",
                            affected_components=[dataset_id],
                            confidence_level="medium",
                            remediation_steps=[
                                "Review dataset usage and ownership",
                                "Consider archiving unused datasets",
                            ],
                            metadata={"dataset_id": dataset_id},
                        )
                    )

            result.metadata.update(
                {
                    "workspace": workspace,
                    "dataset_count": len(datasets),
                    "datasets_analyzed": analyzed,
                    "zero_event_datasets": len(zero_event_datasets),
                    "zero_query_datasets": len(zero_query_datasets),
                    "analysis_timestamp": now.isoformat(),
                }
            )

            result.success = True
        except Exception as exc:
            log.error("search_dataset_stats_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-dataset-stats-error",
                    category="search",
                    severity="critical",
                    title="Search Dataset Stats Failed",
                    description=f"Failed to analyze dataset stats: {str(exc)}",
                    affected_components=["Search API"],
                    remediation_steps=["Verify Search API connectivity"],
                    estimated_impact="Dataset stats unavailable",
                    confidence_level="high",
                )
            )

        return result
