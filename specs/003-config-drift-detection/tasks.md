# Implementation Tasks: Configuration Drift Detection

## Overview
**Feature**: 003-config-drift-detection  
**Estimated Effort**: 3-4 hours  
**Dependencies**: None (API endpoints exist)

---

## Tasks

### Task 1: Add Config Drift Detection to FleetAnalyzer
**Priority**: High  
**Effort**: 1.5 hours  
**File**: `src/cribl_hc/analyzers/fleet.py`

**Description**:
Add method `_check_config_drift()` to FleetAnalyzer:
1. Get master summary for current leader version
2. Get all worker groups with their config versions
3. Compare versions and identify mismatches
4. Generate findings for drift and stuck deployments

**Implementation**:
```python
async def _check_config_drift(self, client: CriblAPIClient) -> list[Finding]:
    """Check for configuration version drift across fleet."""
    findings = []
    
    try:
        master_summary = await client.get_master_summary()
        worker_groups = await client.get_worker_groups()
    except Exception as e:
        self.log.warning("config_drift_check_failed", error=str(e))
        return findings
    
    leader_version = master_summary.get("currentVersion", "unknown")
    
    for group in worker_groups:
        group_id = group.get("id", "unknown")
        group_version = group.get("configVersion", "unknown")
        worker_count = group.get("workerCount", 0)
        deploying_count = group.get("deployingWorkerCount", 0)
        
        # Check for deployment in progress
        if deploying_count > 0:
            findings.append(self.create_finding(
                title=f"Config deployment in progress: {group_id}",
                description=f"Worker group '{group_id}' has {deploying_count} of {worker_count} workers still deploying config version {group_version}",
                severity=Severity.WARNING,
                category="fleet",
                remediation="Monitor deployment progress in Cribl UI. If stuck, investigate worker connectivity.",
                metadata={"group_id": group_id, "deploying_count": deploying_count, "total_workers": worker_count}
            ))
        
        # Check for version mismatch
        if group_version != leader_version and group_version != "unknown":
            try:
                version_diff = int(leader_version) - int(group_version)
            except ValueError:
                version_diff = 1  # Default if versions aren't numeric
            
            if version_diff >= 3:
                severity = Severity.CRITICAL
            elif version_diff >= 1:
                severity = Severity.HIGH
            else:
                continue
                
            findings.append(self.create_finding(
                title=f"Config drift detected: {group_id}",
                description=f"Worker group '{group_id}' running config v{group_version}, leader is at v{leader_version} ({version_diff} versions behind)",
                severity=severity,
                category="fleet",
                remediation=f"Deploy latest configuration to worker group '{group_id}' from Cribl UI > Worker Groups > Deploy",
                metadata={
                    "group_id": group_id,
                    "group_version": group_version,
                    "leader_version": leader_version,
                    "versions_behind": version_diff,
                    "worker_count": worker_count
                }
            ))
    
    return findings
```

**Acceptance Criteria**:
- [ ] Method added to FleetAnalyzer
- [ ] Called from `analyze()` method
- [ ] Findings include group ID, versions, and remediation

---

### Task 2: Write Unit Tests for Config Drift Detection
**Priority**: High  
**Effort**: 1 hour  
**File**: `tests/unit/test_analyzers/test_fleet.py`

**Description**:
Test cases:
1. All workers in sync (no findings)
2. Single group 1 version behind (HIGH)
3. Single group 3+ versions behind (CRITICAL)
4. Multiple groups with different drift levels
5. Deployment in progress (WARNING)
6. Mixed drift and deployment
7. API error handling

**Test Structure**:
```python
class TestConfigDriftDetection:
    """Test configuration drift detection."""

    async def test_no_drift_no_findings(self, fleet_analyzer, mock_client):
        """Test that in-sync fleet generates no findings."""
        mock_client.get_master_summary.return_value = {"currentVersion": "10"}
        mock_client.get_worker_groups.return_value = [
            {"id": "default", "configVersion": "10", "workerCount": 3, "deployingWorkerCount": 0}
        ]
        result = await fleet_analyzer.analyze(mock_client)
        drift_findings = [f for f in result.findings if "drift" in f.title.lower()]
        assert len(drift_findings) == 0

    async def test_critical_drift_multiple_versions(self, fleet_analyzer, mock_client):
        """Test CRITICAL severity for 3+ versions behind."""
        mock_client.get_master_summary.return_value = {"currentVersion": "10"}
        mock_client.get_worker_groups.return_value = [
            {"id": "prod-workers", "configVersion": "5", "workerCount": 5, "deployingWorkerCount": 0}
        ]
        result = await fleet_analyzer.analyze(mock_client)
        drift_findings = [f for f in result.findings if "drift" in f.title.lower()]
        assert len(drift_findings) == 1
        assert drift_findings[0].severity == Severity.CRITICAL

    async def test_deployment_in_progress_warning(self, fleet_analyzer, mock_client):
        """Test WARNING for deployment in progress."""
        mock_client.get_master_summary.return_value = {"currentVersion": "10"}
        mock_client.get_worker_groups.return_value = [
            {"id": "default", "configVersion": "10", "workerCount": 5, "deployingWorkerCount": 2}
        ]
        result = await fleet_analyzer.analyze(mock_client)
        deploy_findings = [f for f in result.findings if "deployment" in f.title.lower()]
        assert len(deploy_findings) == 1
        assert deploy_findings[0].severity == Severity.WARNING
```

**Acceptance Criteria**:
- [ ] All severity levels tested
- [ ] Deployment detection tested
- [ ] Tests pass locally

---

### Task 3: Add Integration Test
**Priority**: Medium  
**Effort**: 30 minutes  
**File**: `tests/integration/test_fleet_analyzer.py`

**Description**:
Integration test with mocked HTTP responses verifying end-to-end config drift detection.

**Acceptance Criteria**:
- [ ] Integration test passes
- [ ] Uses respx for HTTP mocking

---

### Task 4: Update Documentation
**Priority**: Medium  
**Effort**: 15 minutes  
**Files**: `README.md`, `docs/ANALYZERS.md`

**Description**:
- Add config drift to FleetAnalyzer description
- Document detection thresholds
- Show example findings

**Acceptance Criteria**:
- [ ] Documentation updated
- [ ] Example output shown

---

## Test Plan

### Unit Tests
| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| All in sync | All versions match | No drift findings |
| 1 version behind | v9 vs v10 | HIGH finding |
| 3+ versions behind | v5 vs v10 | CRITICAL finding |
| Deployment in progress | deployingWorkerCount > 0 | WARNING finding |
| Multiple groups | Mixed versions | Appropriate findings each |
| API error | Exception | Graceful handling |

### Manual Verification
1. Run against deployment with known version mismatch
2. Verify findings match expected severity
3. Confirm remediation steps are accurate

---

## Definition of Done

- [ ] Code implemented
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] Linting passes

