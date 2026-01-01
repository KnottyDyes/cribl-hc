"""
Lookup Health Analyzer for Cribl Stream Health Check.

Analyzes lookup table configurations to identify:
- Oversized lookup tables that may impact performance
- Large in-memory lookups that should use disk mode
- Unused or orphaned lookup tables
- Missing lookups referenced by pipelines
"""

from typing import Any, Dict, List, Set

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger


class LookupHealthAnalyzer(BaseAnalyzer):
    """
    Analyzer for lookup table health and optimization.

    Phase 10 - Data Quality & Topology

    Checks:
    - Lookup table sizes and mode recommendations
    - Memory vs disk mode optimization
    - Orphaned lookups (not referenced by any pipeline)
    - Missing lookups (referenced but not defined)
    - MMDB file health
    """

    # Size thresholds in bytes
    LARGE_LOOKUP_THRESHOLD = 50 * 1024 * 1024  # 50 MB
    MEDIUM_LOOKUP_THRESHOLD = 10 * 1024 * 1024  # 10 MB
    MEMORY_MODE_MAX_RECOMMENDED = 100 * 1024 * 1024  # 100 MB

    # Warning thresholds
    MAX_RECOMMENDED_MEMORY_LOOKUPS = 10
    MAX_TOTAL_MEMORY_SIZE = 500 * 1024 * 1024  # 500 MB total in memory

    def __init__(self):
        """Initialize the lookup health analyzer."""
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "lookup_health"

    @property
    def supported_products(self) -> List[str]:
        """Lookup analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Lookup table health analysis, size optimization, and usage validation"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: lookups(1) + pipelines(1) = 2.
        """
        return 2

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:lookups",
            "read:pipelines"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform lookup health analysis.

        Args:
            client: Cribl API client

        Returns:
            AnalyzerResult with findings and recommendations
        """
        result = self.create_result()

        try:
            # Fetch lookup tables
            lookups = await client.get_lookups()
            result.metadata["lookup_count"] = len(lookups)

            # Fetch pipelines to check for lookup references
            pipelines = await client.get_pipelines()
            result.metadata["pipeline_count"] = len(pipelines)

            # Find all lookup references in pipelines
            referenced_lookups = self._find_lookup_references(pipelines)
            result.metadata["referenced_lookups"] = list(referenced_lookups)

            # Analyze each lookup
            memory_lookups = []
            disk_lookups = []
            total_memory_size = 0

            for lookup in lookups:
                lookup_id = lookup.get("id", "unknown")
                size = lookup.get("size", 0)
                mode = lookup.get("mode", "memory")

                if mode == "memory":
                    memory_lookups.append(lookup)
                    total_memory_size += size
                else:
                    disk_lookups.append(lookup)

                # Check for oversized lookups
                self._check_lookup_size(result, lookup)

                # Check memory mode appropriateness
                self._check_memory_mode(result, lookup)

            result.metadata["memory_lookups"] = len(memory_lookups)
            result.metadata["disk_lookups"] = len(disk_lookups)
            result.metadata["total_memory_size_mb"] = round(total_memory_size / (1024 * 1024), 2)

            # Check for orphaned lookups
            self._check_orphaned_lookups(result, lookups, referenced_lookups)

            # Check for missing lookups
            self._check_missing_lookups(result, lookups, referenced_lookups)

            # Check total memory usage
            self._check_total_memory_usage(result, memory_lookups, total_memory_size)

            # Check MMDB files
            self._check_mmdb_lookups(result, lookups)

            # Add summary finding
            self._add_summary_finding(result, lookups, memory_lookups, disk_lookups)

            self.log.info(
                "lookup_health_analysis_completed",
                lookup_count=len(lookups),
                memory_lookups=len(memory_lookups),
                total_memory_mb=result.metadata["total_memory_size_mb"]
            )

        except Exception as e:
            self.log.error("lookup_health_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _find_lookup_references(self, pipelines: List[Dict[str, Any]]) -> Set[str]:
        """
        Find all lookup table references in pipeline configurations.

        Searches for:
        - C.Lookup function calls
        - lookup_table function calls
        - Lookup function references in pipeline functions
        """
        referenced = set()

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "")
            functions = pipeline.get("conf", {}).get("functions", [])

            for func in functions:
                func_id = func.get("id", "")
                conf = func.get("conf", {})

                # Check for lookup function
                if func_id == "lookup":
                    file_ref = conf.get("file", "")
                    if file_ref:
                        referenced.add(file_ref)

                # Check for regex_extract with lookup
                if func_id == "regex_extract":
                    lookup_file = conf.get("lookupFile", "")
                    if lookup_file:
                        referenced.add(lookup_file)

                # Check function filter expressions for C.Lookup calls
                filter_expr = func.get("filter", "") or ""
                if "C.Lookup" in filter_expr or "lookup" in filter_expr.lower():
                    # Try to extract lookup file name from C.Lookup('filename', ...)
                    import re
                    matches = re.findall(r"C\.Lookup\s*\(\s*['\"]([^'\"]+)['\"]", filter_expr)
                    referenced.update(matches)

                # Check all string values in conf for lookup references
                self._search_for_lookup_refs(conf, referenced)

        return referenced

    def _search_for_lookup_refs(self, obj: Any, referenced: Set[str]) -> None:
        """Recursively search for lookup references in config objects."""
        import re

        if isinstance(obj, str):
            # Look for C.Lookup('filename', ...) patterns
            matches = re.findall(r"C\.Lookup\s*\(\s*['\"]([^'\"]+)['\"]", obj)
            referenced.update(matches)
            # Also look for .csv or .mmdb file references
            file_matches = re.findall(r"['\"](\w+\.(?:csv|mmdb|gz))['\"]", obj)
            referenced.update(file_matches)
        elif isinstance(obj, dict):
            for value in obj.values():
                self._search_for_lookup_refs(value, referenced)
        elif isinstance(obj, list):
            for item in obj:
                self._search_for_lookup_refs(item, referenced)

    def _check_lookup_size(self, result: AnalyzerResult, lookup: Dict[str, Any]) -> None:
        """Check if lookup size is within recommended limits."""
        lookup_id = lookup.get("id", "unknown")
        size = lookup.get("size", 0)
        mode = lookup.get("mode", "memory")
        size_mb = size / (1024 * 1024)

        if size >= self.LARGE_LOOKUP_THRESHOLD:
            result.add_finding(
                Finding(
                    id=f"lookup-oversized-{lookup_id}",
                    title=f"Large Lookup Table: {lookup_id}",
                    description=f"Lookup table '{lookup_id}' is {size_mb:.1f} MB which may impact performance. "
                               f"Consider using disk mode or optimizing the data.",
                    severity="medium" if mode == "disk" else "high",
                    category="lookup_health",
                    confidence_level="high",
                    affected_components=[f"lookup:{lookup_id}"],
                    estimated_impact=f"Large lookups can slow down pipeline processing and increase memory usage",
                    remediation_steps=[
                        f"Switch '{lookup_id}' to disk mode if not already",
                        "Consider reducing lookup size by removing unused columns",
                        "Evaluate if all rows are necessary or if filtering is possible",
                        "For GeoIP lookups, consider using MMDB format"
                    ],
                    metadata={
                        "lookup_id": lookup_id,
                        "size_bytes": size,
                        "size_mb": size_mb,
                        "mode": mode
                    }
                )
            )

    def _check_memory_mode(self, result: AnalyzerResult, lookup: Dict[str, Any]) -> None:
        """Check if memory mode is appropriate for lookup size."""
        lookup_id = lookup.get("id", "unknown")
        size = lookup.get("size", 0)
        mode = lookup.get("mode", "memory")
        size_mb = size / (1024 * 1024)

        if mode == "memory" and size >= self.MEMORY_MODE_MAX_RECOMMENDED:
            result.add_finding(
                Finding(
                    id=f"lookup-memory-large-{lookup_id}",
                    title=f"Large In-Memory Lookup: {lookup_id}",
                    description=f"Lookup '{lookup_id}' ({size_mb:.1f} MB) is loaded in memory. "
                               f"Lookups over 100 MB should use disk mode to reduce memory pressure.",
                    severity="high",
                    category="lookup_health",
                    confidence_level="high",
                    affected_components=[f"lookup:{lookup_id}"],
                    estimated_impact="Excessive memory usage can cause OOM conditions and worker instability",
                    remediation_steps=[
                        f"Change '{lookup_id}' mode from 'memory' to 'disk'",
                        "Monitor worker memory after the change",
                        "Disk mode adds minimal latency but significantly reduces memory"
                    ],
                    metadata={
                        "lookup_id": lookup_id,
                        "size_mb": size_mb,
                        "current_mode": mode,
                        "recommended_mode": "disk"
                    }
                )
            )

            result.add_recommendation(
                Recommendation(
                    id=f"rec-lookup-disk-mode-{lookup_id}",
                    title=f"Switch {lookup_id} to Disk Mode",
                    description=f"Convert '{lookup_id}' from memory to disk mode to reduce memory usage by {size_mb:.1f} MB",
                    priority="high",
                    category="lookup_health",
                    impact_estimate=ImpactEstimate(
                        storage_reduction_gb=None,
                        performance_improvement=f"Reduce memory by {size_mb:.1f} MB",
                        time_to_implement="5-10 minutes"
                    ),
                    implementation_effort="low",
                    related_findings=[f"lookup-memory-large-{lookup_id}"],
                    product_tags=["stream", "edge"]
                )
            )

    def _check_orphaned_lookups(
        self,
        result: AnalyzerResult,
        lookups: List[Dict[str, Any]],
        referenced: Set[str]
    ) -> None:
        """Check for lookup tables not referenced by any pipeline."""
        lookup_ids = {l.get("id", "") for l in lookups if l.get("id")}
        orphaned = lookup_ids - referenced

        if orphaned:
            total_size = sum(
                l.get("size", 0) for l in lookups
                if l.get("id") in orphaned
            )
            total_size_mb = total_size / (1024 * 1024)

            result.add_finding(
                Finding(
                    id="lookup-orphaned",
                    title=f"Orphaned Lookup Tables ({len(orphaned)})",
                    description=f"Found {len(orphaned)} lookup table(s) not referenced by any pipeline: "
                               f"{', '.join(sorted(orphaned)[:5])}{'...' if len(orphaned) > 5 else ''}. "
                               f"These consume {total_size_mb:.1f} MB of storage.",
                    severity="low",
                    category="lookup_health",
                    confidence_level="medium",
                    affected_components=[f"lookup:{lid}" for lid in list(orphaned)[:10]],
                    estimated_impact="Orphaned lookups waste storage and may cause confusion",
                    remediation_steps=[
                        "Review orphaned lookups to confirm they are unused",
                        "Remove lookups that are no longer needed",
                        "Document lookups used by external systems"
                    ],
                    metadata={
                        "orphaned_count": len(orphaned),
                        "orphaned_lookups": sorted(orphaned),
                        "total_size_mb": total_size_mb
                    }
                )
            )

    def _check_missing_lookups(
        self,
        result: AnalyzerResult,
        lookups: List[Dict[str, Any]],
        referenced: Set[str]
    ) -> None:
        """Check for lookups referenced in pipelines but not defined."""
        lookup_ids = {l.get("id", "") for l in lookups if l.get("id")}
        missing = referenced - lookup_ids

        # Filter out common false positives (variables, empty strings)
        missing = {m for m in missing if m and not m.startswith("$") and "." in m or m.endswith(".csv") or m.endswith(".mmdb")}

        if missing:
            result.add_finding(
                Finding(
                    id="lookup-missing",
                    title=f"Missing Lookup Tables ({len(missing)})",
                    description=f"Found {len(missing)} lookup table(s) referenced in pipelines but not defined: "
                               f"{', '.join(sorted(missing)[:5])}{'...' if len(missing) > 5 else ''}. "
                               f"This will cause pipeline errors.",
                    severity="high",
                    category="lookup_health",
                    confidence_level="high",
                    affected_components=[f"lookup:{lid}" for lid in list(missing)[:10]],
                    estimated_impact="Missing lookups will cause runtime errors in pipelines",
                    remediation_steps=[
                        "Upload the missing lookup files",
                        "Verify the lookup filenames in pipeline configurations",
                        "Check if lookups were accidentally deleted"
                    ],
                    metadata={
                        "missing_count": len(missing),
                        "missing_lookups": sorted(missing)
                    }
                )
            )

    def _check_total_memory_usage(
        self,
        result: AnalyzerResult,
        memory_lookups: List[Dict[str, Any]],
        total_size: int
    ) -> None:
        """Check total memory usage from in-memory lookups."""
        total_mb = total_size / (1024 * 1024)

        if total_size >= self.MAX_TOTAL_MEMORY_SIZE:
            result.add_finding(
                Finding(
                    id="lookup-memory-total-high",
                    title="High Total Lookup Memory Usage",
                    description=f"Total in-memory lookup usage is {total_mb:.1f} MB across {len(memory_lookups)} lookups. "
                               f"This exceeds the recommended limit of 500 MB.",
                    severity="high",
                    category="lookup_health",
                    confidence_level="high",
                    affected_components=["lookup:memory_total"],
                    estimated_impact="Excessive memory usage can cause OOM conditions",
                    remediation_steps=[
                        "Convert large lookups to disk mode",
                        "Consolidate or deduplicate lookup data",
                        "Increase worker memory allocation if necessary"
                    ],
                    metadata={
                        "total_memory_mb": total_mb,
                        "memory_lookup_count": len(memory_lookups),
                        "threshold_mb": self.MAX_TOTAL_MEMORY_SIZE / (1024 * 1024)
                    }
                )
            )

        if len(memory_lookups) > self.MAX_RECOMMENDED_MEMORY_LOOKUPS:
            result.add_finding(
                Finding(
                    id="lookup-memory-count-high",
                    title="Many In-Memory Lookups",
                    description=f"Found {len(memory_lookups)} in-memory lookups (recommended max: {self.MAX_RECOMMENDED_MEMORY_LOOKUPS}). "
                               f"Consider consolidating or converting to disk mode.",
                    severity="low",
                    category="lookup_health",
                    confidence_level="medium",
                    affected_components=["lookup:memory_count"],
                    estimated_impact="Many small lookups can fragment memory",
                    remediation_steps=[
                        "Evaluate if lookups can be consolidated",
                        "Convert infrequently-used lookups to disk mode",
                        "Review if all lookups are necessary"
                    ],
                    metadata={
                        "memory_lookup_count": len(memory_lookups),
                        "recommended_max": self.MAX_RECOMMENDED_MEMORY_LOOKUPS
                    }
                )
            )

    def _check_mmdb_lookups(self, result: AnalyzerResult, lookups: List[Dict[str, Any]]) -> None:
        """Check MMDB (MaxMind database) lookup health."""
        mmdb_lookups = [l for l in lookups if l.get("id", "").endswith(".mmdb")]

        for lookup in mmdb_lookups:
            lookup_id = lookup.get("id", "unknown")
            size = lookup.get("size", 0)
            size_mb = size / (1024 * 1024)

            # MMDB files are typically large and should use disk mode
            if lookup.get("mode") == "memory" and size > 50 * 1024 * 1024:
                result.add_finding(
                    Finding(
                        id=f"lookup-mmdb-memory-{lookup_id}",
                        title=f"MMDB in Memory Mode: {lookup_id}",
                        description=f"MMDB file '{lookup_id}' ({size_mb:.1f} MB) is in memory mode. "
                                   f"MMDB files are optimized for disk access and should use disk mode.",
                        severity="medium",
                        category="lookup_health",
                        confidence_level="high",
                        affected_components=[f"lookup:{lookup_id}"],
                        estimated_impact="MMDB files in memory waste resources without performance benefit",
                        remediation_steps=[
                            f"Switch '{lookup_id}' to disk mode",
                            "MMDB format is designed for efficient disk access"
                        ],
                        metadata={
                            "lookup_id": lookup_id,
                            "size_mb": size_mb,
                            "file_type": "mmdb"
                        }
                    )
                )

    def _add_summary_finding(
        self,
        result: AnalyzerResult,
        lookups: List[Dict[str, Any]],
        memory_lookups: List[Dict[str, Any]],
        disk_lookups: List[Dict[str, Any]]
    ) -> None:
        """Add summary finding for lookup health."""
        total_size = sum(l.get("size", 0) for l in lookups)
        memory_size = sum(l.get("size", 0) for l in memory_lookups)
        total_mb = total_size / (1024 * 1024)
        memory_mb = memory_size / (1024 * 1024)

        # Determine overall health
        issues = len([f for f in result.findings if f.severity in ("high", "critical")])

        if issues == 0:
            severity = "info"
            status = "Healthy"
            description = f"Lookup tables are well configured. {len(lookups)} lookups totaling {total_mb:.1f} MB."
        elif issues <= 2:
            severity = "medium"
            status = "Minor Issues"
            description = f"Found {issues} issue(s) with lookup configuration. Review recommendations."
        else:
            severity = "high"
            status = "Needs Attention"
            description = f"Found {issues} issue(s) requiring attention. Lookup optimization recommended."

        result.add_finding(
            Finding(
                id="lookup-health-summary",
                title=f"Lookup Health: {status}",
                description=description,
                severity=severity,
                category="lookup_health",
                confidence_level="high",
                affected_components=["lookup:summary"],
                estimated_impact=f"Total: {len(lookups)} lookups, {memory_mb:.1f} MB in memory, {total_mb - memory_mb:.1f} MB on disk",
                remediation_steps=[] if severity == "info" else ["Review high-severity lookup findings"],
                metadata={
                    "total_lookups": len(lookups),
                    "memory_lookups": len(memory_lookups),
                    "disk_lookups": len(disk_lookups),
                    "total_size_mb": total_mb,
                    "memory_size_mb": memory_mb,
                    "issue_count": issues
                }
            )
        )
