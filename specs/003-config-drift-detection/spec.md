# Feature Specification: Configuration Drift Detection

## Overview

**Feature Name**: Configuration Drift Detection  
**Short Name**: config-drift  
**Priority**: P1 (High Value, Low Effort)  
**Status**: Specified  
**Created**: 2025-01-04  

### Problem Statement

Configuration drift occurs when workers run different config versions than the leader, causing:
- Inconsistent data processing across workers
- "Works on some workers but not others" bugs
- Failed deployments that only partially propagate
- Difficult troubleshooting with no visibility into version mismatches

This is the #1 community-reported operational pain point for Cribl deployments.

### Solution

Enhance FleetAnalyzer to detect configuration version mismatches:
1. Query worker groups for config versions
2. Compare worker config versions against leader
3. Identify workers with stale configurations
4. Detect stuck/in-progress deployments
5. Generate findings with specific affected workers

## User Scenarios

### Scenario 1: Detect Stale Worker Configurations
**As a** Cribl administrator  
**I want** to know if any workers are running old configurations  
**So that** I can trigger a redeployment or investigate stuck workers

**Acceptance Criteria**:
- Analysis identifies workers with config version mismatches
- Finding shows which workers have stale configs
- Current vs expected version is displayed

### Scenario 2: Identify Stuck Deployments
**As a** SRE  
**I want** to detect deployments that are stuck or failing  
**So that** I can investigate and resolve the issue

**Acceptance Criteria**:
- Worker groups with `deployingWorkerCount > 0` for extended time flagged
- Finding includes count of workers still deploying
- Deployment status is shown

### Scenario 3: Fleet-Wide Version Summary
**As a** Cribl administrator  
**I want** a summary of config versions across my fleet  
**So that** I can ensure consistency

**Acceptance Criteria**:
- Summary shows version distribution across worker groups
- Identifies groups that are out of sync with each other
- Clear visibility into overall fleet health

## Functional Requirements

### FR-1: Worker Group Config Version Check
- Query `/master/groups` to get all worker groups
- For each group, get `configVersion` field
- Query `/master/summary` for leader's current version
- Compare worker group versions against leader

### FR-2: Worker-Level Config Check
- Query individual worker status within groups
- Identify specific workers with version mismatches
- Report worker IDs/hostnames with stale configs

### FR-3: Deployment Status Detection
- Check `deployingWorkerCount` for each group
- Flag groups where deployment appears stuck (>0 for extended analysis)
- Report deployment progress

### FR-4: Severity Classification
| Condition | Severity |
|-----------|----------|
| Workers 3+ versions behind | CRITICAL |
| Workers 1-2 versions behind | HIGH |
| Deployment in progress | WARNING |
| All workers in sync | No finding |

### FR-5: Finding Content
Each finding must include:
- Worker group name
- Expected version (leader)
- Actual version (worker/group)
- Number of affected workers
- Remediation: "Trigger redeployment from Cribl UI"

## Success Criteria

1. **Detection Rate**: 100% of config mismatches detected
2. **Accuracy**: Zero false positives
3. **Specificity**: Exact workers identified
4. **Actionability**: Clear remediation steps
5. **Performance**: <2 seconds additional analysis time

## Technical Notes

### API Endpoints
```
GET /api/v1/master/groups
GET /api/v1/master/groups/{id}
GET /api/v1/master/groups/{id}/configVersion
GET /api/v1/master/summary
GET /api/v1/master/workers
```

### Expected Response Structure
```json
// /master/groups
{
  "items": [
    {
      "id": "default",
      "configVersion": "42",
      "workerCount": 5,
      "deployingWorkerCount": 0
    }
  ]
}

// /master/summary
{
  "currentVersion": "45",
  "groups": [...]
}
```

### Integration Point
Add to `FleetAnalyzer.analyze()` in `src/cribl_hc/analyzers/fleet.py`

## Out of Scope

- Automatic deployment triggering (read-only tool)
- Root cause analysis of why deployment failed
- Config content comparison (just version numbers)

## Dependencies

- API client `get_worker_groups()` method (exists)
- API client `get_master_summary()` method (exists)
- FleetAnalyzer registered (exists)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Leader unavailable | Skip check, log warning |
| Single-node deployment | Detect and skip (no workers to compare) |
| Version format changes | Use string comparison, log unusual formats |

