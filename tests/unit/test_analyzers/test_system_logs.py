from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_logs import SystemLogsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemLogsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemLogsAnalyzer:
        return SystemLogsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_system_logs = AsyncMock(
            return_value=[{"id": "log-1", "path": "/var/log/cribl.log"}]
        )
        client.search_system_logs = AsyncMock(return_value=[{"message": "error"}])
        return client

    def test_objective_name(self, analyzer: SystemLogsAnalyzer) -> None:
        assert analyzer.objective_name == "system_logs"

    @pytest.mark.asyncio
    async def test_error_logs(
        self, analyzer: SystemLogsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "system-logs-errors" for f in result.findings)
