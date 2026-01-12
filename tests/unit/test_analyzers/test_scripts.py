"""
Unit tests for ScriptsAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.scripts import ScriptsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestScriptsAnalyzer:
    """Test suite for ScriptsAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> ScriptsAnalyzer:
        return ScriptsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_scripts = AsyncMock(return_value=[])
        client.product_type = "stream"
        client.is_edge = False
        return client

    def test_objective_name(self, analyzer: ScriptsAnalyzer) -> None:
        assert analyzer.objective_name == "scripts"

    def test_estimated_api_calls(self, analyzer: ScriptsAnalyzer) -> None:
        assert analyzer.get_estimated_api_calls() == 1

    def test_required_permissions(self, analyzer: ScriptsAnalyzer) -> None:
        assert "read:system" in analyzer.get_required_permissions()

    @pytest.mark.asyncio
    async def test_no_scripts(self, analyzer: ScriptsAnalyzer, mock_client: CriblAPIClient) -> None:
        result = await analyzer.analyze(mock_client)
        assert result.success is True
        assert any(f.id == "scripts-none" for f in result.findings)

    @pytest.mark.asyncio
    async def test_disabled_script(
        self, analyzer: ScriptsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_scripts = AsyncMock(return_value=[{"id": "foo", "disabled": True}])
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "scripts-disabled-foo" for f in result.findings)

    @pytest.mark.asyncio
    async def test_error_script(
        self, analyzer: ScriptsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_scripts = AsyncMock(return_value=[{"id": "bar", "status": "error"}])
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "scripts-error-bar" for f in result.findings)
