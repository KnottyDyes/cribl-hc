# Cribl Health Check - API Reference

## Overview

Cribl Health Check provides both a Python library API and a REST API for programmatic access.

## Python Library API

### Quick Start

```python
from cribl_hc import analyze_deployment, Deployment, AnalysisRun

# Create deployment configuration
deployment = Deployment(
    id="prod",
    name="Production",
    url="https://cribl.example.com",
    environment_type="self-hosted",
    auth_token="your-api-token"
)

# Run analysis
result: AnalysisRun = await analyze_deployment(
    deployment,
    objectives=["health", "config", "security"]
)

# Access results
print(f"Health Score: {result.health_score.overall_score}")
for finding in result.findings:
    print(f"[{finding.severity}] {finding.title}")
```

### Core Classes

#### CriblAPIClient

The main interface for communicating with Cribl APIs.

```python
from cribl_hc.core.api_client import CriblAPIClient

async with CriblAPIClient(
    base_url="https://cribl.example.com",
    auth_token="your-token",
    # Optional OAuth
    client_id="client-id",
    client_secret="client-secret"
) as client:
    # Check connection
    result = await client.test_connection()
    print(f"Connected: {result.success}")
    print(f"Version: {result.cribl_version}")
    print(f"Product: {result.product_type}")
```

**Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `test_connection()` | Test API connectivity | `ConnectionTestResult` |
| `get_workers()` | Get worker/node list | `List[Dict]` |
| `get_pipelines()` | Get pipeline configs | `List[Dict]` |
| `get_routes()` | Get route configs | `List[Dict]` |
| `get_inputs()` | Get input configs | `List[Dict]` |
| `get_outputs()` | Get output configs | `List[Dict]` |
| `get_lookups()` | Get lookup tables | `List[Dict]` |
| `get_parsers()` | Get parser library | `List[Dict]` |
| `get_groups()` | Get worker groups | `List[Dict]` |
| `get_system_info()` | Get system info | `Dict` |

**Lake-specific Methods:**

| Method | Description |
|--------|-------------|
| `get_lake_datasets(lake_id)` | Get Lake datasets |
| `get_lakehouses()` | Get Lakehouses |
| `get_dataset_stats(lake_id, dataset_id)` | Get dataset statistics |

**Search-specific Methods:**

| Method | Description |
|--------|-------------|
| `get_search_jobs(workspace)` | Get Search jobs |
| `get_search_datasets(workspace)` | Get Search datasets |
| `get_search_dashboards(workspace)` | Get dashboards |
| `get_search_saved_searches(workspace)` | Get saved searches |

#### Analyzers

All analyzers follow the same interface:

```python
from cribl_hc.analyzers import get_analyzer

analyzer = get_analyzer("health")  # or "config", "security", etc.
result = await analyzer.analyze(client)

print(f"Success: {result.success}")
print(f"Findings: {len(result.findings)}")
print(f"Metadata: {result.metadata}")
```

**Available Analyzers:**

| Objective | Analyzer Class | Description |
|-----------|----------------|-------------|
| `health` | HealthAnalyzer | Worker health, overall score |
| `config` | ConfigAnalyzer | Pipeline/route validation |
| `resource` | ResourceAnalyzer | Capacity analysis |
| `storage` | StorageAnalyzer | Storage optimization |
| `security` | SecurityAnalyzer | Security posture |
| `cost` | CostAnalyzer | License tracking |
| `fleet` | FleetAnalyzer | Multi-deployment |
| `predictive` | PredictiveAnalyzer | Forecasting |
| `backpressure` | BackpressureAnalyzer | Queue health |
| `pipeline_performance` | PipelinePerformanceAnalyzer | Function analysis |
| `lookup_health` | LookupHealthAnalyzer | Lookup tables |
| `schema_quality` | SchemaQualityAnalyzer | Parser analysis |
| `dataflow_topology` | DataFlowTopologyAnalyzer | Route topology |
| `lake_health` | LakeHealthAnalyzer | Lake datasets |
| `lake_storage` | LakeStorageAnalyzer | Lake storage |
| `search_health` | SearchHealthAnalyzer | Search jobs |
| `search_performance` | SearchPerformanceAnalyzer | Query performance |

### Data Models

#### Finding

```python
from cribl_hc.models.finding import Finding

finding = Finding(
    id="worker-cpu-high",
    title="High CPU Usage",
    description="Worker has CPU usage above 90%",
    severity="critical",  # critical, high, medium, low, info
    category="health",
    affected_components=["worker:worker-01"],
    remediation_steps=[
        "Check for resource-intensive pipelines",
        "Consider horizontal scaling"
    ],
    documentation_links=["https://docs.cribl.io/..."],
    confidence_level="high",  # high, medium, low
    estimated_impact="May cause event drops",
    product_tags=["stream", "edge"],
    metadata={"cpu_percent": 95.2}
)
```

#### AnalyzerResult

```python
from cribl_hc.analyzers.base import AnalyzerResult

result = AnalyzerResult(objective="health")
result.success = True
result.add_finding(finding)
result.metadata["workers_analyzed"] = 5
```

#### HealthScore

```python
from cribl_hc.models.health import HealthScore

score = HealthScore(
    overall_score=85.0,
    component_scores={
        "workers": 90.0,
        "pipelines": 80.0,
        "connectivity": 85.0
    },
    critical_issues=1,
    warnings=3
)
```

---

## REST API

The REST API is provided via FastAPI and runs on port 8080 by default.

### Starting the API Server

```bash
# Start with default settings
python run_api.py

# Or with Docker
docker-compose up -d

# Access Swagger docs
open http://localhost:8080/api/docs
```

### Authentication

Currently, the REST API does not require authentication. Credentials for Cribl deployments are managed via the credentials endpoints.

### Endpoints

#### System

**GET /api/v1/system/health**

Health check endpoint.

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### Analyzers

**GET /api/v1/analyzers**

List all available analyzers.

```json
{
  "analyzers": [
    {
      "name": "health",
      "description": "Overall health assessment...",
      "api_calls": 3,
      "permissions": ["read:workers", "read:system"],
      "categories": ["health"]
    }
  ],
  "total_count": 17,
  "total_api_calls": 41
}
```

**GET /api/v1/analyzers/{name}**

Get details about a specific analyzer.

```json
{
  "name": "health",
  "description": "Overall health assessment...",
  "api_calls": 3,
  "permissions": ["read:workers", "read:system", "read:metrics"],
  "categories": ["health"]
}
```

#### Credentials

**POST /api/v1/credentials**

Store deployment credentials.

Request:
```json
{
  "id": "prod",
  "name": "Production",
  "url": "https://cribl.example.com",
  "auth_token": "your-token"
}
```

**GET /api/v1/credentials**

List stored credentials (tokens redacted).

**GET /api/v1/credentials/{id}**

Get specific credential details.

**DELETE /api/v1/credentials/{id}**

Remove stored credentials.

**POST /api/v1/credentials/{id}/test**

Test credential connectivity.

```json
{
  "success": true,
  "cribl_version": "4.5.0",
  "product_type": "stream",
  "message": "Connection successful"
}
```

#### Analysis

**POST /api/v1/analysis/run**

Run analysis on a deployment.

Request:
```json
{
  "deployment_id": "prod",
  "objectives": ["health", "config", "security"]
}
```

Response:
```json
{
  "run_id": "uuid",
  "status": "completed",
  "health_score": {
    "overall_score": 85.0,
    "component_scores": {...}
  },
  "findings": [...],
  "recommendations": [...],
  "metadata": {...}
}
```

**GET /api/v1/analysis/{run_id}**

Get analysis results by run ID.

**GET /api/v1/analysis/{run_id}/report**

Get formatted report.

Query params:
- `format`: `json` | `markdown` (default: `json`)

### WebSocket API

**WS /api/v1/analysis/ws/{deployment_id}**

Real-time analysis progress updates.

```javascript
const ws = new WebSocket('ws://localhost:8080/api/v1/analysis/ws/prod');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}%`);
  console.log(`Current: ${data.current_analyzer}`);
};
```

---

## Error Handling

### Python Library

```python
from cribl_hc.core.api_client import CriblAPIClient
import httpx

try:
    async with CriblAPIClient(...) as client:
        result = await client.test_connection()
except httpx.ConnectError:
    print("Connection failed")
except httpx.HTTPStatusError as e:
    print(f"API error: {e.response.status_code}")
```

### REST API

All errors return JSON with consistent format:

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

Common status codes:
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Internal server error

---

## Rate Limiting

The library implements automatic rate limiting:

- Default: 10 requests/second
- Exponential backoff on 429 responses
- Configurable via `RateLimiter` class

```python
from cribl_hc.utils.rate_limiter import RateLimiter

limiter = RateLimiter(
    max_requests_per_second=5,
    max_retries=3
)
```

---

## Examples

### Run Full Analysis

```python
import asyncio
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.orchestrator import AnalysisOrchestrator

async def main():
    async with CriblAPIClient(
        base_url="https://cribl.example.com",
        auth_token="token"
    ) as client:
        orchestrator = AnalysisOrchestrator(client)
        result = await orchestrator.run_analysis(
            objectives=["health", "config", "security"]
        )

        print(f"Score: {result.health_score.overall_score}")
        for f in result.findings:
            print(f"[{f.severity}] {f.title}")

asyncio.run(main())
```

### Generate Report

```python
from cribl_hc.core.report_generator import generate_report

# After running analysis...
json_report = generate_report(result, format="json")
md_report = generate_report(result, format="markdown")

# Save to files
with open("report.json", "w") as f:
    f.write(json_report)
with open("report.md", "w") as f:
    f.write(md_report)
```

### Filter Results by Product

```python
# Filter findings for Stream only
stream_findings = result.filter_by_product("stream")

# Sort by severity
sorted_findings = result.sort_findings_by_severity()
```
