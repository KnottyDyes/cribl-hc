from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.search import DatasetProviderTypeList
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchDatasetProviderTypesAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "search_dataset_provider_types"

    @property
    def supported_products(self) -> list[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:search:provider_types"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            types_resp = await client.get_search_dataset_provider_types()
            type_list = DatasetProviderTypeList(**types_resp)
            provider_types = type_list.items

            if not provider_types:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-provider-types-empty",
                        category="search",
                        severity="medium",
                        title="No Dataset Provider Types Found",
                        description="Could not retrieve any dataset provider types.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )

            result.metadata.update(
                {
                    "provider_type_count": len(provider_types),
                    "provider_types": [t.id for t in provider_types],
                }
            )

            result.success = True

        except Exception as exc:
            log.error("search_dataset_provider_types_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-dataset-provider-types-error",
                    category="search",
                    severity="critical",
                    title="Search Provider Types Analysis Failed",
                    description=f"Failed to analyze provider types: {str(exc)}",
                    affected_components=["Search API"],
                    remediation_steps=["Verify Search API connectivity"],
                    estimated_impact="Search provider types unavailable",
                    confidence_level="high",
                )
            )

        return result
