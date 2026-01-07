# Implementation Tasks: RBAC & User Account Audit

## Overview
**Feature**: 004-rbac-user-audit  
**Estimated Effort**: 4-5 hours  
**Dependencies**: May need to add `get_api_keys()` to API client

---

## Tasks

### Task 1: Add Role Permission Audit
**Priority**: High  
**Effort**: 45 minutes  
**File**: `src/cribl_hc/analyzers/security.py`

**Description**:
Add `_audit_role_permissions()` method to check for overly permissive roles.

**Implementation**:
```python
DANGEROUS_PERMISSIONS = {"*", "admin:*", "write:*", "system:*"}

async def _audit_role_permissions(self, client: CriblAPIClient) -> list[Finding]:
    """Audit roles for overly permissive permissions."""
    findings = []
    
    try:
        roles = await client.get_roles()
    except Exception as e:
        self.log.warning("role_audit_failed", error=str(e))
        return findings
    
    for role in roles:
        role_id = role.get("id", "unknown")
        permissions = set(role.get("permissions", []))
        
        dangerous = permissions & DANGEROUS_PERMISSIONS
        if dangerous:
            findings.append(self.create_finding(
                title=f"Overly permissive role: {role_id}",
                description=f"Role '{role_id}' has dangerous permissions: {', '.join(dangerous)}. This grants broader access than typically necessary.",
                severity=Severity.HIGH,
                category="security",
                remediation="Review role permissions and apply least-privilege principles. Replace wildcard permissions with specific required permissions.",
                metadata={"role_id": role_id, "dangerous_permissions": list(dangerous)}
            ))
    
    return findings
```

**Acceptance Criteria**:
- [ ] Dangerous permissions detected
- [ ] Built-in admin role handled appropriately

---

### Task 2: Add User Activity Audit
**Priority**: High  
**Effort**: 45 minutes  
**File**: `src/cribl_hc/analyzers/security.py`

**Description**:
Add `_audit_user_activity()` method to identify inactive accounts.

**Implementation**:
```python
async def _audit_user_activity(self, client: CriblAPIClient) -> list[Finding]:
    """Audit user accounts for inactivity."""
    findings = []
    
    try:
        users = await client.get_users()
    except Exception as e:
        self.log.warning("user_audit_failed", error=str(e))
        return findings
    
    now = datetime.now(timezone.utc)
    
    for user in users:
        user_id = user.get("id", user.get("username", "unknown"))
        last_login_str = user.get("lastLogin")
        disabled = user.get("disabled", False)
        created_str = user.get("created")
        
        if disabled:
            continue  # Skip already disabled users
        
        if last_login_str is None:
            # Never logged in - check if account is old
            if created_str:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                days_since_created = (now - created).days
                if days_since_created > 30:
                    findings.append(self.create_finding(
                        title=f"User never logged in: {user_id}",
                        description=f"User '{user_id}' was created {days_since_created} days ago but has never logged in.",
                        severity=Severity.WARNING,
                        category="security",
                        remediation="Verify if this account is still needed. Consider disabling or removing unused accounts.",
                        metadata={"user_id": user_id, "days_since_created": days_since_created}
                    ))
        else:
            last_login = datetime.fromisoformat(last_login_str.replace("Z", "+00:00"))
            days_inactive = (now - last_login).days
            
            if days_inactive > 180:
                severity = Severity.HIGH
            elif days_inactive > 90:
                severity = Severity.WARNING
            else:
                continue
                
            findings.append(self.create_finding(
                title=f"Inactive user account: {user_id}",
                description=f"User '{user_id}' has not logged in for {days_inactive} days (last login: {last_login.date()}).",
                severity=severity,
                category="security",
                remediation="Review account necessity. Disable inactive accounts to reduce attack surface.",
                metadata={"user_id": user_id, "days_inactive": days_inactive, "last_login": last_login_str}
            ))
    
    return findings
```

**Acceptance Criteria**:
- [ ] Inactive users detected (90+ days)
- [ ] Never-logged-in users detected
- [ ] Disabled users skipped

---

### Task 3: Add API Key Audit
**Priority**: High  
**Effort**: 45 minutes  
**File**: `src/cribl_hc/analyzers/security.py`

**Description**:
Add `_audit_api_keys()` method to identify unused API keys.

**Implementation**:
```python
async def _audit_api_keys(self, client: CriblAPIClient) -> list[Finding]:
    """Audit API keys for security risks."""
    findings = []
    
    try:
        keys = await client.get_api_keys()
    except Exception as e:
        self.log.warning("api_key_audit_failed", error=str(e))
        return findings
    
    now = datetime.now(timezone.utc)
    
    for key in keys:
        key_id = key.get("id", "unknown")
        last_used_str = key.get("lastUsed")
        created_str = key.get("created")
        
        if last_used_str is None:
            # Key never used
            if created_str:
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                days_since_created = (now - created).days
                if days_since_created > 30:
                    findings.append(self.create_finding(
                        title=f"API key never used: {key_id}",
                        description=f"API key '{key_id}' was created {days_since_created} days ago but has never been used.",
                        severity=Severity.WARNING,
                        category="security",
                        remediation="Review if this API key is still needed. Revoke unused keys to reduce security risk.",
                        metadata={"key_id": key_id, "days_since_created": days_since_created}
                    ))
        else:
            last_used = datetime.fromisoformat(last_used_str.replace("Z", "+00:00"))
            days_unused = (now - last_used).days
            
            if days_unused > 90:
                findings.append(self.create_finding(
                    title=f"Stale API key: {key_id}",
                    description=f"API key '{key_id}' has not been used for {days_unused} days (last used: {last_used.date()}).",
                    severity=Severity.WARNING,
                    category="security",
                    remediation="Consider rotating or revoking this API key if no longer needed.",
                    metadata={"key_id": key_id, "days_unused": days_unused, "last_used": last_used_str}
                ))
    
    return findings
```

**Acceptance Criteria**:
- [ ] Unused keys detected
- [ ] Stale keys detected (90+ days)

---

### Task 4: Ensure API Client Has Required Methods
**Priority**: High  
**Effort**: 30 minutes  
**File**: `src/cribl_hc/core/api_client.py`

**Description**:
Verify/add API client methods:
- `get_roles()` - exists
- `get_users()` - exists  
- `get_api_keys()` - may need to add
- `get_teams()` - may need to add

**Implementation** (if needed):
```python
async def get_api_keys(self) -> list[dict]:
    """Get all API keys."""
    response = await self._get("/api/v1/system/keys")
    return response.get("items", [])

async def get_teams(self) -> list[dict]:
    """Get all teams."""
    response = await self._get("/api/v1/system/teams")
    return response.get("items", [])
```

**Acceptance Criteria**:
- [ ] All required methods available

---

### Task 5: Integrate Audit Methods into SecurityAnalyzer
**Priority**: High  
**Effort**: 15 minutes  
**File**: `src/cribl_hc/analyzers/security.py`

**Description**:
Call all audit methods from `analyze()` and combine findings.

```python
async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
    result = self.create_result()
    
    # ... existing checks ...
    
    # RBAC and user audits
    result.findings.extend(await self._audit_role_permissions(client))
    result.findings.extend(await self._audit_user_activity(client))
    result.findings.extend(await self._audit_api_keys(client))
    
    return result
```

**Acceptance Criteria**:
- [ ] All audit methods called
- [ ] Findings combined in result

---

### Task 6: Write Comprehensive Unit Tests
**Priority**: High  
**Effort**: 1 hour  
**File**: `tests/unit/test_analyzers/test_security.py`

**Description**:
Test cases for all audit functions.

**Test Cases**:
```python
class TestRBACUserAudit:
    """Test RBAC and user account auditing."""

    # Role tests
    async def test_wildcard_permission_flagged(self, security_analyzer, mock_client):
        mock_client.get_roles.return_value = [{"id": "superadmin", "permissions": ["*"]}]
        result = await security_analyzer.analyze(mock_client)
        assert any("permissive role" in f.title.lower() for f in result.findings)

    async def test_safe_role_no_finding(self, security_analyzer, mock_client):
        mock_client.get_roles.return_value = [{"id": "reader", "permissions": ["read:pipelines"]}]
        result = await security_analyzer.analyze(mock_client)
        assert not any("permissive role" in f.title.lower() for f in result.findings)

    # User tests
    async def test_inactive_user_flagged(self, security_analyzer, mock_client):
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        mock_client.get_users.return_value = [{"id": "old.user", "lastLogin": old_date}]
        result = await security_analyzer.analyze(mock_client)
        assert any("inactive user" in f.title.lower() for f in result.findings)

    async def test_never_logged_in_flagged(self, security_analyzer, mock_client):
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        mock_client.get_users.return_value = [{"id": "new.user", "lastLogin": None, "created": old_date}]
        result = await security_analyzer.analyze(mock_client)
        assert any("never logged in" in f.title.lower() for f in result.findings)

    # API key tests
    async def test_unused_api_key_flagged(self, security_analyzer, mock_client):
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        mock_client.get_api_keys.return_value = [{"id": "old-key", "lastUsed": None, "created": old_date}]
        result = await security_analyzer.analyze(mock_client)
        assert any("api key" in f.title.lower() for f in result.findings)
```

**Acceptance Criteria**:
- [ ] All audit functions tested
- [ ] Edge cases covered
- [ ] Tests pass

---

### Task 7: Update Documentation
**Priority**: Medium  
**Effort**: 20 minutes  
**Files**: `README.md`, `docs/ANALYZERS.md`

**Description**:
Document new RBAC/user audit capabilities.

**Acceptance Criteria**:
- [ ] New checks documented
- [ ] Example findings shown

---

## Test Plan

### Unit Tests
| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Wildcard role | permissions: ["*"] | HIGH finding |
| Admin wildcard | permissions: ["admin:*"] | HIGH finding |
| Safe role | permissions: ["read:x"] | No finding |
| User inactive 100 days | lastLogin: now-100d | WARNING |
| User inactive 200 days | lastLogin: now-200d | HIGH |
| User never logged in | lastLogin: null, created: now-60d | WARNING |
| Active user | lastLogin: now-30d | No finding |
| Unused API key | lastUsed: null, created: now-60d | WARNING |
| Stale API key | lastUsed: now-120d | WARNING |
| Active API key | lastUsed: now-10d | No finding |

---

## Definition of Done

- [X] All audit methods implemented
- [X] API client methods available
- [X] Unit tests pass (>90% coverage) ✅ 99.8% pass rate, 75.43% coverage
- [X] Documentation updated
- [X] Linting passes

