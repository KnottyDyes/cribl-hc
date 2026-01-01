# Cribl Lake & Search API Research

**Date**: 2025-12-28
**Purpose**: Document Lake and Search API structures for Phase 7 & 8 implementation
**Status**: Initial Research Complete - Sandbox Testing Required

---

## Research Summary

### Documentation Sources

Based on research of official Cribl documentation:

1. **[Cribl API Reference](https://docs.cribl.io/api-reference/)** - Main API documentation
2. **[Cribl Lake Documentation](https://docs.cribl.io/lake/)** - Lake product documentation
3. **[Cribl Search Documentation](https://docs.cribl.io/search/)** - Search product documentation
4. **[Lake Datasets](https://docs.cribl.io/lake/datasets/)** - Dataset management
5. **[Managing Lake Datasets](https://docs.cribl.io/lake/managing-datasets/)** - Dataset operations
6. **[Cribl Search API](https://docs.cribl.io/search/set-up-apis/)** - Search API configuration
7. **[Search and Retrieve Results](https://docs.cribl.io/cribl-as-code/search-results/)** - Query execution

### Key Findings

**API Structure**:
- All Cribl products (Stream, Edge, Lake, Search) use unified API infrastructure
- Base URL for Cribl.Cloud: `https://${workspaceName}-${organizationId}.cribl.cloud/api/v1`
- Base URL for on-prem: `https://${hostname}:${port}/api/v1`
- In-product API Reference available at: Settings > Global > API Reference

**Authentication**:
- API Token Clients/Secrets available at Org/Workspace/Product levels
- Same authentication mechanism as Stream/Edge

---

## Cribl Lake - Documented Features

### Core Components

#### 1. Datasets
- **Description**: Primary data organization unit in Cribl Lake
- **Capacity**: Up to 200 Lake Datasets per Workspace
- **Storage Format**: gzip-compressed JSON or Parquet format
- **Built-in Datasets**:
  - `cribl_logs` - Audit and access logs
  - `cribl_metrics` - Cloud Leader Node metrics
- **Custom Datasets**: User-created with configurable retention

#### 2. Retention Policies
- **Built-in Datasets**: Fixed 10-30 days (varies by dataset)
- **Custom Datasets**: Configurable from 1 day to 10 years
- **Per-Dataset Control**: Independent retention for each dataset

#### 3. Storage Locations (New in 2025)
- **BYOS**: Bring Your Own Storage support
- **Amazon S3**: Create datasets on customer-managed S3 buckets
- **Compliance**: Direct data ownership for regulatory requirements
- **Integration**: Cribl-managed access control and analytics

#### 4. Lakehouses
- **Purpose**: Optimized search performance
- **Benefit**: Faster query execution for mirrored datasets
- **Limitation**: Results limited to past 30 days
- **Format**: Lakehouse execution for efficiency

### Monitoring & Cost Management

#### FinOps Center
- **Location**: Cribl.Cloud portal
- **Metrics**: Data usage monitoring
- **Cost Tracking**: Storage usage and costs
- **Credit Allocation**: Flexible Cribl.Cloud credit allocation

---

## Cribl Search - Documented Features

### Core Components

#### 1. Data Connectivity
- **Cribl Lake/Lakehouse**: Primary integration
- **Cloud Storage**: S3, Azure Blob, Google Cloud Storage
- **Databases**: ClickHouse, Elasticsearch, Snowflake
- **APIs**: AWS, Azure, Google Workspace, Okta, Microsoft Graph

#### 2. Query Language
- **Language**: Kusto Query Language (KQL)
- **Operators**: Aggregation, filtering, data manipulation, display
- **Functions**: Math, string, datetime, statistical, window-based
- **Virtual Tables**:
  - `$vt_datasets` - Dataset inventory
  - `$vt_dataset_providers` - Provider information
  - `$vt_jobs` - Active search jobs

#### 3. Search Jobs
- **Endpoint**: `POST /search/jobs`
- **Required**: Always begin query with `cribl` operator
- **Monitoring**: Track via `$vt_jobs` virtual table
- **Metrics**: searchCount, lastSearch, users, averageSearchTimeSec

#### 4. Scheduled Searches
- **Purpose**: Recurring queries
- **Triggers**: Notification-based
- **Automation**: Regular monitoring and alerting

#### 5. Performance Optimization
- **Lakehouse Search**: Automatic when available
- **Query Ordering**: Affects results and performance
- **API Throttling**: Avoid for consistent performance
- **Path Optimization**: Reduce costs and improve speed

### API Constraints
- **Request Size Limit**: 5 MB maximum
- **Performance**: 4.13.0 & 4.14.0 include significant improvements
- **Lakehouse Execution**: Faster results, 30-day limitation

---

## What We Need from Sandbox Testing

### Cribl Lake API Endpoints (Unknown)

Need to discover via sandbox:

1. **Dataset Management**
   - `GET /datasets` - List all datasets
   - `GET /datasets/{id}` - Get dataset details
   - `POST /datasets` - Create dataset
   - `PUT /datasets/{id}` - Update dataset
   - `DELETE /datasets/{id}` - Delete dataset

2. **Health & Metrics**
   - `GET /health` or `/system/status` - Lake health status
   - `GET /metrics` - Lake performance metrics
   - `GET /datasets/{id}/metrics` - Per-dataset metrics
   - `GET /datasets/{id}/stats` - Dataset statistics

3. **Storage Management**
   - `GET /storage/locations` - List storage locations
   - `GET /storage/usage` - Storage consumption
   - `GET /datasets/{id}/retention` - Retention policy
   - `PUT /datasets/{id}/retention` - Update retention

4. **Lakehouse Operations**
   - `GET /lakehouses` - List lakehouses
   - `GET /lakehouses/{id}` - Lakehouse details
   - `POST /lakehouses` - Create lakehouse
   - `GET /lakehouses/{id}/status` - Lakehouse health

### Cribl Search API Endpoints (Partially Known)

Need to verify/discover:

1. **Search Jobs** (Known)
   - `POST /search/jobs` - Execute search query
   - `GET /search/jobs` - List search jobs
   - `GET /search/jobs/{id}` - Get job status
   - `DELETE /search/jobs/{id}` - Cancel job

2. **Datasets** (Need to verify)
   - `GET /search/datasets` - List searchable datasets
   - `GET /search/datasets/{id}/schema` - Dataset schema
   - Query `$vt_datasets` - Virtual table for datasets

3. **Performance** (Need to discover)
   - `GET /search/metrics` - Search performance metrics
   - Query `$vt_jobs` - Active job metrics
   - `GET /search/stats` - Search statistics

4. **Workspaces** (Need to discover)
   - `GET /workspaces` - List workspaces
   - `GET /workspaces/{id}/usage` - Usage metrics

---

## Proposed Analyzer Structure

### Phase 7: Cribl Lake Support

#### LakeHealthAnalyzer
- Dataset health monitoring
- Storage utilization tracking
- Retention policy validation
- Lakehouse performance

**Findings**:
- Datasets approaching retention limit
- Storage locations over capacity
- Orphaned or unused datasets
- Lakehouse availability issues

**Recommendations**:
- Optimize retention policies
- Archive or delete unused datasets
- Enable BYOS for compliance
- Create lakehouses for frequently-queried data

#### LakeStorageAnalyzer
- Storage cost optimization
- Data reduction opportunities
- Compression analysis
- BYOS migration planning

**Findings**:
- High storage costs
- Inefficient data formats
- Redundant datasets
- Missing compression

**Recommendations**:
- Convert to Parquet format
- Implement data reduction pipelines
- Consolidate duplicate datasets
- Enable BYOS for cost savings

#### LakeSecurityAnalyzer
- Access control validation
- Data governance compliance
- Audit log review
- Token/credential management

**Findings**:
- Overly permissive access
- Missing audit logs
- Expired tokens
- Compliance violations

**Recommendations**:
- Implement least-privilege access
- Enable audit logging
- Rotate API tokens
- Configure data retention for compliance

---

### Phase 8: Cribl Search Support

#### SearchHealthAnalyzer
- Query performance monitoring
- Search job tracking
- Dataset availability
- Connection health

**Findings**:
- Slow-running queries
- Failed search jobs
- Unavailable datasets
- Provider connection issues

**Recommendations**:
- Optimize query operators
- Use lakehouse search when available
- Fix broken data connections
- Schedule resource-intensive searches

#### SearchPerformanceAnalyzer
- Query optimization
- Cost analysis
- Lakehouse usage
- API throttling detection

**Findings**:
- Inefficient query patterns
- High query costs
- Underutilized lakehouses
- API throttling detected

**Recommendations**:
- Reorder query operators
- Enable lakehouse for datasets
- Implement query result caching
- Adjust API rate limits

---

## Sandbox Discovery Results

**Date**: 2025-12-28
**Instance**: https://sandboxdev-serene-lovelace-dd6mau4.cribl.cloud

### Endpoints Discovered

**Common Endpoints** (3 found):
- `GET /api/v1/system/settings` - System settings
- `GET /api/v1/health` - Health check
- `GET /api/v1/version` - Version info

**Lake Endpoints** (0 found):
- No Lake-specific endpoints responding
- Suggests Lake may not be provisioned in this sandbox

**Search Endpoints** (1 found):
- `GET /api/v1/jobs` - Jobs list (returns items, count, offset, limit)
  - Sample: `{"items": [], "count": 0, "offset": 0, "limit": 500}`
  - Suggests job/task tracking capability

### Findings

1. **Product Type**: Cribl.Cloud (unified platform with multiple products)
2. **Lake Status**: No Lake product provisioned in sandbox
3. **Search Status**: ✅ FULLY OPERATIONAL - discovered workspace-scoped endpoints
4. **Access**: API authentication working correctly
5. **Workspaces Discovered**: 5 workspaces (default, defaultHybrid, hday_macbook_docker_worker, default_fleet, **default_search**)
6. **Search Workspace**: `default_search` contains all Search functionality

### Updated Discovery Results (2025-12-28 - Workspace-Scoped)

**Critical Finding**: Search APIs use **workspace-scoped endpoints** with pattern:
```
/api/v1/m/{workspace}/search/{resource}
```

**Confirmed Working Endpoints** (workspace: `default_search`):

✅ **Search Jobs**: `GET /api/v1/m/default_search/search/jobs`
- Response: `{items: [], count: 0}`
- Sample Job Data:
  - `id`: Job ID (e.g., "1766939703881.P0akH8")
  - `query`: KQL query string
  - `earliest`, `latest`: Time range
  - `status`: Job status ("running", "completed", "failed")
  - `user`, `displayUsername`: User info
  - `stages`: Query execution stages
  - `cpuMetrics`: Execution metrics (totalCPUSeconds, billableCPUSeconds, executorsCPUSeconds)
  - `metadata`: Datasets, providers, operators used
  - `timeCreated`, `timeStarted`: Timestamps

✅ **Search Datasets**: `GET /api/v1/m/default_search/search/datasets`
- Response: `{items: [], count: 0}`
- Sample Dataset Data:
  - `id`: Dataset ID (e.g., "cribl_edge_appscope_events")
  - `provider`: Provider name (e.g., "cribl_edge")
  - `type`: Dataset type (e.g., "cribl_edge", "s3")
  - `description`: Human-readable description
  - `fleets`: Associated fleets (e.g., ["*"])
  - `path`: Data path pattern
  - `filter`: Filter expression

✅ **Dashboards**: `GET /api/v1/m/default_search/search/dashboards`
- Response: `{items: [], count: 0}`
- Sample Dashboard Data:
  - `id`: Dashboard ID
  - `name`: Dashboard name
  - `description`: Description
  - `category`: Category
  - `elements`: Dashboard elements/widgets
  - `schedule`: Schedule configuration
  - `groups`: Associated groups
  - `createdBy`, `modifiedBy`: User info
  - `created`, `modified`: Timestamps

✅ **Saved Searches**: `GET /api/v1/m/default_search/search/saved`
- Response: `{items: [], count: 0}`
- Sample Saved Search Data:
  - `id`: Saved search ID
  - `name`: Name
  - `description`: Description
  - `query`: KQL query string
  - `earliest`, `latest`: Default time range
  - `lib`: Library/folder

**Endpoints Not Available** (404 responses):
- `/api/v1/m/default_search/search/metrics`
- `/api/v1/m/default_search/search/stats`
- `/api/v1/m/default_search/search/health`
- `/api/v1/m/default_search/search/providers`

### Lake API Discovery (2025-12-28 - Product-Scoped)

**Critical Finding**: Lake APIs use **product-scoped endpoints** with pattern:
```
/api/v1/products/lake/lakes/{lake_name}/{resource}
```

**Confirmed Working Endpoints** (lake: `default`):

✅ **Lake Datasets**: `GET /api/v1/products/lake/lakes/default/datasets`
- Response: `{items: [], count: 0}`
- With Metrics: `?includeMetrics=true&storageLocationId=cribl_lake`
- Sample Dataset Data:
  - `id`: Dataset ID (e.g., "default_logs", "cribl_metrics")
  - `bucketName`: S3 bucket name
  - `description`: Human-readable description
  - `retentionPeriodInDays`: Retention period (5-30 days in sandbox)
  - `format`: Data format ("json", "parquet")
  - `viewName`: View name for querying
  - `metrics`: Dataset metrics (when requested)

✅ **Dataset Stats**: `GET /api/v1/products/lake/lakes/default/datasets/stats`
- Response: `{items: [], count: 0}`
- Returns statistics for datasets

✅ **Lakehouses**: `GET /api/v1/products/lake/lakes/default/lakehouses`
- Response: `{items: [], count: 0}`
- Returns lakehouse configurations

**Built-in Lake Datasets Found**:
- `cribl_logs` - Internal logs from Cribl deployments (30 days retention)
- `cribl_metrics` - Internal metrics from Cribl deployments (30 days retention)
- `default_events` - Events from Kubernetes/APIs (30 days retention)
- `default_logs` - Logs from multiple sources (30 days retention)
- `default_metrics` - Metrics from multiple sources (15 days retention)
- `default_spans` - Distributed trace spans (10 days retention)
- `storage_test` - Test dataset (5 days retention)

**Endpoints Not Available** (404 responses):
- `/api/v1/products/lake/lakes/default/health`
- `/api/v1/products/lake/lakes/default/metrics`
- `/api/v1/products/lake/lakes/default/status`
- `/api/v1/products/lake/storage/locations`
- `/api/v1/products/lake/lakes/default/storage/usage`

### Recommendations

**✅ PROCEED with BOTH Phase 7 AND Phase 8**

**Phase 7: Cribl Lake Support**
- Lake IS available with product-scoped endpoint pattern
- Full dataset information available (id, retention, format, bucket)
- Can build LakeHealthAnalyzer and LakeStorageAnalyzer
- Lakehouse endpoints available

**Phase 8: Cribl Search Support**
- Search fully operational with workspace-scoped endpoints
- Full job, dataset, dashboard, saved search data available
- Can build SearchHealthAnalyzer and SearchPerformanceAnalyzer

---

## Next Steps

### Completed Actions

1. **✅ Access Sandbox Environment** - DONE
   - Accessed sandboxdev-serene-lovelace-dd6mau4.cribl.cloud
   - API access tokens working

2. **✅ API Discovery** - DONE
   - Discovered **workspace-scoped endpoint pattern** for Search: `/api/v1/m/{workspace}/search/...`
   - Discovered **product-scoped endpoint pattern** for Lake: `/api/v1/products/lake/lakes/{lake}/...`
   - Found all Search endpoints in `default_search` workspace
   - Found all Lake endpoints in `default` lake
   - Documented both API structures with sample data

3. **✅ Decision Made**
   - PROCEED with BOTH Phase 7 (Lake) AND Phase 8 (Search)
   - Both products are fully operational in sandbox

### Implementation Plan for Phase 7 & 8: Lake and Search Support

**Phase 7: Cribl Lake Support**

1. **Create Lake Data Models** (src/cribl_hc/models/lake.py)
   - LakeDataset (id, bucketName, description, retentionPeriodInDays, format, viewName, metrics)
   - Lakehouse (id, name, configuration, status)
   - DatasetStats (dataset metrics and statistics)

2. **Extend API Client** (src/cribl_hc/core/api_client.py)
   - Add `get_lake_datasets(lake_name: str, include_metrics: bool = False)`
   - Add `get_lake_dataset_stats(lake_name: str)`
   - Add `get_lake_lakehouses(lake_name: str)`
   - Support product-scoped endpoint pattern

3. **Build LakeHealthAnalyzer** (src/cribl_hc/analyzers/lake_health.py)
   - Check dataset retention policies
   - Identify datasets approaching retention limits
   - Validate dataset configurations
   - Monitor lakehouse availability

4. **Build LakeStorageAnalyzer** (src/cribl_hc/analyzers/lake_storage.py)
   - Analyze retention policies (identify inefficient settings)
   - Check data format efficiency (JSON vs Parquet)
   - Recommend storage optimizations
   - Identify unused or redundant datasets

**Phase 8: Cribl Search Support**

5. **Create Search Data Models** (src/cribl_hc/models/search.py)
   - SearchJob (id, query, status, user, cpuMetrics, metadata, timestamps)
   - SearchDataset (id, provider, type, description, fleets, path, filter)
   - Dashboard (id, name, description, elements, schedule, groups)
   - SavedSearch (id, name, query, earliest, latest, description)

6. **Extend API Client** (src/cribl_hc/core/api_client.py)
   - Add `get_workspace_search_jobs(workspace: str)`
   - Add `get_workspace_search_datasets(workspace: str)`
   - Add `get_workspace_dashboards(workspace: str)`
   - Add `get_workspace_saved_searches(workspace: str)`
   - Support workspace-scoped endpoint pattern

7. **Build SearchHealthAnalyzer** (src/cribl_hc/analyzers/search_health.py)
   - Check for failed/long-running search jobs
   - Validate dataset availability
   - Monitor query performance
   - Check dashboard health

8. **Build SearchPerformanceAnalyzer** (src/cribl_hc/analyzers/search_performance.py)
   - Analyze CPU metrics from jobs
   - Identify expensive queries
   - Track billable vs total CPU usage
   - Recommend query optimizations

9. **Write Comprehensive Tests**
   - Unit tests for all data models
   - API client tests with mocked responses
   - Analyzer tests with sample data
   - Integration tests (if possible)

### Updated User Stories

**Phase 7: Cribl Lake Support** (NOW PROCEEDING)
- US7: Lake Dataset Health & Retention Management
  - Monitor dataset retention policies
  - Identify datasets approaching retention limits
  - Validate dataset configurations (format, bucket, view)
  - Check lakehouse availability and status
  - Recommend retention optimizations

- US8: Lake Storage Optimization
  - Analyze data format efficiency (JSON vs Parquet)
  - Identify unused or low-activity datasets
  - Recommend storage cost optimizations
  - Validate bucket configurations

**Phase 8: Cribl Search Support** (NOW PROCEEDING)
- US9: Search Job Health Monitoring
  - Monitor search job status (running, failed, completed)
  - Identify long-running or stuck jobs
  - Validate dataset availability for queries
  - Track dashboard and saved search health

- US10: Search Performance & Cost Optimization
  - Analyze CPU metrics (total vs billable)
  - Identify expensive queries and patterns
  - Recommend query optimizations
  - Track executor performance distribution
  - Monitor provider health and availability

---

## Questions for Sandbox Testing

### Cribl Lake

1. What health metrics are available at the Lake level?
2. How are dataset statistics exposed (size, record count, last updated)?
3. What lakehouse management operations are available?
4. How is storage usage reported (per-dataset, per-location)?
5. What retention policy options can be configured via API?
6. Are there any Lake-specific alert conditions?

### Cribl Search

1. How are query performance metrics accessed?
2. What job management operations are available?
3. How is search cost calculated and reported?
4. What workspace usage metrics are exposed?
5. Are scheduled searches manageable via API?
6. What dataset provider health metrics exist?

---

## Expected Deliverables

**Phase 7 - Cribl Lake Support** (ACTIVE):
- ✅ Lake API endpoint documentation (COMPLETE)
- ✅ Product-scoped endpoint pattern discovery (COMPLETE)
- Lake data models (Pydantic) - LakeDataset, Lakehouse, DatasetStats
- Extended APIClient with product-scoped methods
- LakeHealthAnalyzer (with tests)
- LakeStorageAnalyzer (with tests)
- Lake user stories document (US7, US8)
- Integration with existing CLI

**Phase 8 - Cribl Search Support** (ACTIVE):
- ✅ Search API endpoint documentation (COMPLETE)
- ✅ Workspace-scoped endpoint pattern discovery (COMPLETE)
- Search data models (Pydantic) - SearchJob, SearchDataset, Dashboard, SavedSearch
- Extended APIClient with workspace-scoped methods
- SearchHealthAnalyzer (with tests)
- SearchPerformanceAnalyzer (with tests)
- Search user stories document (US9, US10)
- Integration with existing CLI

**Estimated Effort**:
- ✅ API Discovery & Documentation: 3 hours (COMPLETE)
- Lake Data Models: 1 hour
- Search Data Models: 1-2 hours
- APIClient Extensions: 1-2 hours
- LakeHealthAnalyzer: 2-3 hours
- LakeStorageAnalyzer: 2-3 hours
- SearchHealthAnalyzer: 2-3 hours
- SearchPerformanceAnalyzer: 2-3 hours
- Testing & Documentation: 3-4 hours
- **Remaining**: 14-20 hours

---

## References

All research based on official Cribl documentation as of 2025-12-28.
