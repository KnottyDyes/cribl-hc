from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_policies import SystemPoliciesAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemPoliciesAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemPoliciesAnalyzer:
        return SystemPoliciesAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_system_policies = AsyncMock(return_value={"items": [], "count": 0})
        return client

    def test_objective_name(self, analyzer: SystemPoliciesAnalyzer) -> None:
        assert analyzer.objective_name == "system_policies"

    @pytest.mark.asyncio
    async def test_no_policies(
        self, analyzer: SystemPoliciesAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "system-policies-none" for f in result.findings)
