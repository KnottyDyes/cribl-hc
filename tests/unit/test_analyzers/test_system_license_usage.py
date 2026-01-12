from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_license_usage import SystemLicenseUsageAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemLicenseUsageAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemLicenseUsageAnalyzer:
        return SystemLicenseUsageAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_licenses = AsyncMock(return_value=[{"id": "lic-1", "expirationDate": 0}])
        client.get_license_usage = AsyncMock(return_value={"summary": {"used": 95, "limit": 100}})
        return client

    def test_objective_name(self, analyzer: SystemLicenseUsageAnalyzer) -> None:
        assert analyzer.objective_name == "system_license_usage"

    @pytest.mark.asyncio
    async def test_license_findings(
        self, analyzer: SystemLicenseUsageAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any("system-license-expired" in f.id for f in result.findings)
        assert any(f.id == "system-license-usage-critical" for f in result.findings)
