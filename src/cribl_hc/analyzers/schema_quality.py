"""
Schema Quality Analyzer for Cribl Stream Health Check.

Analyzes schema and parsing configurations to identify:
- Parser configuration issues
- Schema mapping problems
- Field extraction quality
- Event breaker configuration
"""

from typing import Any, Dict, List, Set
from collections import defaultdict

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger


class SchemaQualityAnalyzer(BaseAnalyzer):
    """
    Analyzer for schema and parsing quality.

    Phase 10 - Data Quality & Topology

    Checks:
    - Parser library configuration and usage
    - Regex pattern complexity and performance
    - Field extraction consistency
    - Event breaker configuration
    - Schema mapping coverage
    """

    # Regex complexity thresholds
    COMPLEX_REGEX_LENGTH = 200  # Very long regex
    MULTIPLE_CAPTURE_GROUPS = 10  # Too many capture groups

    # Known problematic patterns
    PROBLEMATIC_PATTERNS = [
        (r".*", "Greedy .* can cause catastrophic backtracking"),
        (r".+", "Greedy .+ at pattern start is inefficient"),
        (r"(.+)+", "Nested quantifiers cause exponential backtracking"),
        (r"(.*)*", "Nested quantifiers cause exponential backtracking"),
    ]

    def __init__(self):
        """Initialize the schema quality analyzer."""
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "schema_quality"

    @property
    def supported_products(self) -> List[str]:
        """Schema analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Schema and parsing quality analysis, regex optimization, field extraction validation"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: parsers(1) + pipelines(1) + inputs(1) = 3.
        """
        return 3

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:parsers",
            "read:pipelines",
            "read:inputs"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform schema quality analysis.

        Args:
            client: Cribl API client

        Returns:
            AnalyzerResult with findings and recommendations
        """
        result = self.create_result()

        try:
            # Fetch parser library
            parsers = await client.get_parsers()
            result.metadata["parser_count"] = len(parsers)

            # Fetch pipelines to check parser usage
            pipelines = await client.get_pipelines()
            result.metadata["pipeline_count"] = len(pipelines)

            # Fetch inputs to check event breaker config
            inputs = await client.get_inputs()
            result.metadata["input_count"] = len(inputs)

            # Analyze parsers
            self._analyze_parsers(result, parsers, pipelines)

            # Analyze regex functions in pipelines
            self._analyze_regex_functions(result, pipelines)

            # Analyze event breakers
            self._analyze_event_breakers(result, inputs)

            # Check for schema mapping issues
            self._analyze_schema_mapping(result, pipelines)

            # Add summary finding
            self._add_summary_finding(result, parsers, pipelines, inputs)

            self.log.info(
                "schema_quality_analysis_completed",
                parser_count=len(parsers),
                pipeline_count=len(pipelines)
            )

        except Exception as e:
            self.log.error("schema_quality_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _analyze_parsers(
        self,
        result: AnalyzerResult,
        parsers: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]]
    ) -> None:
        """Analyze parser library entries."""
        # Find all parser references in pipelines
        referenced_parsers = self._find_parser_references(pipelines)

        parser_types = defaultdict(int)
        for parser in parsers:
            parser_id = parser.get("id", "unknown")
            parser_type = parser.get("type", "unknown")
            parser_types[parser_type] += 1

            # Check for regex parsers
            if parser_type in ("regex", "grok"):
                self._check_regex_parser(result, parser)

            # Check if parser is unused
            if parser_id not in referenced_parsers:
                result.add_finding(
                    Finding(
                        id=f"parser-unused-{parser_id}",
                        title=f"Unused Parser: {parser_id}",
                        description=f"Parser '{parser_id}' (type: {parser_type}) is not referenced by any pipeline.",
                        severity="info",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"parser:{parser_id}"],
                        estimated_impact="Unused parsers add clutter to configuration",
                        remediation_steps=[
                            "Verify if the parser is used by external systems",
                            "Remove unused parsers to simplify configuration"
                        ],
                        metadata={
                            "parser_id": parser_id,
                            "parser_type": parser_type
                        }
                    )
                )

        result.metadata["parser_types"] = dict(parser_types)

    def _find_parser_references(self, pipelines: List[Dict[str, Any]]) -> Set[str]:
        """Find all parser references in pipeline configurations."""
        referenced = set()

        for pipeline in pipelines:
            functions = pipeline.get("conf", {}).get("functions", [])

            for func in functions:
                func_id = func.get("id", "")
                conf = func.get("conf", {})

                # Check parser function
                if func_id == "parser":
                    parser_ref = conf.get("parserLibEntry", "") or conf.get("parser", "")
                    if parser_ref:
                        referenced.add(parser_ref)

                # Check serialize function
                if func_id == "serialize":
                    parser_ref = conf.get("parserLibEntry", "")
                    if parser_ref:
                        referenced.add(parser_ref)

        return referenced

    def _check_regex_parser(self, result: AnalyzerResult, parser: Dict[str, Any]) -> None:
        """Check regex/grok parser for potential issues."""
        parser_id = parser.get("id", "unknown")
        parser_type = parser.get("type", "regex")

        # For regex parsers, check the pattern
        if parser_type == "regex":
            pattern = parser.get("regex", "") or parser.get("pattern", "")
            if pattern:
                self._check_regex_pattern(result, parser_id, pattern, "parser")

        # For grok parsers, patterns are typically safe
        if parser_type == "grok":
            pattern = parser.get("pattern", "")
            # Grok patterns that reference custom patterns
            if pattern and "%{" in pattern:
                custom_refs = pattern.count("%{")
                if custom_refs > 10:
                    result.add_finding(
                        Finding(
                            id=f"parser-grok-complex-{parser_id}",
                            title=f"Complex Grok Pattern: {parser_id}",
                            description=f"Grok pattern in '{parser_id}' references {custom_refs} sub-patterns. "
                                       f"Consider simplifying for better performance.",
                            severity="low",
                            category="schema_quality",
                            confidence_level="medium",
                            affected_components=[f"parser:{parser_id}"],
                            estimated_impact="Complex grok patterns can slow parsing",
                            remediation_steps=[
                                "Consider breaking into multiple simpler patterns",
                                "Evaluate if all captured fields are needed"
                            ],
                            metadata={
                                "parser_id": parser_id,
                                "pattern_refs": custom_refs
                            }
                        )
                    )

    def _analyze_regex_functions(self, result: AnalyzerResult, pipelines: List[Dict[str, Any]]) -> None:
        """Analyze regex functions in pipelines for performance issues."""
        regex_function_count = 0

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])

            for func in functions:
                func_id = func.get("id", "")
                conf = func.get("conf", {})

                if func_id in ("regex_extract", "regex", "mask"):
                    regex_function_count += 1

                    # Check regex patterns
                    regex_pattern = conf.get("regex", "") or conf.get("pattern", "")
                    if regex_pattern:
                        self._check_regex_pattern(result, f"{pipeline_id}/{func_id}", regex_pattern, "pipeline")

                    # Check for multiple regex iterations
                    iterations = conf.get("iterations", 1)
                    if iterations and int(iterations) > 5:
                        result.add_finding(
                            Finding(
                                id=f"regex-high-iterations-{pipeline_id}",
                                title=f"High Regex Iterations in {pipeline_id}",
                                description=f"Regex function in '{pipeline_id}' has {iterations} iterations. "
                                           f"High iteration counts can significantly impact performance.",
                                severity="medium",
                                category="schema_quality",
                                confidence_level="high",
                                affected_components=[f"pipeline:{pipeline_id}"],
                                estimated_impact="High iteration counts multiply regex processing time",
                                remediation_steps=[
                                    "Reduce iteration count if possible",
                                    "Consider using a single comprehensive regex",
                                    "Evaluate if all iterations are necessary"
                                ],
                                metadata={
                                    "pipeline_id": pipeline_id,
                                    "iterations": iterations
                                }
                            )
                        )

        result.metadata["regex_function_count"] = regex_function_count

    def _check_regex_pattern(
        self,
        result: AnalyzerResult,
        context: str,
        pattern: str,
        source_type: str
    ) -> None:
        """Check a regex pattern for potential performance issues."""
        import re

        # Check pattern length
        if len(pattern) > self.COMPLEX_REGEX_LENGTH:
            result.add_finding(
                Finding(
                    id=f"regex-complex-length-{context.replace('/', '-')}",
                    title=f"Very Long Regex Pattern",
                    description=f"Regex pattern in '{context}' is {len(pattern)} characters. "
                               f"Very long patterns can be slow and hard to maintain.",
                    severity="low",
                    category="schema_quality",
                    confidence_level="medium",
                    affected_components=[f"{source_type}:{context}"],
                    estimated_impact="Long regex patterns can be slow to compile and execute",
                    remediation_steps=[
                        "Consider breaking into multiple simpler patterns",
                        "Evaluate if pattern can be optimized"
                    ],
                    metadata={
                        "context": context,
                        "pattern_length": len(pattern)
                    }
                )
            )

        # Count capture groups
        try:
            compiled = re.compile(pattern)
            groups = compiled.groups
            if groups > self.MULTIPLE_CAPTURE_GROUPS:
                result.add_finding(
                    Finding(
                        id=f"regex-many-groups-{context.replace('/', '-')}",
                        title=f"Many Regex Capture Groups",
                        description=f"Regex in '{context}' has {groups} capture groups. "
                                   f"Consider reducing capture groups for better performance.",
                        severity="low",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"{source_type}:{context}"],
                        estimated_impact="Many capture groups increase memory and processing overhead",
                        remediation_steps=[
                            "Use non-capturing groups (?:...) where captures aren't needed",
                            "Evaluate if all captured fields are necessary"
                        ],
                        metadata={
                            "context": context,
                            "capture_groups": groups
                        }
                    )
                )
        except re.error:
            # Invalid regex
            result.add_finding(
                Finding(
                    id=f"regex-invalid-{context.replace('/', '-')}",
                    title=f"Invalid Regex Pattern",
                    description=f"Regex pattern in '{context}' is invalid or cannot be compiled.",
                    severity="high",
                    category="schema_quality",
                    confidence_level="high",
                    affected_components=[f"{source_type}:{context}"],
                    estimated_impact="Invalid regex will cause runtime errors",
                    remediation_steps=[
                        "Fix the regex pattern syntax",
                        "Test the pattern before deploying"
                    ],
                    metadata={
                        "context": context,
                        "pattern_preview": pattern[:100] if len(pattern) > 100 else pattern
                    }
                )
            )

        # Check for problematic patterns
        for bad_pattern, reason in self.PROBLEMATIC_PATTERNS:
            if bad_pattern in pattern:
                result.add_finding(
                    Finding(
                        id=f"regex-problematic-{context.replace('/', '-')}-{hash(bad_pattern) % 10000}",
                        title=f"Potentially Slow Regex Pattern",
                        description=f"Regex in '{context}' contains '{bad_pattern}'. {reason}",
                        severity="medium",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"{source_type}:{context}"],
                        estimated_impact="Pattern can cause slow matching or backtracking",
                        remediation_steps=[
                            "Use more specific patterns instead of greedy wildcards",
                            "Consider using possessive quantifiers or atomic groups",
                            "Test pattern performance with representative data"
                        ],
                        metadata={
                            "context": context,
                            "problematic_pattern": bad_pattern,
                            "reason": reason
                        }
                    )
                )
                break  # Only report first match

    def _analyze_event_breakers(self, result: AnalyzerResult, inputs: List[Dict[str, Any]]) -> None:
        """Analyze event breaker configuration on inputs."""
        breaker_types = defaultdict(int)
        custom_breaker_count = 0

        for inp in inputs:
            input_id = inp.get("id", "unknown")
            input_type = inp.get("type", "unknown")

            # Check event breaker settings
            breaker = inp.get("breakerRulesets", []) or []
            breaker_type = inp.get("breakerType", "auto")

            breaker_types[breaker_type] += 1

            if breaker_type == "regex" or breaker:
                custom_breaker_count += 1

                # Check for overly complex breaker rules
                if len(breaker) > 5:
                    result.add_finding(
                        Finding(
                            id=f"input-many-breakers-{input_id}",
                            title=f"Many Event Breaker Rules on {input_id}",
                            description=f"Input '{input_id}' has {len(breaker)} event breaker rulesets. "
                                       f"Consider consolidating for better performance.",
                            severity="low",
                            category="schema_quality",
                            confidence_level="medium",
                            affected_components=[f"input:{input_id}"],
                            estimated_impact="Many breaker rules can slow event processing",
                            remediation_steps=[
                                "Consolidate similar breaking rules",
                                "Evaluate if all rules are necessary"
                            ],
                            metadata={
                                "input_id": input_id,
                                "breaker_count": len(breaker)
                            }
                        )
                    )

        result.metadata["event_breaker_types"] = dict(breaker_types)
        result.metadata["custom_breaker_count"] = custom_breaker_count

    def _analyze_schema_mapping(self, result: AnalyzerResult, pipelines: List[Dict[str, Any]]) -> None:
        """Analyze schema mapping and field renaming patterns."""
        rename_patterns = defaultdict(int)
        eval_field_count = 0

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])

            for func in functions:
                func_id = func.get("id", "")
                conf = func.get("conf", {})

                # Check rename function
                if func_id == "rename":
                    fields = conf.get("fields", [])
                    for field in fields:
                        old_name = field.get("inFieldName", "")
                        new_name = field.get("outFieldName", "")
                        if old_name and new_name:
                            rename_patterns[f"{old_name}->{new_name}"] += 1

                # Check eval function for field creation
                if func_id == "eval":
                    add_fields = conf.get("add", []) or []
                    eval_field_count += len(add_fields)

        result.metadata["rename_patterns"] = len(rename_patterns)
        result.metadata["eval_field_creations"] = eval_field_count

        # Check for duplicate rename patterns across pipelines
        duplicates = {k: v for k, v in rename_patterns.items() if v > 3}
        if duplicates:
            result.add_finding(
                Finding(
                    id="schema-duplicate-renames",
                    title="Duplicate Field Renames Across Pipelines",
                    description=f"Found {len(duplicates)} field rename patterns used in multiple pipelines. "
                               f"Consider using a shared pack for common transformations.",
                    severity="info",
                    category="schema_quality",
                    confidence_level="medium",
                    affected_components=["schema:renames"],
                    estimated_impact="Duplicate logic increases maintenance burden",
                    remediation_steps=[
                        "Consolidate common field renames into a shared pack",
                        "Use pre-processing pipelines for common transformations"
                    ],
                    metadata={
                        "duplicate_patterns": dict(duplicates)
                    }
                )
            )

    def _add_summary_finding(
        self,
        result: AnalyzerResult,
        parsers: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]]
    ) -> None:
        """Add summary finding for schema quality."""
        issues = len([f for f in result.findings if f.severity in ("high", "critical", "medium")])

        if issues == 0:
            severity = "info"
            status = "Good"
            description = f"Schema configuration is healthy. {len(parsers)} parsers, {len(pipelines)} pipelines analyzed."
        elif issues <= 3:
            severity = "medium"
            status = "Minor Issues"
            description = f"Found {issues} schema/parsing issue(s). Review recommendations for optimization."
        else:
            severity = "high"
            status = "Needs Attention"
            description = f"Found {issues} schema/parsing issue(s). Schema optimization recommended."

        result.add_finding(
            Finding(
                id="schema-quality-summary",
                title=f"Schema Quality: {status}",
                description=description,
                severity=severity,
                category="schema_quality",
                confidence_level="high",
                affected_components=["schema:summary"],
                estimated_impact=f"Analyzed {len(parsers)} parsers across {len(pipelines)} pipelines",
                remediation_steps=[] if severity == "info" else ["Review schema quality findings"],
                metadata={
                    "parser_count": len(parsers),
                    "pipeline_count": len(pipelines),
                    "input_count": len(inputs),
                    "issue_count": issues
                }
            )
        )
