"""
Unit tests for hybrid worker group detection and handling.
"""

import pytest
from unittest.mock import AsyncMock
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.analyzers.fleet import FleetAnalyzer


class TestWorkerGroupTypeDetection:
    """Test worker group type detection logic."""

    @pytest.fixture
    def client(self):
        """Create CriblAPIClient for testing."""
        return CriblAPIClient("https://test.cribl.com", "fake-token")

    def test_on_prem_worker_group_detection(self, client):
        """Test detection of on-premises worker groups."""
        group = {"id": "on-prem-group", "onPrem": True, "provisioned": False}

        group_type = client.get_worker_group_type(group)
        assert group_type == "on_prem"

    def test_cloud_managed_worker_group_detection(self, client):
        """Test detection of Cribl-managed cloud worker groups."""
        group = {
            "id": "cloud-managed-group",
            "onPrem": False,
            "provisioned": True,
            "cloud": {"provider": "aws", "region": "us-east-1"},
        }

        group_type = client.get_worker_group_type(group)
        assert group_type == "cloud_managed"

    def test_hybrid_worker_group_detection(self, client):
        """Test detection of hybrid (customer-managed cloud) worker groups."""
        group = {"id": "hybrid-group", "onPrem": False, "provisioned": False}

        group_type = client.get_worker_group_type(group)
        assert group_type == "hybrid"

    def test_edge_fleet_detection(self, client):
        """Test detection of Edge fleets."""
        group = {"id": "edge-fleet", "isFleet": True, "onPrem": False}

        group_type = client.get_worker_group_type(group)
        assert group_type == "edge_fleet"

    def test_search_group_detection(self, client):
        """Test detection of Search groups."""
        group = {"id": "search-group", "isSearch": True, "onPrem": False}

        group_type = client.get_worker_group_type(group)
        assert group_type == "search_group"

    def test_default_on_prem_for_missing_flags(self, client):
        """Test that missing onPrem flag defaults to on-premises."""
        group = {"id": "default-group"}

        group_type = client.get_worker_group_type(group)
        assert group_type == "on_prem"

    def test_edge_fleet_takes_precedence(self, client):
        """Test that isFleet flag takes precedence over other flags."""
        group = {
            "id": "edge-fleet",
            "isFleet": True,
            "isSearch": True,
            "onPrem": False,
            "provisioned": True,
        }

        group_type = client.get_worker_group_type(group)
        assert group_type == "edge_fleet"

    def test_search_takes_precedence_over_cloud_flags(self, client):
        """Test that isSearch flag takes precedence over cloud deployment flags."""
        group = {"id": "search-group", "isSearch": True, "onPrem": False, "provisioned": True}

        group_type = client.get_worker_group_type(group)
        assert group_type == "search_group"


class TestWorkerGroupsByType:
    """Test get_worker_groups_by_type method."""

    @pytest.fixture
    def client(self):
        """Create CriblAPIClient for testing."""
        return CriblAPIClient("https://test.cribl.com", "fake-token")

    @pytest.mark.asyncio
    async def test_categorize_mixed_worker_groups(self, client):
        """Test categorizing mixed worker group types."""
        mock_groups = [
            {"id": "on-prem", "onPrem": True, "provisioned": False},
            {"id": "cloud-managed", "onPrem": False, "provisioned": True},
            {"id": "hybrid", "onPrem": False, "provisioned": False},
            {"id": "edge-fleet", "isFleet": True},
            {"id": "search-group", "isSearch": True},
        ]

        client.get_worker_groups = AsyncMock(return_value=mock_groups)

        groups_by_type = await client.get_worker_groups_by_type()

        assert len(groups_by_type["on_prem"]) == 1
        assert groups_by_type["on_prem"][0]["id"] == "on-prem"

        assert len(groups_by_type["cloud_managed"]) == 1
        assert groups_by_type["cloud_managed"][0]["id"] == "cloud-managed"

        assert len(groups_by_type["hybrid"]) == 1
        assert groups_by_type["hybrid"][0]["id"] == "hybrid"

        assert len(groups_by_type["edge_fleet"]) == 1
        assert groups_by_type["edge_fleet"][0]["id"] == "edge-fleet"

        assert len(groups_by_type["search_group"]) == 1
        assert groups_by_type["search_group"][0]["id"] == "search-group"

    @pytest.mark.asyncio
    async def test_empty_worker_groups(self, client):
        """Test handling of empty worker groups list."""
        client.get_worker_groups = AsyncMock(return_value=[])

        groups_by_type = await client.get_worker_groups_by_type()

        for group_type in ["on_prem", "cloud_managed", "hybrid", "edge_fleet", "search_group"]:
            assert groups_by_type[group_type] == []

    @pytest.mark.asyncio
    async def test_all_same_type(self, client):
        """Test when all groups are the same type."""
        mock_groups = [
            {"id": "hybrid-1", "onPrem": False, "provisioned": False},
            {"id": "hybrid-2", "onPrem": False, "provisioned": False},
            {"id": "hybrid-3", "onPrem": False, "provisioned": False},
        ]

        client.get_worker_groups = AsyncMock(return_value=mock_groups)

        groups_by_type = await client.get_worker_groups_by_type()

        assert len(groups_by_type["hybrid"]) == 3
        assert len(groups_by_type["on_prem"]) == 0
        assert len(groups_by_type["cloud_managed"]) == 0


class TestFleetAnalyzerHybridSupport:
    """Test FleetAnalyzer support for hybrid worker groups."""

    @pytest.fixture
    def fleet_analyzer(self):
        """Create FleetAnalyzer instance."""
        return FleetAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock CriblAPIClient."""
        client = AsyncMock(spec=CriblAPIClient)
        client.deployment_name = "test"
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        client.worker_group = "default"
        return client

    @pytest.mark.asyncio
    async def test_hybrid_worker_group_detection_finding(self, fleet_analyzer, mock_client):
        """Test that hybrid worker groups generate appropriate findings."""
        mock_groups = [
            {
                "id": "hybrid-group",
                "name": "Hybrid Workers",
                "onPrem": False,
                "provisioned": False,
                "workerCount": 5,
            }
        ]

        mock_groups_by_type = {
            "on_prem": [],
            "cloud_managed": [],
            "hybrid": mock_groups,
            "edge_fleet": [],
            "search_group": [],
        }

        mock_client.get_worker_groups.return_value = mock_groups
        mock_client.get_worker_groups_by_type.return_value = mock_groups_by_type
        mock_client.get_master_summary.return_value = {"workerCount": 5, "healthyWorkerCount": 5}
        mock_client.get_workers.return_value = []

        result = await fleet_analyzer.analyze(mock_client)

        hybrid_findings = [f for f in result.findings if "hybrid-worker-groups" in f.id]
        assert len(hybrid_findings) == 1

        finding = hybrid_findings[0]
        assert finding.severity == "low"
        assert "hybrid worker group" in finding.description.lower()
        assert finding.metadata["hybrid_group_count"] == 1
        assert finding.metadata["hybrid_worker_count"] == 5
        assert "Hybrid Workers" in finding.metadata["hybrid_group_names"]

    @pytest.mark.asyncio
    async def test_high_throughput_cloud_group_finding(self, fleet_analyzer, mock_client):
        """Test detection of high throughput cloud-managed groups."""
        mock_cloud_groups = [
            {
                "id": "high-throughput",
                "name": "High Throughput Group",
                "onPrem": False,
                "provisioned": True,
                "workerCount": 10,
                "estimatedIngestRate": 15360,
            }
        ]

        mock_groups_by_type = {
            "on_prem": [],
            "cloud_managed": mock_cloud_groups,
            "hybrid": [],
            "edge_fleet": [],
            "search_group": [],
        }

        mock_client.get_worker_groups.return_value = mock_cloud_groups
        mock_client.get_worker_groups_by_type.return_value = mock_groups_by_type
        mock_client.get_master_summary.return_value = {"workerCount": 10, "healthyWorkerCount": 10}
        mock_client.get_workers.return_value = []

        result = await fleet_analyzer.analyze(mock_client)

        throughput_findings = [f for f in result.findings if "high-throughput-cloud-group" in f.id]
        assert len(throughput_findings) == 1

        finding = throughput_findings[0]
        assert finding.severity == "low"
        assert "high estimated ingest rate" in finding.description.lower()
        assert finding.metadata["estimated_ingest_rate"] == 15360

    @pytest.mark.asyncio
    async def test_worker_group_type_metadata(self, fleet_analyzer, mock_client):
        """Test that worker group type breakdown is included in metadata."""
        mock_groups_by_type = {
            "on_prem": [{"id": "on-prem-1"}],
            "cloud_managed": [{"id": "cloud-1"}, {"id": "cloud-2"}],
            "hybrid": [{"id": "hybrid-1"}],
            "edge_fleet": [],
            "search_group": [],
        }

        mock_client.get_worker_groups.return_value = [
            {"id": "on-prem-1"},
            {"id": "cloud-1"},
            {"id": "cloud-2"},
            {"id": "hybrid-1"},
        ]
        mock_client.get_worker_groups_by_type.return_value = mock_groups_by_type
        mock_client.get_master_summary.return_value = {"workerCount": 4, "healthyWorkerCount": 4}
        mock_client.get_workers.return_value = []

        result = await fleet_analyzer.analyze(mock_client)

        assert "worker_groups_by_type" in result.metadata
        type_breakdown = result.metadata["worker_groups_by_type"]

        assert type_breakdown["on_prem"] == 1
        assert type_breakdown["cloud_managed"] == 2
        assert type_breakdown["hybrid"] == 1
        assert type_breakdown["edge_fleet"] == 0
        assert type_breakdown["search_group"] == 0

    @pytest.mark.asyncio
    async def test_no_findings_for_standard_groups(self, fleet_analyzer, mock_client):
        """Test that standard groups don't generate hybrid-specific findings."""
        mock_groups_by_type = {
            "on_prem": [{"id": "standard-group", "workerCount": 3}],
            "cloud_managed": [],
            "hybrid": [],
            "edge_fleet": [],
            "search_group": [],
        }

        mock_client.get_worker_groups.return_value = [{"id": "standard-group"}]
        mock_client.get_worker_groups_by_type.return_value = mock_groups_by_type
        mock_client.get_master_summary.return_value = {"workerCount": 3, "healthyWorkerCount": 3}
        mock_client.get_workers.return_value = []

        result = await fleet_analyzer.analyze(mock_client)

        hybrid_findings = [f for f in result.findings if "hybrid" in f.id.lower()]
        assert len(hybrid_findings) == 0
