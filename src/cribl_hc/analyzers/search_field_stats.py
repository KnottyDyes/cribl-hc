from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.search import FieldStatsResponse, SearchDatasetList
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchFieldStatsAnalyzer(BaseAnalyzer):
    MAX_DATASETS = 10

    @property
    def objective_name(self) -> str:
        return "search_field_stats"

    @property
    def supported_products(self) -> list[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 5

    def get_required_permissions(self) -> list[str]:
        return ["read:search:datasets", "read:search:stats"]

    async def analyze(
        self, client: CriblAPIClient, workspace: str = "default_search"
    ) -> AnalyzerResult:
        result = self.create_result()

        try:
            datasets_resp = await client.get_search_datasets(workspace)
            dataset_list = SearchDatasetList(**datasets_resp)
            datasets = dataset_list.items

            if not datasets:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-field-stats-empty",
                        category="search",
                        severity="info",
                        title="No Search Datasets",
                        description="No Search datasets found to analyze field stats.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )
                result.success = True
                return result

            sampled_datasets = datasets[: self.MAX_DATASETS]
            analyzed_count = 0
            null_field_count = 0

            for dataset in sampled_datasets:
                dataset_id = dataset.id
                try:
                    stats_resp = await client.get_search_field_stats(dataset_id)
                    field_stats = FieldStatsResponse(**stats_resp)
                    analyzed_count += 1
                except Exception as exc:
                    log.warning("field_stats_fetch_failed", dataset_id=dataset_id, error=str(exc))
                    continue

                total_events = field_stats.total_events or 0
                if total_events == 0:
                    continue

                for field in field_stats.fields:
                    null_count = field.null_count or 0
                    if total_events > 0 and null_count == total_events:
                        null_field_count += 1
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"search-field-always-null-{dataset_id}-{field.name}",
                                category="search",
                                severity="info",
                                title=f"Field Always Null: {field.name}",
                                description=f"Field '{field.name}' in dataset '{dataset_id}' is null in all {total_events} analyzed events.",
                                affected_components=[dataset_id],
                                confidence_level="medium",
                                remediation_steps=[
                                    "Verify extraction rules for this field",
                                    "Remove field from schema if unused",
                                ],
                                metadata={
                                    "dataset_id": dataset_id,
                                    "field_name": field.name,
                                    "total_events": total_events,
                                },
                            )
                        )

            result.metadata.update(
                {
                    "workspace": workspace,
                    "datasets_analyzed": analyzed_count,
                    "null_fields_found": null_field_count,
                }
            )

            result.success = True

        except Exception as exc:
            log.error("search_field_stats_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-field-stats-error",
                    category="search",
                    severity="critical",
                    title="Search Field Stats Analysis Failed",
                    description=f"Failed to analyze field stats: {str(exc)}",
                    affected_components=["Search API"],
                    remediation_steps=["Verify Search API connectivity"],
                    estimated_impact="Search field statistics unavailable",
                    confidence_level="high",
                )
            )

        return result
