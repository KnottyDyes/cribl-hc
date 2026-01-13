"""
Unit tests for worker group context functionality in Finding model.
Tests cover the new worker_group field and validation requirements.
"""


from cribl_hc.models.finding import Finding


def test_finding_worker_group_field():
    """Test Finding model supports new worker_group field."""
    finding = Finding(
        id="test-001",
        category="health",
        severity="info",
        title="Test Finding",
        description="Test description with worker group",
        confidence_level="high",
        remediation_steps=["No action required"],
        worker_group="default",
    )

    assert finding.worker_group == "default"
    print("✅ Worker group field works")


def test_finding_metadata_worker_group_context():
    """Test metadata can include worker group context."""
    finding = Finding(
        id="test-002",
        category="security",
        severity="high",
        title="Security Finding",
        description="Security finding with metadata context",
        confidence_level="high",
        estimated_impact="Potential security breach",
        remediation_steps=["Review security settings"],
        metadata={
            "worker_group_id": "prod-group",
            "worker_group_source": "auto-detected",
            "fleet_id": "fleet-123",
        },
    )

    assert finding.worker_group is None
    assert finding.metadata.get("worker_group_id") == "prod-group"
    assert finding.metadata.get("worker_group_source") == "auto-detected"
    assert finding.metadata.get("fleet_id") == "fleet-123"
    assert finding.estimated_impact == "Potential security breach"
    print("✅ Metadata worker group context works")


def test_finding_example_includes_worker_group():
    """Test Finding JSON schema example includes worker_group."""

    finding = Finding(
        id="finding-mem-001",
        category="health",
        severity="high",
        title="Worker node approaching memory exhaustion",
        description="Worker worker-01 is using 92% of allocated memory",
        confidence_level="high",
        estimated_impact="High risk of worker crash",
        remediation_steps=["Review memory allocation"],
        worker_group="default",
        metadata={"current_memory_gb": 14.7, "worker_group_id": "default"},
    )

    finding_dict = finding.model_dump(mode="json")
    assert "worker_group" in finding_dict
    assert finding_dict["worker_group"] == "default"
    assert "metadata" in finding_dict
    assert finding_dict["metadata"]["worker_group_id"] == "default"
    print("✅ Finding JSON schema includes worker_group")
