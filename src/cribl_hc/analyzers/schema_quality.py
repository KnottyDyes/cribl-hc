"""
Schema Quality Analyzer for Cribl Health Check.

Analyzes schema and parsing configurations to identify:
- Parser configuration issues
- Schema mapping problems
- Field extraction quality
- Event breaker configuration
- Search datatypes and field quality
"""

from collections import defaultdict
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


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
    - Search datatypes and schema field quality
    """

    COMPLEX_REGEX_LENGTH = 200
    MULTIPLE_CAPTURE_GROUPS = 10

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
    def supported_products(self) -> list[str]:
        """Schema analyzer applies to Stream, Edge, and Search."""
        return ["stream", "edge", "search"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return (
            "Schema and parsing quality analysis, regex optimization, field extraction validation"
        )

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: parsers(1) + pipelines(1) + inputs(1) + search_datatypes(1) = 4.
        """
        return 4

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:parsers", "read:pipelines", "read:inputs", "read:search:datatypes"]

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
            # Fetch common data
            parsers = await client.get_parsers()
            pipelines = await client.get_pipelines()
            inputs = await client.get_inputs()

            result.metadata.update(
                {
                    "parser_count": len(parsers),
                    "pipeline_count": len(pipelines),
                    "input_count": len(inputs),
                }
            )

            # Analyze Stream/Edge components
            self._analyze_parsers(result, parsers, pipelines)
            self._analyze_regex_functions(result, pipelines)
            self._analyze_event_breakers(result, inputs)
            self._analyze_schema_mapping(result, pipelines)

            # Analyze Search datatypes if applicable
            if "search" in self.supported_products:
                try:
                    datatypes_response = await client.get_search_datatypes()
                    datatypes = datatypes_response.get("items", [])
                    self._analyze_search_datatypes(result, datatypes)
                    result.metadata["search_datatype_count"] = len(datatypes)
                except Exception as e:
                    self.log.warning("failed_to_fetch_search_datatypes", error=str(e))

            # Add summary finding
            self._add_summary_finding(result, parsers, pipelines, inputs)

            self.log.info(
                "schema_quality_analysis_completed",
                parser_count=len(parsers),
                pipeline_count=len(pipelines),
            )

        except Exception as e:
            self.log.error("schema_quality_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)

        return result

    def _analyze_parsers(
        self, result: AnalyzerResult, parsers: list[dict[str, Any]], pipelines: list[dict[str, Any]]
    ) -> None:
        """Analyze parser library entries."""
        referenced_parsers = self._find_parser_references(pipelines)

        parser_types = defaultdict(int)
        for parser in parsers:
            parser_id = parser.get("id", "unknown")
            parser_type = parser.get("type", "unknown")
            parser_types[parser_type] += 1

            if parser_type in ("regex", "grok"):
                self._check_regex_parser(result, parser)

            if parser_id not in referenced_parsers:
                result.add_finding(
                    self.create_finding(
                        id=f"parser-unused-{parser_id}",
                        title=f"Unused Parser: {parser_id}",
                        description=f"Parser '{parser_id}' is not referenced by any pipeline.",
                        severity="info",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"parser:{parser_id}"],
                        metadata={"parser_id": parser_id, "parser_type": parser_type},
                    )
                )

        result.metadata["parser_types"] = dict(parser_types)

    def _find_parser_references(self, pipelines: list[dict[str, Any]]) -> set[str]:
        """Find all parser references in pipeline configurations."""
        referenced = set()

        for pipeline in pipelines:
            functions = pipeline.get("conf", {}).get("functions", [])
            for func in functions:
                func_id = func.get("id", "")
                conf = func.get("conf", {})

                if func_id == "parser":
                    parser_ref = conf.get("parserLibEntry", "") or conf.get("parser", "")
                    if parser_ref:
                        referenced.add(parser_ref)

                if func_id == "serialize":
                    parser_ref = conf.get("parserLibEntry", "")
                    if parser_ref:
                        referenced.add(parser_ref)

        return referenced

    def _check_regex_parser(self, result: AnalyzerResult, parser: dict[str, Any]) -> None:
        """Check regex/grok parser for potential issues."""
        parser_id = parser.get("id", "unknown")
        parser_type = parser.get("type", "regex")

        if parser_type == "regex":
            pattern = parser.get("regex", "") or parser.get("pattern", "")
            if pattern:
                self._check_regex_pattern(result, parser_id, pattern, "parser")

        if parser_type == "grok":
            pattern = parser.get("pattern", "")
            if pattern and "%{" in pattern:
                custom_refs = pattern.count("%{")
                if custom_refs > 10:
                    result.add_finding(
                        self.create_finding(
                            id=f"parser-grok-complex-{parser_id}",
                            title=f"Complex Grok Pattern: {parser_id}",
                            description=f"Grok pattern in '{parser_id}' references {custom_refs} sub-patterns.",
                            severity="low",
                            category="schema_quality",
                            confidence_level="medium",
                            affected_components=[f"parser:{parser_id}"],
                            metadata={"parser_id": parser_id, "pattern_refs": custom_refs},
                        )
                    )

    def _analyze_regex_functions(
        self, result: AnalyzerResult, pipelines: list[dict[str, Any]]
    ) -> None:
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
                    regex_pattern = conf.get("regex", "") or conf.get("pattern", "")
                    if regex_pattern:
                        self._check_regex_pattern(
                            result, f"{pipeline_id}/{func_id}", regex_pattern, "pipeline"
                        )

                    iterations = conf.get("iterations", 1)
                    if iterations and int(iterations) > 5:
                        result.add_finding(
                            self.create_finding(
                                id=f"regex-high-iterations-{pipeline_id}",
                                title=f"High Regex Iterations in {pipeline_id}",
                                description=f"Regex function in '{pipeline_id}' has {iterations} iterations, which may impact performance.",
                                severity="medium",
                                category="schema_quality",
                                confidence_level="high",
                                affected_components=[f"pipeline:{pipeline_id}"],
                                remediation_steps=[
                                    f"Review regex function in pipeline '{pipeline_id}'",
                                    "Consider reducing iterations to 5 or fewer",
                                    "Optimize regex patterns to be more specific",
                                    "Test performance after reducing iterations",
                                ],
                                metadata={"pipeline_id": pipeline_id, "iterations": iterations},
                            )
                        )

        result.metadata["regex_function_count"] = regex_function_count

    def _check_regex_pattern(
        self, result: AnalyzerResult, context: str, pattern: str, source_type: str
    ) -> None:
        """Check a regex pattern for potential performance issues."""
        import re

        if len(pattern) > self.COMPLEX_REGEX_LENGTH:
            result.add_finding(
                self.create_finding(
                    id=f"regex-complex-length-{context.replace('/', '-')}",
                    title="Very Long Regex Pattern",
                    description=f"Regex pattern in '{context}' is {len(pattern)} characters.",
                    severity="low",
                    category="schema_quality",
                    confidence_level="medium",
                    affected_components=[f"{source_type}:{context}"],
                    metadata={"context": context, "pattern_length": len(pattern)},
                )
            )

        try:
            compiled = re.compile(pattern)
            groups = compiled.groups
            if groups > self.MULTIPLE_CAPTURE_GROUPS:
                result.add_finding(
                    self.create_finding(
                        id=f"regex-many-groups-{context.replace('/', '-')}",
                        title="Many Regex Capture Groups",
                        description=f"Regex in '{context}' has {groups} capture groups.",
                        severity="low",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"{source_type}:{context}"],
                        metadata={"context": context, "capture_groups": groups},
                    )
                )
        except re.error:
            result.add_finding(
                self.create_finding(
                    id=f"regex-invalid-{context.replace('/', '-')}",
                    title="Invalid Regex Pattern",
                    description=f"Regex pattern in '{context}' is invalid.",
                    severity="high",
                    category="schema_quality",
                    confidence_level="high",
                    affected_components=[f"{source_type}:{context}"],
                    metadata={
                        "context": context,
                        "pattern_preview": pattern[:100] if len(pattern) > 100 else pattern,
                    },
                )
            )

        for bad_pattern, reason in self.PROBLEMATIC_PATTERNS:
            if bad_pattern in pattern:
                result.add_finding(
                    self.create_finding(
                        id=f"regex-problematic-{context.replace('/', '-')}-{hash(bad_pattern) % 10000}",
                        title="Potentially Slow Regex Pattern",
                        description=f"Regex in '{context}' contains '{bad_pattern}'. {reason}",
                        severity="medium",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"{source_type}:{context}"],
                        metadata={"context": context, "problematic_pattern": bad_pattern},
                    )
                )
                break

    def _analyze_event_breakers(self, result: AnalyzerResult, inputs: list[dict[str, Any]]) -> None:
        """Analyze event breaker configuration on inputs."""
        breaker_types = defaultdict(int)
        custom_breaker_count = 0

        for inp in inputs:
            input_id = inp.get("id", "unknown")
            breaker = inp.get("breakerRulesets", []) or []
            breaker_type = inp.get("breakerType", "auto")
            breaker_types[breaker_type] += 1

            if breaker_type == "regex" or breaker:
                custom_breaker_count += 1
                if len(breaker) > 5:
                    result.add_finding(
                        self.create_finding(
                            id=f"input-many-breakers-{input_id}",
                            title=f"Many Event Breaker Rules on {input_id}",
                            description=f"Input '{input_id}' has {len(breaker)} event breaker rulesets.",
                            severity="low",
                            category="schema_quality",
                            confidence_level="medium",
                            affected_components=[f"input:{input_id}"],
                            metadata={"input_id": input_id, "breaker_count": len(breaker)},
                        )
                    )

        result.metadata["event_breaker_types"] = dict(breaker_types)
        result.metadata["custom_breaker_count"] = custom_breaker_count

    def _analyze_schema_mapping(
        self, result: AnalyzerResult, pipelines: list[dict[str, Any]]
    ) -> None:
        """Analyze schema mapping and field renaming patterns."""
        rename_patterns = defaultdict(int)
        eval_field_count = 0

        for pipeline in pipelines:
            functions = pipeline.get("conf", {}).get("functions", [])
            for func in functions:
                func_id = func.get("id", "")
                conf = func.get("conf", {})

                if func_id == "rename":
                    fields = conf.get("fields", [])
                    for field in fields:
                        old_name = field.get("inFieldName", "")
                        new_name = field.get("outFieldName", "")
                        if old_name and new_name:
                            rename_patterns[f"{old_name}->{new_name}"] += 1

                if func_id == "eval":
                    add_fields = conf.get("add", []) or []
                    eval_field_count += len(add_fields)

        result.metadata["rename_patterns"] = len(rename_patterns)
        result.metadata["eval_field_creations"] = eval_field_count

        duplicates = {k: v for k, v in rename_patterns.items() if v > 3}
        if duplicates:
            result.add_finding(
                self.create_finding(
                    id="schema-duplicate-renames",
                    title="Duplicate Field Renames Across Pipelines",
                    description=f"Found {len(duplicates)} field rename patterns used in multiple pipelines.",
                    severity="info",
                    category="schema_quality",
                    confidence_level="medium",
                    affected_components=["schema:renames"],
                    metadata={"duplicate_patterns": dict(duplicates)},
                )
            )

    def _analyze_search_datatypes(
        self, result: AnalyzerResult, datatypes: list[dict[str, Any]]
    ) -> None:
        """Analyze Search datatypes and field quality."""
        if not datatypes:
            return

        for dtype in datatypes:
            dtype_id = dtype.get("id", "unknown")
            fields = dtype.get("fields", [])

            if not fields:
                result.add_finding(
                    self.create_finding(
                        id=f"search-datatype-no-fields-{dtype_id}",
                        title=f"Search Datatype Without Fields: {dtype_id}",
                        description=f"Datatype '{dtype_id}' has no fields defined, which may impact search quality.",
                        severity="medium",
                        category="schema_quality",
                        confidence_level="high",
                        affected_components=[f"search:datatype:{dtype_id}"],
                        remediation_steps=[
                            f"Navigate to Search > Datatypes > {dtype_id}",
                            "Add appropriate field definitions for structured searching",
                            "Consider common fields like timestamp, source, sourcetype",
                            "Test search functionality after adding fields",
                        ],
                        metadata={"datatype_id": dtype_id},
                    )
                )

            many_fields_threshold = 100
            if len(fields) > many_fields_threshold:
                result.add_finding(
                    self.create_finding(
                        id=f"search-datatype-many-fields-{dtype_id}",
                        title=f"Large Number of Fields in Datatype: {dtype_id}",
                        description=f"Datatype '{dtype_id}' has {len(fields)} fields. High field counts can impact Search performance.",
                        severity="low",
                        category="schema_quality",
                        confidence_level="medium",
                        affected_components=[f"search:datatype:{dtype_id}"],
                        metadata={"datatype_id": dtype_id, "field_count": len(fields)},
                    )
                )

    def _add_summary_finding(
        self,
        result: AnalyzerResult,
        parsers: list[dict[str, Any]],
        pipelines: list[dict[str, Any]],
        inputs: list[dict[str, Any]],
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
            description = f"Found {issues} schema/parsing issue(s)."
        else:
            severity = "high"
            status = "Needs Attention"
            description = f"Found {issues} schema/parsing issue(s)."

        result.add_finding(
            self.create_finding(
                id="schema-quality-summary",
                title=f"Schema Quality: {status}",
                description=description,
                severity=severity,
                category="schema_quality",
                confidence_level="high",
                affected_components=["schema:summary"],
                metadata={
                    "parser_count": len(parsers),
                    "pipeline_count": len(pipelines),
                    "input_count": len(inputs),
                    "issue_count": issues,
                },
            )
        )
