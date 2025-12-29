"""
Pipeline Performance Analyzer for Cribl Health Check.

Analyzes pipeline function performance, regex complexity, JavaScript anti-patterns,
and provides timing instrumentation recommendations.

Priority: P1 (High Impact - Production Operations)
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class PipelinePerformanceAnalyzer(BaseAnalyzer):
    """
    Analyzer for pipeline function performance and optimization.

    Identifies:
    - Functions with high latency or processing time
    - Complex regex patterns that risk catastrophic backtracking
    - JavaScript filter anti-patterns (test() vs indexOf())
    - Pipelines without timing instrumentation
    - Inefficient function ordering

    Priority: P1 (High Impact - addresses production performance issues)
    """

    # Function latency thresholds (milliseconds per event)
    LATENCY_WARNING_MS = 1.0  # >1ms per event is slow
    LATENCY_CRITICAL_MS = 5.0  # >5ms per event is very slow

    # Regex complexity thresholds
    REGEX_NESTED_QUANTIFIER_PATTERN = re.compile(
        r'\([^)]*[+*][^)]*\)[+*]|\([^)]*\([^)]*[+*][^)]*\)[^)]*\)[+*]'
    )
    REGEX_ALTERNATION_REPEAT_PATTERN = re.compile(
        r'\([^|)]+\|[^|)]+\|[^|)]+\)[+*]'
    )
    REGEX_MAX_LENGTH = 500  # Very long regex are suspicious

    # JavaScript anti-patterns
    JS_TEST_PATTERN = re.compile(r'\.test\s*\(')
    JS_MATCH_PATTERN = re.compile(r'\.match\s*\(')
    JS_INDEXOF_PATTERN = re.compile(r'\.indexOf\s*\(')
    JS_INCLUDES_PATTERN = re.compile(r'\.includes\s*\(')

    # Function types that commonly have performance issues
    HEAVY_FUNCTION_TYPES = ["regex_extract", "eval", "code", "geoip", "lookup"]

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "pipeline_performance"

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Analyzes pipeline function performance, regex complexity, and code patterns"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: pipelines(1) + metrics(1) = 2.
        """
        return 2

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:pipelines",
            "read:metrics",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze pipeline performance across all pipelines.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with pipeline performance findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("pipeline_performance_analysis_started")

            # Fetch pipeline configurations
            pipelines = await client.get_pipelines()

            # Fetch metrics for runtime performance data
            metrics = await client.get_metrics(time_range="1h")

            # Extract pipeline-specific metrics
            pipeline_metrics = self._extract_pipeline_metrics(metrics)

            # Count functions
            total_functions = sum(
                len(p.get("functions", [])) for p in pipelines
            )

            # Initialize metadata
            result.metadata.update({
                "total_pipelines": len(pipelines),
                "total_functions": total_functions,
                "analysis_timestamp": datetime.utcnow().isoformat()
            })

            # Handle empty state
            if not pipelines:
                result.add_finding(
                    Finding(
                        id="pipeline-perf-no-pipelines",
                        category="pipeline_performance",
                        severity="info",
                        title="No Pipelines Configured",
                        description="No pipelines found for performance analysis.",
                        affected_components=["Pipelines"],
                        confidence_level="high",
                        metadata={}
                    )
                )
                result.success = True
                return result

            # Analyze each pipeline
            for pipeline in pipelines:
                self._analyze_pipeline(pipeline, pipeline_metrics, result)

            # Analyze function ordering patterns across all pipelines
            self._analyze_function_ordering(pipelines, result)

            # Check for pipelines without timing instrumentation
            self._check_timing_instrumentation(pipelines, result)

            # Add summary metadata
            self._add_summary_metadata(result)

            result.success = True
            log.info(
                "pipeline_performance_analysis_completed",
                pipelines=len(pipelines),
                functions=total_functions,
                findings=len(result.findings),
                recommendations=len(result.recommendations)
            )

        except Exception as e:
            log.error("pipeline_performance_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="pipeline-perf-analysis-error",
                    category="pipeline_performance",
                    severity="critical",
                    title="Pipeline Performance Analysis Failed",
                    description=f"Failed to analyze pipeline performance: {str(e)}",
                    affected_components=["Pipeline Analyzer"],
                    remediation_steps=["Check API connectivity", "Verify permissions"],
                    estimated_impact="Cannot assess pipeline performance",
                    confidence_level="high",
                    metadata={"error": str(e)}
                )
            )

        return result

    def _extract_pipeline_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract pipeline-specific metrics from the metrics response.

        Returns dict keyed by pipeline ID with metrics like:
        - events_in: total events processed
        - events_out: total events output
        - processing_time_ms: total processing time
        - avg_latency_ms: average latency per event
        """
        pipeline_metrics = {}

        # Metrics may be nested under various keys
        pipelines_data = metrics.get("pipelines", {})
        if not pipelines_data:
            pipelines_data = metrics.get("routes", {}).get("pipelines", {})

        for pipeline_id, data in pipelines_data.items():
            if isinstance(data, dict):
                events_in = data.get("in", {}).get("events", 0)
                processing_time = data.get("processing_time_ms", 0)

                avg_latency = 0
                if events_in > 0 and processing_time > 0:
                    avg_latency = processing_time / events_in

                pipeline_metrics[pipeline_id] = {
                    "events_in": events_in,
                    "events_out": data.get("out", {}).get("events", 0),
                    "processing_time_ms": processing_time,
                    "avg_latency_ms": avg_latency,
                    "dropped_events": data.get("dropped", {}).get("events", 0),
                }

        return pipeline_metrics

    def _analyze_pipeline(
        self,
        pipeline: Dict[str, Any],
        pipeline_metrics: Dict[str, Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Analyze a single pipeline for performance issues."""
        pipeline_id = pipeline.get("id", "unknown")
        functions = pipeline.get("functions", [])
        conf = pipeline.get("conf", {})

        # Check pipeline-level metrics
        metrics = pipeline_metrics.get(pipeline_id, {})
        avg_latency = metrics.get("avg_latency_ms", 0)

        if avg_latency >= self.LATENCY_CRITICAL_MS:
            self._report_slow_pipeline(pipeline_id, avg_latency, "critical", result)
        elif avg_latency >= self.LATENCY_WARNING_MS:
            self._report_slow_pipeline(pipeline_id, avg_latency, "warning", result)

        # Analyze each function
        for idx, func in enumerate(functions):
            self._analyze_function(pipeline_id, idx, func, result)

    def _analyze_function(
        self,
        pipeline_id: str,
        func_idx: int,
        func: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """Analyze a single function for performance issues."""
        func_id = func.get("id", f"func-{func_idx}")
        func_type = func.get("type", func.get("filter", "unknown"))
        func_conf = func.get("conf", {})

        # Check for disabled functions (still analyzed but noted)
        if func.get("disabled", False):
            return

        # Analyze based on function type
        if func_type in ["regex_extract", "regex_filter"]:
            self._analyze_regex_function(pipeline_id, func_id, func_conf, result)

        elif func_type in ["eval", "code"]:
            self._analyze_javascript_function(pipeline_id, func_id, func_conf, result)

        elif func_type == "lookup":
            self._analyze_lookup_function(pipeline_id, func_id, func_conf, result)

        elif func_type == "geoip":
            self._analyze_geoip_function(pipeline_id, func_id, func_conf, result)

    def _analyze_regex_function(
        self,
        pipeline_id: str,
        func_id: str,
        conf: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """Analyze regex function for complexity issues."""
        # Get regex pattern from various possible locations
        regex_pattern = conf.get("regex", "") or conf.get("pattern", "")

        if not regex_pattern:
            return

        issues = []

        # Check for very long regex
        if len(regex_pattern) > self.REGEX_MAX_LENGTH:
            issues.append(f"Very long pattern ({len(regex_pattern)} chars)")

        # Check for nested quantifiers (catastrophic backtracking risk)
        if self.REGEX_NESTED_QUANTIFIER_PATTERN.search(regex_pattern):
            issues.append("Nested quantifiers detected (backtracking risk)")

        # Check for repeated alternations
        if self.REGEX_ALTERNATION_REPEAT_PATTERN.search(regex_pattern):
            issues.append("Repeated alternations detected (performance risk)")

        # Check for .* or .+ without anchors
        if re.search(r'(?<!\\)\.\*', regex_pattern) or re.search(r'(?<!\\)\.\+', regex_pattern):
            if not regex_pattern.startswith('^') and not regex_pattern.endswith('$'):
                issues.append("Unbounded .* or .+ without anchors")

        if issues:
            result.add_finding(
                Finding(
                    id=f"pipeline-perf-regex-{pipeline_id}-{func_id}",
                    category="pipeline_performance",
                    severity="medium",
                    title=f"Complex Regex in {pipeline_id}:{func_id}",
                    description=(
                        f"Regex function '{func_id}' in pipeline '{pipeline_id}' has "
                        f"potential performance issues: {', '.join(issues)}"
                    ),
                    affected_components=["Pipelines", pipeline_id, func_id],
                    remediation_steps=[
                        "Review regex pattern for optimization opportunities",
                        "Use possessive quantifiers or atomic groups if supported",
                        "Add anchors (^ or $) to constrain matching",
                        "Consider using simpler string matching if possible",
                        "Test regex with representative data to measure performance"
                    ],
                    estimated_impact="Potential slow processing or CPU spikes",
                    confidence_level="medium",
                    metadata={
                        "pipeline_id": pipeline_id,
                        "function_id": func_id,
                        "pattern_length": len(regex_pattern),
                        "issues": issues
                    }
                )
            )

            result.metadata["regex_issues"] = result.metadata.get("regex_issues", 0) + 1

    def _analyze_javascript_function(
        self,
        pipeline_id: str,
        func_id: str,
        conf: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """Analyze JavaScript/eval function for anti-patterns."""
        # Get code from various possible locations
        code = conf.get("code", "") or conf.get("expression", "") or conf.get("filter", "")

        if not code:
            return

        anti_patterns = []

        # Check for .test() which is slower than indexOf for simple checks
        if self.JS_TEST_PATTERN.search(code):
            # Only flag if it looks like a simple substring check
            if not re.search(r'/[^/]+\.\+\*\?/', code):  # No complex regex
                anti_patterns.append(
                    ".test() used - consider .includes() for simple string checks"
                )

        # Check for .match() when only checking existence
        if self.JS_MATCH_PATTERN.search(code):
            if "= " not in code and "[" not in code:  # Not capturing
                anti_patterns.append(
                    ".match() for existence check - consider .test() or .includes()"
                )

        # Check for inefficient string concatenation in loops
        if re.search(r'for\s*\([^)]+\)\s*\{[^}]*\+=[^}]*\}', code):
            anti_patterns.append(
                "String concatenation in loop - consider Array.join()"
            )

        # Check for eval() usage (security and performance)
        if re.search(r'\beval\s*\(', code):
            anti_patterns.append(
                "eval() usage - significant security and performance risk"
            )

        if anti_patterns:
            result.add_finding(
                Finding(
                    id=f"pipeline-perf-js-{pipeline_id}-{func_id}",
                    category="pipeline_performance",
                    severity="low",
                    title=f"JavaScript Anti-patterns in {pipeline_id}:{func_id}",
                    description=(
                        f"JavaScript function '{func_id}' in pipeline '{pipeline_id}' "
                        f"contains patterns that may impact performance: "
                        f"{'; '.join(anti_patterns)}"
                    ),
                    affected_components=["Pipelines", pipeline_id, func_id],
                    remediation_steps=[
                        "Review code for optimization opportunities",
                        "Use indexOf/includes instead of regex for simple string checks",
                        "Avoid eval() - use safer alternatives",
                        "Use Array.join() for string building in loops"
                    ],
                    estimated_impact="Suboptimal code execution performance",
                    confidence_level="medium",
                    metadata={
                        "pipeline_id": pipeline_id,
                        "function_id": func_id,
                        "anti_patterns": anti_patterns
                    }
                )
            )

            result.metadata["js_antipatterns"] = result.metadata.get("js_antipatterns", 0) + 1

    def _analyze_lookup_function(
        self,
        pipeline_id: str,
        func_id: str,
        conf: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """Analyze lookup function for potential issues."""
        lookup_type = conf.get("type", "file")
        match_mode = conf.get("matchMode", "exact")

        # Flag if using regex match mode (slower)
        if match_mode == "regex":
            result.add_finding(
                Finding(
                    id=f"pipeline-perf-lookup-regex-{pipeline_id}-{func_id}",
                    category="pipeline_performance",
                    severity="low",
                    title=f"Regex Lookup in {pipeline_id}:{func_id}",
                    description=(
                        f"Lookup function '{func_id}' uses regex match mode, "
                        "which is slower than exact or cidr matching."
                    ),
                    affected_components=["Pipelines", pipeline_id, func_id],
                    remediation_steps=[
                        "Consider exact match if possible",
                        "Pre-process lookup table for faster matching",
                        "Monitor lookup performance in metrics"
                    ],
                    estimated_impact="Slower lookup performance per event",
                    confidence_level="medium",
                    metadata={
                        "pipeline_id": pipeline_id,
                        "function_id": func_id,
                        "match_mode": match_mode
                    }
                )
            )

    def _analyze_geoip_function(
        self,
        pipeline_id: str,
        func_id: str,
        conf: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """Analyze GeoIP function for potential issues."""
        # GeoIP is inherently heavy - flag if used without filtering
        result.metadata["geoip_functions"] = result.metadata.get("geoip_functions", 0) + 1

    def _report_slow_pipeline(
        self,
        pipeline_id: str,
        avg_latency_ms: float,
        severity_level: str,
        result: AnalyzerResult
    ) -> None:
        """Report a slow pipeline."""
        severity = "high" if severity_level == "critical" else "medium"

        result.add_finding(
            Finding(
                id=f"pipeline-perf-slow-{pipeline_id}",
                category="pipeline_performance",
                severity=severity,
                title=f"Slow Pipeline: {pipeline_id}",
                description=(
                    f"Pipeline '{pipeline_id}' has an average latency of "
                    f"{avg_latency_ms:.2f}ms per event, which is above the "
                    f"recommended threshold of {self.LATENCY_WARNING_MS}ms."
                ),
                affected_components=["Pipelines", pipeline_id],
                remediation_steps=[
                    "Review pipeline function ordering",
                    "Add filter functions early to reduce event volume",
                    "Optimize or remove expensive functions",
                    "Consider splitting into multiple pipelines",
                    "Enable pipeline timing to identify slow functions"
                ],
                estimated_impact=f"{avg_latency_ms:.2f}ms latency per event",
                confidence_level="high",
                metadata={
                    "pipeline_id": pipeline_id,
                    "avg_latency_ms": round(avg_latency_ms, 2)
                }
            )
        )

        result.metadata["slow_pipelines"] = result.metadata.get("slow_pipelines", 0) + 1

    def _analyze_function_ordering(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Analyze function ordering for optimization opportunities."""
        pipelines_with_ordering_issues = []

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("functions", [])

            if len(functions) < 2:
                continue

            # Check if heavy functions come before filters
            first_heavy_idx = -1
            first_filter_idx = -1

            for idx, func in enumerate(functions):
                func_type = func.get("type", func.get("filter", ""))

                if func_type in self.HEAVY_FUNCTION_TYPES and first_heavy_idx == -1:
                    first_heavy_idx = idx

                if func_type in ["drop", "filter", "sampling"] and first_filter_idx == -1:
                    first_filter_idx = idx

            # If heavy function comes before filter, flag it
            if first_heavy_idx != -1 and first_filter_idx != -1:
                if first_heavy_idx < first_filter_idx:
                    pipelines_with_ordering_issues.append(pipeline_id)

        if pipelines_with_ordering_issues:
            result.add_finding(
                Finding(
                    id="pipeline-perf-ordering",
                    category="pipeline_performance",
                    severity="low",
                    title=f"{len(pipelines_with_ordering_issues)} Pipeline(s) with Suboptimal Function Ordering",
                    description=(
                        "Some pipelines have expensive functions (lookup, geoip, eval) "
                        "before filter/drop functions. Moving filters earlier reduces "
                        "the number of events processed by expensive operations."
                    ),
                    affected_components=["Pipelines"] + pipelines_with_ordering_issues[:5],
                    remediation_steps=[
                        "Move filter/drop functions earlier in the pipeline",
                        "Place sampling functions before expensive operations",
                        "Review function ordering for each flagged pipeline"
                    ],
                    estimated_impact="Reduced CPU usage from filtering early",
                    confidence_level="medium",
                    metadata={
                        "pipeline_count": len(pipelines_with_ordering_issues),
                        "pipeline_ids": pipelines_with_ordering_issues
                    }
                )
            )

            result.add_recommendation(
                Recommendation(
                    id="rec-pipeline-ordering",
                    type="optimization",
                    priority="p2",
                    title="Optimize Pipeline Function Ordering",
                    description=(
                        f"Found {len(pipelines_with_ordering_issues)} pipelines where "
                        "expensive functions run before filters. Reordering can improve performance."
                    ),
                    rationale="Filtering events early reduces work for expensive functions.",
                    implementation_steps=[
                        "Review each flagged pipeline's function order",
                        "Move drop/filter/sampling functions before lookup/geoip/eval",
                        "Test pipeline after reordering to verify behavior",
                        "Monitor pipeline metrics after changes"
                    ],
                    before_state="Expensive functions process all events",
                    after_state="Filters reduce events before expensive processing",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Reduced CPU usage per pipeline"
                    ),
                    implementation_effort="low",
                    product_tags=["stream", "edge"]
                )
            )

    def _check_timing_instrumentation(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Check which pipelines have timing instrumentation enabled."""
        pipelines_without_timing = []

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            conf = pipeline.get("conf", {})

            # Check for timing/profiling settings
            timing_enabled = conf.get("timingEnabled", False)
            if not timing_enabled:
                pipelines_without_timing.append(pipeline_id)

        result.metadata["pipelines_without_timing"] = len(pipelines_without_timing)

        # Only flag if there are performance issues but no timing
        slow_pipelines = result.metadata.get("slow_pipelines", 0)
        if slow_pipelines > 0 and pipelines_without_timing:
            result.add_finding(
                Finding(
                    id="pipeline-perf-no-timing",
                    category="pipeline_performance",
                    severity="info",
                    title="Performance Issues Without Timing Instrumentation",
                    description=(
                        f"Found {slow_pipelines} slow pipeline(s), but "
                        f"{len(pipelines_without_timing)} pipeline(s) don't have "
                        "timing enabled. Enable timing to identify slow functions."
                    ),
                    affected_components=["Pipelines"],
                    remediation_steps=[
                        "Enable timing on slow pipelines for function-level metrics",
                        "Use Cribl's monitoring to view per-function latency",
                        "Identify specific functions causing slowdowns"
                    ],
                    estimated_impact="Better visibility into pipeline performance",
                    confidence_level="high",
                    metadata={
                        "pipelines_without_timing": len(pipelines_without_timing)
                    }
                )
            )

    def _add_summary_metadata(self, result: AnalyzerResult) -> None:
        """Add summary metadata to result."""
        slow_pipelines = result.metadata.get("slow_pipelines", 0)
        regex_issues = result.metadata.get("regex_issues", 0)
        js_antipatterns = result.metadata.get("js_antipatterns", 0)
        total_issues = slow_pipelines + regex_issues + js_antipatterns

        # Calculate pipeline performance score
        total_pipelines = result.metadata.get("total_pipelines", 1)
        if total_pipelines > 0:
            # Score based on percentage of pipelines without issues
            issue_ratio = min(1.0, total_issues / total_pipelines)
            result.metadata["pipeline_performance_score"] = round((1 - issue_ratio) * 100, 2)
        else:
            result.metadata["pipeline_performance_score"] = 100.0

        # Overall status
        if slow_pipelines > 0:
            result.metadata["overall_status"] = "needs_attention"
        elif regex_issues > 0 or js_antipatterns > 0:
            result.metadata["overall_status"] = "optimization_opportunities"
        else:
            result.metadata["overall_status"] = "healthy"
