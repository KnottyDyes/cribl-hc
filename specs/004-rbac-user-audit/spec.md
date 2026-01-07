# Feature Specification: RBAC & User Account Audit

## Overview

**Feature Name**: RBAC & User Account Audit  
**Short Name**: rbac-audit  
**Priority**: P1 (High Value, Medium Effort)  
**Status**: Specified  
**Created**: 2025-01-04  

### Problem Statement

Organizations struggle with access control hygiene in Cribl deployments:
- **Permission sprawl**: Roles with wildcard (`*`) permissions grant excessive access
- **Stale accounts**: Former employees' accounts remain active
- **Compliance gaps**: No visibility into who has access to what
- **API key risks**: Unused or never-used API keys pose security risks

These issues create security vulnerabilities and compliance failures.

### Solution

Enhance SecurityAnalyzer with comprehensive RBAC and user account auditing:
1. Audit roles for overly permissive permissions
2. Identify inactive user accounts
3. Check for unused API keys
4. Detect empty teams and orphaned policies
5. Generate actionable security findings

## User Scenarios

### Scenario 1: Identify Overly Permissive Roles
**As a** Security administrator  
**I want** to find roles with excessive permissions  
**So that** I can implement least-privilege access

**Acceptance Criteria**:
- Roles with wildcard (`*`) permissions flagged
- Roles with `admin:*` permissions flagged
- Finding shows specific overly-broad permissions

### Scenario 2: Detect Inactive User Accounts
**As a** IT administrator  
**I want** to identify users who haven't logged in recently  
**So that** I can disable or remove stale accounts

**Acceptance Criteria**:
- Users inactive for 90+ days flagged
- Last login date shown in finding
- Users who have never logged in flagged

### Scenario 3: Audit API Key Usage
**As a** Security engineer  
**I want** to find unused or stale API keys  
**So that** I can rotate or revoke them

**Acceptance Criteria**:
- API keys never used flagged
- API keys not used in 90+ days flagged
- Key creation date and last used shown

### Scenario 4: Compliance Reporting
**As a** Compliance officer  
**I want** a summary of access control health  
**So that** I can report on security posture

**Acceptance Criteria**:
- Overall RBAC health score
- Count of issues by category
- Exportable findings for audit

## Functional Requirements

### FR-1: Role Permission Audit
- Query `/system/roles` for all roles
- Parse permissions array for each role
- Flag roles with:
  - `*` (full wildcard)
  - `admin:*` (admin wildcard)
  - `write:*` (write wildcard)
  - Permissions granting global access

### FR-2: User Activity Audit
- Query `/system/users` for all users
- Check `lastLogin` field for each user
- Calculate days since last login
- Flag users inactive >90 days
- Flag users with `lastLogin: null` (never logged in)

### FR-3: API Key Audit
- Query `/system/keys` for all API keys
- Check `lastUsed` field for each key
- Flag keys never used
- Flag keys not used in >90 days
- Report key age and permissions

### FR-4: Team Audit
- Query `/system/teams` for all teams
- Identify teams with no members
- Flag orphaned teams

### FR-5: Severity Classification
| Condition | Severity |
|-----------|----------|
| Role with `*` permission | HIGH |
| Role with `admin:*` permission | HIGH |
| User inactive 90-180 days | WARNING |
| User inactive >180 days | HIGH |
| User never logged in (>30 days old) | WARNING |
| API key never used (>30 days old) | WARNING |
| API key unused >90 days | WARNING |
| Empty team | INFO |

### FR-6: Finding Content
Each finding must include:
- Specific entity (role/user/key name)
- Issue details (permissions, dates)
- Remediation steps
- Compliance impact

## Success Criteria

1. **Coverage**: All users, roles, keys, teams audited
2. **Accuracy**: Correct identification of issues
3. **Thresholds**: Configurable inactive periods (default 90 days)
4. **Compliance**: Findings support SOC2/SOX reporting
5. **Performance**: <3 seconds additional analysis time

## Technical Notes

### API Endpoints
```
GET /api/v1/system/users
GET /api/v1/system/roles
GET /api/v1/system/keys
GET /api/v1/system/teams
GET /api/v1/system/policies
```

### Expected Response Structures
```json
// /system/users
{
  "items": [
    {
      "id": "user@example.com",
      "username": "user@example.com",
      "lastLogin": "2024-06-15T10:30:00Z",
      "disabled": false,
      "roles": ["admin"]
    }
  ]
}

// /system/roles
{
  "items": [
    {
      "id": "admin",
      "permissions": ["*"]
    }
  ]
}

// /system/keys
{
  "items": [
    {
      "id": "api-key-1",
      "lastUsed": null,
      "created": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Integration Point
Enhance `SecurityAnalyzer.analyze()` in `src/cribl_hc/analyzers/security.py`

## Out of Scope

- Automatic role modification
- User deactivation
- API key rotation
- Active Directory/LDAP integration

## Dependencies

- API client methods (most exist, may need to add `get_api_keys()`)
- SecurityAnalyzer registered (exists)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No lastLogin for cloud SSO users | Note in finding, don't flag as inactive |
| Built-in roles flagged | Exclude system roles or note as expected |
| Large user count | Batch findings, summarize if >50 |
| RBAC API not available | Skip check, log warning |

