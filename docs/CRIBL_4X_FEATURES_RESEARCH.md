# Cribl 4.x Feature Research (Follow-up)

## Scope
This file captures the librarian research context for Cribl 4.x feature opportunities and the local codebase checkpoints used to implement them.

## Features to Leverage
1. **Cribl Insights**
2. **Virtual Tables** (KQL: `$vt_jobs`, `$vt_datasets`)
3. **Cribl Guard (v4.14+)**
4. **Internal Cribl Source metrics**

## Local Codebase Findings

### Available API Client Methods
- `get_system_messages()` → `/api/v1/system/messages`
- `get_banners()` → `/api/v1/system/banners`
- `get_metrics()` → `/api/v1/m/default/system/metrics` (used by multiple analyzers)
- `get_auth_config()` → `/api/v1/system/auth`
- `get_certificates()` → `/api/v1/system/certificates`

### Newly Added (for Guard support)
- `get_security_settings()` → `/api/v1/system/security`

## Implementation Direction

### Cribl Insights
- **Signal source**: System messages
- **Proposed detection**: Filter system messages by `channel`, `title`, or `message` containing `insight`
- **Analyzer**: `HealthAnalyzer`

### Internal Cribl Metrics
- **Signal source**: Metrics API
- **Proposed detection**: Presence and count of metrics items
- **Analyzer**: `HealthAnalyzer`

### Cribl Guard Masking Policies
- **Signal source**: `/api/v1/system/security`
- **Proposed detection**: Look for masking policy collections in `security_settings`
- **Analyzer**: `SecurityAnalyzer`

### Virtual Tables (KQL)
- **Status**: Not implemented
- **Blocked by**: Need confirmed KQL query endpoint and response schema
- **Next step**: Identify API endpoints for KQL execution in Cribl 4.x

## Documentation Links (Unavailable)
Attempts to fetch public docs returned 404:
- `https://docs.cribl.com/docs/virtual-tables/`
- `https://docs.cribl.com/docs/health-check/`

## Open Questions
1. Exact schema of `/api/v1/system/security` for Guard masking policies
2. Official API for KQL query execution (Virtual Tables)
3. Structure of Insights alerts in system messages

## Recommended Next Steps
1. Validate `/api/v1/system/security` response schema on a live 4.x deployment
2. Identify KQL execution endpoint and test `$vt_jobs`, `$vt_datasets` queries
3. Confirm Insights message structure (channel/title) in production
