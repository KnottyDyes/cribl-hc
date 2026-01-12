"""
Unit tests for LakeStorageLocationsAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.lake_storage_locations import LakeStorageLocationsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestLakeStorageLocationsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> LakeStorageLocationsAnalyzer:
        return LakeStorageLocationsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_lake_groups = AsyncMock(return_value={"items": [{"id": "lake-1"}]})
        client.get_lake_storage_locations = AsyncMock(
            return_value={
                "items": [
                    {"id": "loc-1", "status": "failed"},
                    {"id": "loc-2", "status": "ready"},
                ]
            }
        )
        client.get_lake_datasets = AsyncMock(return_value={"items": []})
        return client

    def test_objective_name(self, analyzer: LakeStorageLocationsAnalyzer) -> None:
        assert analyzer.objective_name == "lake_storage_locations"

    def test_required_permissions(self, analyzer: LakeStorageLocationsAnalyzer) -> None:
        permissions = analyzer.get_required_permissions()
        assert "read:lake:datasets" in permissions
        assert "read:lake:storage_locations" in permissions

    @pytest.mark.asyncio
    async def test_failed_storage_location(
        self, analyzer: LakeStorageLocationsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "lake-storage-status-loc-1" for f in result.findings)

    @pytest.mark.asyncio
    async def test_orphaned_storage_location(
        self, analyzer: LakeStorageLocationsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "lake-storage-orphaned-loc-2" for f in result.findings)
