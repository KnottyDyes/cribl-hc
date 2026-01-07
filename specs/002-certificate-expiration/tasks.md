# Implementation Tasks: Certificate Expiration Monitoring

## Overview
**Feature**: 002-certificate-expiration  
**Estimated Effort**: 2-3 hours  
**Dependencies**: None (API endpoint exists)

---

## Tasks

### Task 1: Add Certificate Expiration Check to SecurityAnalyzer
**Priority**: High  
**Effort**: 1 hour  
**File**: `src/cribl_hc/analyzers/security.py`

**Description**:
Add a new method `_check_certificate_expiration()` to SecurityAnalyzer that:
1. Calls `client.get_certificates()` 
2. Iterates through certificates
3. Calculates days until expiration
4. Creates findings based on severity thresholds

**Implementation**:
```python
async def _check_certificate_expiration(self, client: CriblAPIClient) -> list[Finding]:
    """Check for certificates approaching expiration."""
    findings = []
    
    try:
        certificates = await client.get_certificates()
    except Exception as e:
        self.log.warning("certificate_check_failed", error=str(e))
        return findings
    
    now = datetime.now(timezone.utc)
    
    for cert in certificates:
        cert_id = cert.get("id", "unknown")
        expires_at_str = cert.get("expiresAt")
        
        if not expires_at_str:
            continue
            
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except ValueError:
            continue
            
        days_until = (expires_at - now).days
        
        if days_until < 0:
            severity = Severity.CRITICAL
            title = f"Certificate expired: {cert_id}"
            description = f"Certificate '{cert_id}' expired {abs(days_until)} days ago on {expires_at.date()}"
        elif days_until <= 7:
            severity = Severity.CRITICAL
            title = f"Certificate expires in {days_until} days: {cert_id}"
            description = f"Certificate '{cert_id}' expires on {expires_at.date()} ({days_until} days)"
        elif days_until <= 14:
            severity = Severity.HIGH
            title = f"Certificate expires in {days_until} days: {cert_id}"
            description = f"Certificate '{cert_id}' expires on {expires_at.date()} ({days_until} days)"
        elif days_until <= 30:
            severity = Severity.WARNING
            title = f"Certificate expires in {days_until} days: {cert_id}"
            description = f"Certificate '{cert_id}' expires on {expires_at.date()} ({days_until} days)"
        else:
            continue  # No finding for certs with >30 days
            
        findings.append(self.create_finding(
            title=title,
            description=description,
            severity=severity,
            category="security",
            remediation="Renew the certificate before expiration. See Cribl docs: https://docs.cribl.io/stream/certificates/",
            metadata={"certificate_id": cert_id, "expires_at": expires_at_str, "days_remaining": days_until}
        ))
    
    return findings
```

**Acceptance Criteria**:
- [ ] Method added to SecurityAnalyzer
- [ ] Called from `analyze()` method
- [ ] Findings added to result

---

### Task 2: Write Unit Tests for Certificate Expiration
**Priority**: High  
**Effort**: 45 minutes  
**File**: `tests/unit/test_analyzers/test_security.py`

**Description**:
Add test cases for certificate expiration checking:
1. Test with expired certificate (CRITICAL)
2. Test with certificate expiring in 5 days (CRITICAL)
3. Test with certificate expiring in 10 days (HIGH)
4. Test with certificate expiring in 20 days (WARNING)
5. Test with certificate expiring in 60 days (no finding)
6. Test with empty certificate list
7. Test with API error (graceful handling)

**Test Structure**:
```python
class TestCertificateExpiration:
    """Test certificate expiration monitoring."""

    @pytest.fixture
    def security_analyzer(self):
        return SecurityAnalyzer()

    async def test_expired_certificate_critical(self, security_analyzer, mock_client):
        """Test that expired certificates generate CRITICAL findings."""
        mock_client.get_certificates.return_value = [
            {"id": "expired-cert", "expiresAt": "2024-01-01T00:00:00Z"}
        ]
        result = await security_analyzer.analyze(mock_client)
        
        cert_findings = [f for f in result.findings if "expired" in f.title.lower()]
        assert len(cert_findings) == 1
        assert cert_findings[0].severity == Severity.CRITICAL

    async def test_certificate_expiring_soon_critical(self, security_analyzer, mock_client):
        """Test that certificates expiring in <7 days are CRITICAL."""
        # Set expiration to 5 days from now
        expires = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        mock_client.get_certificates.return_value = [
            {"id": "soon-cert", "expiresAt": expires}
        ]
        result = await security_analyzer.analyze(mock_client)
        
        cert_findings = [f for f in result.findings if "soon-cert" in f.title]
        assert len(cert_findings) == 1
        assert cert_findings[0].severity == Severity.CRITICAL

    # ... additional tests
```

**Acceptance Criteria**:
- [ ] All severity thresholds tested
- [ ] Edge cases covered
- [ ] Tests pass locally

---

### Task 3: Add Integration Test with Mock API
**Priority**: Medium  
**Effort**: 30 minutes  
**File**: `tests/integration/test_security_analyzer.py`

**Description**:
Add integration test that verifies certificate checking works end-to-end with mocked API responses.

**Acceptance Criteria**:
- [ ] Integration test added
- [ ] Uses respx for HTTP mocking
- [ ] Covers full analyze flow

---

### Task 4: Update Documentation
**Priority**: Medium  
**Effort**: 15 minutes  
**Files**: `README.md`, `docs/ANALYZERS.md`

**Description**:
- Add certificate expiration to SecurityAnalyzer description
- Update analyzer capabilities list
- Add example finding output

**Acceptance Criteria**:
- [ ] README updated
- [ ] ANALYZERS.md updated
- [ ] Example output shown

---

## Test Plan

### Unit Tests
| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Expired cert | expiresAt in past | CRITICAL finding |
| 5 days to expire | expiresAt = now + 5d | CRITICAL finding |
| 10 days to expire | expiresAt = now + 10d | HIGH finding |
| 20 days to expire | expiresAt = now + 20d | WARNING finding |
| 60 days to expire | expiresAt = now + 60d | No finding |
| Empty list | [] | No findings |
| API error | Exception | Graceful handling, warning logged |

### Integration Tests
| Test Case | Description |
|-----------|-------------|
| Full analysis | Run SecurityAnalyzer with mock certs, verify findings |
| API unavailable | Verify analyzer continues without cert check |

### Manual Verification
1. Run against a Cribl instance with known certificate expiration dates
2. Verify findings match expected severity
3. Confirm remediation links work

---

## Definition of Done

- [ ] Code implemented and reviewed
- [ ] Unit tests pass (>90% coverage for new code)
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] No regressions in existing tests
- [ ] Linting passes (ruff, mypy)

