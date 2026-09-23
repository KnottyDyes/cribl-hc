# Phase 14 Missing Analyzer Specifications

## 1. EnhancedTeamPermissionsAnalyzer

### Overview
**Objective**: `enhanced-team-permissions`  
**Category**: Organization & Optimization (Phase 14C)  
**Effort**: 4 hours  
**Priority**: Medium

### Description
Analyzes team structure and permission configurations to identify overly permissive roles, unused permissions, and potential security risks in team access patterns.

### Key Capabilities
- **Permission Overlap Detection**: Identifies users with overlapping or excessive permissions
- **Unused Permission Analysis**: Finds permissions granted but never used
- **Role Consistency Validation**: Ensures consistent permission patterns across similar roles
- **Team Membership Hygiene**: Validates team membership and access patterns
- **Security Posture Assessment**: Evaluates overall permission security posture

### API Endpoints Required
- `GET /api/v1/auth/users` - List all users and their roles
- `GET /api/v1/auth/roles` - Get role definitions and permissions
- `GET /api/v1/auth/teams` - List teams and memberships
- `GET /api/v1/system/audit` - Audit logs for permission usage (if available)

### Key Findings & Recommendations

#### Critical Severity
- **Overly Permissive Admin Users**: Users with admin access who haven't logged in for 90+ days
- **Permission Escalation Risks**: Users with both read and write access to sensitive areas
- **Orphaned Admin Accounts**: Admin users not belonging to any team

#### High Severity
- **Unused High-Privilege Permissions**: Admin/write permissions granted but unused for 60+ days
- **Inconsistent Role Patterns**: Similar roles with significantly different permission sets
- **Team Membership Gaps**: Critical system access without team oversight

#### Medium Severity
- **Permission Drift**: Roles that have drifted from standard permission templates
- **Underutilized Roles**: Roles defined but assigned to very few users (< 3)
- **Team Size Anomalies**: Teams with 1 member or 50+ members

### Implementation Approach
1. **Data Collection**: Fetch users, roles, teams, and audit logs
2. **Permission Analysis**: Build permission matrices and usage patterns
3. **Risk Assessment**: Apply security heuristics and thresholds
4. **Recommendations**: Generate role optimization and security improvements

### Success Criteria
- Identifies 90% of permission security risks
- Provides actionable role consolidation recommendations
- Zero false positives on critical findings

---

## 2. LibraryAndResourceAnalyzer

### Overview
**Objective**: `library-resource-optimization`  
**Category**: Organization & Optimization (Phase 14C)  
**Effort**: 5 hours  
**Priority**: Medium

### Description
Analyzes library entries, functions, and reusable resources to identify unused dependencies, optimization opportunities, and maintenance overhead.

### Key Capabilities
- **Unused Library Detection**: Identifies libraries defined but never referenced
- **Dependency Chain Analysis**: Maps library usage patterns and dependencies
- **Performance Impact Assessment**: Evaluates library size vs usage frequency
- **Maintenance Burden Analysis**: Identifies complex libraries requiring frequent updates
- **Reuse Pattern Optimization**: Suggests consolidation of duplicate functionality

### API Endpoints Required
- `GET /api/v1/libs` - List all library entries
- `GET /api/v1/libs/{id}` - Get detailed library content and metadata
- `GET /api/v1/pipelines` - Search for library references in pipelines
- `GET /api/v1/routes` - Search for library references in routes
- `GET /api/v1/functions` - Get function definitions and usage

### Key Findings & Recommendations

#### Critical Severity
- **Broken Library Dependencies**: Libraries with invalid references causing runtime errors
- **Massive Unused Libraries**: Libraries > 10MB never referenced
- **Security-Risk Libraries**: Libraries containing hardcoded credentials or secrets

#### High Severity
- **Memory-Inefficient Libraries**: Large libraries loaded but rarely used (< 10% usage rate)
- **Duplicate Functionality**: Multiple libraries implementing same logic
- **Complex Maintenance Burden**: Libraries with 50+ functions requiring frequent updates

#### Medium Severity
- **Underutilized Libraries**: Libraries referenced by only 1 pipeline
- **Size Optimization Opportunities**: Libraries that could be split or compressed
- **Documentation Gaps**: Complex libraries lacking adequate documentation

### Implementation Approach
1. **Library Inventory**: Catalog all libraries with metadata (size, functions, last modified)
2. **Usage Analysis**: Search pipelines/routes for library references using AST parsing
3. **Dependency Mapping**: Build reference graphs and usage patterns
4. **Optimization Scoring**: Calculate efficiency metrics and recommendations

### Success Criteria
- 95% accuracy in detecting unused libraries
- Provides storage savings estimates for optimizations
- Identifies all broken dependencies

---

## 3. SearchWorkspaceOptimizationAnalyzer

### Overview
**Objective**: `search-workspace-optimization`  
**Category**: Search & Licensing (Phase 14D)  
**Effort**: 4 hours  
**Priority**: Medium

### Description
Analyzes Cribl Search workspace organization, saved search usage patterns, and dashboard efficiency to identify optimization opportunities and best practices violations.

### Key Capabilities
- **Workspace Organization Analysis**: Evaluates folder structure and naming conventions
- **Saved Search Optimization**: Identifies inefficient or duplicate saved searches
- **Dashboard Query Analysis**: Reviews dashboard element efficiency and performance
- **Usage Pattern Detection**: Finds underutilized vs overutilized search assets
- **Cost Efficiency Assessment**: Evaluates search patterns for licensing optimization

### API Endpoints Required
- `GET /api/v1/m/{workspace}/search/saved-searches` - List saved searches
- `GET /api/v1/m/{workspace}/search/dashboards` - List dashboards
- `GET /api/v1/m/{workspace}/search/jobs` - Get recent job history and performance
- `GET /api/v1/m/{workspace}/search/datasets` - List available datasets
- `GET /api/v1/m/{workspace}/system/audit` - Usage audit logs

### Key Findings & Recommendations

#### Critical Severity
- **Broken Dashboard Elements**: Dashboards with invalid dataset references
- **Costly Saved Searches**: Saved searches running > $100/month without business justification
- **Security Violations**: Saved searches exposing sensitive data patterns

#### High Severity
- **Inefficient Dashboard Queries**: Dashboard elements with wildcard dataset usage
- **Duplicate Saved Searches**: Multiple searches with identical logic
- **Unused High-Cost Assets**: Expensive saved searches/dashboards used < 5 times/month

#### Medium Severity
- **Poor Naming Conventions**: Inconsistent naming across workspace assets
- **Underutilized Dashboards**: Dashboards accessed by < 3 users
- **Query Optimization Opportunities**: Searches that could benefit from dataset filtering

### Implementation Approach
1. **Asset Inventory**: Catalog all saved searches, dashboards, and datasets
2. **Usage Analysis**: Analyze access patterns and execution frequency
3. **Performance Evaluation**: Assess query efficiency and cost patterns
4. **Optimization Recommendations**: Generate workspace organization and efficiency improvements

### Success Criteria
- Identifies all broken references and inefficient patterns
- Provides cost savings estimates for optimizations
- Zero false positives on critical findings

---

## 4. LicenseOptimizationAnalyzer

### Overview
**Objective**: `license-optimization`  
**Category**: Search & Licensing (Phase 14D)  
**Effort**: 5 hours  
**Priority**: High

### Description
Analyzes license consumption patterns, drop rule effectiveness, and licensing efficiency to identify cost optimization opportunities and ensure optimal license utilization.

### Key Capabilities
- **Consumption Trend Analysis**: Tracks license usage over time with forecasting
- **Drop Rule Effectiveness**: Evaluates drop rules for actual data reduction impact
- **Cost Efficiency Assessment**: Identifies high-cost, low-value data processing
- **Licensing Optimization**: Suggests configuration changes for better license utilization
- **Budget Impact Analysis**: Quantifies potential savings from optimizations

### API Endpoints Required
- `GET /api/v1/system/license` - Current license status and consumption
- `GET /api/v1/system/license/history` - Historical license usage data
- `GET /api/v1/pipelines` - Analyze drop rules and filter effectiveness
- `GET /api/v1/routes` - Route-level data processing analysis
- `GET /api/v1/metrics` - Performance and throughput metrics for cost analysis

### Key Findings & Recommendations

#### Critical Severity
- **License Exhaustion Risk**: Projected exhaustion within 30 days
- **Ineffective Drop Rules**: Drop rules removing < 5% of data volume
- **Cost Inefficiency**: Processing high-volume, low-value data streams

#### High Severity
- **Underutilized Licenses**: License capacity > 80% unused for extended periods
- **Inefficient Processing**: High CPU/memory usage per processed event
- **Budget Overruns**: Monthly costs exceeding budget by > 20%

#### Medium Severity
- **Optimization Opportunities**: Drop rules that could be strengthened
- **Usage Spikes**: Unexplained increases in license consumption
- **Capacity Planning**: Need for license upgrades within 90 days

### Implementation Approach
1. **License Data Collection**: Gather current and historical license metrics
2. **Consumption Analysis**: Build usage trends and forecasting models
3. **Drop Rule Evaluation**: Analyze pipeline effectiveness and data reduction
4. **Optimization Scoring**: Calculate efficiency metrics and savings potential

### Success Criteria
- Accurate license exhaustion predictions (within 10% accuracy)
- Identifies all ineffective drop rules and optimization opportunities
- Provides quantified cost savings estimates

---

## Implementation Guidelines

### Common Patterns for All Analyzers

#### Error Handling
```python
try:
    # API calls and analysis logic
    data = await client.get_endpoint()
    analysis_results = self._analyze_data(data)
except Exception as e:
    self.log.error(f"Error during {self.objective_name} analysis: {e}", exc_info=True)
    result.success = False
    result.error = str(e)
```

#### Finding Creation
```python
result.add_finding(
    self.create_finding(
        id=f"unique-finding-id-{identifier}",
        category="Security|Performance|Cost|Configuration",
        severity="critical|high|medium|low|info",
        title="Clear, actionable title",
        description="Detailed explanation with evidence",
        recommendation="Specific remediation steps",
        impact=ImpactEstimate(
            severity="high",
            scope="deployment",
            affected_components=["component1", "component2"]
        )
    )
)
```

#### Testing Requirements
- Unit tests for core logic (15-20 tests per analyzer)
- Integration tests with mock API responses
- Edge case coverage (empty data, invalid responses, timeouts)
- Performance testing for large datasets

### File Structure
```
src/cribl_hc/analyzers/{analyzer_name}.py
tests/unit/test_analyzers/test_{analyzer_name}.py
```

### Naming Conventions
- **Analyzer Classes**: `{Purpose}{Component}Analyzer` (e.g., `EnhancedTeamPermissionsAnalyzer`)
- **Objective Names**: `kebab-case` (e.g., `enhanced-team-permissions`)
- **Finding IDs**: `descriptive-prefix-{identifier}` (e.g., `unused-admin-permission-user123`)

### Effort Breakdown
- **Research & Design**: 1 hour (API exploration, finding definitions)
- **Core Implementation**: 2-3 hours (analysis logic, error handling)
- **Testing**: 1-2 hours (unit tests, edge cases)
- **Documentation**: 30 minutes (docstrings, comments)