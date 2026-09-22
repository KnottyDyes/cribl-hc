"""
Configuration Analyzer for Cribl Stream Health Check.

Validates pipelines, routes, and configurations to detect errors and best practice violations.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import structlog

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.rules.loader import RuleEvaluator, RuleLoader

log = structlog.get_logger(__name__)


class ConfigAnalyzer(BaseAnalyzer):
    # Functions whose cost scales with event volume, so they are cheapest to
    # run after the event set has been narrowed.
    EXPENSIVE_FUNCTIONS = frozenset(
        {"regex_extract", "regex", "grok", "lookup", "eval", "mask", "code"}
    )
    # Functions that reduce the event set.
    FILTERING_FUNCTIONS = frozenset({"drop", "filter", "sampling", "suppress"})

    # Field/expression tokens that indicate personal or secret data. Matched
    # case-insensitively as substrings, so "user_email_address" matches "email".
    PII_PATTERNS: dict[str, tuple[str, ...]] = {
        "ssn": ("ssn", "social_security", "socialsecurity"),
        "credit_card": ("credit_card", "creditcard", "card_number", "cardnumber", "ccn"),
        "email": ("email", "e_mail"),
        "phone": ("phone", "telephone", "mobile_number"),
        "password": ("password", "passwd", "secret"),
        "api_credential": ("api_key", "apikey", "api_token", "access_token", "auth_token"),
        "date_of_birth": ("date_of_birth", "birthdate", "dob"),
        "address": ("home_address", "street_address", "address"),
        "name": ("full_name", "first_name", "last_name", "name"),
        "ip_address": ("ip_address", "client_ip", "src_ip", "dest_ip"),
    }
    # Functions that already protect a field, so its presence is not a finding.
    MASKING_FUNCTIONS = frozenset({"mask", "redact", "obfuscate", "hash", "encrypt"})
    MAX_EFFICIENT_EXPENSIVE_OPS = 3

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

    ROUTE_FILTER_REGEX_MAX_LENGTH = 200
    ROUTE_FILTER_PROBLEMATIC_PATTERNS = [
        (".*", "Greedy .* can cause catastrophic backtracking"),
        (".+", "Greedy .+ at pattern start is inefficient"),
        ("(.+)+", "Nested quantifiers cause exponential backtracking"),
        ("(.*)*", "Nested quantifiers cause exponential backtracking"),
    ]

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
        self._current_worker_group: Optional[str] = "default"

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
            self._check_route_filter_regex(routes, result, client)
            self._analyze_pipeline_efficiency(pipelines, result, client)
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
            if "routes" in routes_obj and isinstance(nested_routes, list):
                flattened.extend(nested_routes)
            # If routes_obj IS a route (backward compatibility), add it directly.
            # Test for key presence, not truthiness: a catch-all route carries
            # filter="", and dropping it here hid exactly the routes that
            # shadow everything after them.
            elif "filter" in routes_obj or "pipeline" in routes_obj:
                flattened.append(routes_obj)
        return flattened

    def _validate_pipeline_syntax(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        findings_before = len(result.findings)
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
                # Silently skipped before, so a malformed pipeline looked clean.
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-syntax-{pipeline_id}-invalid-functions-type",
                        grouping_id="config-syntax-invalid-functions-type",
                        category="config",
                        severity="critical",
                        title=f"Pipeline 'functions' Is Not a List: {pipeline_id}",
                        description=(
                            f"Pipeline '{pipeline_id}' declares 'functions' as "
                            f"{type(functions).__name__}; it must be a list."
                        ),
                        affected_components=[f"pipeline-{pipeline_id}"],
                        confidence_level="high",
                        estimated_impact="The pipeline cannot be loaded, so its routes process nothing.",
                        remediation_steps=[
                            f"Edit pipeline '{pipeline_id}' so 'functions' is a list of function objects.",
                            "Re-import the pipeline if it came from a pack or an export.",
                        ],
                        metadata={"pipeline": pipeline_id},
                    )
                )
                continue
            for func_idx, function in enumerate(functions):
                if not isinstance(function, dict):
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-syntax-{pipeline_id}-func-{func_idx}-invalid-type",
                            grouping_id="config-syntax-invalid-function-type",
                            category="config",
                            severity="high",
                            title=f"Function Is Not an Object: {pipeline_id}",
                            description=(
                                f"Function at position {func_idx} in pipeline '{pipeline_id}' is "
                                f"{type(function).__name__}, not a function object."
                            ),
                            affected_components=[f"pipeline-{pipeline_id}"],
                            confidence_level="high",
                            remediation_steps=[
                                f"Remove or correct entry {func_idx} in pipeline '{pipeline_id}'.",
                            ],
                            metadata={"pipeline": pipeline_id, "position": func_idx},
                        )
                    )
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

        result.metadata["syntax_errors"] = len(result.findings) - findings_before

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

            # A route with no Destination processes events and then drops them.
            if not route.get("output"):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-route-missing-output-{route_id}",
                        grouping_id="config-route-missing-output",
                        category="config",
                        severity="medium",
                        title=f"Route Missing Output: {route_id}",
                        description=(
                            f"Route '{route_id}' does not name an output, so events matching it "
                            f"are processed and then discarded."
                        ),
                        affected_components=[f"route-{route_id}"],
                        confidence_level="high",
                        remediation_steps=[
                            f"Set a Destination on route '{route_id}'.",
                            "If the route is meant to drop events, say so in its description.",
                        ],
                        metadata={"route": route_id},
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
                                "Update function configuration to use the modern syntax.",
                                "Test pipeline functionality after replacement.",
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

        for pipeline_id in sorted(unused_pipelines):
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
        for output_id in sorted(unused_outputs):
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
        encryption_issues = 0
        for output in outputs:
            output_id = output.get("id", "unknown")
            output.get("type", "unknown")

            # Plaintext transport: anything addressed over http:// leaves the
            # deployment unencrypted.
            for url_key in ("url", "endpoint", "host"):
                url = output.get(url_key)
                if isinstance(url, str) and url.lower().startswith("http://"):
                    encryption_issues += 1
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-security-no-tls-{output_id}",
                            grouping_id="config-security-no-tls",
                            category="config",
                            severity="medium",
                            title=f"Unencrypted Connection: {output_id}",
                            description=(
                                f"Destination '{output_id}' sends data to {url} over plain HTTP, "
                                f"so events travel unencrypted."
                            ),
                            affected_components=[f"output-{output_id}"],
                            confidence_level="high",
                            remediation_steps=[
                                f"Change the '{output_id}' Destination URL to use https://.",
                                "Confirm the receiving endpoint presents a valid certificate.",
                            ],
                            metadata={"output": output_id, "url": url},
                        )
                    )
                    break

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

        result.metadata["encryption_issues"] = encryption_issues

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
        findings_before = len(result.findings)
        scores: list[float] = []
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])
            scores.append(self._calculate_pipeline_efficiency_score(functions))
            self._check_function_ordering(pipeline_id, functions, result, client)
            self._check_performance_antipatterns(pipeline_id, functions, result, client)

        result.metadata["pipeline_efficiency_score"] = (
            round(sum(scores) / len(scores), 2) if scores else 100.0
        )
        result.metadata["max_pipeline_efficiency"] = max(scores) if scores else 100.0
        result.metadata["min_pipeline_efficiency"] = min(scores) if scores else 100.0
        result.metadata["performance_opportunities"] = len(result.findings) - findings_before

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
                    metadata={"regex_function_count": len(regex_funcs)},
                )
            )
        return issues_found

    def _filter_fields(self, route_filter: str) -> set[str]:
        """Field names a route filter compares against."""
        return set(re.findall(r"([A-Za-z_][\w.]*)\s*(?:==|!=|>=|<=|>|<|=~)", route_filter or ""))

    def _filter_syntax_error(self, route_filter: str) -> Optional[str]:
        """Describe a structural problem in a filter, or None if it parses."""
        if not route_filter:
            return None
        if route_filter.count("(") != route_filter.count(")"):
            return "unbalanced parentheses"
        # Quote counting ignores escaped quotes, which a filter rarely uses.
        for quote, name in (("'", "single"), ('"', "double")):
            if route_filter.replace(f"\\{quote}", "").count(quote) % 2:
                return f"unbalanced {name} quotes"
        return None

    def _analyze_route_conflicts(
        self,
        routes: list[dict[str, Any]],
        pipelines: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        conflicts = 0
        unreachable_total = 0

        for i, route in enumerate(routes):
            route_id = route.get("id", f"route_{i}")
            route_filter = route.get("filter", "")

            # A catch-all anywhere but last shadows everything after it.
            if self._is_catchall_route(route_filter) and i < len(routes) - 1:
                shadowed = routes[i + 1 :]
                shadowed_ids = [r.get("id", f"route_{j}") for j, r in enumerate(shadowed, i + 1)]
                unreachable_total += len(shadowed_ids)
                conflicts += 1
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
                        metadata={
                            "route": route_id,
                            "unreachable_routes": len(shadowed_ids),
                            "unreachable_route_ids": shadowed_ids,
                        },
                    )
                )

            syntax_error = self._filter_syntax_error(route_filter)
            if syntax_error:
                conflicts += 1
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-route-invalid-filter-{route_id}",
                        grouping_id="config-route-invalid-filter",
                        category="config",
                        severity="high",
                        title=f"Invalid Route Filter: {route_id}",
                        description=(
                            f"Route '{route_id}' has a filter with {syntax_error}, "
                            f"so it cannot be evaluated: {route_filter}"
                        ),
                        affected_components=[f"route-{route_id}"],
                        confidence_level="high",
                        estimated_impact="The route never matches, so data intended for it is not processed.",
                        remediation_steps=[
                            f"Correct the {syntax_error} in the filter for route '{route_id}'.",
                            "Use the route preview in the UI to confirm the filter evaluates.",
                        ],
                        metadata={"route": route_id, "filter": route_filter},
                    )
                )

        # Routes that test the same fields can shadow one another, since the
        # first match wins.
        for i, route in enumerate(routes):
            fields_a = self._filter_fields(route.get("filter", ""))
            if not fields_a:
                continue
            for other in routes[i + 1 :]:
                fields_b = self._filter_fields(other.get("filter", ""))
                shared = fields_a & fields_b
                if not shared:
                    continue
                route_a = route.get("id", f"route_{i}")
                route_b = other.get("id", "unknown")
                conflicts += 1
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"config-route-overlap-{route_a}-{route_b}",
                        grouping_id="config-route-overlap",
                        category="config",
                        severity="medium",
                        title=f"Overlapping Routes: {route_a} and {route_b}",
                        description=(
                            f"Routes '{route_a}' and '{route_b}' both filter on "
                            f"{', '.join(sorted(shared))}, so the earlier one may shadow the later."
                        ),
                        affected_components=[f"route-{route_a}", f"route-{route_b}"],
                        confidence_level="low",
                        remediation_steps=[
                            f"Confirm '{route_a}' and '{route_b}' are meant to match different events.",
                            "Narrow the earlier filter, or enable Final on it deliberately.",
                        ],
                        metadata={
                            "route_1": route_a,
                            "route_2": route_b,
                            "shared_fields": sorted(shared),
                        },
                    )
                )

        result.metadata["route_conflicts_found"] = conflicts
        result.metadata["unreachable_routes"] = unreachable_total

    def _is_catchall_route(self, route_filter: str) -> bool:
        if not route_filter or route_filter.strip() == "":
            return True
        return route_filter.strip().lower() in ["true", "1==1", "1 == 1", "'true'"]

    def _check_route_filter_regex(
        self, routes: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        for route in routes:
            route_id = route.get("id", "unknown")
            filter_expr = route.get("filter", "") or ""
            if not isinstance(filter_expr, str) or not filter_expr.strip():
                continue

            patterns = self._extract_regex_patterns_from_filter(filter_expr)
            for pattern in patterns:
                if len(pattern) > self.ROUTE_FILTER_REGEX_MAX_LENGTH:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-route-filter-regex-length-{route_id}",
                            grouping_id="config-route-filter-regex-length",
                            category="config",
                            severity="medium",
                            title=f"Long Regex in Route Filter: {route_id}",
                            description=(
                                f"Route '{route_id}' filter contains a regex pattern "
                                f"with {len(pattern)} characters."
                            ),
                            affected_components=[f"route-{route_id}"],
                            confidence_level="medium",
                            remediation_steps=[
                                "Simplify regex patterns in route filters",
                                "Move complex matching into pipeline functions",
                                "Anchor regex patterns where possible",
                            ],
                            metadata={"route_id": route_id, "pattern_length": len(pattern)},
                        )
                    )

                for bad_pattern, reason in self.ROUTE_FILTER_PROBLEMATIC_PATTERNS:
                    if bad_pattern in pattern:
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"config-route-filter-regex-problematic-{route_id}-{hash(bad_pattern) % 10000}",
                                grouping_id="config-route-filter-regex-problematic",
                                category="config",
                                severity="medium",
                                title=f"Potentially Slow Regex in Route Filter: {route_id}",
                                description=(
                                    f"Route '{route_id}' filter contains '{bad_pattern}'. {reason}"
                                ),
                                affected_components=[f"route-{route_id}"],
                                confidence_level="medium",
                                remediation_steps=[
                                    "Rewrite regex to avoid nested quantifiers",
                                    "Use more specific patterns",
                                    "Move regex matching into pipeline functions",
                                ],
                                metadata={"route_id": route_id, "pattern": bad_pattern},
                            )
                        )
                        break

    @staticmethod
    def _extract_regex_patterns_from_filter(filter_expr: str) -> list[str]:
        patterns = []
        for match in re.finditer(r"/([^/\\]*(?:\\.[^/\\]*)*)/", filter_expr):
            patterns.append(match.group(1))

        for match in re.finditer(r"regex\(\s*['\"](.+?)['\"]\s*\)", filter_expr):
            patterns.append(match.group(1))

        for match in re.finditer(r"match\(\s*[^,]+,\s*['\"](.+?)['\"]\s*\)", filter_expr):
            patterns.append(match.group(1))

        return patterns

    def _calculate_pipeline_complexity(self, functions: list[dict[str, Any]]) -> int:
        """
        Score how hard a pipeline is to reason about.

        Counts each function, then adds for the things that make one hard to
        follow: nested filter expressions, long inline expressions, and
        functions carrying a large amount of configuration.
        """
        if not functions:
            return 0

        complexity = 0
        for function in functions:
            complexity += 2
            conf = function.get("conf") or {}
            complexity += str(conf.get("filter") or "").count("(") * 3
            if len(str(conf.get("expression") or "")) > 50:
                complexity += 5
            if len(conf) > 5:
                complexity += 3
        return complexity

    def _calculate_pipeline_efficiency_score(self, functions: list[dict[str, Any]]) -> float:
        """
        Score function ordering from 0-100.

        Penalises expensive functions placed ahead of the first filtering
        function, since those run against the full event set, and penalises
        pipelines carrying more expensive functions than
        MAX_EFFICIENT_EXPENSIVE_OPS.
        """
        if not functions:
            return 100.0

        score = 100.0
        first_filter = next(
            (i for i, f in enumerate(functions) if f.get("id") in self.FILTERING_FUNCTIONS),
            None,
        )
        expensive_positions = [
            i for i, f in enumerate(functions) if f.get("id") in self.EXPENSIVE_FUNCTIONS
        ]

        # Only meaningful when the pipeline filters at all.
        if first_filter is not None:
            score -= sum(1 for i in expensive_positions if i < first_filter) * 15

        excess = len(expensive_positions) - self.MAX_EFFICIENT_EXPENSIVE_OPS
        if excess > 0:
            score -= excess * 5

        return max(0.0, min(100.0, score))

    def _analyze_complexity_metrics(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        complexities: list[int] = []
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])
            complexity = self._calculate_pipeline_complexity(functions)
            complexities.append(complexity)
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

        result.metadata["avg_pipeline_complexity"] = (
            round(sum(complexities) / len(complexities), 2) if complexities else 0.0
        )
        result.metadata["max_pipeline_complexity"] = max(complexities) if complexities else 0
        result.metadata["min_pipeline_complexity"] = min(complexities) if complexities else 0
        result.metadata.setdefault("duplicate_patterns_found", 0)

    def _match_pii_types(self, text: str) -> list[str]:
        """Return the PII categories whose tokens appear in text."""
        lowered = text.lower()
        return [
            pii_type
            for pii_type, tokens in self.PII_PATTERNS.items()
            if any(token in lowered for token in tokens)
        ]

    def _masked_fields(self, functions: list[dict[str, Any]]) -> set[str]:
        """Collect field names already covered by a masking function."""
        masked: set[str] = set()
        for function in functions:
            if function.get("id") not in self.MASKING_FUNCTIONS:
                continue
            conf = function.get("conf") or {}
            if isinstance(conf.get("field"), str):
                masked.add(conf["field"].lower())
            for field in conf.get("fields") or []:
                if isinstance(field, str):
                    masked.add(field.lower())
        return masked

    async def _check_advanced_security(
        self, pipelines: list[dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """
        Flag personal or secret data handled in the clear.

        Two separate concerns: PII named in an expression, which usually means
        it is being copied or logged, and sensitive fields referenced by a
        pipeline that never masks them.
        """
        pii_risks = 0
        unmasked = 0

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", []) or []
            masked = self._masked_fields(functions)

            for index, function in enumerate(functions):
                if function.get("id") in self.MASKING_FUNCTIONS:
                    continue
                conf = function.get("conf") or {}

                expression = str(conf.get("expression") or "")
                for pii_type in self._match_pii_types(expression):
                    pii_risks += 1
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-sec-pii-{pipeline_id}-{index}-{pii_type}",
                            grouping_id="config-sec-pii",
                            category="config",
                            severity="high",
                            title=f"PII in Expression: {pii_type}",
                            description=(
                                f"Pipeline '{pipeline_id}' references {pii_type} in an expression, "
                                f"which copies the value into the event in the clear."
                            ),
                            affected_components=[f"pipeline-{pipeline_id}"],
                            confidence_level="medium",
                            estimated_impact=(
                                f"{pii_type} values are written unprotected into downstream data"
                            ),
                            remediation_steps=[
                                f"Mask or hash {pii_type} before it is referenced in this expression.",
                                f"Add a mask function to pipeline '{pipeline_id}' ahead of this step.",
                            ],
                            metadata={"pipeline": pipeline_id, "pii_type": pii_type},
                        )
                    )

                candidate_fields = []
                if isinstance(conf.get("field"), str):
                    candidate_fields.append(conf["field"])
                for field in conf.get("fields") or []:
                    if isinstance(field, str):
                        candidate_fields.append(field)

                for field in candidate_fields:
                    if field.lower() in masked:
                        continue
                    pii_types = self._match_pii_types(field)
                    if not pii_types:
                        continue
                    unmasked += 1
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"config-sec-unmasked-{pipeline_id}-{index}-{field}",
                            grouping_id="config-sec-unmasked",
                            category="config",
                            severity="medium",
                            title=f"Unmasked Sensitive Field: {field}",
                            description=(
                                f"Pipeline '{pipeline_id}' handles field '{field}' "
                                f"({', '.join(pii_types)}) without masking it."
                            ),
                            affected_components=[f"pipeline-{pipeline_id}"],
                            confidence_level="medium",
                            remediation_steps=[
                                f"Add a mask function covering '{field}' to pipeline '{pipeline_id}'.",
                                "Place it before the field reaches any Destination.",
                            ],
                            metadata={
                                "pipeline": pipeline_id,
                                "field": field,
                                "pii_types": pii_types,
                            },
                        )
                    )

        result.metadata["pii_exposure_risks"] = pii_risks
        result.metadata["unmasked_sensitive_fields"] = unmasked

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
