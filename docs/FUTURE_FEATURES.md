# Future Features & Roadmap

This document tracks planned features, enhancements, and architectural initiatives for the Cribl Health Check project. It serves as the single source of truth for the project's future direction, following the completion of Phases 1-11.

## Executive Summary

The Cribl Health Check project has successfully established a robust foundation with **19 specialized analyzers** covering Stream, Edge, Lake, and Search products. Core operational risks such as certificate expiration, configuration drift, and RBAC security gaps have been addressed in the current production version.

Moving forward, the roadmap shifts focus from basic health assessment to **Enterprise Operations**, **Predictive Intelligence**, and **Automated Remediation**. The immediate focus (P1) is on surfacing internal system visibility and optimizing worker group performance.

---

## Quick Wins (P1)
*High-value, low-effort enhancements targeted for the next minor release.*

### 1. System Messages Surfacing
- **Description**: Integrate the `/system/messages` API endpoint to surface Cribl's internal warnings and error banners directly in the Health assessment.
- **Value Proposition**: Surfaces critical operational notices that may be buried in the UI, ensuring administrators see system-level issues immediately.
- **Estimated Effort**: LOW (~2 hours)
- **Dependencies**: None (Endpoint exists in client)
- **Acceptance Criteria**: `HealthAnalyzer` includes system messages in its findings; critical banners are flagged as HIGH severity.

### 2. Worker Group Imbalance Detection
- **Description**: Analyze traffic distribution across workers within a group to identify hotspots or idle nodes.
- **Value Proposition**: Identifies load balancing issues that can lead to localized resource exhaustion even when aggregate capacity is sufficient.
- **Estimated Effort**: MEDIUM (~4 hours)
- **Dependencies**: Metrics API (available)
- **Acceptance Criteria**: Finding generated when a single worker handles >50% more traffic than the group average.

### 3. API Key Usage Audit
- **Description**: Beyond expiration checking, cross-reference API keys with usage metrics to identify stale or unused credentials.
- **Value Proposition**: Reduces security surface area by identifying credentials that are no longer needed but remain active.
- **Estimated Effort**: MEDIUM (~3 hours)
- **Dependencies**: `/system/keys` and usage metrics
- **Acceptance Criteria**: Finding generated for keys not used in 90+ days or keys with "Admin" permissions that have never been used.

---

## Medium Priority (P2)
*Significant features that improve the utility of the tool for large-scale deployments.*

### 4. Multi-Deployment Comparison
- **Description**: A dedicated comparison engine and CLI command to perform side-by-side analysis of two or more deployments (e.g., Prod vs. Dev).
- **Value Proposition**: Essential for troubleshooting "it works in dev" issues and ensuring environment parity.
- **Estimated Effort**: HIGH (~12 hours)
- **Dependencies**: Fleet orchestration layer
- **Acceptance Criteria**: CLI command `cribl-hc analyze compare <dep1> <dep2>` generates a diff report highlighting config and health discrepancies.

### 5. Historical Data Persistence
- **Description**: Implement a lightweight storage layer (SQLite or JSON-based) to persist analysis results over time.
- **Value Proposition**: Enables trend analysis, "was it better yesterday?" comparisons, and long-term health reporting.
- **Estimated Effort**: MEDIUM (~8 hours)
- **Dependencies**: Result model refactoring
- **Acceptance Criteria**: Users can run `cribl-hc analyze history` to see health score trends over the last 30 days.

### 6. Scheduled Health Checks
- **Description**: Add a daemon mode or cron-compatible scheduling mechanism to run analyses periodically without manual intervention.
- **Value Proposition**: Moves the tool from reactive "check now" to proactive "monitor always."
- **Estimated Effort**: MEDIUM (~6 hours)
- **Dependencies**: Historical data persistence
- **Acceptance Criteria**: Configurable schedule in `config.yaml`; auto-generation of reports to a specified directory.

---

## Major Enhancements (P3+)
*Strategic initiatives requiring significant research and development.*

### 7. PII/PHI Leakage Detection
- **Description**: Sample data flows (using read-only preview APIs) to detect unmasked sensitive data like SSNs, Credit Cards, or API Keys.
- **Value Proposition**: Critical for SOC2/HIPAA compliance and preventing data leaks to downstream destinations.
- **Estimated Effort**: HIGH (Requires sampling logic and regex libraries)
- **Dependencies**: Preview API access
- **Acceptance Criteria**: Finding generated when unmasked sensitive patterns are detected in pipeline previews.

### 8. End-to-End Freshness Monitor
- **Description**: Calculate the delta between event creation time (`_time`) and output processing time to identify silent pipeline lag.
- **Value Proposition**: Identifies "slow but not broken" pipelines that are introducing business-critical delays.
- **Estimated Effort**: HIGH
- **Dependencies**: Advanced metrics or preview sampling
- **Acceptance Criteria**: Metric-based finding showing "95th percentile lag" per pipeline.

### 9. Schema Drift Detection
- **Description**: Monitor field existence and type consistency across datasets to alert when source schemas change unexpectedly.
- **Value Proposition**: Prevents downstream breakage in SIEMs or Data Lakes when upstream sources change their format.
- **Estimated Effort**: HIGH
- **Dependencies**: Historical metadata storage
- **Acceptance Criteria**: Finding generated when a "Required" field disappears from a dataset for >1 hour.

---

## Future Architecture (Phase 12+)
*Long-term vision for the project's evolution.*

### 10. Remediation Automation
- **Remediation Script Generation**: Automatically generate `curl` commands or Terraform snippets to fix identified findings (e.g., "Enable TLS").
- **Dry-Run Validation**: Safe simulation of fixes before application.

### 11. Integration Hooks (Ticketing & Alerting)
- **Auto-Ticketing**: Integration with Jira and ServiceNow to convert findings into actionable tickets.
- **Notification Routing**: Push critical findings to Slack, Teams, or PagerDuty.

### 12. Advanced Report Customization
- **White-Label Mode**: Remove all `cribl-hc` branding for MSP/Consultant use cases.
- **Multi-Language Support**: Support for localized reports (i18n).
- **Custom Templates**: Support for user-provided Jinja2/Mustache templates for report generation.

### 13. AI-Powered Intelligence
- **Natural Language Queries**: "Ask" the health check about deployment status in plain English.
- **Smart Recommendations**: ML-based suggestions derived from patterns across hundreds of deployments.

---

## Removed from Backlog (Completed)
*The following features were previously planned but have been fully implemented in Phases 1-11.*

- **Report Branding Customization**: Fully implemented with provider/client logos, themes, and custom styling.
- **Certificate Expiration Monitoring**: Integrated into `SecurityAnalyzer`.
- **RBAC & User Audit**: Comprehensive checks for inactive users, wildcard roles, and empty teams in `SecurityAnalyzer`.
- **Configuration Drift Detection**: Implemented in `FleetAnalyzer` (Leader-to-Worker and Environment-to-Environment).
- **Notification Target Validation**: Implemented in `AlertingAnalyzer`.
- **Regex Efficiency Analyzer**: Built into `PipelinePerformanceAnalyzer` and `SchemaQualityAnalyzer`.
- **Lake & Search Support**: Fully implemented as dedicated analyzer suites.

---

*For historical context, refer to the original `ROADMAP.md` and `FEATURE_RESEARCH_REPORT.md` files.*
