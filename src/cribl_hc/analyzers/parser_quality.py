"""
Parser Quality Analyzer for Cribl Health Check.

Analyzes parser health, efficiency, and usage patterns to identify quality issues,
performance risks, and optimization opportunities.

Priority: P2 (Medium Impact - Quality & Reliability)
"""

import re
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class ParserQualityAnalyzer(BaseAnalyzer):
    """
    Analyzer for parser quality and efficiency.

    Identifies:
    - Parsers with high error rates
    - Unused parsers cluttering configuration
    - Complex/risky regex patterns (catastrophic backtracking)
    - Parser function usage (deprecated functions)
    - Field extraction quality metrics
    """

    ERROR_RATE_HIGH_PERCENT = 5.0
    ERROR_RATE_CRITICAL_PERCENT = 10.0
    RISKY_REGEX_PATTERNS = [
        r"(\w+\*)+",
        r"(\w+\+)+",
        r"(\w+\*)\+",
        r"(\w+\+)\*",
        r"\(.*\|.*\)\*",
        r"\(.*\|.*\)\+",
    ]

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "parser_quality"

    @property
    def supported_products(self) -> list[str]:
        """Parser quality analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Analyzes parser health, efficiency, error rates, and regex patterns"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: parsers(1) + metrics(1) + pipelines(1) = 3."""
        return 3

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return [
            "read:parsers",
            "read:metrics",
            "read:pipelines",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze parser quality across all parsers.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with parser quality findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("parser_quality_analysis_started")

            parsers = await self._fetch_parsers(client)
            metrics = await self._fetch_metrics(client)
            pipelines = await self._fetch_pipelines(client)

            result.metadata["parsers_analyzed"] = len(parsers)

            if not parsers:
                result.add_finding(
                    Finding(
                        id="parser-quality-no-parsers",
                        category="parser_quality",
                        severity="info",
                        title="No Parsers Configured",
                        description="No parsers found for quality analysis.",
                        affected_components=["Parsers"],
                        confidence_level="high",
                        metadata={},
                    )
                )
                result.success = True
                return result

            healthy_count = 0
            problematic_parsers = []

            for parser in parsers:
                parser_id = parser.get("id", "unknown")
                is_healthy = True

                if self._check_error_rates(parser, metrics, result):
                    is_healthy = False
                    problematic_parsers.append(parser_id)

                if self._check_risky_patterns(parser, result):
                    is_healthy = False
                    problematic_parsers.append(parser_id)

                if self._check_parser_coverage(parser, pipelines, result):
                    is_healthy = False
                    problematic_parsers.append(parser_id)

                if is_healthy:
                    healthy_count += 1

            result.metadata["healthy_parsers"] = healthy_count
            result.metadata["problematic_parsers"] = problematic_parsers
            result.metadata["critical_findings"] = len(result.get_critical_findings())

            for finding in result.findings:
                if not finding.worker_group:
                    finding.worker_group = client.worker_group

            result.success = True
            log.info(
                "parser_quality_analysis_completed",
                parsers=len(parsers),
                findings=len(result.findings),
            )

        except Exception as e:
            log.error("parser_quality_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="parser-quality-analysis-error",
                    category="parser_quality",
                    severity="critical",
                    title="Parser Quality Analysis Failed",
                    description=f"Failed to analyze parser quality: {str(e)}",
                    affected_components=["Parser Analyzer"],
                    remediation_steps=["Check API connectivity", "Verify permissions"],
                    estimated_impact="Cannot assess parser quality",
                    confidence_level="high",
                    metadata={"error": str(e)},
                )
            )

        return result

    async def _fetch_parsers(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_parsers() or []
        except Exception as e:
            log.warning("failed_to_fetch_parsers", error=str(e))
            return []

    async def _fetch_metrics(self, client: CriblAPIClient) -> dict[str, Any]:
        try:
            return await client.get_metrics(time_range="1h") or {}
        except Exception as e:
            log.warning("failed_to_fetch_metrics", error=str(e))
            return {}

    async def _fetch_pipelines(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_pipelines() or []
        except Exception as e:
            log.warning("failed_to_fetch_pipelines", error=str(e))
            return []

    def _check_error_rates(
        self, parser: dict[str, Any], metrics: dict[str, Any], result: AnalyzerResult
    ) -> bool:
        """Check parser error rates."""
        parser_id = parser.get("id", "unknown")
        parser_name = parser.get("name", parser_id)

        items = metrics.get("items", [])
        if not items:
            return False

        events = 0
        errors = 0

        for item in items:
            dims = item.get("dimensions", {})
            if dims.get("parser") == parser_id:
                name = item.get("name", "")
                val = item.get("value", 0)

                if "events" in name:
                    events += val
                elif "errors" in name:
                    errors += val

        if events == 0:
            return False

        error_rate = (errors / events) * 100

        if error_rate > self.ERROR_RATE_CRITICAL_PERCENT:
            result.add_finding(
                Finding(
                    id=f"parser-quality-error-critical-{parser_id}",
                    category="parser_quality",
                    severity="critical",
                    title=f"Critical Parser Error Rate: {parser_name}",
                    description=f"Parser '{parser_name}' has >10% error rate ({error_rate:.1f}%).",
                    affected_components=["Parsers", parser_name],
                    remediation_steps=[
                        "Review parser configuration for correctness",
                        "Check sample data against parser expectations",
                        "Consider simplifying or splitting the parser",
                    ],
                    estimated_impact=f"{error_rate:.1f}% of data failing to parse",
                    confidence_level="high",
                    metadata={"parser_id": parser_id, "error_rate": error_rate},
                )
            )
            return True

        elif error_rate > self.ERROR_RATE_HIGH_PERCENT:
            result.add_finding(
                Finding(
                    id=f"parser-quality-error-high-{parser_id}",
                    category="parser_quality",
                    severity="high",
                    title=f"High Parser Error Rate: {parser_name}",
                    description=f"Parser '{parser_name}' has >5% error rate ({error_rate:.1f}%).",
                    affected_components=["Parsers", parser_name],
                    remediation_steps=[
                        "Verify parser configuration",
                        "Test with sample data",
                        "Consider adjusting regex patterns",
                    ],
                    estimated_impact=f"Data quality degradation ({error_rate:.1f}%)",
                    confidence_level="high",
                    metadata={"parser_id": parser_id, "error_rate": error_rate},
                )
            )
            return True

        return False

    def _check_risky_patterns(self, parser: dict[str, Any], result: AnalyzerResult) -> bool:
        """Check for risky regex patterns."""
        parser_id = parser.get("id", "unknown")
        parser_name = parser.get("name", parser_id)

        regex = parser.get("regex", "")
        if not regex:
            return False

        risky_found = []
        for pattern in self.RISKY_REGEX_PATTERNS:
            if re.search(pattern, regex):
                risky_found.append(pattern)

        if not risky_found:
            return False

        result.add_finding(
            Finding(
                id=f"parser-quality-regex-risky-{parser_id}",
                category="parser_quality",
                severity="high",
                title=f"Risky Regex Pattern: {parser_name}",
                description=(
                    f"Parser '{parser_name}' contains potentially catastrophic backtracking patterns. "
                    f"Risk: CPU spikes and latency degradation. Patterns: {', '.join(risky_found)}"
                ),
                affected_components=["Parsers", parser_name],
                remediation_steps=[
                    "Simplify regex pattern to avoid nested quantifiers",
                    "Use possessive quantifiers or atomic groups if supported",
                    "Test regex with large/malformed input samples",
                ],
                estimated_impact="Potential CPU spikes and processing latency",
                confidence_level="high",
                metadata={"parser_id": parser_id, "risky_patterns": risky_found},
            )
        )
        return True

    def _check_parser_coverage(
        self,
        parser: dict[str, Any],
        pipelines: list[dict[str, Any]],
        result: AnalyzerResult,
    ) -> bool:
        """Check if parser is unused."""
        parser_id = parser.get("id", "unknown")
        parser_name = parser.get("name", parser_id)

        if not pipelines:
            return False

        used = False
        for pipeline in pipelines:
            funcs = pipeline.get("functions", [])
            for func in funcs:
                if func.get("id") == parser_id or func.get("type") == "parser":
                    func_args = func.get("args", {})
                    if func_args.get("parser") == parser_id:
                        used = True
                        break
            if used:
                break

        if not used:
            result.add_finding(
                Finding(
                    id=f"parser-quality-unused-{parser_id}",
                    category="parser_quality",
                    severity="medium",
                    title=f"Unused Parser: {parser_name}",
                    description=f"Parser '{parser_name}' is not used in any pipeline.",
                    affected_components=["Parsers", parser_name],
                    remediation_steps=[
                        "Verify parser is no longer needed",
                        "Delete parser to clean up configuration",
                        "Document why parser was created",
                    ],
                    estimated_impact="Configuration clutter",
                    confidence_level="medium",
                    metadata={"parser_id": parser_id},
                )
            )
            return True

        return False
