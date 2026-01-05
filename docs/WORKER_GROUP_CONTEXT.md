# Worker Group Context Feature

## Overview
This feature adds automatic worker group context to all health check findings, making it easier to identify which worker group a specific issue or configuration belongs to.

## Changes

### Finding Model Enhancement
Added `worker_group` field to track which worker group a finding applies to:
```python
worker_group: str | None = Field(
    None,
    description="Worker group this finding applies to (e.g., 'default', 'prod-group'). "
    "None indicates finding applies to all groups or group context is not applicable."
)
```

### Example Usage
```python
from cribl_hc.models.finding import Finding

# Finding with explicit worker group
finding = Finding(
    id="health-001",
    category="health",
    severity="high",
    title="High Memory Usage",
    description="Worker worker-01 is using 92% memory",
    worker_group="prod-group",
    confidence_level="high",
    remediation_steps=["Review memory allocation"],
    estimated_impact="Risk of OOM kills"
)

# Finding with metadata context
finding = Finding(
    id="security-002",
    category="security",
    severity="high",
    title="Wildcard Permission Detected",
    description="Role has wildcard permission",
    confidence_level="high",
    estimated_impact="Unrestricted access",
    metadata={
        "worker_group_id": "prod-group",
        "worker_group_source": "auto-detected",
        "fleet_id": "fleet-123"
    }
)
```

## Benefits
- **Clear Context**: All findings now include which worker group they apply to
- **Actionable**: Teams can quickly identify which worker group needs attention
- **Backwards Compatible**: `worker_group` is optional, existing code continues to work
- **Standardized**: Consistent format across all findings

## Future Enhancements
- Add Edge fleet context support
- Auto-populate from API client when available
- Update existing analyzers to use new `worker_group` field

## Files Modified
- `src/cribl_hc/models/finding.py` - Added worker_group field
- `tests/unit/test_worker_group_context.py` - Test coverage
