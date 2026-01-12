# /research.features - Feature Research & Discovery Skill

**Description**: Research new features, use cases, and opportunities to provide value in cribl-hc.

**Scope**: project

---

## Command Instructions

When the user invokes `/research.features`, conduct comprehensive research to identify valuable new features.

## Arguments

Optional focus area:
- `/research.features` - Full research across all areas
- `/research.features analyzers` - Focus on new analyzer opportunities
- `/research.features api` - Focus on unused API endpoints
- `/research.features integrations` - Focus on external integrations
- `/research.features ux` - Focus on UX/usability improvements

---

## Execution Flow

### Phase 1: Current State Analysis

#### 1.1 Inventory Existing Features

Read and analyze:

```
# Current analyzers
src/cribl_hc/analyzers/*.py

# Current CLI commands  
src/cribl_hc/cli/*.py

# Current API endpoints
src/cribl_hc/api/*.py

# Current models
src/cribl_hc/models/*.py
```

Build inventory:
- List all analyzer objectives and what they check
- List supported products per analyzer (stream, edge, lake, search)
- Identify coverage gaps by product

#### 1.2 Review Existing Research

Read local documentation:

```
docs/FUTURE_FEATURES.md          # Already planned features
docs/CORE_API_RESEARCH.md        # API capabilities research
docs/LAKE_SEARCH_API_RESEARCH.md # Lake/Search API research
docs/PRODUCT_COMPATIBILITY.md    # Product support matrix
docs/EDGE_API_MAPPING.md         # Edge API coverage
development/*.md                 # Development notes
```

Extract:
- Planned but unimplemented features
- Identified pain points
- API endpoints not yet used
- Community feedback captured

#### 1.3 Analyze Cribl API Specs

Parse OpenAPI specifications:

```
cribl_api_reference/cribl-apidocs-4.15.1-1b453caa_stream.yml
cribl_api_reference/cribl-apidocs-4.15.1-1b453caa_edge.yml
cribl_api_reference/cribl-apidocs-4.15.1-1b453caa_lake.yml
cribl_api_reference/cribl-apidocs-4.15.1-1b453caa_search.yml
cribl_api_reference/cribl-apidocs-4.15.1-1b453caa_core.yml
```

Identify:
- Total endpoints available vs currently used
- Endpoint categories with no analyzer coverage
- New endpoints in v4.15.x not yet leveraged
- Deprecated endpoints we should stop using

### Phase 2: External Research

#### 2.1 Spawn Librarian Agent for Industry Research

```python
background_task(
    agent="librarian",
    prompt="""
    Research observability and monitoring tool capabilities:
    
    1. What health checks do similar tools provide?
       - Splunk Health Check tools
       - Datadog infrastructure monitoring
       - Elastic Stack health monitoring
       - Vector/Fluent observability
    
    2. What are industry best practices for:
       - Log pipeline health monitoring
       - Data quality validation
       - Capacity planning
       - Security posture assessment
    
    3. What operational pain points do Cribl users report?
       - Search Cribl community forums
       - Check Cribl GitHub issues
       - Look for CriblCon session topics
    
    Return specific feature ideas with justification.
    """,
    description="Research industry monitoring practices"
)
```

#### 2.2 Spawn Librarian for Cribl Docs Research

```python
background_task(
    agent="librarian", 
    prompt="""
    Research Cribl's latest capabilities:
    
    1. What new features are in Cribl Stream 4.x?
    2. What monitoring/observability features does Cribl recommend?
    3. What are documented best practices we could automate checking?
    4. What metrics does CriblVision pack monitor?
    5. What health indicators does Cribl's built-in monitoring expose?
    
    Focus on features that could become automated health checks.
    """,
    description="Research Cribl documentation"
)
```

### Phase 3: Gap Analysis

#### 3.1 Coverage Matrix

Create a matrix of what's covered vs not:

| Category | Stream | Edge | Lake | Search | Coverage |
|----------|--------|------|------|--------|----------|
| Worker Health | ✅ | ✅ | ❌ | ❌ | 50% |
| Config Validation | ✅ | ✅ | ❌ | ❌ | 50% |
| Resource Usage | ✅ | ✅ | ❌ | ❌ | 50% |
| Security | ✅ | ✅ | ❌ | ❌ | 50% |
| Data Quality | ✅ | ✅ | ❌ | ❌ | 50% |
| Alerting | ✅ | ✅ | ❌ | ❌ | 50% |
| Version Control | ✅ | ❌ | ❌ | ❌ | 25% |
| ...etc | | | | | |

#### 3.2 Unused API Analysis

Compare API specs against current usage:

```python
# Pseudo-analysis
available_endpoints = parse_openapi_specs()
used_endpoints = scan_api_client_usage()
unused = available_endpoints - used_endpoints

# Group by value potential
high_value_unused = [
    ep for ep in unused 
    if ep.category in ['monitoring', 'health', 'security', 'config']
]
```

#### 3.3 Pain Point Mapping

Map common pain points to potential features:

| Pain Point | Source | Current Coverage | Opportunity |
|------------|--------|------------------|-------------|
| Config drift | CORE_API_RESEARCH.md | Partial | Enhanced FleetAnalyzer |
| Cert expiration | Community | None | New CertificateAnalyzer |
| RBAC audit | Community | SecurityAnalyzer | Enhance with user/role analysis |
| Alert delivery | Community | AlertingAnalyzer | Add notification target validation |

### Phase 4: Feature Proposals

#### 4.1 Categorize Opportunities

**Quick Wins (< 1 day effort)**
- Features using existing infrastructure
- Simple additions to current analyzers
- Documentation/UX improvements

**Medium Effort (1-3 days)**
- New analyzers with straightforward API usage
- Integration enhancements
- CLI improvements

**Large Effort (1+ week)**
- New product support (Lake, Search expansion)
- Major architectural changes
- External integrations (Slack, PagerDuty, Jira)

#### 4.2 Prioritization Framework

Score each opportunity:

| Factor | Weight | Scoring |
|--------|--------|---------|
| User Value | 40% | How much pain does it solve? (1-5) |
| Effort | 25% | How hard to implement? (inverse 1-5) |
| API Ready | 20% | Is the API available? (1-5) |
| Uniqueness | 15% | Do other tools offer this? (1-5) |

### Phase 5: Output Report

Generate a comprehensive report:

```markdown
# Feature Research Report

**Generated**: [DATE]
**Focus Area**: [AREA or "Full Research"]
**Researched By**: AI Feature Research Agent

---

## Executive Summary

- **Current Coverage**: X analyzers covering Y% of Cribl API
- **Opportunities Identified**: N features across M categories
- **Top 3 Recommendations**: [Quick summary]

---

## Current State

### Analyzer Inventory
| Analyzer | Objective | Products | Endpoints Used |
|----------|-----------|----------|----------------|
| HealthAnalyzer | health | stream, edge | /workers, /status |
| ... | ... | ... | ... |

### API Coverage
- **Stream**: X/Y endpoints used (Z%)
- **Edge**: X/Y endpoints used (Z%)
- **Lake**: X/Y endpoints used (Z%)
- **Search**: X/Y endpoints used (Z%)
- **Core**: X/Y endpoints used (Z%)

---

## Opportunities Identified

### 🎯 High Priority (Recommended)

#### 1. [Feature Name]
- **Problem**: [What pain point it solves]
- **Solution**: [What we'd build]
- **Value**: [Why users care]
- **Effort**: [S/M/L]
- **API Endpoints**: [Which endpoints to use]
- **Example Finding**: 
  ```
  CRITICAL: TLS certificate expires in 7 days
  Affected: worker-03.example.com
  Remediation: Renew certificate before [DATE]
  ```

#### 2. [Feature Name]
...

### 📋 Medium Priority

...

### 💡 Future Considerations

...

---

## Unused API Endpoints (High Value)

| Endpoint | Category | Potential Use |
|----------|----------|---------------|
| `/system/certificates` | Security | Certificate expiration monitoring |
| `/version/uncommitted` | Config | Detect uncommitted changes |
| ... | ... | ... |

---

## External Research Findings

### Industry Best Practices
- [Finding 1]
- [Finding 2]

### Competitor Capabilities
- [What others offer that we don't]

### Community Feedback
- [Pain points from forums/issues]

---

## Recommended Next Steps

1. **Immediate** (this session): [Specific action]
2. **Short-term** (this week): [Specific action]
3. **Medium-term** (this month): [Specific action]

---

## Appendix

### A. Full Unused Endpoint List
[Detailed list]

### B. Research Sources
[Links and references]

### C. Raw Research Data
[Librarian agent outputs]
```

---

## Integration Points

### After Research Completes

Offer next steps:
1. **Create spec**: `/speckit.specify [feature description]` for top recommendation
2. **Update FUTURE_FEATURES.md**: Add newly identified opportunities
3. **Create GitHub issues**: For tracking implementation

### Periodic Research

Suggest running `/research.features` when:
- New Cribl version released (check new API endpoints)
- Quarterly roadmap planning
- After major feature completion (what's next?)

---

## Example Invocation

**User**: `/research.features analyzers`

**Agent Output**:

```markdown
# Feature Research Report: Analyzers

## Quick Analysis

Scanned 19 existing analyzers across 4 products.

### Coverage Gaps Identified

1. **Certificate Health** (HIGH VALUE)
   - No analyzer monitors TLS certificate expiration
   - API available: `/system/certificates`
   - Community reports this as top pain point
   - Effort: Small

2. **Git/Version Control Health** (MEDIUM VALUE)  
   - VersionControlAnalyzer exists but limited
   - Unused endpoints: `/version/uncommitted`, `/version/status`
   - Could detect pending deploys, uncommitted changes
   - Effort: Small

3. **Notification Target Validation** (MEDIUM VALUE)
   - AlertingAnalyzer checks alerts exist
   - Doesn't validate notification targets work
   - API: `/notification-targets`, `/system/messages`
   - Effort: Medium

### Recommendation

Start with Certificate Health - it's:
- Highest user-reported pain point
- Simple API (single endpoint)
- High-impact finding (prevents outages)

Would you like me to create a spec for CertificateAnalyzer?
```

---

## Notes for Agent

- Always read local docs first (faster, project-specific context)
- Spawn librarian agents in parallel for external research
- Be specific in proposals (endpoint names, example findings)
- Prioritize actionability over comprehensiveness
- Link opportunities to user pain points, not just "nice to have"
