# Product Compatibility Guide

## Overview

cribl-hc is designed to work with the Cribl suite of products. This document outlines current support, planned support, and compatibility considerations.

## Supported Products

### ✅ Cribl Stream (Self-Hosted)

**Status:** Fully Supported

**Features:**
- ✅ Worker health monitoring
- ✅ Configuration validation (pipelines, routes, inputs, outputs)
- ✅ Resource utilization (CPU, memory, disk)
- ✅ Performance optimization recommendations
- ✅ Security and compliance validation
- ✅ Cost and license tracking

**API Endpoints Used:**
- `/api/v1/master/workers` - Worker status and metrics
- `/api/v1/m/{group}/pipelines` - Pipeline configurations
- `/api/v1/m/{group}/routes` - Route configurations
- `/api/v1/m/{group}/inputs` - Input configurations
- `/api/v1/m/{group}/outputs` - Output configurations
- `/api/v1/health` - System health
- `/api/v1/version` - Version information

**Requirements:**
- Cribl Stream 4.x (4.5 and above; validated against 4.20)
- API bearer token with read permissions
- Network access to Cribl API endpoints

---

### ✅ Cribl Stream (Cribl Cloud)

**Status:** Fully Supported*

**Features:**
- ✅ Worker health monitoring
- ✅ Configuration validation (pipelines, routes, inputs, outputs)
- ✅ Resource utilization (CPU, memory)
- ⚠️ Disk metrics (not available - API limitation)
- ✅ Performance optimization recommendations
- ✅ Security and compliance validation
- ✅ Cost and license tracking

**API Endpoints Used:**
- `/api/v1/master/workers` - Worker status and CPU/memory metrics
- `/api/v1/m/{group}/pipelines` - Pipeline configurations
- `/api/v1/m/{group}/routes` - Route configurations
- `/api/v1/m/{group}/inputs` - Input configurations
- `/api/v1/m/{group}/outputs` - Output configurations
- `/api/v1/health` - System health
- `/api/v1/version` - Version information

**API Endpoints NOT Available:**
- ❌ `/api/v1/metrics` - Metrics endpoint (404)
- ❌ `/api/v1/system/status` - System status (404)
- ❌ Disk utilization metrics (not exposed)

**Workarounds:**
- CPU and memory metrics available via `/api/v1/master/workers`
- Load average available via worker metrics
- Disk monitoring should be done via Cribl's built-in monitoring or infrastructure tools

**URL Format:**
```
https://<workspace>-<org-name>.cribl.cloud
```

Where:
- `<workspace>` = workspace identifier (e.g., "main", "dev", "prod", "staging")
- `<org-name>` = your organization name

**Requirements:**
- Cribl Cloud account
- Workspace-specific bearer token
- HTTPS connectivity to `*.cribl.cloud`

**See Also:** [cribl_cloud_api_notes.md](./cribl_cloud_api_notes.md)

---

## Planned Products

### ✅ Cribl Edge (Phase 5)

**Status:** Phase 5A Complete ✅ (Foundation) | Phase 5B Complete ✅ (Health Analyzer)

**Completed (Phase 5A - Foundation):**
- ✅ Product type detection (Stream vs Edge vs Lake)
- ✅ Automatic product detection via `/api/v1/version`
- ✅ Endpoint probing fallback detection
- ✅ Edge API endpoint mapping documented
- ✅ Unit tests for product detection (16/16 passing)
- ✅ No breaking changes to existing Stream functionality

**Completed (Phase 5B - Health Analyzer):**
- ✅ Edge Node health monitoring (via HealthAnalyzer)
- ✅ Edge Fleet support (nodes grouped by fleet)
- ✅ Unified `get_nodes()` API (works for both Stream and Edge)
- ✅ Edge data normalization layer (Edge → Stream format)
- ✅ Product-aware findings ("Edge Node" vs "Worker")
- ✅ Edge-specific API methods (`get_edge_nodes`, `get_edge_fleets`)
- ✅ Unit tests for Edge analyzer (5/5 passing)
- ✅ Unit tests for Edge API client (8/8 passing)
- ✅ Zero breaking changes to Stream functionality

**Target Features (Phase 5C - Future):**
- Edge-specific configuration validation (ConfigAnalyzer adaptation)
- Edge route and pipeline analysis
- Data source connectivity health
- Edge-specific resource analyzer

**Key Differences from Stream:**
- Uses **Edge Fleets** instead of Worker Groups
- Different API endpoint structure
- Edge Nodes vs Workers
- Fleet-based management

**Planned Implementation:**
- Automatic product detection (Edge vs Stream)
- Edge-specific analyzers
- Fleet-level health scoring
- Node-level capacity planning
- Edge configuration best practices

**Estimated Availability:** Phase 5 (TBD)

**Research Notes:**
- API endpoint mapping: Stream endpoints → Edge equivalents
- Fleet-based aggregation logic
- Edge Node metrics collection
- Edge-specific security considerations

---

### 🔮 Cribl Lake (Phase 6)

**Status:** Planned

**Target Features:**
- Storage bucket utilization monitoring
- Data retention and lifecycle analysis
- Query performance metrics
- Cost optimization for storage
- Lake-specific health indicators
- Dataset health and availability

**Key Differences from Stream:**
- Storage-focused (not worker-focused)
- No traditional "workers" or "pipelines"
- Focus on data retention, queries, storage efficiency
- Different API structure

**Planned Implementation:**
- Storage capacity planning
- Data lifecycle recommendations
- Query performance optimization
- Cost analysis for storage tiers
- Dataset health validation

**Estimated Availability:** Phase 6 (TBD)

**Use Cases:**
- Storage capacity planning
- Cost optimization
- Query performance tuning
- Data retention compliance
- Dataset availability monitoring

---

### 🤔 Cribl Search

**Status:** Evaluating Applicability

**Considerations:**
- Cribl Search is a query/analysis tool (not data routing)
- Health checking may not be applicable
- Different use case from Stream/Edge/Lake

**Potential Features (if applicable):**
- Query performance monitoring
- Resource utilization for search workloads
- Search dataset availability

**Decision:** To be determined based on user feedback and use cases

---

## Multi-Product Fleet Analytics (Phase 7)

**Status:** Future Planning

**Vision:**
- Unified health dashboard across all Cribl products
- Cross-product data flow visualization
- Holistic capacity planning (Stream + Edge + Lake)
- Fleet-wide configuration compliance
- End-to-end data pipeline health

**Example Scenarios:**
1. Monitor data flow from Edge → Stream → Lake
2. Unified resource planning across all products
3. Cross-product security and compliance validation
4. Cost optimization across entire Cribl stack

---

## Product Detection

cribl-hc automatically detects the deployment type:

```python
# Cloud detection (based on URL pattern)
if ".cribl.cloud" in url:
    deployment_type = "cloud"
    is_cloud = True
else:
    deployment_type = "self-hosted"
    is_cloud = False
```

**Future:** Automatic product detection (Stream vs Edge vs Lake) based on available API endpoints and version information.

---

## Compatibility Matrix

| Feature | Stream (Self-Hosted) | Stream (Cloud) | Edge (Planned) | Lake (Planned) |
|---------|---------------------|----------------|----------------|----------------|
| Worker Health | ✅ | ✅ | 🔮 (Edge Nodes) | ❌ N/A |
| Config Validation | ✅ | ✅ | 🔮 | 🔮 (Datasets) |
| CPU Metrics | ✅ | ✅ | 🔮 | 🔮 |
| Memory Metrics | ✅ | ✅ | 🔮 | 🔮 |
| Disk Metrics | ✅ | ❌ API limit | 🔮 | 🔮 (Storage) |
| Pipeline Analysis | ✅ | ✅ | 🔮 | ❌ N/A |
| Route Analysis | ✅ | ✅ | 🔮 | ❌ N/A |
| Security Validation | ✅ | ✅ | 🔮 | 🔮 |
| Cost Management | ✅ | ✅ | 🔮 | 🔮 |

**Legend:**
- ✅ Fully Supported
- ⚠️ Partial Support
- ❌ Not Available
- 🔮 Planned
- N/A - Not Applicable

---

## Migration Path

If you're currently using cribl-hc with Cribl Stream and planning to adopt other Cribl products:

1. **Current (Phase 1-4):** Continue using cribl-hc for Stream deployments
2. **Phase 5:** Upgrade to version with Edge support
3. **Phase 6:** Upgrade to version with Lake support
4. **Phase 7:** Enable multi-product fleet analytics

All upgrades will maintain backward compatibility with existing Stream deployments.

---

## Feedback and Requests

If you're using Cribl Edge, Lake, or Search and would like to see support added:

1. Open a feature request: [GitHub Issues](https://github.com/KnottyDyes/cribl-hc/issues)
2. Share your use case and desired features
3. Help us prioritize multi-product support

---

## References

- [Cribl Stream Documentation](https://docs.cribl.io/stream/)
- [Cribl Edge Documentation](https://docs.cribl.io/edge/)
- [Cribl Lake Documentation](https://docs.cribl.io/lake/)
- [Cribl Search Documentation](https://docs.cribl.io/search/)
- [Cribl Cloud API Notes](./cribl_cloud_api_notes.md)
- [API Documentation](./API.md)

---

**Last Updated:** December 2024
**Version:** 1.0.0
