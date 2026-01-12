import pytest

from cribl_hc.analyzers.base import BaseAnalyzer
from cribl_hc.models.finding import Finding


class MockAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "mock"

    async def analyze(self, client):
        return None


def test_create_finding_auto_grouping():
    analyzer = MockAnalyzer()
    finding = analyzer.create_finding(
        id="test-grouping",
        category="mock",
        severity="low",
        title="Delivery Confirmation Disabled: output-1",
        description="Test",
        confidence_level="high",
        remediation_steps=["Test"],
        estimated_impact="Test",
    )

    assert finding.grouping_id == "mock-delivery-confirmation-disabled"


def test_create_finding_worker_group_from_metadata():
    analyzer = MockAnalyzer()
    finding = analyzer.create_finding(
        id="test-worker-group",
        category="mock",
        severity="low",
        title="Test",
        description="Test",
        confidence_level="high",
        remediation_steps=["Test"],
        estimated_impact="Test",
        metadata={"worker_group_id": "wg-1"},
    )

    assert finding.worker_group == "wg-1"
    assert finding.metadata.get("worker_group_id") == "wg-1"


def test_create_finding_worker_group_from_client():
    analyzer = MockAnalyzer()

    class Client:
        worker_group = "wg-client"

    finding = analyzer.create_finding(
        client=Client(),
        id="test-worker-group-client",
        category="mock",
        severity="low",
        title="Test",
        description="Test",
        confidence_level="high",
        remediation_steps=["Test"],
        estimated_impact="Test",
    )

    assert finding.worker_group == "wg-client"
    assert finding.metadata.get("worker_group_id") == "wg-client"


def test_create_finding_respects_grouping_id():
    analyzer = MockAnalyzer()
    finding = analyzer.create_finding(
        id="test-grouping-explicit",
        category="mock",
        severity="low",
        title="Delivery Confirmation Disabled: output-2",
        description="Test",
        confidence_level="high",
        remediation_steps=["Test"],
        estimated_impact="Test",
        grouping_id="explicit-group",
    )

    assert finding.grouping_id == "explicit-group"


def test_create_finding_sets_product_tags_default():
    analyzer = MockAnalyzer()
    finding = analyzer.create_finding(
        id="test-products",
        category="mock",
        severity="low",
        title="Test",
        description="Test",
        confidence_level="high",
        remediation_steps=["Test"],
        estimated_impact="Test",
    )

    assert finding.product_tags == ["stream", "edge", "lake", "search"]
