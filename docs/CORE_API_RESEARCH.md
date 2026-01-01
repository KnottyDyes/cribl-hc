# Core API Research & Analyzer Enhancement Workshop

## Executive Summary

After analyzing the Cribl Core API spec, community forums, CriblCon sessions, and our existing codebase, I've identified significant opportunities to leverage Core API endpoints for high-value health checks that address real operational pain points.

**Current State:** We added 20 Core API endpoints but none are integrated into analyzers.
**Opportunity:** These endpoints address the most common operational challenges Cribl users face.

---

## Research Sources

### Official Documentation
- [Cribl Monitoring Docs](https://docs.cribl.io/stream/monitoring/)
- [Fleet Management Best Practices](https://docs.cribl.io/edge/fleets-design/)
- [Access Management](https://docs.cribl.io/stream/access-management/)
- [Version Control](https://docs.cribl.io/stream/version-control/)
- [Notification Targets](https://docs.cribl.io/stream/notifications-targets/)

### Community Insights
- [SIEMtune: Cribl Edge Fleet Management 2025](https://siemtune.com/cribl-edge-fleet-management-best-practices/)
- [CriblCon 2024 Recap](https://cribl.io/blog/criblcon-2024-recap/)
- [CriblVision Pack](https://cribl.io/blog/criblvision-pack/)
- [Cribl Community Knowledge Base](https://knowledge.cribl.io/)

---

## Common Operational Pain Points (from Community Research)

### 1. Configuration Drift (HIGH frequency)
- Workers running different config versions than leader
- Fleets out of sync after partial deploys
- Config changes not propagating to all workers

### 2. Certificate Expiration (MEDIUM-HIGH frequency)
- TLS certs expiring without warning
- Outages caused by expired certs on worker-leader communication
- No centralized view of cert expiration dates

### 3. RBAC/Permission Issues (MEDIUM frequency)
- Users with excessive permissions
- Stale user accounts after employee departures
- Unclear who has access to what

### 4. Fleet Health Visibility (HIGH frequency)
- Workers going offline without alerts
- Difficulty identifying which worker groups are healthy
- Metrics overload on leader from too many workers

### 5. Alerting Infrastructure Gaps (MEDIUM frequency)
- Notification targets not configured
- Alerts not reaching intended recipients
- No visibility into alert configuration health

### 6. Version Control Issues (MEDIUM frequency)
- Uncommitted changes in production
- Unclear deployment history
- Difficulty rolling back bad changes

---

## Core API Capabilities Mapped to Pain Points

| Pain Point | Core API Endpoints | Potential Value |
|------------|-------------------|-----------------|
| Config Drift | `/master/groups`, `/master/groups/{id}/configVersion` | Detect version mismatches across fleet |
| Cert Expiration | `/system/certificates` | Alert before certs expire |
| RBAC Audit | `/system/roles`, `/system/users`, `/system/teams`, `/system/policies` | Security compliance checks |
| Fleet Health | `/master/summary`, `/products/{product}/groups/{id}/summary` | Aggregate health view |
| Alert Infrastructure | `/notification-targets`, `/notifications` | Verify alerting is configured |
| Version Control | `/version/info`, `/version/status` | Detect uncommitted changes |
| API Key Security | `/system/keys` | Find stale/unused API keys |
| System Messages | `/system/messages` | Surface system-generated warnings |

---

## Proposed Analyzer Enhancements

### 1. Enhanced Fleet Analyzer (fleet.py) - HIGH VALUE

**Current:** Uses `get_workers()`, `get_system_status()`, `get_pipelines()`

**Add:**
```python
# Config drift detection
worker_groups = await client.get_worker_groups()
master_summary = await client.get_master_summary()

# Check for config version mismatches
for group in worker_groups:
    group_id = group.get('id')
    config_version = group.get('configVersion')
    summary = await client.get_worker_group_summary(group_id)
    deploying_count = group.get('deployingWorkerCount', 0)

    if deploying_count > 0:
        findings.append(Finding(
            severity="warning",
            title=f"Config deployment in progress for {group_id}",
            description=f"{deploying_count} workers still deploying config {config_version}"
        ))
```

**New Checks:**
- Workers with stale config versions
- Worker groups with deployment in progress
- Fleet-wide health summary vs individual worker health
- Config drift between worker groups

---

### 2. Enhanced Security Analyzer (security.py) - HIGH VALUE

**Current:** Uses `get_outputs()`, `get_inputs()`, `get_auth_config()`, `get_system_settings()`

**Add:**
```python
# RBAC audit
roles = await client.get_roles()
users = await client.get_users()
teams = await client.get_teams()
policies = await client.get_policies()

# Check for overly permissive roles
for role in roles:
    permissions = role.get('permissions', [])
    if '*' in permissions or 'admin:*' in permissions:
        findings.append(Finding(
            severity="warning",
            title=f"Overly permissive role: {role['id']}",
            description="Role grants wildcard permissions"
        ))

# Check for stale users
for user in users:
    last_login = user.get('lastLogin')
    if is_stale(last_login, days=90):
        findings.append(Finding(
            severity="info",
            title=f"Inactive user: {user['id']}",
            description=f"User has not logged in for 90+ days"
        ))

# Certificate expiration checks
certificates = await client.get_certificates()
for cert in certificates:
    expires_at = cert.get('expiresAt')
    if expires_within(expires_at, days=30):
        findings.append(Finding(
            severity="critical",
            title=f"Certificate expiring soon: {cert['id']}",
            description=f"Certificate expires {expires_at}"
        ))

# API key audit
api_keys = await client.get_api_keys()
for key in api_keys:
    last_used = key.get('lastUsed')
    if last_used is None or is_stale(last_used, days=90):
        findings.append(Finding(
            severity="info",
            title=f"Unused API key: {key['id']}",
            description="API key has not been used in 90+ days"
        ))
```

**New Checks:**
- Overly permissive roles (wildcard permissions)
- Inactive user accounts (no login in 90 days)
- Certificate expiration warnings (30, 14, 7 days)
- Unused API keys
- Teams without members
- Orphaned policies

---

### 3. NEW: Alerting Infrastructure Analyzer - MEDIUM VALUE

**Create: `alerting.py`**

```python
class AlertingAnalyzer(BaseAnalyzer):
    """Analyze alerting infrastructure health."""

    async def analyze(self, client: CriblAPIClient) -> AnalysisResult:
        # Get notification targets and rules
        targets = await client.get_notification_targets()
        notifications = await client.get_notifications()

        findings = []

        # Check for no notification targets configured
        if not targets:
            findings.append(Finding(
                severity="warning",
                title="No notification targets configured",
                description="Configure Slack, PagerDuty, or webhook targets for alerting"
            ))

        # Check target types
        target_types = {t.get('type') for t in targets}
        if 'pagerduty' not in target_types:
            findings.append(Finding(
                severity="info",
                title="No PagerDuty integration",
                description="Consider PagerDuty for critical alerting"
            ))

        # Check for disabled notifications
        disabled_count = sum(1 for n in notifications if not n.get('enabled', True))
        if disabled_count > 0:
            findings.append(Finding(
                severity="info",
                title=f"{disabled_count} notifications are disabled",
                description="Review disabled notifications to ensure they're intentional"
            ))

        # Check for notifications without targets
        for notification in notifications:
            if not notification.get('targets'):
                findings.append(Finding(
                    severity="warning",
                    title=f"Notification has no targets: {notification['id']}",
                    description="Notification will not be delivered"
                ))
```

---

### 4. NEW: Version Control Health Analyzer - MEDIUM VALUE

**Create: `version_control.py`**

```python
class VersionControlAnalyzer(BaseAnalyzer):
    """Analyze version control and git health."""

    async def analyze(self, client: CriblAPIClient) -> AnalysisResult:
        # Get version/git status
        version_status = await client.get("/api/v1/version/status")
        version_info = await client.get("/api/v1/version/info")

        findings = []

        # Check for uncommitted changes
        if version_status.get('uncommittedChanges'):
            findings.append(Finding(
                severity="warning",
                title="Uncommitted configuration changes",
                description="Changes exist that have not been committed to version control"
            ))

        # Check for undeployed commits
        if version_status.get('undeployedCommits'):
            findings.append(Finding(
                severity="info",
                title="Undeployed commits exist",
                description="Committed changes have not been deployed to workers"
            ))

        # Check git remote connectivity
        if not version_info.get('remoteConfigured'):
            findings.append(Finding(
                severity="info",
                title="No remote git repository configured",
                description="Configure remote git for disaster recovery backups"
            ))
```

---

### 5. Enhanced Health Analyzer (health.py) - MEDIUM VALUE

**Add:**
```python
# System messages (warnings from Cribl itself)
system_messages = await client.get_system_messages()
for msg in system_messages:
    severity = msg.get('severity', 'info')
    if severity in ('warning', 'error', 'critical'):
        findings.append(Finding(
            severity=severity,
            title=f"System message: {msg.get('title', 'Unknown')}",
            description=msg.get('message', '')
        ))

# Banners (operational notices)
banners = await client.get_banners()
for banner in banners:
    if banner.get('enabled') and banner.get('type') == 'system':
        findings.append(Finding(
            severity="info",
            title="Active system banner",
            description=banner.get('message', '')
        ))
```

---

## API Spec Compliance Audit

### Current Issues Found

1. **Missing group parameter in routes/pipelines calls**
   - Spec: `/api/v1/m/{group}/routes`
   - Our code: `/api/v1/routes` (assumes default group)
   - Impact: May fail for multi-group deployments

2. **Hardcoded endpoints vs product-aware paths**
   - Spec: `/products/{product}/groups/{id}/summary`
   - Our code: Mixed legacy and new paths
   - Impact: Some endpoints may not work with newer API versions

3. **Missing pagination handling**
   - Spec: Most list endpoints support `offset` and `limit`
   - Our code: Always fetches without pagination
   - Impact: May miss data in large deployments

4. **Response schema validation**
   - Spec: Defines exact response schemas
   - Our code: Uses `response.json()` without validation
   - Impact: Could break on API changes

### Recommended Fixes

```python
# 1. Add group parameter support
async def get_routes(self, group: str = "default") -> List[Dict]:
    response = await self.get(f"/api/v1/m/{group}/routes")
    ...

# 2. Add pagination support
async def get_workers(self, offset: int = 0, limit: int = 1000) -> List[Dict]:
    response = await self.get(
        "/api/v1/master/workers",
        params={"offset": offset, "limit": limit}
    )
    ...

# 3. Add response validation with Pydantic
from pydantic import BaseModel

class WorkerResponse(BaseModel):
    items: List[WorkerInfo]
    count: int
```

---

## Priority Matrix

| Enhancement | Value | Effort | Priority |
|------------|-------|--------|----------|
| Config drift detection (Fleet) | HIGH | LOW | P1 |
| Certificate expiration alerts (Security) | HIGH | LOW | P1 |
| RBAC audit (Security) | HIGH | MEDIUM | P1 |
| Alerting infrastructure analyzer | MEDIUM | MEDIUM | P2 |
| System messages surfacing | MEDIUM | LOW | P2 |
| Version control health | MEDIUM | MEDIUM | P2 |
| API spec compliance fixes | HIGH | HIGH | P3 |
| Pagination support | MEDIUM | MEDIUM | P3 |

---

## Recommended Implementation Phases

### Phase 1: Quick Wins (1-2 days)
- Add config drift detection to Fleet analyzer
- Add certificate expiration checks to Security analyzer
- Surface system messages in Health analyzer

### Phase 2: RBAC & Alerting (2-3 days)
- Complete RBAC audit in Security analyzer
- Create Alerting Infrastructure analyzer
- Add API key audit

### Phase 3: Spec Compliance (3-5 days)
- Add group parameter support to all relevant methods
- Implement pagination for large deployments
- Add response validation with Pydantic models

---

## Next Steps

1. Create feature branch: `feature/core-api-integration`
2. Prioritize Phase 1 quick wins
3. Add tests alongside implementation
4. Update documentation

---

*Research compiled: 2025-12-29*
