# Cribl Edge API Endpoint Mapping

## Overview

This document maps Cribl Stream API endpoints to their Cribl Edge equivalents for Phase 5 implementation.

**Status:** Research Phase - Endpoint mapping based on documentation and inference

**Last Updated:** December 2024

---

## Base URL Structure

### Cribl Stream
```
Self-hosted: https://cribl.example.com/api/v1/master/{resource}
Cloud:       https://<workspace>-<org>.cribl.cloud/api/v1/m/{group}/{resource}
```

### Cribl Edge (Expected)
```
Self-hosted: https://edge.example.com/api/v1/edge/{resource}
Cloud:       https://<workspace>-<org>.cribl.cloud/api/v1/e/{fleet}/{resource}
```

**Context Indicators:**
- `/m/{group}` = Worker Group context (Stream)
- `/e/{fleet}` = Edge Fleet context (Edge)
- `/w/{nodeId}` = Specific Worker/Node context

---

## Endpoint Mapping

### 1. Health & Version

| Purpose | Stream Endpoint | Edge Endpoint (Expected) | Notes |
|---------|----------------|--------------------------|-------|
| Version info | `/api/v1/version` | `/api/v1/version` | ✅ Same |
| Health check | `/api/v1/health` | `/api/v1/health` | ✅ Same |
| System status | `/api/v1/system/status` | `/api/v1/system/status` | ⚠️ May differ |

**Status:** Version and health endpoints should be universal

---

### 2. Worker/Node Listing

| Purpose | Stream Endpoint | Edge Endpoint (Expected) | Notes |
|---------|----------------|--------------------------|-------|
| List workers | `/api/v1/master/workers` | `/api/v1/edge/nodes` | 🔮 Different resource name |
| Worker details | `/api/v1/master/workers/{id}` | `/api/v1/edge/nodes/{id}` | 🔮 Different resource name |
| Worker metrics | `worker.metrics` (in response) | `node.metrics` (expected) | ⚠️ Structure may differ |

**Key Differences:**
- Stream: "workers" = processing nodes in a Worker Group
- Edge: "nodes" = Edge nodes in an Edge Fleet
- Terminology change: Worker → Node

**Expected Node Response Structure:**
```json
{
  "items": [
    {
      "id": "edge-node-001",
      "guid": "...",
      "status": "connected",  // vs Stream's "healthy"
      "info": {
        "hostname": "edge-collector-01",
        "os": "Linux",
        "arch": "x64",
        "cpus": 4,
        "totalMemory": 16777216000,
        "freeMemory": 8388608000
      },
      "metrics": {
        "cpu": {
          "perc": 0.45,
          "loadAverage": [1.2, 1.5, 1.3]
        },
        "memory": {
          "used": 8388608000,
          "free": 8388608000
        }
      },
      "fleet": "production-edge",  // vs Stream's "group"
      "lastSeen": "2024-12-13T12:00:00Z"
    }
  ]
}
```

---

### 3. Fleet/Group Management

| Purpose | Stream Endpoint | Edge Endpoint (Expected) | Notes |
|---------|----------------|--------------------------|-------|
| List groups | `/api/v1/master/groups` | `/api/v1/edge/fleets` | 🔮 Different resource |
| Group config | `/api/v1/m/{group}/...` | `/api/v1/e/{fleet}/...` | 🔮 Different prefix |
| Fleet hierarchy | N/A | `/api/v1/edge/fleets/{id}/subfleets` | ✨ New in Edge |

**Edge-Specific Concepts:**
- **Fleets**: Top-level grouping (max 50 per Cloud org)
- **Subfleets**: Nested grouping under Fleets
- Fleet hierarchy: `Fleet → Subfleet → Nodes`

Stream has simpler flat groups: `Worker Group → Workers`

---

### 4. Configuration Endpoints

| Purpose | Stream Endpoint | Edge Endpoint (Expected) | Notes |
|---------|----------------|--------------------------|-------|
| Pipelines | `/api/v1/m/{group}/pipelines` | `/api/v1/e/{fleet}/pipelines` | 🔮 Similar structure |
| Routes | `/api/v1/m/{group}/routes` | `/api/v1/e/{fleet}/routes` | 🔮 Similar structure |
| Inputs | `/api/v1/m/{group}/inputs` | `/api/v1/e/{fleet}/sources` | ⚠️ "sources" not "inputs" |
| Outputs | `/api/v1/m/{group}/outputs` | `/api/v1/e/{fleet}/destinations` | 🔮 Similar |

**Key Differences:**
- Edge uses "sources" instead of "inputs" (terminology)
- Edge configurations are Fleet-level (distributed to all nodes in fleet)
- Stream configurations are Worker Group-level

---

### 5. Metrics & Monitoring

| Purpose | Stream Endpoint | Edge Endpoint | Notes |
|---------|----------------|---------------|-------|
| Metrics (general) | `/api/v1/metrics` | ❌ Not available in Cloud | Stream limitation applies |
| Worker metrics | `/api/v1/master/workers` | `/api/v1/edge/nodes` | Embedded in list response |
| System metrics | `/api/v1/system/status` | ❌ Not available in Cloud | Same limitation |

**Edge-Specific Metrics:**
- Connection status to sources
- Data ingest rates per source
- Fleet-wide aggregated metrics
- Node-to-Leader connectivity

---

## Product Detection Strategy

### 1. Explicit Detection (Preferred)
Check `/api/v1/version` response for product field:
```json
{
  "version": "4.8.0",
  "product": "edge"  // or "stream" or "lake"
}
```

### 2. Endpoint Probing (Fallback)
Try product-specific endpoints:

**Edge Detection:**
```
GET /api/v1/edge/fleets
→ 200/401/403 = Edge
→ 404 = Not Edge
```

**Lake Detection:**
```
GET /api/v1/datasets
→ 200/401/403 = Lake
→ 404 = Not Lake
```

**Default:** If neither Edge nor Lake, assume Stream

---

## Implementation Checklist

### Phase 5A: Foundation ✅
- [x] Add `product_type` detection to API client
- [x] Add `is_edge`, `is_stream`, `is_lake` properties
- [x] Implement `_detect_product_type()` method
- [x] Update `test_connection()` to detect product
- [ ] Document Edge endpoint mapping (this file)

### Phase 5B: Edge Support (Next)
- [ ] Add `get_edge_nodes()` method (maps to Stream's `get_workers()`)
- [ ] Add `get_edge_fleets()` method
- [ ] Add Edge-specific config endpoints
- [ ] Create Edge data models (EdgeNode, EdgeFleet)
- [ ] Adapter layer for unified analyzer interface

### Phase 5C: Edge Analyzers
- [ ] EdgeHealthAnalyzer (adapt HealthAnalyzer)
- [ ] EdgeConfigAnalyzer (adapt ConfigAnalyzer)
- [ ] EdgeResourceAnalyzer (adapt ResourceAnalyzer)

---

## API Client Updates Needed

### 1. Add Edge Node Methods

```python
async def get_edge_nodes(self, fleet: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get list of Edge Nodes.

    Args:
        fleet: Optional fleet name to filter nodes

    Returns:
        List of Edge Node dictionaries

    Note:
        Maps to Stream's get_workers() but uses /api/v1/edge/nodes
    """
    if fleet:
        endpoint = f"/api/v1/e/{fleet}/nodes"
    else:
        endpoint = "/api/v1/edge/nodes"

    async with self.rate_limiter:
        response = await self._request("GET", endpoint)

    return response.get("items", [])
```

### 2. Add Edge Fleet Methods

```python
async def get_edge_fleets(self) -> List[Dict[str, Any]]:
    """Get list of Edge Fleets."""
    endpoint = "/api/v1/edge/fleets"

    async with self.rate_limiter:
        response = await self._request("GET", endpoint)

    return response.get("items", [])
```

### 3. Update Config Endpoint Builder

```python
def _build_config_endpoint(self, resource: str) -> str:
    """
    Build config endpoint for current product type.

    Returns:
        Stream: /api/v1/m/{group}/{resource}
        Edge:   /api/v1/e/{fleet}/{resource}
        Lake:   /api/v1/datasets (different structure)
    """
    if self.is_edge:
        fleet = self._edge_fleet or "default"
        return f"/api/v1/e/{fleet}/{resource}"
    elif self.is_stream:
        if self._is_cloud:
            group = self._worker_group or "default"
            return f"/api/v1/m/{group}/{resource}"
        else:
            return f"/api/v1/master/{resource}"
    elif self.is_lake:
        # Lake has different structure - no traditional configs
        return f"/api/v1/{resource}"
    else:
        # Default to Stream
        return f"/api/v1/master/{resource}"
```

---

## Data Model Mapping

### Stream Worker → Edge Node

```python
# Stream Worker
{
  "id": "worker-001",
  "status": "healthy",  # "healthy", "unhealthy", "unreachable"
  "group": "production",
  "info": {...},
  "metrics": {...}
}

# Edge Node (expected)
{
  "id": "node-001",
  "status": "connected",  # "connected", "disconnected", "unreachable"
  "fleet": "production-edge",
  "info": {...},
  "metrics": {...},
  "lastSeen": "2024-12-13T12:00:00Z"
}
```

### Key Terminology Changes
| Stream | Edge |
|--------|------|
| Worker | Node |
| Worker Group | Fleet |
| healthy/unhealthy | connected/disconnected |
| group | fleet |
| Input | Source |

---

## Testing Strategy

### 1. Mock Edge Responses
Create test fixtures with expected Edge API responses

### 2. Product Detection Tests
- Test explicit product field detection
- Test endpoint probing fallback
- Test default to Stream behavior

### 3. Integration Tests
- Test against real Edge deployment (if available)
- Test Fleet hierarchy handling
- Test Node listing and metrics

---

## References

- [Cribl API Reference](https://docs.cribl.io/api-reference/)
- [Fleet Management](https://docs.cribl.io/edge/fleet-management/)
- [Cribl Edge Documentation](https://docs.cribl.io/edge/)

---

## Open Questions

1. **Edge Node Metrics Structure**: Does Edge expose disk metrics? Same structure as Stream?
2. **Fleet Hierarchy API**: How to query subfleets? Recursive or flat?
3. **Edge Configuration Validation**: Do Edge pipelines support all Stream functions?
4. **Authentication**: Any differences in auth tokens between Stream and Edge?
5. **Rate Limiting**: Does Edge have different API rate limits?

**Action:** Need access to real Edge deployment or complete API documentation to answer these questions.

---

**Status:** This mapping is based on inference from documentation. Phase 5B will validate and refine based on actual Edge API testing.
