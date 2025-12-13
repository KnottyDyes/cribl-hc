# Cribl Cloud API Limitations

> **See Also:** [Product Compatibility Guide](./PRODUCT_COMPATIBILITY.md) for information about support for Cribl Edge, Lake, and Search.

## Summary

Cribl Cloud has a **different API surface** compared to self-hosted Cribl Stream deployments. Many endpoints that work on self-hosted installations return 404 on Cribl Cloud.

## Working Endpoints

### ✅ Configuration Endpoints
All configuration endpoints work with the `/api/v1/m/{workerGroup}/` prefix:

- `/api/v1/m/{group}/pipelines` - Pipeline configurations
- `/api/v1/m/{group}/routes` - Route configurations
- `/api/v1/m/{group}/inputs` - Input configurations
- `/api/v1/m/{group}/outputs` - Output/destination configurations

### ✅ Worker Endpoints
- `/api/v1/master/workers` - Worker node information including:
  - `worker.id` - Worker identifier
  - `worker.status` - Health status
  - `worker.info.cpus` - CPU count
  - `worker.info.totalMemory` - Total RAM (bytes)
  - `worker.info.freeMemory` - Free RAM (bytes)
  - `worker.metrics.cpu.perc` - CPU utilization (0.0-1.0)
  - `worker.metrics.cpu.loadAverage` - Load average [1m, 5m, 15m]

### ✅ Health Endpoint
- `/api/v1/health` - Basic health check
  ```json
  {
    "status": "healthy",
    "startTime": 1763554149762,
    "role": "primary"
  }
  ```

### ✅ Version Endpoint
- `/api/v1/version` - Cribl version information

## Missing Endpoints (404 on Cribl Cloud)

### ❌ Metrics Endpoints
- `/api/v1/metrics` - **NOT AVAILABLE**
- `/api/v1/m/{group}/metrics` - **NOT AVAILABLE**
- `/api/v1/master/workers/metrics` - **NOT AVAILABLE**
- `/api/v1/m/{group}/workers/metrics` - **NOT AVAILABLE**

**Impact**: Disk metrics are not available through the API. Worker CPU and memory can be obtained from the workers endpoint, but disk utilization data is not exposed.

### ❌ System Status Endpoints
- `/api/v1/system/status` - **NOT AVAILABLE**
- `/api/v1/m/{group}/system/status` - **NOT AVAILABLE**

### ❌ Stats Endpoints
- `/api/v1/stats` - **NOT AVAILABLE**
- `/api/v1/m/{group}/stats` - **NOT AVAILABLE**

### ❌ Monitoring Endpoints
- `/api/v1/monitoring/metrics` - **NOT AVAILABLE**
- `/api/v1/m/{group}/monitoring/metrics` - **NOT AVAILABLE**

## Impact on Analyzers

### HealthAnalyzer
✅ **Fully functional**
- Uses `/api/v1/master/workers` for worker health checks
- All required data available

### ConfigAnalyzer
✅ **Fully functional**
- Uses configuration endpoints (`/api/v1/m/{group}/pipelines`, etc.)
- All required data available

### ResourceAnalyzer
⚠️ **Partially functional**

**Working:**
- ✅ CPU monitoring (from `worker.metrics.cpu.perc`)
- ✅ Memory monitoring (from `worker.info.totalMemory/freeMemory`)
- ✅ Load average monitoring (from `worker.metrics.cpu.loadAverage`)
- ✅ Resource imbalance detection

**Not Working:**
- ❌ Disk monitoring (no data source available)

**Recommendation**: Document disk monitoring as unavailable for Cribl Cloud deployments. CPU and memory monitoring provide the most critical capacity planning metrics.

## Worker Group Detection

Cribl Cloud requires worker group in endpoints. The API client auto-detects the worker group by trying common names:

1. `default`
2. `defaultGroup`
3. `workers`
4. `main`

The first successful response to `/api/v1/m/{group}/pipelines` determines the active worker group.

## API Differences Summary

| Feature | Self-Hosted | Cribl Cloud |
|---------|-------------|-------------|
| Configuration APIs | `/api/v1/master/{resource}` | `/api/v1/m/{group}/{resource}` |
| Worker data | `/api/v1/master/workers` | `/api/v1/master/workers` (same) |
| Metrics endpoint | `/api/v1/metrics` ✅ | ❌ Not available |
| System status | `/api/v1/system/status` ✅ | ❌ Not available |
| Disk metrics | Available via metrics | ❌ Not exposed |
| CPU metrics | Available via workers | ✅ Available via workers |
| Memory metrics | Available via workers | ✅ Available via workers |

## Testing Notes

- Token expiration returns `401 Unauthorized`
- Invalid endpoints return `404 Not Found`
- Worker group mismatch returns `404 Not Found`
- Valid token + valid endpoint returns `200 OK`

## Recommendations

1. **For disk monitoring**: Consider alternative approaches:
   - Use Cribl's built-in monitoring/alerting for disk space
   - Monitor via infrastructure tools (CloudWatch, Datadog, etc.)
   - Request API enhancement from Cribl support

2. **For capacity planning**: CPU and memory metrics provide 80% of capacity planning value. Disk is important but less frequently the bottleneck.

3. **Documentation**: Clearly document in user-facing docs that disk monitoring requires self-hosted Cribl Stream.

## References

- Cribl Cloud API tested: December 2024
- Self-hosted Cribl Stream: v4.x API
- Worker group detection: Automatic via endpoint probing
