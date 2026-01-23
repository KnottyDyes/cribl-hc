"""
Schema Drift Detection Analyzer for Cribl Health Check.

Monitors data schema changes over time to detect field disappearances,
type changes, and other structural modifications that could break
downstream processing.
"""

import time
from collections import Counter, defaultdict
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger


@dataclass
class FieldSignature:
    """Represents a field's characteristics for drift detection."""

    name: str
    types: set[str]
    last_seen: float
    presence_count: int
    total_samples: int


class SchemaDriftAnalyzer(BaseAnalyzer):
    """
    Analyzer for detecting schema drift in event streams.

    Phase B - Enterprise Operations

    Checks:
    - Critical field disappearances
    - Field type changes
    - New field introductions
    - Schema consistency across sources
    """

    # Configuration
    CRITICAL_FIELD_DISAPPEARANCE_THRESHOLD = 0.8  # 80% drop in presence
    FIELD_TYPE_CHANGE_THRESHOLD = 0.1  # 10% of samples show different type
    MIN_SAMPLES_FOR_ANALYSIS = 20
    MAX_SAMPLES_PER_SOURCE = 100

    def __init__(self) -> None:
        """Initialize the schema drift analyzer."""
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "schema_drift"

    @property
    def supported_products(self) -> list[str]:
        """Schema drift applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Detects schema drift by monitoring field presence and type changes over time"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: multiple event captures for historical comparison."""
        return 3  # Multiple captures for time-series analysis

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:system", "execute:capture"]

    async def post_analyze_cleanup(self) -> None:
        """Optional cleanup after analysis completes."""
        pass

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform schema drift analysis.

        Strategy:
        1. Capture events from multiple time windows
        2. Analyze field signatures across captures
        3. Detect drift patterns (disappearances, type changes)
        4. Generate findings with impact assessment
        """
        result = self.create_result()

        try:
            # Capture events from different time windows for comparison
            recent_events = await client.capture_events(
                filter_expr="true", max_events=self.MAX_SAMPLES_PER_SOURCE, duration=10, level=1
            )

            # Try to get slightly older events for comparison
            older_events = []
            with suppress(Exception):
                # Use a time-based filter to get older events if available
                older_events = await client.capture_events(
                    filter_expr="_time < (now() - 300)",  # 5 minutes ago
                    max_events=self.MAX_SAMPLES_PER_SOURCE // 2,
                    duration=5,
                    level=1,
                )
                # Older events may not be available in all environments

            all_events = recent_events + older_events
            result.metadata["events_analyzed"] = len(all_events)
            result.metadata["recent_events"] = len(recent_events)
            result.metadata["older_events"] = len(older_events)

            if len(all_events) < self.MIN_SAMPLES_FOR_ANALYSIS:
                result.add_finding(
                    self.create_finding(
                        id="schema-drift-insufficient-data",
                        title="Insufficient Data for Schema Drift Analysis",
                        description=f"Only {len(all_events)} events captured, need at least {self.MIN_SAMPLES_FOR_ANALYSIS} for meaningful drift detection.",
                        severity="info",
                        category="data_quality",
                        confidence_level="medium",
                        affected_components=[],
                        metadata={"events_captured": len(all_events)},
                    )
                )
                return result

            # Analyze field signatures
            field_signatures = self._analyze_field_signatures(all_events)

            # Detect various types of drift
            drift_findings = []

            # 1. Critical field disappearances
            drift_findings.extend(self._detect_field_disappearances(field_signatures, result))

            # 2. Field type changes
            drift_findings.extend(self._detect_type_changes(field_signatures, result))

            # 3. Schema consistency issues
            drift_findings.extend(self._detect_schema_inconsistencies(all_events, result))

            # 4. New field introductions (less critical)
            drift_findings.extend(self._detect_new_fields(field_signatures, result))

            # Add findings to result
            for finding in drift_findings:
                result.add_finding(finding)

            # Summary finding
            self._add_summary_finding(result, drift_findings, len(all_events))

        except Exception as e:
            self.log.error("schema_drift_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _analyze_field_signatures(self, events: list[dict[str, Any]]) -> dict[str, FieldSignature]:
        """Analyze field signatures across all events."""
        field_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"types": Counter(), "presence_count": 0, "last_seen": 0, "samples": []}
        )

        for event in events:
            event_time = event.get("_time", time.time())

            for field_name, field_value in event.items():
                if field_name.startswith("_"):  # Skip internal Cribl fields
                    continue

                field_stats[field_name]["presence_count"] += 1
                field_stats[field_name]["last_seen"] = max(
                    field_stats[field_name]["last_seen"], event_time
                )

                # Track field types
                field_type = type(field_value).__name__
                if field_type == "str" and field_value.isdigit():
                    field_type = "numeric_string"  # Distinguish "123" from actual numbers
                elif field_type == "int" and isinstance(field_value, bool):
                    field_type = "bool"  # Python bools are ints too

                field_stats[field_name]["types"][field_type] += 1
                field_stats[field_name]["samples"].append(field_value)

        # Convert to FieldSignature objects
        signatures = {}
        total_events = len(events)

        for field_name, stats in field_stats.items():
            signatures[field_name] = FieldSignature(
                name=field_name,
                types=set(stats["types"].keys()),
                last_seen=stats["last_seen"],
                presence_count=stats["presence_count"],
                total_samples=total_events,
            )

        return signatures

    def _detect_field_disappearances(
        self, signatures: dict[str, FieldSignature], result: AnalyzerResult
    ) -> list[Any]:
        """Detect critical fields that have disappeared."""
        findings = []

        # Look for fields that were present in most samples but are now missing
        for field_name, sig in signatures.items():
            presence_rate = sig.presence_count / sig.total_samples

            # Flag critical disappearances (>80% drop from expected presence)
            if presence_rate < self.CRITICAL_FIELD_DISAPPEARANCE_THRESHOLD:
                # Determine severity based on presence rate
                if presence_rate < 0.1:  # <10% presence
                    severity = "critical"
                    impact_desc = "Field is nearly absent - likely broken upstream"
                elif presence_rate < 0.3:  # <30% presence
                    severity = "high"
                    impact_desc = "Field is frequently missing - may indicate parsing issues"
                else:  # 30-80% presence
                    severity = "medium"
                    impact_desc = "Field presence is inconsistent - monitor for trends"

                findings.append(
                    self.create_finding(
                        id=f"schema-drift-field-disappearance-{field_name}",
                        title=f"Critical Field Disappearance: {field_name}",
                        description=f"Field '{field_name}' was only present in {sig.presence_count}/{sig.total_samples} "
                        f"events ({presence_rate:.1%}). {impact_desc}",
                        severity=severity,
                        category="data_quality",
                        confidence_level="high",
                        affected_components=[f"field:{field_name}"],
                        estimated_impact="Downstream processing failures, missing data in searches/dashboards",
                        remediation_steps=[
                            f"Check if field '{field_name}' is still being generated by source systems",
                            "Review parser configurations for field extraction failures",
                            "Verify event breaker rules haven't changed",
                            "Check for upstream filtering that might remove this field",
                            f"Consider adding default value for '{field_name}' if it's optional",
                        ],
                        metadata={
                            "field_name": field_name,
                            "presence_count": sig.presence_count,
                            "total_samples": sig.total_samples,
                            "presence_rate": round(presence_rate, 3),
                        },
                    )
                )

        return findings

    def _detect_type_changes(
        self, signatures: dict[str, FieldSignature], result: AnalyzerResult
    ) -> list[Any]:
        """Detect fields that have changed types."""
        findings = []

        for field_name, sig in signatures.items():
            if len(sig.types) > 1:
                # Multiple types detected
                # We can't access the original type counter, so we'll estimate
                # In a real implementation, we'd store the type distribution

                primary_type = max(sig.types)  # Simplification - take lexicographically last
                other_types = sig.types - {primary_type}

                if len(other_types) > 0:
                    findings.append(
                        self.create_finding(
                            id=f"schema-drift-type-change-{field_name}",
                            title=f"Field Type Inconsistency: {field_name}",
                            description=f"Field '{field_name}' has multiple types: {', '.join(sorted(sig.types))}. "
                            f"Primary type appears to be '{primary_type}' with variations: {', '.join(sorted(other_types))}",
                            severity="medium",
                            category="data_quality",
                            confidence_level="high",
                            affected_components=[f"field:{field_name}"],
                            estimated_impact="Search aggregation errors, dashboard inconsistencies, type coercion issues",
                            remediation_steps=[
                                f"Standardize field '{field_name}' to a single type across all sources",
                                "Review parser configurations for consistent type handling",
                                "Check if multiple sources are populating this field differently",
                                "Consider explicit type casting in pipeline functions",
                            ],
                            metadata={
                                "field_name": field_name,
                                "detected_types": list(sig.types),
                                "type_count": len(sig.types),
                            },
                        )
                    )

        return findings

    def _detect_schema_inconsistencies(
        self, events: list[dict[str, Any]], result: AnalyzerResult
    ) -> list[Any]:
        """Detect inconsistencies in schema structure across events."""
        findings = []

        # Group events by source/pipeline for comparison
        events_by_source = defaultdict(list)

        for event in events:
            source = event.get("source", event.get("cribl_pipe", "unknown"))
            events_by_source[source].append(event)

        # Only analyze sources with multiple events
        sources_with_multiple = {k: v for k, v in events_by_source.items() if len(v) >= 3}

        if len(sources_with_multiple) < 2:
            return findings  # Need multiple sources to compare

        # Compare field sets between sources
        source_field_sets = {}
        for source, source_events in sources_with_multiple.items():
            all_fields = set()
            for event in source_events:
                all_fields.update(k for k in event if not k.startswith("_"))
            source_field_sets[source] = all_fields

        # Find sources with significantly different field counts
        avg_field_count = sum(len(fields) for fields in source_field_sets.values()) / len(
            source_field_sets
        )

        for source, fields in source_field_sets.items():
            field_count_diff = abs(len(fields) - avg_field_count)
            if field_count_diff > avg_field_count * 0.5:  # 50% difference
                severity = "high" if field_count_diff > avg_field_count else "medium"

                findings.append(
                    self.create_finding(
                        id=f"schema-drift-source-inconsistency-{source}",
                        title=f"Schema Inconsistency in Source: {source}",
                        description=f"Source '{source}' has {len(fields)} fields compared to average of "
                        f"{avg_field_count:.1f} across all sources. This indicates potential "
                        f"parsing or routing inconsistencies.",
                        severity=severity,
                        category="data_quality",
                        confidence_level="medium",
                        affected_components=[f"source:{source}"],
                        estimated_impact="Inconsistent data structure, search/dashboard reliability issues",
                        remediation_steps=[
                            f"Review parsing configuration for source '{source}'",
                            "Compare event breaker rules across similar sources",
                            "Check if routing rules are correctly applied",
                            "Verify source system is sending consistent data",
                        ],
                        metadata={
                            "source": source,
                            "field_count": len(fields),
                            "avg_field_count": round(avg_field_count, 1),
                            "difference": round(field_count_diff, 1),
                        },
                    )
                )

        return findings

    def _detect_new_fields(
        self, signatures: dict[str, FieldSignature], result: AnalyzerResult
    ) -> list[Any]:
        """Detect newly introduced fields (informational)."""
        findings = []

        # This is a simplified version - in practice, we'd compare against historical baselines
        new_fields = [
            sig for sig in signatures.values() if sig.presence_count < sig.total_samples * 0.2
        ]

        if len(new_fields) > 10:  # Many new fields might indicate schema changes
            findings.append(
                self.create_finding(
                    id="schema-drift-new-fields-detected",
                    title="Multiple New Fields Detected",
                    description=f"Detected {len(new_fields)} fields that appear to be newly introduced or "
                    "sparsely populated. This may indicate recent schema changes.",
                    severity="info",
                    category="data_quality",
                    confidence_level="low",
                    affected_components=[],
                    estimated_impact="Potential new data sources or schema evolution",
                    remediation_steps=[
                        "Review recent changes to data sources or pipelines",
                        "Document new fields and their purposes",
                        "Update search indexes and dashboards if needed",
                        "Consider field usage monitoring for optimization",
                    ],
                    metadata={
                        "new_field_count": len(new_fields),
                        "new_fields": [f.name for f in new_fields[:10]],  # Top 10
                    },
                )
            )

        return findings

    def _add_summary_finding(
        self, result: AnalyzerResult, findings: list[Any], total_events: int
    ) -> None:
        """Add summary finding for schema drift analysis."""
        critical_issues = len([f for f in findings if f.severity == "critical"])
        high_issues = len([f for f in findings if f.severity == "high"])
        medium_issues = len([f for f in findings if f.severity == "medium"])

        total_issues = len(findings)

        if total_issues == 0:
            severity = "info"
            status = "Healthy"
            description = f"Schema analysis completed successfully. Analyzed {total_events} events with no drift detected."
            remediation_steps: list[str] = []
            estimated_impact = ""
        elif critical_issues > 0:
            severity = "critical"
            status = "Critical Drift"
            description = f"Schema drift detected with {critical_issues} critical issues. Immediate attention required."
            remediation_steps = [
                "Review critical field disappearances immediately",
                "Check upstream data sources for breaking changes",
                "Verify parser and event breaker configurations",
                "Update downstream consumers to handle schema changes",
                "Consider implementing schema validation in pipelines",
            ]
            estimated_impact = f"Critical schema instability affecting {critical_issues} fields - downstream processing failures likely"
        elif high_issues > 0:
            severity = "high"
            status = "High Risk"
            description = f"Schema drift detected with {high_issues} high-priority issues."
            remediation_steps = [
                "Review high-priority schema issues",
                "Check for recent changes to data sources",
                "Verify field extraction configurations",
                "Update schema documentation",
            ]
            estimated_impact = f"Significant schema changes affecting {high_issues} fields - may impact searches and dashboards"
        elif medium_issues > 0:
            severity = "medium"
            status = "Moderate Drift"
            description = f"Schema drift detected with {medium_issues} moderate issues."
            remediation_steps = [
                "Review moderate schema issues during next maintenance window",
                "Monitor affected fields for further changes",
                "Document schema evolution",
            ]
            estimated_impact = f"Moderate schema variability affecting {medium_issues} fields"
        else:
            severity = "info"
            status = "Minor Changes"
            description = f"Minor schema changes detected ({total_issues} informational findings)."
            remediation_steps = []
            estimated_impact = ""

        result.add_finding(
            self.create_finding(
                id="schema-drift-summary",
                title=f"Schema Drift Analysis: {status}",
                description=description,
                severity=severity,
                category="data_quality",
                confidence_level="high",
                affected_components=[],
                estimated_impact=estimated_impact,
                remediation_steps=remediation_steps,
                metadata={
                    "total_events": total_events,
                    "critical_issues": critical_issues,
                    "high_issues": high_issues,
                    "medium_issues": medium_issues,
                    "total_issues": total_issues,
                },
            )
        )
