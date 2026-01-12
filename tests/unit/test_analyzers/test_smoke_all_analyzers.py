import pytest

from cribl_hc.analyzers import get_global_registry


class DummyClient:
    def __init__(self):
        self.is_cloud = False
        self.is_edge = False
        self.is_stream = True
        self.product_type = "stream"
        self.worker_group = "default"
        self.version = "4.0.0"

    def get_api_calls_used(self):
        return 0

    def get_api_calls_remaining(self):
        return 100

    async def get_metrics(self, *args, **kwargs):
        return {"items": []}

    async def get_system_status(self):
        return {"version": "4.0.0"}

    async def get_version_info(self):
        return {"version": "4.0.0"}

    async def get_license_info(self):
        return {"license": {}, "currentUsage": {}}

    async def get_system_messages(self):
        return []

    async def get_banners(self):
        return []

    async def get_auth_config(self):
        return {}

    async def get_security_settings(self):
        return {}

    async def get_certificates(self):
        return []

    async def get_roles(self):
        return []

    async def get_users(self):
        return []

    async def get_api_keys(self):
        return []

    async def get_teams(self):
        return []

    async def get_outputs(self):
        return []

    async def get_inputs(self):
        return []

    async def get_pipelines(self):
        return []

    async def get_routes(self):
        return []

    async def get_workers(self):
        return []

    async def get_worker_groups(self):
        return []

    async def get_worker_groups_by_type(self, *args, **kwargs):
        return []

    async def get_worker_group_config_version(self, *args, **kwargs):
        return {}

    async def get_notification_targets(self):
        return []

    async def get_notifications(self):
        return []

    async def get_lookup_tables(self):
        return []

    async def get_parsers(self):
        return []

    async def get_search_jobs(self):
        return []

    async def get_search_dashboards(self):
        return []

    async def get_search_usage_groups(self):
        return []

    async def get_search_datatypes(self):
        return []

    async def get_lake_groups(self):
        return []

    async def get_lake_datasets(self, *args, **kwargs):
        return []

    async def get_lake_storage_locations(self, *args, **kwargs):
        return []

    async def get_lake_dataset_stats(self, *args, **kwargs):
        return {}

    async def capture_events(self, *args, **kwargs):
        return {"events": []}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __getattr__(self, name):
        if name.startswith("get_"):

            async def _default(*args, **kwargs):
                return []

            return _default
        raise AttributeError(name)


@pytest.mark.asyncio
async def test_smoke_all_analyzers_run_without_error():
    registry = get_global_registry()
    client = DummyClient()
    failures = []

    for objective in registry.list_objectives():
        analyzer = registry.get_analyzer(objective)
        if analyzer is None:
            continue
        try:
            result = await analyzer.analyze(client)
        except Exception as exc:
            failures.append((objective, type(exc).__name__))
        else:
            assert result is not None

    assert failures == []
