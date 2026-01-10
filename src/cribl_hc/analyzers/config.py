"""
Configuration Analyzer for Cribl Stream Health Check.

Validates pipelines, routes, and configurations to detect errors and best practice violations.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.rules.loader import RuleEvaluator, RuleLoader

log = structlog.get_logger(__name__)


class ConfigAnalyzer(BaseAnalyzer):
    DEPRECATED_FUNCTIONS = {
        "regex": {
            "replacement": "regex_extract",
            "reason": "regex_extract provides better performance and clearer syntax",
            "docs": "https://docs.cribl.io/stream/regex-extract-function/",
        },
        "code": {
            "replacement": "eval",
            "reason": "eval function is the modern replacement with better performance",
            "docs": "https://docs.cribl.io/stream/eval-function/",
        },
    }

    CREDENTIAL_PATTERNS = [
        r'"password"\s*:\s*"([^"$][^"]{2,})"',
        r'"token"\s*:\s*"([^"$][^"]{2,})"',
        r'"secret"\s*:\s*"([^"$][^"]{2,})"',
        r'"api[_-]?key"\s*:\s*"([^"$][^"]{2,})"',
        r'"auth"\s*:\s*"([^"$][^"]{2,})"',
    ]

    def __init__(self):
        super().__init__()
        self.log = structlog.get_logger(__name__)
        self.rule_loader = RuleLoader()
        self.rule_evaluator = RuleEvaluator()
        self._rules_cache = None
        self._current_worker_group: str | None = "default"

    @property
    def objective_name(self) -> str:
        return "config"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_estimated_api_calls(self) -> int:
        return 5

    def get_required_permissions(self) -> list[str]:
        return ["read:pipelines", "read:routes", "read:inputs", "read:outputs"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()
        self._current_worker_group = client.worker_group
        try:
            pipelines = await self._fetch_pipelines(client)
            routes_objects = await self._fetch_routes(client)
            routes = self._flatten_routes(routes_objects)
            inputs = await self._fetch_inputs(client)
            outputs = await self._fetch_outputs(client)

            result.metadata["product_type"] = client.product_type
            result.metadata["worker_group"] = self._current_worker_group

            self._validate_pipeline_syntax(pipelines, result, client)
            self._validate_route_configuration(routes, pipelines, result, client)
            self._check_deprecated_functions(pipelines, result, client)
            self._find_unused_components(pipelines, routes, inputs, outputs, result, client)
            self._check_security_misconfigurations(outputs, result, client)
            self._evaluate_best_practice_rules(pipelines, routes, inputs, outputs, result, client)
            self._analyze_route_conflicts(routes, pipelines, result, client)
            self._analyze_complexity_metrics(pipelines, result, client)
            await self._check_advanced_security(pipelines, result, client)

            compliance_score = self._calculate_compliance_score(result)
            self._generate_recommendations(result)

            result.metadata.update(
                {
                    "pipelines_analyzed": len(pipelines),
                    "routes_analyzed": len(routes),
                    "inputs_analyzed": len(inputs),
                    "outputs_analyzed": len(outputs),
                    "compliance_score": compliance_score,
                }
            )
        except Exception as e:
            self.log.error("config_analysis_failed", error=str(e), exc_info=True)
            result.success = True
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="config-analysis-error",
                    grouping_id="config-analysis-error",
                    category="config",
                    severity="high",
                    title="Configuration Analysis Error",
                    description=f"Failed to complete configuration analysis: {str(e)}",
                    affected_components=["configuration"],
                    confidence_level="high",
                    estimated_impact="Configuration issues may go undetected without proper analysis.",
                    remediation_steps=[
                        "Check API connectivity and permissions.",
                        "Verify configuration endpoints are accessible.",
                        "Review logs for specific error details.",
                        "Contact support if issue persists.",
                    ],
                )
            )
        return result

    async def _fetch_pipelines(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_pipelines() or []
        except Exception:
            return []

    async def _fetch_routes(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_routes() or []
        except Exception:
            return []

    async def _fetch_inputs(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_inputs() or []
        except Exception:
            return []

    async def _fetch_outputs(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_outputs() or []
        except Exception:
            return []

    def _flatten_routes(self, routes_objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Flatten Routes objects to individual routes.

        The Cribl API returns Routes objects (routing tables) which contain nested routes.
        This method extracts all individual routes from all Routes objects.

        Args:
            routes_objects: List of Routes objects from API

        Returns:
            Flat list of individual route configurations
        """
        flattened = []
        for routes_obj in routes_objects:
            # Each Routes object has a 'routes' array containing individual routes
            nested_routes = routes_obj.get("routes", [])
            if isinstance(nested_routes, list):
                flattened.extend(nested_routes)
            # If routes_obj IS a route (backward compatibility), add it directly
            elif routes_obj.get("filter") or routes_obj.get("pipeline"):
                flattened.append(routes_obj)
        return flattened

    def _validate_pipeline_syntax(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            if not pipeline.get("id"):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-syntax-missing-id-{hash(str(pipeline))}",
                        grouping_id="config-syntax-missing-id",
                        category="config",
                        severity="critical",
                        title="Pipeline Missing Required 'id' Field",
                        description="Pipeline configuration is missing required 'id' field.",
                        affected_components=["pipeline-unknown"],
                        confidence_level="high",
                        estimated_impact="This pipeline cannot be referenced and may cause deployment failures.",
                        remediation_steps=["Edit the pipeline JSON to add a unique 'id' field."],
                    )
                )
                continue
            functions = pipeline.get("functions") or pipeline.get("conf", {}).get("functions")
            if functions is None:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-syntax-{pipeline_id}-missing-functions",
                        grouping_id="config-syntax-missing-functions",
                        category="config",
                        severity="high",
                        title=f"Pipeline Missing 'functions' Field: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' is missing required 'functions' field.",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        confidence_level="high",
                        estimated_impact="Pipeline cannot process data without function definitions.",
                        remediation_steps=[
                            f"Edit pipeline '{pipeline_id}' to add 'functions' array.",
                            "Define at least one function to process data.",
                            "Test pipeline after adding functions.",
                        ],
                    )
                )
                continue
            if not isinstance(functions, list):
                continue
            for func_idx, function in enumerate(functions):
                if not isinstance(function, dict):
                    continue
                if not function.get("id"):
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-syntax-{pipeline_id}-func-{func_idx}-missing-id",
                            grouping_id="config-syntax-func-missing-id",
                            category="config",
                            severity="medium",
                            title=f"Function Missing 'id' Field: {pipeline_id}",
                            description=f"Function at index {func_idx} in pipeline '{pipeline_id}' is missing 'id' field.",
                            affected_components=[f"pipeline-{pipeline_id}"],
                            confidence_level="high",
                            remediation_steps=[
                                f"Edit pipeline '{pipeline_id}' and add unique 'id' field to function at index {func_idx}.",
                                "Ensure all functions in pipeline have unique identifiers.",
                                "Test pipeline after adding missing IDs.",
                            ],
                        )
                    )

    def _validate_route_configuration(
        self,
        routes: list[dict[str, Any]],
        pipelines: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        valid_pipeline_ids = {str(p.get("id")) for p in pipelines if p.get("id")}
        for route in routes:
            route_id = route.get("id", "unknown")
            pipeline_ref = route.get("pipeline")
            if pipeline_ref and str(pipeline_ref) not in valid_pipeline_ids:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-orphaned-route-{route_id}",
                        grouping_id="config-orphaned-route",
                        category="config",
                        severity="high",
                        title=f"Route References Non-Existent Pipeline: {route_id}",
                        description=f"Route '{route_id}' references pipeline '{pipeline_ref}' which does not exist.",
                        affected_components=[f"route-{route_id}", f"pipeline-{pipeline_ref}"],
                        confidence_level="high",
                        estimated_impact="Route will not process data and may cause processing errors.",
                        remediation_steps=[
                            f"Create the missing pipeline '{pipeline_ref}' that route '{route_id}' references.",
                            f"Or update route '{route_id}' to reference an existing pipeline.",
                            "Verify data flow after fixing the reference.",
                        ],
                    )
                )

    def _check_deprecated_functions(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("functions") or pipeline.get("conf", {}).get("functions") or []
            for func_idx, function in enumerate(functions):
                if not isinstance(function, dict):
                    continue
                func_id = function.get("id", "unknown")
                if func_id in self.DEPRECATED_FUNCTIONS:
                    deprecated_info = self.DEPRECATED_FUNCTIONS[func_id]
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-deprecated-{pipeline_id}-{func_idx}",
                            grouping_id="config-deprecated-function",
                            category="config",
                            severity="medium",
                            title=f"Deprecated Function '{func_id}' in Pipeline: {pipeline_id}",
                            description=f"Pipeline '{pipeline_id}' uses deprecated function '{func_id}'. {deprecated_info['reason']}",
                            affected_components=[f"pipeline-{pipeline_id}", f"function-{func_id}"],
                            confidence_level="high",
                            remediation_steps=[
                                f"Replace deprecated function '{func_id}' with '{deprecated_info['replacement']}' in pipeline '{pipeline_id}'.",
                                f"Update function configuration to use the modern syntax.",
                                f"Test pipeline functionality after replacement.",
                                f"Review documentation: {deprecated_info['docs']}",
                            ],
                        )
                    )

    def _find_unused_components(
        self,
        pipelines: list[dict[str, Any]],
        routes: list[dict[str, Any]],
        inputs: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        all_pipeline_ids = {str(p.get("id")) for p in pipelines if p.get("id")}
        all_output_ids = {str(o.get("id")) for o in outputs if o.get("id")}
        used_pipeline_ids: set[str] = set()
        used_output_ids: set[str] = set()
        for route in routes:
            if pipeline_ref := route.get("pipeline"):
                used_pipeline_ids.add(str(pipeline_ref))
            if output_ref := route.get("output"):
                used_output_ids.add(str(output_ref))

        unused_pipelines = all_pipeline_ids - used_pipeline_ids

        for pipeline_id in sorted(list(unused_pipelines)):
            if pipeline_id.startswith("pack:"):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-unused-pack-pipeline-{pipeline_id}",
                        grouping_id="config-unused-pack-pipeline",
                        category="config",
                        severity="info",
                        title=f"Unused Pack Pipeline: {pipeline_id}",
                        description=f"Pack pipeline '{pipeline_id}' is installed but not referenced by any route. Pack pipelines may be available for use but are not currently active.",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        confidence_level="high",
                        estimated_impact="No impact if pack is intentionally unused. May indicate incomplete pack configuration.",
                        remediation_steps=[
                            f"If pack '{pipeline_id}' should be active, add routes to reference it",
                            "If pack is not needed, consider removing it to reduce clutter",
                            "Verify pack documentation for correct usage",
                        ],
                    )
                )
            else:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-unreferenced-pipeline-{pipeline_id}",
                        grouping_id="config-unreferenced-pipeline",
                        category="config",
                        severity="low",
                        title=f"Unreferenced Pipeline Configuration: {pipeline_id}",
                        description=f"Pipeline configuration '{pipeline_id}' exists but is not referenced by any route. This pipeline configuration is defined but not in use.",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        confidence_level="high",
                        estimated_impact="Configuration clutter and potential confusion. May slow down configuration searches.",
                        remediation_steps=[
                            f"If pipeline '{pipeline_id}' is intended for future use, document its purpose",
                            "If pipeline is obsolete, remove the configuration to reduce clutter",
                            "Consider adding to a route if pipeline should be active",
                        ],
                    )
                )

        unused_outputs = all_output_ids - used_output_ids
        for output_id in sorted(list(unused_outputs)):
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"config-unused-output-{output_id}",
                    grouping_id="config-unused-output",
                    category="config",
                    severity="low",
                    title=f"Unused Output: {output_id}",
                    description=f"Output '{output_id}' is not referenced by any route.",
                    affected_components=[f"output-{output_id}"],
                    confidence_level="medium",
                )
            )

    def _check_security_misconfigurations(
        self, outputs: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        for output in outputs:
            output_id = output.get("id", "unknown")
            output_type = output.get("type", "unknown")
            output_json = json.dumps(output)
            for pattern in self.CREDENTIAL_PATTERNS:
                matches = re.finditer(pattern, output_json, re.IGNORECASE)
                for match in matches:
                    credential_key = match.group(0).split('"')[1]
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-security-hardcoded-{output_id}-{hash(match.group(0))}",
                            grouping_id="config-security-hardcoded",
                            category="config",
                            severity="high",
                            title=f"Hardcoded Credential in Output: {output_id}",
                            description=f"Output '{output_id}' contains hardcoded field '{credential_key}'.",
                            affected_components=[f"output-{output_id}"],
                            confidence_level="high",
                            estimated_impact="Hardcoded credentials can be exposed in version control or backups.",
                            remediation_steps=[
                                "Replace the hardcoded value with an environment variable or secret from a secrets manager.",
                                f"Update the component '{output_id}' to reference the new secret.",
                            ],
                        )
                    )

    def _evaluate_best_practice_rules(
        self,
        pipelines: list[dict[str, Any]],
        routes: list[dict[str, Any]],
        inputs: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        try:
            if self._rules_cache is None:
                all_rules = self.rule_loader.load_all_rules(cache=True)
                self._rules_cache = self.rule_loader.filter_enabled_only(all_rules)
            rules = self._rules_cache
            context = {
                "pipelines": pipelines,
                "routes": routes,
                "inputs": inputs,
                "outputs": outputs,
            }
            for pipeline in pipelines:
                pipeline_id = pipeline.get("id", "unknown")
                for rule in rules:
                    if rule.category in ["performance", "best_practice"]:
                        violated = self.rule_evaluator.evaluate_rule(rule, pipeline, context)
                        if violated:
                            self._create_rule_violation_finding(
                                rule, pipeline_id, "pipeline", result, client
                            )
        except Exception as e:
            self.log.warning("rule_evaluation_failed", error=str(e))

    def _create_rule_violation_finding(
        self,
        rule,
        component_id: str,
        component_type: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        result.add_finding(
            self.create_finding(
                client=client,
                id=f"{rule.id}-{component_id}",
                grouping_id=rule.id,
                category="config",
                severity=rule.severity_if_violated,
                title=f"{rule.name}: {component_id}",
                description=rule.description.format(component_id=component_id),
                affected_components=[f"{component_type}-{component_id}"],
                confidence_level="high",
                remediation_steps=[
                    step.format(component_id=component_id) for step in rule.remediation_steps
                ],
                estimated_impact=rule.estimated_impact or "",
            )
        )

    def _analyze_pipeline_efficiency(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])
            self._check_function_ordering(pipeline_id, functions, result, client)
            self._check_performance_antipatterns(pipeline_id, functions, result, client)

    def _check_function_ordering(
        self,
        pipeline_id: str,
        functions: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        expensive_funcs = {"regex", "regex_extract", "lookup", "eval", "grok"}
        filter_funcs = {"drop", "sampling"}
        first_filter_idx = None
        for idx, func in enumerate(functions):
            if func.get("id", "") in filter_funcs:
                first_filter_idx = idx
                break
        if first_filter_idx is not None:
            for idx in range(first_filter_idx):
                func_id = functions[idx].get("id", "")
                if func_id in expensive_funcs:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-perf-function-ordering-{pipeline_id}",
                            grouping_id="config-perf-function-ordering",
                            category="config",
                            severity="medium",
                            title=f"Suboptimal Function Ordering: {pipeline_id}",
                            description=f"Pipeline '{pipeline_id}' has expensive operations before filtering.",
                            affected_components=[f"pipeline-{pipeline_id}"],
                            confidence_level="high",
                            remediation_steps=[
                                f"Reorder functions in pipeline '{pipeline_id}' to place filters before expensive operations.",
                                "Move regex, lookup, and parsing functions after filtering functions.",
                                "Test pipeline performance after reordering.",
                            ],
                        )
                    )

    def _check_performance_antipatterns(
        self,
        pipeline_id: str,
        functions: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        issues_found = 0
        regex_funcs = [
            f for f in functions if f.get("id", "") in ["regex", "regex_extract", "grok"]
        ]
        if len(regex_funcs) > 2:
            issues_found += 1
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"config-perf-multiple-regex-{pipeline_id}",
                    grouping_id="config-perf-multiple-regex",
                    category="config",
                    severity="medium",
                    title=f"Multiple Regex Operations: {pipeline_id}",
                    description=f"Pipeline '{pipeline_id}' contains {len(regex_funcs)} regex-based operations.",
                    affected_components=[f"pipeline-{pipeline_id}"],
                    confidence_level="high",
                    remediation_steps=[
                        f"Consolidate regex operations in pipeline '{pipeline_id}' where possible.",
                        "Consider using lookup tables instead of complex regex patterns.",
                        "Optimize regex patterns for better performance.",
                    ],
                )
            )
        return issues_found

    def _analyze_route_conflicts(
        self,
        routes: list[dict[str, Any]],
        pipelines: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        for i, route in enumerate(routes):
            route_id = route.get("id", f"route_{i}")
            if self._is_catchall_route(route.get("filter", "")) and i < len(routes) - 1:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-route-catchall-not-last-{route_id}",
                        grouping_id="config-route-catchall-not-last",
                        category="config",
                        severity="high",
                        title=f"Catch-All Route Not Last: {route_id}",
                        description=f"Route '{route_id}' has no filter, shadowing subsequent routes.",
                        affected_components=[f"route-{route_id}"],
                        confidence_level="high",
                        estimated_impact="Subsequent routes will never be evaluated, leading to misrouted or dropped data.",
                        remediation_steps=[
                            f"Move route '{route_id}' to the bottom of the routes list.",
                            "Add appropriate filter conditions to the route.",
                            "Review route ordering to ensure proper data flow.",
                        ],
                    )
                )

    def _is_catchall_route(self, route_filter: str) -> bool:
        if not route_filter or route_filter.strip() == "":
            return True
        return route_filter.strip().lower() in ["true", "1==1", "1 == 1", "'true'"]

    def _analyze_complexity_metrics(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])
            complexity = len(functions) * 2
            if complexity > 50:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-complexity-high-{pipeline_id}",
                        grouping_id="config-complexity-high",
                        category="config",
                        severity="medium",
                        title=f"High Pipeline Complexity: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' has complexity score of {complexity}.",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        confidence_level="high",
                        remediation_steps=[
                            f"Review pipeline '{pipeline_id}' for simplification opportunities.",
                            "Consider breaking complex pipeline into smaller, focused pipelines.",
                            "Optimize function chains and remove redundant processing.",
                        ],
                    )
                )

    async def _check_advanced_security(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        pass

    def _calculate_compliance_score(self, result: AnalyzerResult) -> float:
        score = 100.0
        penalties = {"critical": 20, "high": 10, "medium": 5, "low": 2}
        for finding in result.findings:
            score -= penalties.get(finding.severity, 0)
        return max(0.0, min(100.0, round(score, 2)))

    def _generate_recommendations(self, result: AnalyzerResult) -> None:
        pass

    def _add_clean_config_finding(
        self, result: AnalyzerResult, client, pipelines, routes, inputs, outputs
    ) -> None:
        pass
