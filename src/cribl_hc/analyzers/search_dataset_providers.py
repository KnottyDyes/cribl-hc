
from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.search import DatasetProviderList, SearchDatasetList
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SearchDatasetProvidersAnalyzer(BaseAnalyzer):
    BUILTIN_PROVIDERS = {"cribl_edge", "cribl_lake", "s3"}

    @property
    def objective_name(self) -> str:
        return "search_dataset_providers"

    @property
    def supported_products(self) -> list[str]:
        return ["search"]

    def get_estimated_api_calls(self) -> int:
        return 2

    def get_required_permissions(self) -> list[str]:
        return ["read:search:datasets", "read:search:providers"]

    async def analyze(
        self, client: CriblAPIClient, workspace: str = "default_search"
    ) -> AnalyzerResult:
        result = self.create_result()

        try:
            providers_resp = await client.get_search_dataset_providers()
            provider_list = DatasetProviderList(**providers_resp)
            providers = provider_list.items
            provider_ids = {p.id for p in providers}

            if not providers:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="search-providers-empty",
                        category="search",
                        severity="info",
                        title="No Search Dataset Providers",
                        description="No Search dataset providers configured.",
                        affected_components=["Search"],
                        confidence_level="high",
                    )
                )

            datasets_resp = await client.get_search_datasets(workspace)
            dataset_list = SearchDatasetList(**datasets_resp)
            datasets = dataset_list.items

            used_providers = {
                dataset.provider
                for dataset in datasets
                if dataset.provider and dataset.provider in provider_ids
            }
            unknown_providers = {
                dataset.provider
                for dataset in datasets
                if dataset.provider
                and dataset.provider not in provider_ids
                and dataset.provider not in self.BUILTIN_PROVIDERS
            }

            unused_providers = provider_ids - used_providers

            for provider_id in sorted(unused_providers):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"search-provider-unused-{provider_id}",
                        category="search",
                        severity="low",
                        title=f"Unused Dataset Provider: {provider_id}",
                        description=f"Provider '{provider_id}' is configured but not used by any dataset.",
                        affected_components=[provider_id],
                        confidence_level="medium",
                        remediation_steps=["Remove unused provider if it is no longer needed"],
                    )
                )

            for provider_id in sorted(unknown_providers):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"search-provider-missing-{provider_id}",
                        category="search",
                        severity="medium",
                        title=f"Unknown Dataset Provider: {provider_id}",
                        description="Dataset references a provider that is not configured.",
                        affected_components=[provider_id],
                        confidence_level="medium",
                        remediation_steps=["Register the provider or update dataset configuration"],
                    )
                )

            result.metadata.update(
                {
                    "workspace": workspace,
                    "provider_count": len(providers),
                    "unused_providers": sorted(unused_providers),
                    "used_providers": sorted(used_providers),
                    "unknown_providers": sorted(unknown_providers),
                }
            )

            result.success = True

        except Exception as exc:
            log.error("search_dataset_providers_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="search-dataset-providers-error",
                    category="search",
                    severity="critical",
                    title="Search Dataset Providers Analysis Failed",
                    description=f"Failed to analyze dataset providers: {str(exc)}",
                    affected_components=["Search API"],
                    remediation_steps=["Verify Search API connectivity"],
                    estimated_impact="Search provider analysis unavailable",
                    confidence_level="high",
                )
            )

        return result
