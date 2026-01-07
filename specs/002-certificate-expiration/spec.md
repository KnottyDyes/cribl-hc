# Feature Specification: Certificate Expiration Monitoring

## Overview

**Feature Name**: Certificate Expiration Monitoring  
**Short Name**: cert-expiration  
**Priority**: P1 (High Value, Low Effort)  
**Status**: Specified  
**Created**: 2025-01-04  

### Problem Statement

TLS certificate expiration is a top community-reported pain point for Cribl deployments. When certificates expire without warning:
- Worker-leader communication fails
- Data pipeline connections break
- Outages occur with no advance notice

Currently, cribl-hc does not monitor certificate expiration dates, leaving users vulnerable to preventable outages.

### Solution

Add certificate expiration monitoring to the SecurityAnalyzer that:
1. Queries the `/system/certificates` API endpoint
2. Calculates days until expiration for each certificate
3. Generates findings with severity based on urgency
4. Provides actionable remediation guidance

## User Scenarios

### Scenario 1: Proactive Certificate Management
**As a** Cribl administrator  
**I want** to know which certificates are approaching expiration  
**So that** I can renew them before they cause outages

**Acceptance Criteria**:
- Running `cribl-hc analyze` shows certificate expiration warnings
- Certificates expiring within 30 days are flagged
- Each finding includes certificate name, expiration date, and days remaining

### Scenario 2: Critical Expiration Alert
**As a** SRE on-call  
**I want** critical alerts for certificates expiring very soon  
**So that** I can prioritize urgent renewals

**Acceptance Criteria**:
- Certificates expiring in <7 days show as CRITICAL severity
- Certificates expiring in <14 days show as HIGH severity
- Certificates expiring in <30 days show as WARNING severity

### Scenario 3: Already Expired Certificates
**As a** Cribl administrator  
**I want** to identify certificates that have already expired  
**So that** I can understand why connections are failing

**Acceptance Criteria**:
- Expired certificates show as CRITICAL severity
- Finding indicates the certificate is already expired
- Remediation suggests immediate renewal

## Functional Requirements

### FR-1: Certificate Discovery
- Query `/system/certificates` API endpoint
- Parse certificate list from response
- Handle empty certificate list gracefully

### FR-2: Expiration Calculation
- Parse `expiresAt` field from each certificate
- Calculate days until expiration from current date
- Handle timezone differences correctly

### FR-3: Severity Classification
| Days Until Expiration | Severity |
|----------------------|----------|
| Already expired | CRITICAL |
| 0-7 days | CRITICAL |
| 8-14 days | HIGH |
| 15-30 days | WARNING |
| >30 days | No finding |

### FR-4: Finding Generation
Each finding must include:
- Certificate ID/name
- Expiration date (human-readable)
- Days remaining (or "EXPIRED")
- Severity level
- Remediation steps

### FR-5: Remediation Guidance
Provide specific remediation steps:
- How to renew the certificate
- Where to update the certificate in Cribl
- Link to Cribl documentation on certificate management

## Success Criteria

1. **Coverage**: All certificates returned by API are checked
2. **Accuracy**: No false positives (wrong expiration dates)
3. **Timeliness**: Alerts at 30/14/7 day thresholds
4. **Actionability**: Clear remediation in every finding
5. **Performance**: Adds <1 second to analysis time

## Technical Notes

### API Endpoint
```
GET /api/v1/system/certificates
```

### Expected Response Structure
```json
{
  "items": [
    {
      "id": "cert-name",
      "expiresAt": "2025-02-15T00:00:00Z",
      "type": "tls",
      "issuer": "...",
      "subject": "..."
    }
  ]
}
```

### Integration Point
Add to `SecurityAnalyzer.analyze()` method in `src/cribl_hc/analyzers/security.py`

## Out of Scope

- Certificate renewal automation (read-only tool)
- Certificate content validation (chain, algorithms)
- External CA integration
- Certificate deployment

## Dependencies

- API client must support `get_certificates()` method (exists)
- SecurityAnalyzer must be registered (exists)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API endpoint not available in older versions | Check API response, skip gracefully if 404 |
| Timezone parsing issues | Use UTC throughout, dateutil for parsing |
| Large number of certificates | Batch findings, summarize if >10 |

