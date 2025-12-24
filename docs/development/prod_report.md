# Cribl Stream Health Check Report

**Deployment:** prod
**Generated:** 2025-12-18 21:56:31 UTC
**Status:** COMPLETED
**Duration:** 0.59s


## Executive Summary

✅ **Analysis Status:** COMPLETED

### Key Metrics

| Metric | Value |
|--------|-------|
| Objectives Analyzed | config, health, resource |
| Total Findings | 44 |
| Critical Issues | 0 |
| High Severity | 2 |
| Medium Severity | 1 |
| Recommendations | 2 |
| API Calls Used | 11/100 |


## CONFIG Findings

### 🟡 MEDIUM

#### Route Missing Output Destination: default

Route 'default' does not specify an output destination

**Components:** `route-default`

**Impact:** Data may not be routed correctly

**Details:**
```json
{
  "route_id": "default"
}
```

### 🔵 LOW

#### Unused Pipeline: cisco_asa

Pipeline 'cisco_asa' is not referenced by any route

**Components:** `pipeline-cisco_asa`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "cisco_asa",
  "used_by_routes": false
}
```

#### Unused Pipeline: cisco_estreamer

Pipeline 'cisco_estreamer' is not referenced by any route

**Components:** `pipeline-cisco_estreamer`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "cisco_estreamer",
  "used_by_routes": false
}
```

#### Unused Pipeline: connecticut_storage

Pipeline 'connecticut_storage' is not referenced by any route

**Components:** `pipeline-connecticut_storage`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "connecticut_storage",
  "used_by_routes": false
}
```

#### Unused Pipeline: cribl_metrics_rollup

Pipeline 'cribl_metrics_rollup' is not referenced by any route

**Components:** `pipeline-cribl_metrics_rollup`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "cribl_metrics_rollup",
  "used_by_routes": false
}
```

#### Unused Pipeline: devnull

Pipeline 'devnull' is not referenced by any route

**Components:** `pipeline-devnull`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "devnull",
  "used_by_routes": false
}
```

#### Unused Pipeline: keck_output_router_test

Pipeline 'keck_output_router_test' is not referenced by any route

**Components:** `pipeline-keck_output_router_test`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "keck_output_router_test",
  "used_by_routes": false
}
```

#### Unused Pipeline: main

Pipeline 'main' is not referenced by any route

**Components:** `pipeline-main`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "main",
  "used_by_routes": false
}
```

#### Unused Pipeline: maskpassword

Pipeline 'maskpassword' is not referenced by any route

**Components:** `pipeline-maskpassword`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "maskpassword",
  "used_by_routes": false
}
```

#### Unused Pipeline: pack:HelloPacks

Pipeline 'pack:HelloPacks' is not referenced by any route

**Components:** `pipeline-pack:HelloPacks`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "pack:HelloPacks",
  "used_by_routes": false
}
```

#### Unused Pipeline: pack:cribl-cisco-ftd-cleanup

Pipeline 'pack:cribl-cisco-ftd-cleanup' is not referenced by any route

**Components:** `pipeline-pack:cribl-cisco-ftd-cleanup`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "pack:cribl-cisco-ftd-cleanup",
  "used_by_routes": false
}
```

#### Unused Pipeline: pack:cribl-crowdstrike-rest-io

Pipeline 'pack:cribl-crowdstrike-rest-io' is not referenced by any route

**Components:** `pipeline-pack:cribl-crowdstrike-rest-io`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "pack:cribl-crowdstrike-rest-io",
  "used_by_routes": false
}
```

#### Unused Pipeline: pack:cribl-microsoft-sentinel

Pipeline 'pack:cribl-microsoft-sentinel' is not referenced by any route

**Components:** `pipeline-pack:cribl-microsoft-sentinel`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "pack:cribl-microsoft-sentinel",
  "used_by_routes": false
}
```

#### Unused Pipeline: pack:cribl_splunk_forwarder_windows_classic_events_to_json

Pipeline 'pack:cribl_splunk_forwarder_windows_classic_events_to_json' is not referenced by any route

**Components:** `pipeline-pack:cribl_splunk_forwarder_windows_classic_events_to_json`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "pack:cribl_splunk_forwarder_windows_classic_events_to_json",
  "used_by_routes": false
}
```

#### Unused Pipeline: pack:cribl_splunk_forwarder_windows_xml_events_to_json

Pipeline 'pack:cribl_splunk_forwarder_windows_xml_events_to_json' is not referenced by any route

**Components:** `pipeline-pack:cribl_splunk_forwarder_windows_xml_events_to_json`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "pack:cribl_splunk_forwarder_windows_xml_events_to_json",
  "used_by_routes": false
}
```

#### Unused Pipeline: palo_alto_traffic

Pipeline 'palo_alto_traffic' is not referenced by any route

**Components:** `pipeline-palo_alto_traffic`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "palo_alto_traffic",
  "used_by_routes": false
}
```

#### Unused Pipeline: passthru

Pipeline 'passthru' is not referenced by any route

**Components:** `pipeline-passthru`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "passthru",
  "used_by_routes": false
}
```

#### Unused Pipeline: prometheus_metrics

Pipeline 'prometheus_metrics' is not referenced by any route

**Components:** `pipeline-prometheus_metrics`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "prometheus_metrics",
  "used_by_routes": false
}
```

#### Unused Pipeline: ps_help_1

Pipeline 'ps_help_1' is not referenced by any route

**Components:** `pipeline-ps_help_1`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "ps_help_1",
  "used_by_routes": false
}
```

#### Unused Pipeline: regex_extract_xml

Pipeline 'regex_extract_xml' is not referenced by any route

**Components:** `pipeline-regex_extract_xml`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "regex_extract_xml",
  "used_by_routes": false
}
```

#### Unused Pipeline: wineventlogs

Pipeline 'wineventlogs' is not referenced by any route

**Components:** `pipeline-wineventlogs`

**Impact:** Minimal - increases configuration complexity and maintenance burden

**Details:**
```json
{
  "pipeline_id": "wineventlogs",
  "used_by_routes": false
}
```

#### Filtering should occur early in pipeline: cisco_asa

Pipeline does not start with filtering/sampling functions (Component: pipeline 'cisco_asa')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-cisco_asa`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "cisco_asa",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: cisco_estreamer

Pipeline does not start with filtering/sampling functions (Component: pipeline 'cisco_estreamer')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-cisco_estreamer`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "cisco_estreamer",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: cribl_metrics_rollup

Pipeline does not start with filtering/sampling functions (Component: pipeline 'cribl_metrics_rollup')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-cribl_metrics_rollup`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "cribl_metrics_rollup",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: devnull

Pipeline does not start with filtering/sampling functions (Component: pipeline 'devnull')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-devnull`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "devnull",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: main

Pipeline does not start with filtering/sampling functions (Component: pipeline 'main')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-main`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "main",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: palo_alto_traffic

Pipeline does not start with filtering/sampling functions (Component: pipeline 'palo_alto_traffic')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-palo_alto_traffic`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "palo_alto_traffic",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: passthru

Pipeline does not start with filtering/sampling functions (Component: pipeline 'passthru')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-passthru`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "passthru",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: prometheus_metrics

Pipeline does not start with filtering/sampling functions (Component: pipeline 'prometheus_metrics')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-prometheus_metrics`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "prometheus_metrics",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: wineventlogs

Pipeline does not start with filtering/sampling functions (Component: pipeline 'wineventlogs')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-wineventlogs`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "wineventlogs",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: connecticut_storage

Pipeline does not start with filtering/sampling functions (Component: pipeline 'connecticut_storage')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-connecticut_storage`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "connecticut_storage",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: keck_output_router_test

Pipeline does not start with filtering/sampling functions (Component: pipeline 'keck_output_router_test')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-keck_output_router_test`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "keck_output_router_test",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: maskpassword

Pipeline does not start with filtering/sampling functions (Component: pipeline 'maskpassword')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-maskpassword`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "maskpassword",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: ps_help_1

Pipeline does not start with filtering/sampling functions (Component: pipeline 'ps_help_1')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-ps_help_1`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "ps_help_1",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: regex_extract_xml

Pipeline does not start with filtering/sampling functions (Component: pipeline 'regex_extract_xml')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-regex_extract_xml`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "regex_extract_xml",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: pack:HelloPacks

Pipeline does not start with filtering/sampling functions (Component: pipeline 'pack:HelloPacks')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-pack:HelloPacks`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "pack:HelloPacks",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: pack:cribl_splunk_forwarder_windows_xml_events_to_json

Pipeline does not start with filtering/sampling functions (Component: pipeline 'pack:cribl_splunk_forwarder_windows_xml_events_to_json')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-pack:cribl_splunk_forwarder_windows_xml_events_to_json`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "pack:cribl_splunk_forwarder_windows_xml_events_to_json",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: pack:cribl-cisco-ftd-cleanup

Pipeline does not start with filtering/sampling functions (Component: pipeline 'pack:cribl-cisco-ftd-cleanup')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-pack:cribl-cisco-ftd-cleanup`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "pack:cribl-cisco-ftd-cleanup",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: pack:cribl_splunk_forwarder_windows_classic_events_to_json

Pipeline does not start with filtering/sampling functions (Component: pipeline 'pack:cribl_splunk_forwarder_windows_classic_events_to_json')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-pack:cribl_splunk_forwarder_windows_classic_events_to_json`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "pack:cribl_splunk_forwarder_windows_classic_events_to_json",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: pack:cribl-crowdstrike-rest-io

Pipeline does not start with filtering/sampling functions (Component: pipeline 'pack:cribl-crowdstrike-rest-io')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-pack:cribl-crowdstrike-rest-io`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "pack:cribl-crowdstrike-rest-io",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```

#### Filtering should occur early in pipeline: pack:cribl-microsoft-sentinel

Pipeline does not start with filtering/sampling functions (Component: pipeline 'pack:cribl-microsoft-sentinel')

Rationale: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Components:** `pipeline-pack:cribl-microsoft-sentinel`

**Impact:** Best practice violation: Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%

**Details:**
```json
{
  "rule_id": "rule-perf-filter-early",
  "rule_category": "performance",
  "component_id": "pack:cribl-microsoft-sentinel",
  "component_type": "pipeline",
  "check_type": "config_pattern"
}
```


## HEALTH Findings

### 🟠 HIGH

#### Unhealthy Worker: 0a3963e0eda2

Worker 0a3963e0eda2 (group: hday_macbook_docker_worker) has 1 health concern(s): Disconnected

**Components:** `fd344075-b3d2-45bb-8bf1-14cf542d8e4d`

**Impact:** Worker performance degraded - Disconnected

**Details:**
```json
{
  "worker_id": "fd344075-b3d2-45bb-8bf1-14cf542d8e4d",
  "hostname": "0a3963e0eda2",
  "group": "hday_macbook_docker_worker",
  "status": "healthy",
  "disconnected": true,
  "disk_usage_percent": 8.061495261513613,
  "disk_total_gb": 58.367008209228516,
  "disk_free_gb": 53.6617546081543,
  "memory_total_gb": 9.703544616699219,
  "uptime_minutes": 2063.85865,
  "issues": [
    "Disconnected"
  ],
  "warnings": []
}
```

#### System Health: Unhealthy

1/3 workers require attention (health score: 66.67/100)

**Components:** `overall_health`

**Impact:** Overall system health: 66.67/100

**Details:**
```json
{
  "health_score": 66.67,
  "total_workers": 3,
  "unhealthy_workers": 1,
  "status": "unhealthy"
}
```

### 🔵 LOW

#### Suboptimal Worker Process Count: 0a3963e0eda2

Worker 0a3963e0eda2 has 9 process(es) but has 11 CPUs available. Recommended: 10 processes

**Components:** `fd344075-b3d2-45bb-8bf1-14cf542d8e4d`

**Impact:** Underutilizing available CPU resources - could process 10x workload

**Details:**
```json
{
  "worker_id": "fd344075-b3d2-45bb-8bf1-14cf542d8e4d",
  "hostname": "0a3963e0eda2",
  "current_processes": 9,
  "recommended_processes": 10,
  "total_cpus": 11
}
```


## Recommendations

### 🟡 MEDIUM Priority

#### 1. Remediate Worker Health: fd344075-b3d2-45bb-8bf1-14cf542d8e4d

Address health issues on worker fd344075-b3d2-45bb-8bf1-14cf542d8e4d

**Implementation Steps:**

1. Verify network connectivity between worker and leader
2. Check worker process health
3. Review firewall rules and network configuration

**References:**
- https://docs.cribl.io/stream/scaling/
- https://docs.cribl.io/stream/monitoring/

### 🔵 LOW Priority

#### 1. Remove Unused Configuration Components

Remove 20 unused pipelines and 1 unused outputs to reduce configuration complexity

**Implementation Steps:**

1. Review list of unused components and verify they are truly not needed
2. Document any components being kept for future use
3. Remove unused pipelines from configuration
4. Remove unused outputs from configuration
5. Commit configuration changes with clear documentation
6. Monitor for any unexpected issues after cleanup

**Estimated Time:** 30-60 minutes

**References:**
- https://docs.cribl.io/stream/pipelines/
- https://docs.cribl.io/stream/destinations/


## Appendix

### Analysis Metadata

| Field | Value |
|-------|-------|
| Analysis ID | `d2c0db8c-47ab-41d3-bf53-2e41d3fa886b` |
| Started At | 2025-12-18 21:56:31 UTC |
| Completed At | N/A |
| Duration | 0.59 seconds |
| API Calls | 11/100 |
| Partial Completion | No |

---

*Generated by cribl-hc - Cribl Stream Health Check Tool*
