# Feature Research Report

**Generated**: 2026-01-10  
**Research Method**: Local docs analysis + API spec review + external research + recent implementation review  
**Tool**: cribl-hc Feature Research Agent

---

## Executive Summary

### Current State
- **21 analyzers** covering Stream, Edge, Lake, and Search products
- **~30 API endpoints** currently utilized
- **Strong coverage** for health, config, resources, security, and compliance
- **Recently added**: Sensitive data detection, data freshness monitoring
- **Recent UX improvements**: Grouped findings, worker group context

### Top Opportunities Identified

| Priority | Feature | Value | Effort | Status |
|----------|---------|-------|--------|--------|
| 🔴 P1 | Certificate Expiration Monitoring | HIGH | LOW | 📋 Planned |
| 🔴 P1 | Enhanced RBAC/User Audit | HIGH | MEDIUM | 📋 Planned |
| 🔴 P1 | Config Drift Detection | HIGH | LOW | 📋 Planned |
| 🟡 P2 | Notification Target Validation | MEDIUM | LOW | 📋 Planned |
| 🟡 P2 | API Key Lifecycle Management | MEDIUM | LOW | 📋 Planned |
| 🟡 P2 | System Messages Surfacing | MEDIUM | LOW | 📋 Planned |
| ~~🟢 P3~~ | ~~PII/PHI Leakage Detection~~ | ~~HIGH~~ | ~~HIGH~~ | ✅ **COMPLETE** |
| 🟢 P3 | Report Branding/Customization | MEDIUM | HIGH | 📋 Planned |
| 🟢 P3 | Multi-Deployment Comparison | HIGH | HIGH | 📋 Planned |

---

## Recently Completed Features (January 2026)

### ✅ PII/PHI Leakage Detection (P3 - COMPLETE)

**Status**: Implemented as **SensitiveDataAnalyzer**

**Original Priority**: P3 (HIGH value, HIGH effort)  
**Actual Effort**: Medium (implemented in Phase 12)

**Features Delivered**:
- SSN detection with validation (no 000, 666, 9xx patterns)
- Credit card number detection (13-16 digit patterns)
- AWS access key detection (`AKIA[0-9A-Z]{16}`)
- Private key detection (PEM format)
- Generic API key/secret pattern matching
- Critical/high severity findings for compliance

**Value**: SOC2/HIPAA/GDPR compliance, security posture improvement

**API Endpoints**: Uses event sampling (not direct API endpoint)

**Location**: `src/cribl_hc/analyzers/sensitive_data.py`

---

### ✅ Data Freshness Monitoring (NEW)

**Status**: Implemented as **FreshnessAnalyzer**

**Priority**: Not in original research (discovered need during production deployment)

**Features Delivered**:
- Event lag detection (event _time vs current time)
- Clock skew detection (future timestamps)
- Warning threshold: 5 minutes
- Critical threshold: 15 minutes
- Pipeline latency monitoring

**Value**: Identifies silent lag issues, prevents downstream breakage

**API Endpoints**: Uses event sampling

**Location**: `src/cribl_hc/analyzers/freshness.py`

---

### ✅ Worker Group Context Tracking (UX Enhancement)

**Status**: Complete across all analyzers

**Problem Solved**: Findings didn't indicate which worker group they applied to, making it hard to troubleshoot multi-group deployments.

**Solution**:
- Added `worker_group` field to Finding model
- Auto-populated from API client context
- Fixed missing tags in DataFlowTopologyAnalyzer
- Fixed missing tags in SensitiveDataAnalyzer
- Enhanced display in CLI, TUI, and GUI

**Value**: Faster troubleshooting in fleet deployments

---

### ✅ Grouped Findings Display (UX Enhancement)

**Status**: Complete across CLI, TUI, and GUI

**Features**:
- Similar findings grouped by `grouping_id` and `worker_group`
- CLI: Grouped output with component counts
- TUI: Interactive grouped view with expansion
- GUI: `GroupedFindingCard` component with collapsible details
- Shows all affected components in aggregate

**Value**: Reduces noise, improves finding clarity

**PRs**: #42, #39, #37

---

## Current Analyzer Coverage

### By Product

| Product | Analyzers | Coverage Level |
|---------|-----------|----------------|
| Stream | 17 | █████████░ 85% |
| Edge | 15 | ████████░░ 80% |
| Lake | 2 | ████░░░░░░ 40% |
| Search | 2 | ████░░░░░░ 40% |
| Core | 1 | ██░░░░░░░░ 20% |

### By Category

| Category | Analyzers | Notes |
|----------|-----------|-------|
| Health & Monitoring | HealthAnalyzer, LakeHealthAnalyzer, SearchHealthAnalyzer, FreshnessAnalyzer | ✅ **Freshness added** |
| Configuration | ConfigAnalyzer, VersionControlAnalyzer | Basic config validation |
| Resources | ResourceAnalyzer, StorageAnalyzer, LakeStorageAnalyzer | CPU/memory/disk covered |
| Performance | BackpressureAnalyzer, PipelinePerformanceAnalyzer, SearchPerformanceAnalyzer | Pipeline metrics good |
| Security | SecurityAnalyzer, SensitiveDataAnalyzer | ✅ **PII/PHI detection added** |
| Data Quality | LookupHealthAnalyzer, SchemaQualityAnalyzer, DataFlowTopologyAnalyzer | Schema & routing covered |
| Alerting | AlertingAnalyzer | **Needs target validation** |
| Fleet | FleetAnalyzer | **Needs config drift** |
| Cost | CostAnalyzer | License tracking |
| Predictive | PredictiveAnalyzer | Forecasting |

---

## High-Priority Opportunities

### 1. Certificate Expiration Monitoring (P1)

**Problem**: TLS certificate expiration is a top community-reported pain point. Expired certs cause worker-leader communication failures and outages.

**Solution**: Add certificate checks to SecurityAnalyzer

**API Endpoint**: `/system/certificates` (available, unused)

**Implementation**:
```python
certificates = await client.get_certificates()
for cert in certificates:
    expires_at = parse_date(cert.get('expiresAt'))
    days_until = (expires_at - now).days
    
    if days_until <= 7:
        severity = "critical"
    elif days_until <= 14:
        severity = "high"
    elif days_until <= 30:
        severity = "warning"
    else:
        continue
        
    findings.append(Finding(
        severity=severity,
        title=f"Certificate expires in {days_until} days",
        description=f"Certificate '{cert['id']}' expires {expires_at}",
        remediation="Renew certificate before expiration"
    ))
```

**Value**: Prevents outages, enables proactive maintenance  
**Effort**: ~2 hours (endpoint exists, simple date math)

---

### 2. Enhanced RBAC/User Audit (P1)

**Problem**: Organizations struggle with permission sprawl, stale accounts, and compliance audits.

**Solution**: Expand SecurityAnalyzer with comprehensive RBAC checks

**API Endpoints**: 
- `/system/users` ✅ (in client)
- `/system/roles` ✅ (in client)
- `/system/teams` ✅ (in client)
- `/system/policies` ✅ (in client)

**New Checks**:
1. **Inactive users** (no login in 90+ days)
2. **Overly permissive roles** (wildcard permissions)
3. **Empty teams** (teams with no members)
4. **Orphaned policies** (policies not attached to roles)
5. **Admin user count** (flag if too many admins)

**Example Finding**:
```
WARNING: Inactive user account
User 'john.doe' has not logged in for 127 days.
Recommendation: Review and disable or remove inactive accounts.
```

**Value**: Security compliance, audit readiness  
**Effort**: ~4 hours (endpoints exist, need login tracking logic)

---

### 3. Config Drift Detection (P1)

**Problem**: Workers running different config versions than leader causes inconsistent behavior.

**Solution**: Enhance FleetAnalyzer with config version checks

**API Endpoints**:
- `/master/groups` ✅ (in client)
- `/master/groups/{id}/configVersion` (available)
- `/master/summary` ✅ (in client)

**New Checks**:
1. Workers with stale config versions
2. Worker groups with deployment in progress
3. Config version mismatches between groups
4. Long-running deployments (stuck?)

**Example Finding**:
```
CRITICAL: Config drift detected
Worker group 'prod-workers' has 3 workers running config v42 
while leader is at v45.
Recommendation: Trigger re-deployment or investigate stuck workers.
```

**Value**: Operational consistency, faster troubleshooting  
**Effort**: ~3 hours (endpoints exist, comparison logic needed)

---

## Medium-Priority Opportunities

### 4. Notification Target Validation (P2)

**Problem**: AlertingAnalyzer checks if alerts exist, but doesn't validate that notification targets are configured and working.

**Current**: Checks for notification rules  
**Gap**: Doesn't verify targets (Slack, PagerDuty, webhooks) are configured

**API Endpoints**:
- `/notification-targets` ✅ (in client)
- `/notifications` ✅ (in client)

**New Checks**:
1. No notification targets configured
2. Notifications without targets assigned
3. Disabled notifications
4. Missing PagerDuty for critical alerts

**Value**: Ensures alerts actually reach responders  
**Effort**: ~2 hours

---

### 5. API Key Lifecycle Management (P2)

**Problem**: Stale API keys are a security risk and operational debt.

**API Endpoint**: `/system/keys` ✅ (in client)

**New Checks**:
1. API keys never used
2. API keys not used in 90+ days
3. Keys without expiration
4. Keys with overly broad permissions

**Value**: Security hygiene, credential rotation compliance  
**Effort**: ~2 hours

---

### 6. System Messages Surfacing (P2)

**Problem**: Cribl generates system messages (warnings, errors) that may go unnoticed.

**API Endpoint**: `/system/messages` ✅ (in client)

**Solution**: Surface system messages in HealthAnalyzer output

**New Checks**:
1. Critical/error system messages
2. Warning messages
3. Active system banners

**Value**: Surfaces Cribl's own warnings to users  
**Effort**: ~1 hour

---

## Lower-Priority Opportunities

### 7. Report Branding/Customization (P3)

**Status**: Already documented in FUTURE_FEATURES.md

**Use Cases**:
- MSPs delivering branded reports to clients
- Consulting firms with professional deliverables
- Multi-tenant environments

**Effort**: HIGH (template system, logo handling, PDF generation)

---

### 8. Multi-Deployment Comparison (P3)

**Problem**: Organizations with multiple Cribl deployments can't easily compare health/config across environments.

**Solution**: New CLI command to compare deployments

**Features**:
1. Side-by-side health scores
2. Config differences
3. Version comparison
4. Resource utilization comparison

**Effort**: HIGH (new architecture, multiple API calls, diff logic)

---

## Unused API Endpoints (High Value)

From Core API spec, these endpoints are available but not used:

| Endpoint | Potential Use | Priority |
|----------|---------------|----------|
| `/system/certificates` | Cert expiration alerts | P1 |
| `/master/groups/{id}/configVersion` | Config drift detection | P1 |
| `/system/users/{id}/info` | User activity tracking | P1 |
| `/system/banners` | Surface operational notices | P2 |
| `/system/scripts` | Script inventory/validation | P3 |
| `/products/lake/lakes/{id}/storage-locations` | Lake BYOS monitoring | P3 |
| `/search/usage-groups` | Search cost allocation | P3 |
| `/search/datatypes` | Data type validation | P3 |

---

## Research Findings Summary

### From CORE_API_RESEARCH.md

**Top Community Pain Points**:
1. Configuration drift (HIGH frequency)
2. Certificate expiration (MEDIUM-HIGH frequency)
3. RBAC/permission issues (MEDIUM frequency)
4. Fleet health visibility (HIGH frequency)
5. Alerting infrastructure gaps (MEDIUM frequency)
6. Version control issues (MEDIUM frequency)

### From LAKE_SEARCH_API_RESEARCH.md

**Lake Opportunities**:
- Dataset retention policy validation
- Storage format optimization (JSON→Parquet)
- Lakehouse availability monitoring
- BYOS configuration validation

**Search Opportunities**:
- Query cost analysis (CPU metrics available)
- Long-running job detection
- Dashboard health validation
- Saved search optimization

### From FUTURE_FEATURES.md

**Already Planned**:
- Report branding/customization (MSP use case)
- White-label mode
- Multi-language reports
- Custom report templates

---

## Recommended Implementation Phases

### Phase A: Quick Wins (1-2 days)
1. Certificate expiration checks → SecurityAnalyzer
2. System messages surfacing → HealthAnalyzer
3. Notification target validation → AlertingAnalyzer

### Phase B: Security Hardening (2-3 days)
1. Complete RBAC audit → SecurityAnalyzer
2. API key lifecycle checks → SecurityAnalyzer
3. Config drift detection → FleetAnalyzer

### Phase C: Lake/Search Expansion (3-5 days)
1. Expand LakeHealthAnalyzer with storage locations
2. Expand SearchPerformanceAnalyzer with cost analysis
3. Add dashboard health to SearchHealthAnalyzer

### Phase D: Enterprise Features (1-2 weeks)
1. Report branding system
2. Multi-deployment comparison
3. Scheduled health checks

---

## Next Steps

1. **Immediate**: Implement certificate expiration monitoring (highest ROI)
2. **This Week**: Add config drift detection and RBAC audit
3. **This Month**: Complete Phase A and B items
4. **Backlog**: Phase C and D for roadmap planning

---

## Appendix: Current Analyzer Details

| Analyzer | Objective | Products | API Methods Used |
|----------|-----------|----------|------------------|
| AlertingAnalyzer | alerting | stream,edge,search | notifications, notification-targets |
| BackpressureAnalyzer | backpressure | stream,edge | metrics |
| ConfigAnalyzer | config | stream,edge | pipelines, routes, outputs, inputs |
| CostAnalyzer | cost | stream | license_info |
| DataFlowTopologyAnalyzer | dataflow_topology | stream,edge | routes, pipelines, outputs |
| FleetAnalyzer | fleet | stream,edge,lake,search | workers, worker_groups |
| **FreshnessAnalyzer** ✨ | **freshness** | **stream,edge** | **event sampling** |
| HealthAnalyzer | health | stream,edge | workers, system_status |
| LakeHealthAnalyzer | lake | lake | lake_datasets |
| LakeStorageAnalyzer | lake | lake | lake_dataset_stats |
| LookupHealthAnalyzer | lookup_health | stream,edge | lookups |
| PipelinePerformanceAnalyzer | pipeline_performance | stream,edge | pipelines, metrics |
| PredictiveAnalyzer | predictive | stream,edge,lake,search | metrics, workers |
| ResourceAnalyzer | resource | stream,edge | workers, metrics |
| SchemaQualityAnalyzer | schema_quality | stream,edge | pipelines, parsers |
| SearchHealthAnalyzer | search | search | search_jobs, search_dashboards |
| SearchPerformanceAnalyzer | search | search | search_jobs |
| SecurityAnalyzer | security | stream,edge | outputs, inputs, system_settings |
| **SensitiveDataAnalyzer** ✨ | **sensitive_data** | **stream,edge** | **event sampling** |
| StorageAnalyzer | storage | stream,edge | outputs, destinations |
| VersionControlAnalyzer | version_control | stream,edge,lake,search,core | version_info, uncommitted_files |

**Total**: 21 analyzers (2 added in January 2026: FreshnessAnalyzer ✨, SensitiveDataAnalyzer ✨)

---

## External Research Findings

### Cribl-Specific Insights (from Librarian Agent)

**CriblVision Pack Replication Ideas**:
1. **Throughput Bottlenecks** - Identify pipelines where `out_events` << `in_events` without intentional filtering
2. **Worker Group Imbalance** - Check if traffic is unevenly distributed (one worker handling 80% of load)
3. **Backpressure Monitoring** - Detect destination pushback causing queue buildup
4. **Endpoint Health** - Track request failure counts and latency spikes per integration

**Cribl 4.x Features to Leverage**:
1. **Cribl Insights** - Verify if Insights is enabled and surfacing alerts
2. **Virtual Tables** - Use KQL to query `$vt_jobs` for failed jobs, `$vt_datasets` for Lake health
3. **Cribl Guard (v4.14+)** - Verify masking policies are active on high-risk sources
4. **Internal Cribl Source** - Exposes granular metrics queryable via API

### Industry Best Practices (from Librarian Agent)

**Performance & Processing Efficiency**:
| Feature | Description | Value |
|---------|-------------|-------|
| Regex Efficiency Analyzer | Scan for high-risk regex (nested quantifiers, catastrophic backtracking) | Prevents CPU spikes |
| Pipeline Redundancy Detection | Find duplicate transformations/lookups | Reduces CPU overhead |
| Inactive Component Flag | Find routes/pipelines with zero events in 7+ days | Cleans config debt |
| Worker Right-Sizing | Recommend node count based on 95th percentile peaks | Optimizes costs |

**Security & Compliance**:
| Feature | Description | Value |
|---------|-------------|-------|
| In-Stream PII/PHI Detection | Sample data for unmasked SSNs, API keys, credit cards | SOC2/HIPAA/GDPR compliance |
| Git Integrity Audit | Verify Leader is successfully pushing to Git remote | Audit trail integrity |
| Unencrypted Traffic Audit | Flag plaintext protocols (Syslog UDP, HTTP, S3 without SSE) | Zero-trust security |

**Data Quality & Observability**:
| Feature | Description | Value |
|---------|-------------|-------|
| End-to-End Freshness Monitor | Calculate delta between event creation and output time | Identifies silent lag |
| Schema Drift Detection | Alert if critical fields disappear or change type | Prevents downstream breakage |
| Lookup Table Staleness | Check last-updated metadata for enrichment sources | Prevents stale enrichment |

**Cost Management**:
| Feature | Description | Value |
|---------|-------------|-------|
| License Value Optimizer | Flag low-priority data consuming high-cost license volume | Justifies drop-rules |
| LLM Token Tracker | Track AI enrichment token usage and predict overages | Manages variable costs |

---

## Updated Priority Matrix

Based on combined local + external research:

| Priority | Feature | Value | Effort | Source |
|----------|---------|-------|--------|--------|
| 🔴 P1 | Certificate Expiration Monitoring | HIGH | LOW | Community + Industry |
| 🔴 P1 | Config Drift Detection | HIGH | LOW | CriblVision + Community |
| 🔴 P1 | Enhanced RBAC/User Audit | HIGH | MEDIUM | Community + Compliance |
| 🟡 P2 | Regex Efficiency Analyzer | HIGH | MEDIUM | Industry (Elastic) |
| 🟡 P2 | Notification Target Validation | MEDIUM | LOW | Community |
| 🟡 P2 | Orphaned Route/Pipeline Finder | MEDIUM | LOW | CriblVision |
| 🟡 P2 | Worker Group Imbalance Detection | MEDIUM | MEDIUM | CriblVision |
| 🟢 P3 | PII/PHI Leakage Detection | HIGH | HIGH | Industry (Datadog) |
| 🟢 P3 | Schema Drift Detection | MEDIUM | HIGH | Industry (Data Obs) |
| 🟢 P3 | End-to-End Freshness Monitor | MEDIUM | HIGH | Industry (SRE) |

---

*Report generated by /research.features skill*  
*External research: Cribl docs, CriblVision pack, industry observability tools*
