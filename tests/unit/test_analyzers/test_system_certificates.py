from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_certificates import SystemCertificatesAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemCertificatesAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemCertificatesAnalyzer:
        return SystemCertificatesAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_certificates = AsyncMock(
            return_value=[{"id": "cert-1", "expiresAt": "2099-01-01T00:00:00Z"}]
        )
        return client

    def test_objective_name(self, analyzer: SystemCertificatesAnalyzer) -> None:
        assert analyzer.objective_name == "system_certificates"

    @pytest.mark.asyncio
    async def test_no_expiring_cert(
        self, analyzer: SystemCertificatesAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert result.success is True
