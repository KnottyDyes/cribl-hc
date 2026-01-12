"""
Unit tests for SystemMessagesAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_messages import SystemMessagesAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemMessagesAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemMessagesAnalyzer:
        return SystemMessagesAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_system_messages = AsyncMock(return_value=[])
        return client

    def test_objective_name(self, analyzer: SystemMessagesAnalyzer) -> None:
        assert analyzer.objective_name == "system_messages"

    def test_required_permissions(self, analyzer: SystemMessagesAnalyzer) -> None:
        assert "read:system" in analyzer.get_required_permissions()

    @pytest.mark.asyncio
    async def test_no_messages(
        self, analyzer: SystemMessagesAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "system-messages-none" for f in result.findings)

    @pytest.mark.asyncio
    async def test_error_message(self, analyzer: SystemMessagesAnalyzer) -> None:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_system_messages = AsyncMock(
            return_value=[{"id": "msg-1", "message": "Oops", "level": "error"}]
        )
        result = await analyzer.analyze(client)
        assert any(f.severity == "high" for f in result.findings)
