# Product Tagging & Sorting Enhancements

**Date**: 2025-12-28
**Status**: Complete

## Overview

Added product tagging and priority/severity sorting capabilities to the Cribl Health Check system to support multi-product analysis and better report organization.

## Features Implemented

### 1. Product Tagging System

**Supported Products:**
- `stream` - Cribl Stream
- `edge` - Cribl Edge
- `lake` - Cribl Lake (future support)
- `search` - Cribl Search (future support)

**Models Updated:**
- `Finding` model - Added `product_tags` field
- `Recommendation` model - Added `product_tags` field
- `BaseAnalyzer` class - Added `supported_products` property

**Default Behavior:**
- All findings and recommendations default to all products: `["stream", "edge", "lake", "search"]`
- Analyzers can override `supported_products` to indicate which products they support
- Individual findings/recommendations can specify specific product tags

**Example Usage:**
```python
# Finding for Stream only
finding = Finding(
    id="cost-license-001",
    category="cost",
    severity="critical",
    title="License exhaustion approaching",
    description="License consumption at 95%",
    confidence_level="high",
    estimated_impact="Service disruption",
    remediation_steps=["Upgrade license", "Reduce consumption"],
    product_tags=["stream"]  # Only applies to Stream
)

# Analyzer indicating Stream-only support
class CostAnalyzer(BaseAnalyzer):
    @property
    def supported_products(self) -> List[str]:
        return ["stream"]
```

### 2. Sorting & Filtering

**Added Methods to `AnalyzerResult`:**

#### `sort_findings_by_severity()`
Sorts findings in-place by severity:
- critical → high → medium → low → info

```python
result.sort_findings_by_severity()
# Findings now ordered: critical first, info last
```

#### `sort_recommendations_by_priority()`
Sorts recommendations in-place by priority:
- p0 → p1 → p2 → p3

```python
result.sort_recommendations_by_priority()
# Recommendations now ordered: p0 first, p3 last
```

#### `filter_by_product(product: str)`
Returns new `AnalyzerResult` with only findings/recommendations matching the specified product:

```python
# Filter for Stream-specific findings
stream_result = result.filter_by_product("stream")

# Filter for Edge-specific findings
edge_result = result.filter_by_product("edge")
```

## Benefits

1. **Multi-Product Support**: Framework ready for Lake and Search analysis when those user stories are built
2. **Targeted Reporting**: Users can filter findings for their specific product deployment
3. **Better Organization**: Sorted results make it easier to prioritize work (critical issues first, high-priority recommendations first)
4. **Product Awareness**: Each analyzer declares which products it supports

## Current Analyzer Support

| Analyzer | Supported Products | Rationale |
|----------|-------------------|-----------|
| HealthAnalyzer | stream, edge, lake, search | Health monitoring applies to all products |
| ConfigAnalyzer | stream, edge, lake, search | Configuration validation universal |
| ResourceAnalyzer | stream, edge, lake, search | Resource sizing relevant to all |
| StorageAnalyzer | stream, edge, lake, search | Storage optimization universal |
| SecurityAnalyzer | stream, edge, lake, search | Security applies to all products |
| **CostAnalyzer** | **stream** | License tracking specific to Stream model |

## Future Work

### Product-Specific Features to Build:
1. **Lake User Stories**: Build analyzers for Lake-specific features (data catalog, query optimization, retention policies)
2. **Search User Stories**: Build analyzers for Search-specific features (index optimization, query performance, schema management)
3. **Edge-Specific Features**: Add Edge-focused checks (resource constraints, connectivity resilience, edge security)

### API Structures Needed:
- Lake API endpoint mapping and data models
- Search API endpoint mapping and data models
- Product detection logic in API client

## Testing

All enhancements verified with `test_product_tags.py`:
- ✓ Finding model with product tags
- ✓ Recommendation model with product tags
- ✓ Severity sorting (critical > high > medium > low)
- ✓ Priority sorting (p0 > p1 > p2 > p3)
- ✓ Product filtering (stream, edge, lake, search)
- ✓ Analyzer product support declaration

## Usage Examples

### Example 1: Sort Report Results Before Export
```python
# After running analysis
result = await analyzer.analyze(client)

# Sort before generating report
result.sort_findings_by_severity()
result.sort_recommendations_by_priority()

# Export to JSON/MD with sorted results
report = generate_report(result)
```

### Example 2: Filter for Product-Specific Report
```python
# Run full analysis
result = await analyzer.analyze(client)

# Generate Stream-only report
stream_result = result.filter_by_product("stream")
generate_report(stream_result, title="Stream Health Check")

# Generate Edge-only report
edge_result = result.filter_by_product("edge")
generate_report(edge_result, title="Edge Health Check")
```

### Example 3: Create Product-Specific Finding
```python
# In an analyzer
if client.product_type == "edge":
    result.add_finding(Finding(
        id="edge-memory-001",
        category="resource",
        severity="high",
        title="Memory constrained on edge device",
        description="Edge device has limited memory (512MB)",
        confidence_level="high",
        estimated_impact="May cause data loss under load",
        remediation_steps=[
            "Reduce buffer sizes",
            "Enable aggressive compression",
            "Consider hardware upgrade"
        ],
        product_tags=["edge"]  # Edge-specific finding
    ))
```

## Files Modified

- `src/cribl_hc/models/finding.py` - Added `product_tags` field
- `src/cribl_hc/models/recommendation.py` - Added `product_tags` field
- `src/cribl_hc/analyzers/base.py` - Added `supported_products` property and sorting/filtering methods
- `src/cribl_hc/analyzers/cost.py` - Updated to declare Stream-only support

## Files Created

- `test_product_tags.py` - Comprehensive test suite for enhancements
- `ENHANCEMENTS_PRODUCT_TAGS_SORTING.md` - This documentation

## Next Steps

1. Commit enhancements
2. Begin US6 (Fleet Management)
3. Build Lake user stories and API structures
4. Build Search user stories and API structures
5. Add Edge-specific analyzer features
