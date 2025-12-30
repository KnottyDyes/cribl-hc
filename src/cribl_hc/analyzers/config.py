"""
Configuration Analyzer for Cribl Stream Health Check.

Validates pipelines, routes, and configurations to detect errors and best practice violations.
"""

import re
import structlog
from typing import Any, Dict, List, Set

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.rules.loader import RuleLoader, RuleEvaluator


class ConfigAnalyzer(BaseAnalyzer):
    """
    Analyzer for configuration validation and best practices.

    P2 Priority - Validates:
    - Pipeline syntax errors
    - Deprecated function usage
    - Orphaned/unused configurations
    - Security misconfigurations
    - Route conflicts
    """

    # Map of deprecated functions to their replacements
    DEPRECATED_FUNCTIONS = {
        "regex": {
            "replacement": "regex_extract",
            "reason": "regex_extract provides better performance and clearer syntax",
            "docs": "https://docs.cribl.io/stream/regex-extract-function/"
        },
        "code": {
            "replacement": "eval",
            "reason": "eval function is the modern replacement with better performance",
            "docs": "https://docs.cribl.io/stream/eval-function/"
        }
    }

    # Patterns for detecting hardcoded credentials (JSON format)
    CREDENTIAL_PATTERNS = [
        r'"password"\s*:\s*"([^"$][^"]{2,})"',  # Excludes ${env:...}
        r'"token"\s*:\s*"([^"$][^"]{2,})"',
        r'"secret"\s*:\s*"([^"$][^"]{2,})"',
        r'"api[_-]?key"\s*:\s*"([^"$][^"]{2,})"',
        r'"auth"\s*:\s*"([^"$][^"]{2,})"'
    ]

    def __init__(self):
        """Initialize the configuration analyzer."""
        super().__init__()
        self.log = structlog.get_logger(__name__)

        # Initialize rule system (Phase 2A)
        self.rule_loader = RuleLoader()
        self.rule_evaluator = RuleEvaluator()
        self._rules_cache = None

        # Track current worker group for context in findings
        self._current_worker_group: str = "default"

    def _worker_group_context(self) -> str:
        """
        Get formatted worker group context for use in finding descriptions.

        Returns:
            Formatted string like " (Worker Group: production)" or empty string for default.
        """
        if self._current_worker_group and self._current_worker_group != "default":
            return f" (Worker Group: {self._current_worker_group})"
        return f" (Worker Group: {self._current_worker_group})" if self._current_worker_group else ""

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "config"

    @property
    def supported_products(self) -> List[str]:
        """Config analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_estimated_api_calls(self) -> int:
        """
        Return estimated number of API calls.

        API calls:
        1. get_pipelines() - 1 call
        2. get_routes() - 1 call
        3. get_inputs() - 1 call
        4. get_outputs() - 1 call
        5. Reserved for future config endpoints - 1 call

        Total: 5 calls (5% of 100-call budget)
        """
        return 5

    def get_required_permissions(self) -> List[str]:
        """Return list of required API permissions."""
        return [
            "read:pipelines",
            "read:routes",
            "read:inputs",
            "read:outputs"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform configuration analysis on Cribl Stream or Edge deployment.

        Automatically adapts based on detected product type.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        # Track worker group for context in findings
        self._current_worker_group = client.worker_group

        # Detect product type and log appropriately
        product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
        self.log.info("config_analysis_started", product=client.product_type, product_name=product_name, worker_group=self._current_worker_group)

        try:
            # Fetch configuration data
            pipelines = await self._fetch_pipelines(client)
            routes = await self._fetch_routes(client)
            inputs = await self._fetch_inputs(client)
            outputs = await self._fetch_outputs(client)

            # Store product type and worker group in metadata
            result.metadata["product_type"] = client.product_type
            result.metadata["worker_group"] = self._current_worker_group

            # Run basic syntax validation (Phase 1)
            self._validate_pipeline_syntax(pipelines, result)

            # Run route validation (Phase 2)
            self._validate_route_configuration(routes, pipelines, result)

            # Check for deprecated functions (Phase 3)
            self._check_deprecated_functions(pipelines, result)

            # Find unused components (Phase 4)
            self._find_unused_components(pipelines, routes, inputs, outputs, result)

            # Check security misconfigurations (Phase 5)
            self._check_security_misconfigurations(outputs, result)

            # Evaluate best practice rules (Phase 2A)
            self._evaluate_best_practice_rules(pipelines, routes, inputs, outputs, result)

            # Analyze pipeline efficiency (Phase 2B)
            self._analyze_pipeline_efficiency(pipelines, result)

            # Detect route conflicts (Phase 2C)
            self._analyze_route_conflicts(routes, pipelines, result)

            # Analyze configuration complexity (Phase 2D)
            self._analyze_complexity_metrics(pipelines, result)

            # Advanced security checks (Phase 2E)
            await self._check_advanced_security(pipelines, result)

            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(result)

            # Generate recommendations
            self._generate_recommendations(result)

            # Add positive finding if configuration is clean
            self._add_clean_config_finding(result, client, pipelines, routes, inputs, outputs)

            # Store metadata
            result.metadata["pipelines_analyzed"] = len(pipelines)
            result.metadata["routes_analyzed"] = len(routes)
            result.metadata["inputs_analyzed"] = len(inputs)
            result.metadata["outputs_analyzed"] = len(outputs)
            result.metadata["syntax_errors"] = len([
                f for f in result.findings if "syntax" in f.id.lower()
            ])
            result.metadata["deprecated_functions"] = len([
                f for f in result.findings if "deprecated" in f.id.lower()
            ])
            result.metadata["unused_components"] = len([
                f for f in result.findings if "unused" in f.id.lower()
            ])
            result.metadata["security_issues"] = len([
                f for f in result.findings if "security" in f.id.lower()
            ])
            result.metadata["compliance_score"] = compliance_score
            result.metadata["rules_evaluated"] = result.metadata.get("rules_evaluated", 0)
            result.metadata["critical_findings"] = len([
                f for f in result.findings if f.severity == "critical"
            ])
            result.metadata["high_findings"] = len([
                f for f in result.findings if f.severity == "high"
            ])
            result.metadata["medium_findings"] = len([
                f for f in result.findings if f.severity == "medium"
            ])
            result.metadata["low_findings"] = len([
                f for f in result.findings if f.severity == "low"
            ])

            self.log.info(
                "config_analysis_completed",
                product=client.product_type,
                pipelines=len(pipelines),
                routes=len(routes),
                findings=len(result.findings)
            )

        except Exception as e:
            # Graceful degradation - Constitution Principle #6
            self.log.error("config_analysis_failed", product=client.product_type, error=str(e))
            result.success = True  # Still return success
            result.metadata["pipelines_analyzed"] = 0
            result.metadata["routes_analyzed"] = 0
            result.metadata["inputs_analyzed"] = 0
            result.metadata["outputs_analyzed"] = 0
            result.metadata["product_type"] = client.product_type

            # Product-aware error messages
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            docs_link = (
                "https://docs.cribl.io/edge/api-reference/"
                if client.is_edge
                else "https://docs.cribl.io/stream/api-reference/"
            )

            # Add error as finding
            result.add_finding(
                Finding(
                    id="config-analysis-error",
                    category="config",
                    severity="high",
                    title=f"Configuration Analysis Error ({product_name})",
                    description=f"Failed to complete configuration analysis on {product_name}: {str(e)}",
                    affected_components=["configuration"],
                    remediation_steps=[
                        "Check API connectivity and authentication",
                        "Verify read permissions for configuration endpoints",
                        "Review API token permissions",
                        f"Check {product_name} API availability"
                    ],
                    documentation_links=[docs_link],
                    estimated_impact="Unable to validate configuration - manual review recommended",
                    confidence_level="high",
                    metadata={"error": str(e), "product_type": client.product_type}
                )
            )

        return result

    async def _fetch_pipelines(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """
        Fetch all pipelines from Cribl API.

        Args:
            client: Authenticated Cribl API client

        Returns:
            List of pipeline configurations
        """
        try:
            pipelines = await client.get_pipelines()
            self.log.debug("pipelines_fetched", count=len(pipelines))
            return pipelines
        except Exception as e:
            self.log.error("pipelines_fetch_failed", error=str(e))
            return []

    async def _fetch_routes(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """
        Fetch all routes from Cribl API.

        Args:
            client: Authenticated Cribl API client

        Returns:
            List of route configurations
        """
        try:
            routes = await client.get_routes()
            self.log.debug("routes_fetched", count=len(routes))
            return routes
        except Exception as e:
            self.log.error("routes_fetch_failed", error=str(e))
            return []

    async def _fetch_inputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """
        Fetch all inputs from Cribl API.

        Args:
            client: Authenticated Cribl API client

        Returns:
            List of input configurations
        """
        try:
            inputs = await client.get_inputs()
            self.log.debug("inputs_fetched", count=len(inputs))
            return inputs
        except Exception as e:
            self.log.error("inputs_fetch_failed", error=str(e))
            return []

    async def _fetch_outputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """
        Fetch all outputs from Cribl API.

        Args:
            client: Authenticated Cribl API client

        Returns:
            List of output configurations
        """
        try:
            outputs = await client.get_outputs()
            self.log.debug("outputs_fetched", count=len(outputs))
            return outputs
        except Exception as e:
            self.log.error("outputs_fetch_failed", error=str(e))
            return []

    def _validate_pipeline_syntax(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Validate pipeline syntax and structure.

        Checks for:
        - Missing required fields (id, functions)
        - Invalid function structure
        - Missing function IDs

        Args:
            pipelines: List of pipeline configurations
            result: AnalyzerResult to add findings to
        """
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")

            # Check for required 'id' field
            if not pipeline.get("id"):
                result.add_finding(
                    Finding(
                        id=f"config-syntax-missing-id-{hash(str(pipeline))}",
                        category="config",
                        severity="critical",
                        title=f"Pipeline Missing Required 'id' Field{self._worker_group_context()}",
                        description=f"Pipeline configuration is missing required 'id' field{self._worker_group_context()}",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        remediation_steps=[
                            "Add 'id' field to pipeline configuration",
                            "Ensure 'id' is unique across all pipelines",
                            "Redeploy pipeline configuration"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/pipelines/"
                        ],
                        estimated_impact="Pipeline cannot be deployed or referenced",
                        confidence_level="high",
                        metadata={"pipeline": pipeline, "worker_group": self._current_worker_group}
                    )
                )
                continue

            # Skip pack reference pipelines (they don't have functions, just {"conf": {"pack": true}})
            if "conf" in pipeline and isinstance(pipeline["conf"], dict):
                if pipeline["conf"].get("pack") is True and "functions" not in pipeline["conf"]:
                    # This is a pack reference, not an actual pipeline - skip validation
                    continue

            # Get functions - handle both API response formats
            # Cribl Cloud: {"id": "x", "conf": {"functions": [...]}}
            # Self-hosted: {"id": "x", "functions": [...]}
            functions = None
            if "functions" in pipeline:
                functions = pipeline.get("functions")
            elif "conf" in pipeline and isinstance(pipeline["conf"], dict):
                functions = pipeline["conf"].get("functions")

            # Check if functions field exists
            if functions is None:
                result.add_finding(
                    Finding(
                        id=f"config-syntax-{pipeline_id}-missing-functions",
                        category="config",
                        severity="high",
                        title=f"Pipeline Missing 'functions' Field: {pipeline_id}{self._worker_group_context()}",
                        description=f"Pipeline '{pipeline_id}' is missing required 'functions' field{self._worker_group_context()}",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        remediation_steps=[
                            f"Add 'functions' array to pipeline '{pipeline_id}'",
                            "Define at least one function in the pipeline",
                            "Validate pipeline configuration in Cribl UI",
                            "Redeploy pipeline"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/pipelines/",
                            "https://docs.cribl.io/stream/functions/"
                        ],
                        estimated_impact="Pipeline will not process data correctly",
                        confidence_level="high",
                        metadata={"pipeline_id": pipeline_id, "worker_group": self._current_worker_group}
                    )
                )
                continue

            # Validate functions array
            if not isinstance(functions, list):
                result.add_finding(
                    Finding(
                        id=f"config-syntax-{pipeline_id}-invalid-functions-type",
                        category="config",
                        severity="critical",
                        title=f"Pipeline 'functions' Must Be Array: {pipeline_id}{self._worker_group_context()}",
                        description=f"Pipeline '{pipeline_id}' has invalid 'functions' field (must be array){self._worker_group_context()}",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        remediation_steps=[
                            f"Change 'functions' field to array in pipeline '{pipeline_id}'",
                            "Review pipeline JSON structure",
                            "Validate configuration syntax",
                            "Redeploy pipeline"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/pipelines/"
                        ],
                        estimated_impact="Pipeline will fail to load",
                        confidence_level="high",
                        metadata={"pipeline_id": pipeline_id, "functions_type": type(functions).__name__, "worker_group": self._current_worker_group}
                    )
                )
                continue

            # Validate each function in the pipeline
            for func_idx, function in enumerate(functions):
                if not isinstance(function, dict):
                    result.add_finding(
                        Finding(
                            id=f"config-syntax-{pipeline_id}-func-{func_idx}-invalid-type",
                            category="config",
                            severity="high",
                            title=f"Invalid Function Type in Pipeline: {pipeline_id}{self._worker_group_context()}",
                            description=f"Function at index {func_idx} in pipeline '{pipeline_id}' is not an object{self._worker_group_context()}",
                            affected_components=[f"pipeline-{pipeline_id}"],
                            remediation_steps=[
                                f"Fix function at index {func_idx} in pipeline '{pipeline_id}'",
                                "Ensure function is a valid JSON object",
                                "Review function configuration",
                                "Redeploy pipeline"
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/functions/"
                            ],
                            estimated_impact="Function will not execute",
                            confidence_level="high",
                            metadata={
                                "pipeline_id": pipeline_id,
                                "function_index": func_idx,
                                "function_type": type(function).__name__,
                                "worker_group": self._current_worker_group
                            }
                        )
                    )
                    continue

                # Check for required 'id' field in function
                if not function.get("id"):
                    result.add_finding(
                        Finding(
                            id=f"config-syntax-{pipeline_id}-func-{func_idx}-missing-id",
                            category="config",
                            severity="medium",
                            title=f"Function Missing 'id' Field: {pipeline_id}{self._worker_group_context()}",
                            description=f"Function at index {func_idx} in pipeline '{pipeline_id}' is missing 'id' field{self._worker_group_context()}",
                            affected_components=[f"pipeline-{pipeline_id}"],
                            remediation_steps=[
                                f"Add 'id' field to function at index {func_idx}",
                                "Specify function type (e.g., 'eval', 'mask', 'drop')",
                                "Validate function configuration",
                                "Redeploy pipeline"
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/functions/"
                            ],
                            estimated_impact="Function may not execute as expected",
                            confidence_level="high",
                            metadata={
                                "pipeline_id": pipeline_id,
                                "function_index": func_idx,
                                "function": function,
                                "worker_group": self._current_worker_group
                            }
                        )
                    )

    def _validate_route_configuration(
        self,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Validate route configuration for orphaned references.

        Checks for:
        - Routes referencing non-existent pipelines
        - Routes with missing output destinations

        Args:
            routes: List of route configurations
            pipelines: List of pipeline configurations
            result: AnalyzerResult to add findings to
        """
        # Build set of valid pipeline IDs
        valid_pipeline_ids = {p.get("id") for p in pipelines if p.get("id")}

        for route in routes:
            route_id = route.get("id", "unknown")
            pipeline_ref = route.get("pipeline")

            # Check if route references a pipeline that doesn't exist
            if pipeline_ref and pipeline_ref not in valid_pipeline_ids:
                result.add_finding(
                    Finding(
                        id=f"config-orphaned-route-{route_id}",
                        category="config",
                        severity="high",
                        title=f"Route References Non-Existent Pipeline: {route_id}{self._worker_group_context()}",
                        description=f"Route '{route_id}' references pipeline '{pipeline_ref}' which does not exist{self._worker_group_context()}",
                        affected_components=[f"route-{route_id}", f"pipeline-{pipeline_ref}"],
                        remediation_steps=[
                            f"Create missing pipeline '{pipeline_ref}' or update route to reference existing pipeline",
                            "Review route configuration in Cribl UI",
                            f"Available pipelines: {', '.join(sorted(valid_pipeline_ids)[:5])}{'...' if len(valid_pipeline_ids) > 5 else ''}",
                            "Test route with sample data after fixing"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/routes/",
                            "https://docs.cribl.io/stream/pipelines/"
                        ],
                        estimated_impact="Route will fail to process data - potential data loss",
                        confidence_level="high",
                        metadata={
                            "route_id": route_id,
                            "missing_pipeline": pipeline_ref,
                            "available_pipelines": sorted(valid_pipeline_ids),
                            "worker_group": self._current_worker_group
                        }
                    )
                )

            # Check if route is missing output destination
            if not route.get("output"):
                result.add_finding(
                    Finding(
                        id=f"config-missing-output-{route_id}",
                        category="config",
                        severity="medium",
                        title=f"Route Missing Output Destination: {route_id}{self._worker_group_context()}",
                        description=f"Route '{route_id}' does not specify an output destination{self._worker_group_context()}",
                        affected_components=[f"route-{route_id}"],
                        remediation_steps=[
                            f"Add output destination to route '{route_id}'",
                            "Review available outputs in Cribl UI",
                            "Test route after adding output"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/routes/",
                            "https://docs.cribl.io/stream/destinations/"
                        ],
                        estimated_impact="Data may not be routed correctly",
                        confidence_level="high",
                        metadata={
                            "route_id": route_id,
                            "worker_group": self._current_worker_group
                        }
                    )
                )

    def _check_deprecated_functions(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Check for deprecated function usage in pipelines.

        Scans pipeline functions for deprecated types and generates
        findings with migration guidance.

        Args:
            pipelines: List of pipeline configurations
            result: AnalyzerResult to add findings to
        """
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("functions", [])

            if not isinstance(functions, list):
                continue

            for func_idx, function in enumerate(functions):
                if not isinstance(function, dict):
                    continue

                func_id = function.get("id", "unknown")

                # Check if function type is deprecated
                if func_id in self.DEPRECATED_FUNCTIONS:
                    deprecation_info = self.DEPRECATED_FUNCTIONS[func_id]
                    replacement = deprecation_info["replacement"]
                    reason = deprecation_info["reason"]
                    docs_link = deprecation_info["docs"]

                    result.add_finding(
                        Finding(
                            id=f"config-deprecated-{pipeline_id}-{func_idx}",
                            category="config",
                            severity="medium",
                            title=f"Deprecated Function '{func_id}' in Pipeline: {pipeline_id}",
                            description=f"Pipeline '{pipeline_id}' uses deprecated function '{func_id}' (should use '{replacement}')",
                            affected_components=[f"pipeline-{pipeline_id}", f"function-{func_id}"],
                            remediation_steps=[
                                f"Replace '{func_id}' function with '{replacement}' in pipeline '{pipeline_id}'",
                                f"Review function configuration and update syntax for '{replacement}'",
                                "Test pipeline with sample data to verify behavior",
                                "Deploy updated pipeline to production",
                                f"Reason for migration: {reason}"
                            ],
                            documentation_links=[
                                docs_link,
                                "https://docs.cribl.io/stream/pipelines/",
                                "https://docs.cribl.io/stream/functions/"
                            ],
                            estimated_impact=f"Function will continue to work but may have degraded performance. Migration to '{replacement}' recommended.",
                            confidence_level="high",
                            metadata={
                                "pipeline_id": pipeline_id,
                                "function_index": func_idx,
                                "deprecated_function": func_id,
                                "replacement_function": replacement,
                                "migration_reason": reason
                            }
                        )
                    )

    def _find_unused_components(
        self,
        pipelines: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Find unused pipelines, inputs, and outputs.

        Builds a usage graph to identify components that are defined
        but not referenced by any routes or other configurations.

        Args:
            pipelines: List of pipeline configurations
            routes: List of route configurations
            inputs: List of input configurations
            outputs: List of output configurations
            result: AnalyzerResult to add findings to
        """
        # Build sets of all components
        all_pipeline_ids = {p.get("id") for p in pipelines if p.get("id")}
        all_output_ids = {o.get("id") for o in outputs if o.get("id")}

        # Build sets of used components
        used_pipeline_ids: Set[str] = set()
        used_output_ids: Set[str] = set()

        # Track which pipelines and outputs are referenced by routes
        for route in routes:
            pipeline_ref = route.get("pipeline")
            if pipeline_ref:
                used_pipeline_ids.add(pipeline_ref)

            output_ref = route.get("output")
            if output_ref:
                used_output_ids.add(output_ref)

        # Find unused pipelines
        unused_pipelines = all_pipeline_ids - used_pipeline_ids
        for pipeline_id in sorted(unused_pipelines):
            result.add_finding(
                Finding(
                    id=f"config-unused-pipeline-{pipeline_id}",
                    category="config",
                    severity="low",
                    title=f"Unused Pipeline: {pipeline_id}",
                    description=f"Pipeline '{pipeline_id}' is not referenced by any route",
                    affected_components=[f"pipeline-{pipeline_id}"],
                    remediation_steps=[
                        f"Review if pipeline '{pipeline_id}' is still needed",
                        "Remove unused pipeline to reduce configuration complexity",
                        "Or add route that uses this pipeline if it's intended for future use",
                        "Document unused pipelines if kept for reference"
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/pipelines/",
                        "https://docs.cribl.io/stream/routes/"
                    ],
                    estimated_impact="Minimal - increases configuration complexity and maintenance burden",
                    confidence_level="high",
                    metadata={
                        "pipeline_id": pipeline_id,
                        "used_by_routes": False
                    }
                )
            )

        # Find unused outputs
        unused_outputs = all_output_ids - used_output_ids
        for output_id in sorted(unused_outputs):
            result.add_finding(
                Finding(
                    id=f"config-unused-output-{output_id}",
                    category="config",
                    severity="low",
                    title=f"Unused Output: {output_id}",
                    description=f"Output '{output_id}' is not referenced by any route",
                    affected_components=[f"output-{output_id}"],
                    remediation_steps=[
                        f"Review if output '{output_id}' is still needed",
                        "Remove unused output to reduce configuration complexity",
                        "Or add route that uses this output if it's intended for future use",
                        "Check if output is used by other non-route mechanisms"
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/destinations/",
                        "https://docs.cribl.io/stream/routes/"
                    ],
                    estimated_impact="Minimal - may have idle connections consuming resources",
                    confidence_level="medium",
                    metadata={
                        "output_id": output_id,
                        "used_by_routes": False
                    }
                )
            )

    def _check_security_misconfigurations(
        self,
        outputs: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Check for security misconfigurations in outputs.

        Detects:
        - Hardcoded credentials in output configurations
        - Missing TLS/encryption settings
        - Plaintext authentication tokens

        Args:
            outputs: List of output configurations
            result: AnalyzerResult to add findings to
        """
        import json

        for output in outputs:
            output_id = output.get("id", "unknown")
            output_type = output.get("type", "unknown")

            # Convert output to JSON string for pattern matching
            try:
                output_json = json.dumps(output)
            except Exception:
                continue

            # Check for hardcoded credentials
            for pattern in self.CREDENTIAL_PATTERNS:
                matches = re.finditer(pattern, output_json, re.IGNORECASE)
                for match in matches:
                    # Extract the matched credential key (but don't include value in finding!)
                    # Pattern matches: "fieldname": "value"
                    credential_key = match.group(0).split('"')[1]  # Get fieldname from "fieldname"

                    result.add_finding(
                        Finding(
                            id=f"config-security-hardcoded-{output_id}-{hash(match.group(0))}",
                            category="config",
                            severity="high",
                            title=f"Hardcoded Credential in Output: {output_id}",
                            description=f"Output '{output_id}' contains hardcoded credential field '{credential_key}'",
                            affected_components=[f"output-{output_id}"],
                            remediation_steps=[
                                f"Remove hardcoded credential from output '{output_id}'",
                                "Use environment variable substitution: ${env:VARIABLE_NAME}",
                                "Store credentials in Cribl secrets management",
                                "Update output configuration and test connectivity",
                                "Review security audit logs for potential exposure"
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/environment-variables/",
                                "https://docs.cribl.io/stream/securing-cribl-stream/"
                            ],
                            estimated_impact="Security risk: credentials exposed in configuration backups and logs",
                            confidence_level="high",
                            metadata={
                                "output_id": output_id,
                                "output_type": output_type,
                                "credential_field": credential_key
                            }
                        )
                    )

            # Check for missing TLS in certain output types
            if output_type in ["splunk", "elasticsearch", "http", "s3", "webhook"]:
                # Check URLs for http:// instead of https://
                url_field = output.get("url", "") or output.get("host", "")
                if isinstance(url_field, str) and url_field.startswith("http://"):
                    result.add_finding(
                        Finding(
                            id=f"config-security-no-tls-{output_id}",
                            category="config",
                            severity="medium",
                            title=f"Output Using Unencrypted Connection: {output_id}",
                            description=f"Output '{output_id}' is configured to use HTTP instead of HTTPS",
                            affected_components=[f"output-{output_id}"],
                            remediation_steps=[
                                f"Update output '{output_id}' URL to use HTTPS",
                                "Enable TLS/SSL encryption for this output",
                                "Verify destination server supports HTTPS",
                                "Test connectivity after enabling encryption"
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/destinations/",
                                "https://docs.cribl.io/stream/securing-cribl-stream/"
                            ],
                            estimated_impact="Data transmitted in plaintext - potential data exposure",
                            confidence_level="high",
                            metadata={
                                "output_id": output_id,
                                "output_type": output_type,
                                "protocol": "http"
                            }
                        )
                    )

    def _evaluate_best_practice_rules(
        self,
        pipelines: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Evaluate configuration-driven best practice rules (Phase 2A).

        Loads rules from YAML and evaluates them against configurations.
        Generates findings for rule violations.

        Args:
            pipelines: List of pipeline configurations
            routes: List of route configurations
            inputs: List of input configurations
            outputs: List of output configurations
            result: AnalyzerResult to add findings to
        """
        try:
            # Load and filter rules
            if self._rules_cache is None:
                all_rules = self.rule_loader.load_all_rules(cache=True)
                self._rules_cache = self.rule_loader.filter_enabled_only(all_rules)

            rules = self._rules_cache
            rules_evaluated = 0

            # Build context for relationship rules
            context = {
                "pipelines": pipelines,
                "routes": routes,
                "inputs": inputs,
                "outputs": outputs
            }

            # Evaluate rules against each configuration type
            # Check pipelines
            for pipeline in pipelines:
                pipeline_id = pipeline.get("id", "unknown")
                functions = pipeline.get("functions", pipeline.get("conf", {}).get("functions", []))

                # Evaluate pipeline-level rules
                for rule in rules:
                    if rule.category in ["performance", "best_practice"]:
                        violated = self.rule_evaluator.evaluate_rule(rule, pipeline, context)
                        rules_evaluated += 1

                        if violated:
                            self._create_rule_violation_finding(
                                rule, pipeline_id, "pipeline", result
                            )

                # Evaluate function-level rules
                if isinstance(functions, list):
                    for func_idx, function in enumerate(functions):
                        if not isinstance(function, dict):
                            continue

                        for rule in rules:
                            # Check for deprecated functions
                            if "deprecated" in rule.id:
                                violated = self.rule_evaluator.evaluate_rule(rule, function, context)
                                rules_evaluated += 1

                                if violated:
                                    self._create_rule_violation_finding(
                                        rule,
                                        f"{pipeline_id}.functions[{func_idx}]",
                                        "function",
                                        result
                                    )

            # Check routes for relationship violations
            for route in routes:
                route_id = route.get("id", "unknown")

                for rule in rules:
                    if rule.check_type == "relationship":
                        violated = self.rule_evaluator.evaluate_rule(rule, route, context)
                        rules_evaluated += 1

                        if violated:
                            self._create_rule_violation_finding(
                                rule, route_id, "route", result
                            )

            # Check outputs for security violations
            for output in outputs:
                output_id = output.get("id", "unknown")

                for rule in rules:
                    if rule.category == "security":
                        violated = self.rule_evaluator.evaluate_rule(rule, output, context)
                        rules_evaluated += 1

                        if violated:
                            self._create_rule_violation_finding(
                                rule, output_id, "output", result
                            )

            # Store rules evaluated count in metadata
            result.metadata["rules_evaluated"] = rules_evaluated

            self.log.debug(
                "best_practice_rules_evaluated",
                rules_count=len(rules),
                evaluations=rules_evaluated,
                violations=len([f for f in result.findings if f.id.startswith("rule-")])
            )

        except Exception as e:
            # Don't fail analysis if rule evaluation fails
            self.log.warning("rule_evaluation_failed", error=str(e))
            result.metadata["rules_evaluated"] = 0

    def _create_rule_violation_finding(
        self,
        rule,
        component_id: str,
        component_type: str,
        result: AnalyzerResult
    ) -> None:
        """
        Create a finding from a rule violation.

        Args:
            rule: BestPracticeRule that was violated
            component_id: ID of the affected component
            component_type: Type of component (pipeline, route, function, etc.)
            result: AnalyzerResult to add finding to
        """
        result.add_finding(
            Finding(
                id=f"{rule.id}-{component_id}",
                category="config",
                severity=rule.severity_if_violated,
                title=f"{rule.name}: {component_id}",
                description=f"{rule.description} (Component: {component_type} '{component_id}')\n\nRationale: {rule.rationale}",
                affected_components=[f"{component_type}-{component_id}"],
                remediation_steps=[
                    f"Review {component_type} '{component_id}' configuration",
                    f"Apply best practice: {rule.name}",
                    "Refer to documentation for implementation guidance",
                    "Test changes in non-production environment first"
                ],
                documentation_links=[rule.documentation_link],
                estimated_impact=f"Best practice violation: {rule.rationale}",
                confidence_level="high",
                metadata={
                    "rule_id": rule.id,
                    "rule_category": rule.category,
                    "component_id": component_id,
                    "component_type": component_type,
                    "check_type": rule.check_type
                }
            )
        )

    def _analyze_pipeline_efficiency(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze pipeline efficiency and function ordering (Phase 2B).

        Detects:
        - Expensive functions (regex, lookup, eval) placed before filtering
        - Multiple regex operations in single pipeline
        - Missing early-stage volume reduction
        - Lack of caching hints on lookups

        Args:
            pipelines: List of pipeline configurations
            result: AnalyzerResult to add findings to
        """
        # Track efficiency scores for metadata
        efficiency_scores = []
        performance_opportunities = 0

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])

            if not functions:
                continue

            # Calculate efficiency score for this pipeline
            efficiency_score = self._calculate_pipeline_efficiency_score(functions)
            efficiency_scores.append(efficiency_score)

            # Check for expensive functions before filtering
            self._check_function_ordering(pipeline_id, functions, result)

            # Check for performance anti-patterns
            perf_issues = self._check_performance_antipatterns(pipeline_id, functions, result)
            performance_opportunities += perf_issues

        # Store efficiency metadata
        if efficiency_scores:
            result.metadata["pipeline_efficiency_score"] = round(
                sum(efficiency_scores) / len(efficiency_scores), 2
            )
            result.metadata["max_pipeline_efficiency"] = round(max(efficiency_scores), 2)
            result.metadata["min_pipeline_efficiency"] = round(min(efficiency_scores), 2)
        else:
            result.metadata["pipeline_efficiency_score"] = 100.0

        result.metadata["performance_opportunities"] = performance_opportunities

        self.log.debug(
            "pipeline_efficiency_analyzed",
            pipelines=len(pipelines),
            avg_efficiency=result.metadata.get("pipeline_efficiency_score", 100.0),
            opportunities=performance_opportunities
        )

    def _calculate_pipeline_efficiency_score(self, functions: List[Dict[str, Any]]) -> float:
        """
        Calculate efficiency score (0-100) for a pipeline based on function ordering.

        Higher scores indicate better efficiency:
        - Filtering early: +points
        - Expensive operations after filtering: +points
        - Expensive operations before filtering: -points
        - Multiple expensive operations: -points

        Args:
            functions: List of function configurations

        Returns:
            Efficiency score from 0.0 to 100.0
        """
        if not functions:
            return 100.0

        score = 100.0
        expensive_funcs = {"regex", "regex_extract", "lookup", "eval", "grok"}
        filter_funcs = {"drop", "sampling", "eval"}  # eval can be used for filtering

        # Find index of first filtering operation
        first_filter_idx = None
        for idx, func in enumerate(functions):
            func_id = func.get("id", "").lower()
            # Check if this is a filtering operation
            if func_id in filter_funcs:
                # For eval, check if it's actually filtering (has filter:true or disabled field)
                if func_id == "eval":
                    if func.get("conf", {}).get("filter") or "disabled" in func.get("conf", {}):
                        first_filter_idx = idx
                        break
                else:
                    first_filter_idx = idx
                    break

        # Penalize expensive functions before filtering
        for idx, func in enumerate(functions):
            func_id = func.get("id", "").lower()

            if func_id in expensive_funcs:
                # If no filtering or expensive func comes before filtering
                if first_filter_idx is None or idx < first_filter_idx:
                    score -= 15  # Heavy penalty for each expensive func before filtering

        # Count total expensive operations (penalize excessive use)
        expensive_count = sum(
            1 for f in functions if f.get("id", "").lower() in expensive_funcs
        )
        if expensive_count > 3:
            score -= (expensive_count - 3) * 5  # Penalty for each operation over 3

        return max(0.0, min(100.0, round(score, 2)))

    def _check_function_ordering(
        self,
        pipeline_id: str,
        functions: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Check for suboptimal function ordering.

        Flags expensive operations (regex, lookup, eval) that appear before
        filtering operations (drop, sampling).

        Args:
            pipeline_id: Pipeline identifier
            functions: List of function configurations
            result: AnalyzerResult to add findings to
        """
        expensive_funcs = {"regex", "regex_extract", "lookup", "eval", "grok"}
        filter_funcs = {"drop", "sampling"}

        # Find first filtering operation
        first_filter_idx = None
        for idx, func in enumerate(functions):
            if func.get("id", "") in filter_funcs:
                first_filter_idx = idx
                break

        # If we have filtering, check for expensive operations before it
        if first_filter_idx is not None:
            expensive_before_filter = []
            for idx in range(first_filter_idx):
                func = functions[idx]
                func_id = func.get("id", "")
                if func_id in expensive_funcs:
                    expensive_before_filter.append((idx + 1, func_id))  # 1-indexed for user display

            if expensive_before_filter:
                func_list = ", ".join([f"'{f[1]}' (position {f[0]})" for f in expensive_before_filter])

                result.add_finding(
                    Finding(
                        id=f"config-perf-function-ordering-{pipeline_id}",
                        category="config",
                        severity="medium",
                        title=f"Suboptimal Function Ordering: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' has expensive operations before filtering: {func_list}",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        remediation_steps=[
                            f"Move filtering functions (drop, sampling) earlier in pipeline '{pipeline_id}'",
                            "Place expensive operations (regex, lookup, eval) after volume reduction",
                            "This reduces the number of events processed by expensive functions",
                            "Expected performance improvement: 20-50% depending on filter selectivity"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/pipelines-performance/",
                            "https://docs.cribl.io/stream/best-practices/"
                        ],
                        estimated_impact="Processing unnecessary events with expensive operations - increased CPU usage",
                        confidence_level="high",
                        metadata={
                            "pipeline_id": pipeline_id,
                            "expensive_functions_before_filter": len(expensive_before_filter),
                            "first_filter_position": first_filter_idx + 1,
                            "functions_to_reorder": [f[1] for f in expensive_before_filter]
                        }
                    )
                )

    def _check_performance_antipatterns(
        self,
        pipeline_id: str,
        functions: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> int:
        """
        Check for performance anti-patterns in pipeline.

        Detects:
        - Multiple regex operations (>2)
        - Lookup functions without caching hints
        - Complex eval expressions

        Args:
            pipeline_id: Pipeline identifier
            functions: List of function configurations
            result: AnalyzerResult to add findings to

        Returns:
            Number of performance issues found
        """
        issues_found = 0

        # Check for multiple regex operations
        regex_funcs = [f for f in functions if f.get("id", "") in ["regex", "regex_extract", "grok"]]
        if len(regex_funcs) > 2:
            issues_found += 1
            result.add_finding(
                Finding(
                    id=f"config-perf-multiple-regex-{pipeline_id}",
                    category="config",
                    severity="medium",
                    title=f"Multiple Regex Operations: {pipeline_id}",
                    description=f"Pipeline '{pipeline_id}' contains {len(regex_funcs)} regex-based operations, which can be CPU-intensive",
                    affected_components=[f"pipeline-{pipeline_id}"],
                    remediation_steps=[
                        f"Consider consolidating regex operations in pipeline '{pipeline_id}'",
                        "Combine multiple regex patterns into single function where possible",
                        "Use simpler string operations (startswith, contains) when regex isn't needed",
                        "Profile pipeline performance to identify bottlenecks"
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/regex-extract-function/",
                        "https://docs.cribl.io/stream/pipelines-performance/"
                    ],
                    estimated_impact="High CPU usage from multiple regex evaluations per event",
                    confidence_level="high",
                    metadata={
                        "pipeline_id": pipeline_id,
                        "regex_function_count": len(regex_funcs),
                        "regex_functions": [f.get("id") for f in regex_funcs]
                    }
                )
            )

        # Check for lookup functions without caching
        for func in functions:
            if func.get("id") == "lookup":
                conf = func.get("conf", {})
                # Check if caching is explicitly disabled or not configured
                if not conf.get("cache", {}).get("enabled", False):
                    issues_found += 1
                    result.add_finding(
                        Finding(
                            id=f"config-perf-lookup-no-cache-{pipeline_id}",
                            category="config",
                            severity="low",
                            title=f"Lookup Without Caching: {pipeline_id}",
                            description=f"Pipeline '{pipeline_id}' has lookup function without caching enabled",
                            affected_components=[f"pipeline-{pipeline_id}"],
                            remediation_steps=[
                                f"Enable caching for lookup function in pipeline '{pipeline_id}'",
                                "Set appropriate TTL based on lookup data freshness requirements",
                                "Monitor cache hit rate after enabling",
                                "Test with representative data volume"
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/lookup-function/"
                            ],
                            estimated_impact="Repeated lookups without caching - increased latency and external system load",
                            confidence_level="medium",
                            metadata={
                                "pipeline_id": pipeline_id,
                                "function": "lookup",
                                "cache_enabled": False
                            }
                        )
                    )

        return issues_found

    def _analyze_route_conflicts(
        self,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze route configurations for conflicts and issues (Phase 2C).

        Detects:
        - Overlapping route filters (multiple routes matching same events)
        - Unreachable routes (shadowed by earlier catch-all routes)
        - Invalid or always-true/always-false filter expressions
        - Routes without filters (catch-all routes)
        """
        if not routes:
            result.metadata["route_conflicts_found"] = 0
            result.metadata["unreachable_routes"] = 0
            return

        conflicts_found = 0
        unreachable_count = 0

        # Check for overlapping and unreachable routes
        for i, route in enumerate(routes):
            route_id = route.get("id", f"route_{i}")
            route_filter = route.get("filter", "")

            # Check if this is a catch-all route (no filter or always-true filter)
            is_catchall = self._is_catchall_route(route_filter)

            if is_catchall and i < len(routes) - 1:
                # Catch-all route that's not last - makes all following routes unreachable
                following_routes = routes[i + 1:]
                unreachable_count += len(following_routes)

                result.add_finding(
                    Finding(
                        id=f"config-route-catchall-not-last-{route_id}",
                        category="config",
                        severity="high",
                        title=f"Catch-All Route Not Last: {route_id}",
                        description=f"Route '{route_id}' at position {i + 1} has no filter (catch-all), making {len(following_routes)} subsequent routes unreachable",
                        affected_components=[f"route-{route_id}"] + [f"route-{r.get('id', f'route_{i+1+j}')}" for j, r in enumerate(following_routes)],
                        remediation_steps=[
                            f"Move catch-all route '{route_id}' to the end of the route list",
                            "Or add a filter to make this route more specific",
                            "Review all routes after this one - they will never be matched",
                            "Consider removing unreachable routes to simplify configuration"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/routes/",
                            "https://docs.cribl.io/stream/routes-best-practices/"
                        ],
                        estimated_impact=f"{len(following_routes)} routes are unreachable and serve no purpose",
                        confidence_level="high",
                        metadata={
                            "route_id": route_id,
                            "route_position": i + 1,
                            "unreachable_routes": len(following_routes),
                            "unreachable_route_ids": [r.get("id", f"route_{i+1+j}") for j, r in enumerate(following_routes)]
                        }
                    )
                )
                conflicts_found += 1

            # Check for overlapping routes (simple heuristic: same or very similar filters)
            for j in range(i + 1, len(routes)):
                other_route = routes[j]
                other_id = other_route.get("id", f"route_{j}")
                other_filter = other_route.get("filter", "")

                if self._filters_overlap(route_filter, other_filter):
                    conflicts_found += 1
                    result.add_finding(
                        Finding(
                            id=f"config-route-overlap-{route_id}-{other_id}",
                            category="config",
                            severity="medium",
                            title=f"Potentially Overlapping Routes: {route_id} and {other_id}",
                            description=f"Routes '{route_id}' (position {i + 1}) and '{other_id}' (position {j + 1}) may have overlapping filters",
                            affected_components=[f"route-{route_id}", f"route-{other_id}"],
                            remediation_steps=[
                                f"Review filters for routes '{route_id}' and '{other_id}'",
                                "Ensure route ordering reflects intended precedence",
                                "Consider making filters mutually exclusive if possible",
                                "Test with sample data to verify routing behavior"
                            ],
                            documentation_links=[
                                "https://docs.cribl.io/stream/routes/",
                                "https://docs.cribl.io/stream/filtering-data/"
                            ],
                            estimated_impact="Events may be routed unpredictably if multiple routes match",
                            confidence_level="medium",
                            metadata={
                                "route_1": route_id,
                                "route_1_position": i + 1,
                                "route_1_filter": route_filter,
                                "route_2": other_id,
                                "route_2_position": j + 1,
                                "route_2_filter": other_filter
                            }
                        )
                    )

            # Validate filter expressions
            if route_filter and not self._is_valid_filter_expression(route_filter):
                conflicts_found += 1
                result.add_finding(
                    Finding(
                        id=f"config-route-invalid-filter-{route_id}",
                        category="config",
                        severity="high",
                        title=f"Invalid Route Filter Expression: {route_id}",
                        description=f"Route '{route_id}' has a potentially invalid filter expression",
                        affected_components=[f"route-{route_id}"],
                        remediation_steps=[
                            f"Review and test filter expression for route '{route_id}'",
                            "Ensure expression follows Cribl expression syntax",
                            "Test filter with sample events",
                            "Check for syntax errors or undefined fields"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/filtering-data/",
                            "https://docs.cribl.io/stream/expressions/"
                        ],
                        estimated_impact="Route may not function as intended or cause processing errors",
                        confidence_level="medium",
                        metadata={
                            "route_id": route_id,
                            "filter_expression": route_filter
                        }
                    )
                )

        result.metadata["route_conflicts_found"] = conflicts_found
        result.metadata["unreachable_routes"] = unreachable_count

    def _is_catchall_route(self, route_filter: str) -> bool:
        """
        Check if a route filter is a catch-all (no filter or always-true).

        Args:
            route_filter: The filter expression

        Returns:
            True if this is a catch-all route
        """
        if not route_filter or route_filter.strip() == "":
            return True

        # Check for always-true expressions
        always_true_patterns = ["true", "1==1", "1 == 1", "'true'"]
        normalized = route_filter.strip().lower()

        return normalized in always_true_patterns

    def _filters_overlap(self, filter1: str, filter2: str) -> bool:
        """
        Check if two route filters potentially overlap.

        This is a simple heuristic check. For more sophisticated analysis,
        would need full expression parsing and SAT solving.

        Args:
            filter1: First filter expression
            filter2: Second filter expression

        Returns:
            True if filters might overlap
        """
        # If either is catch-all, they definitely overlap
        if self._is_catchall_route(filter1) or self._is_catchall_route(filter2):
            return True

        # If filters are identical, they overlap
        if filter1.strip() == filter2.strip():
            return True

        # Simple heuristic: check if filters reference the same fields
        # This is not perfect but catches common cases
        filter1_lower = filter1.lower()
        filter2_lower = filter2.lower()

        # Extract potential field names (simple pattern matching)
        import re
        field_pattern = r'\b([a-z_][a-z0-9_]*)\b'

        fields1 = set(re.findall(field_pattern, filter1_lower))
        fields2 = set(re.findall(field_pattern, filter2_lower))

        # Remove common keywords
        keywords = {'true', 'false', 'null', 'and', 'or', 'not', 'in', 'match'}
        fields1 -= keywords
        fields2 -= keywords

        # If they reference the same fields, they might overlap
        # This is conservative - better to flag potential issues
        if fields1 & fields2:  # Intersection
            return True

        return False

    def _is_valid_filter_expression(self, filter_expr: str) -> bool:
        """
        Perform basic validation of filter expression syntax.

        This is a simple sanity check, not a full parser.

        Args:
            filter_expr: The filter expression to validate

        Returns:
            True if expression appears valid
        """
        if not filter_expr or not filter_expr.strip():
            return True  # Empty filter is valid (catch-all)

        # Check for balanced parentheses
        paren_count = 0
        for char in filter_expr:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            if paren_count < 0:
                return False

        if paren_count != 0:
            return False

        # Check for balanced quotes
        single_quote_count = filter_expr.count("'")
        double_quote_count = filter_expr.count('"')

        if single_quote_count % 2 != 0 or double_quote_count % 2 != 0:
            return False

        # Check for obvious syntax errors
        invalid_patterns = [
            '&&',  # Should use 'and'
            '||',  # Should use 'or'
            '===', # Triple equals
            '!==', # Not equals equals
        ]

        for pattern in invalid_patterns:
            if pattern in filter_expr:
                return False

        return True

    def _analyze_complexity_metrics(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Analyze configuration complexity and detect duplicate patterns (Phase 2D).

        Calculates:
        - Pipeline complexity scores based on function count and nesting
        - Duplicate configuration patterns across pipelines
        - Complexity-based recommendations for simplification
        """
        if not pipelines:
            result.metadata["avg_pipeline_complexity"] = 0.0
            result.metadata["max_pipeline_complexity"] = 0
            result.metadata["duplicate_patterns_found"] = 0
            return

        complexity_scores = []
        pipeline_patterns = {}  # Track patterns for duplicate detection

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])

            # Calculate complexity score for this pipeline
            complexity = self._calculate_pipeline_complexity(functions)
            complexity_scores.append(complexity)

            # Track function patterns for duplicate detection
            pattern_key = self._get_pipeline_pattern(functions)
            if pattern_key not in pipeline_patterns:
                pipeline_patterns[pattern_key] = []
            pipeline_patterns[pattern_key].append(pipeline_id)

            # Flag overly complex pipelines
            if complexity > 50:  # High complexity threshold
                result.add_finding(
                    Finding(
                        id=f"config-complexity-high-{pipeline_id}",
                        category="config",
                        severity="medium" if complexity <= 75 else "high",
                        title=f"High Pipeline Complexity: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' has complexity score of {complexity} (threshold: 50). High complexity makes pipelines harder to maintain and debug.",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        remediation_steps=[
                            f"Review pipeline '{pipeline_id}' for opportunities to simplify",
                            "Consider splitting into multiple smaller, focused pipelines",
                            "Reduce nesting depth in conditional expressions",
                            "Extract repeated logic into reusable functions or routes"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/pipelines-best-practices/",
                            "https://docs.cribl.io/stream/pipeline-design-patterns/"
                        ],
                        estimated_impact="Complex pipelines are harder to troubleshoot and maintain",
                        confidence_level="high",
                        metadata={
                            "pipeline_id": pipeline_id,
                            "complexity_score": complexity,
                            "function_count": len(functions)
                        }
                    )
                )

            # Flag pipelines with too many functions
            if len(functions) > 10:
                result.add_finding(
                    Finding(
                        id=f"config-complexity-function-count-{pipeline_id}",
                        category="config",
                        severity="low",
                        title=f"Many Functions in Pipeline: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' contains {len(functions)} functions. Consider splitting for better maintainability.",
                        affected_components=[f"pipeline-{pipeline_id}"],
                        remediation_steps=[
                            f"Review if pipeline '{pipeline_id}' can be split into logical stages",
                            "Consider using routes to split processing paths",
                            "Group related functions into separate pipelines"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/pipelines-best-practices/"
                        ],
                        estimated_impact="Large pipelines are harder to understand and maintain",
                        confidence_level="medium",
                        metadata={
                            "pipeline_id": pipeline_id,
                            "function_count": len(functions)
                        }
                    )
                )

        # Detect duplicate pipeline patterns
        duplicate_count = 0
        for pattern_key, pipeline_ids in pipeline_patterns.items():
            if len(pipeline_ids) > 1 and pattern_key != "":  # Multiple pipelines with same pattern
                duplicate_count += 1
                result.add_finding(
                    Finding(
                        id=f"config-complexity-duplicate-pattern-{'-'.join(sorted(pipeline_ids)[:2])}",
                        category="config",
                        severity="low",
                        title=f"Duplicate Pipeline Pattern: {', '.join(pipeline_ids[:3])}{'...' if len(pipeline_ids) > 3 else ''}",
                        description=f"Found {len(pipeline_ids)} pipelines with identical or very similar function configurations: {', '.join(pipeline_ids)}",
                        affected_components=[f"pipeline-{pid}" for pid in pipeline_ids],
                        remediation_steps=[
                            "Consider consolidating duplicate pipelines into a single reusable pipeline",
                            "Use routes to direct different data sources to the same processing logic",
                            "If variations are needed, parameterize the differences",
                            "This reduces maintenance burden and ensures consistency"
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/routes/",
                            "https://docs.cribl.io/stream/pipelines-best-practices/"
                        ],
                        estimated_impact="Duplicate configurations increase maintenance burden and risk of inconsistency",
                        confidence_level="high",
                        metadata={
                            "duplicate_pipeline_ids": pipeline_ids,
                            "pattern_hash": pattern_key[:16]  # First 16 chars of hash
                        }
                    )
                )

        # Store complexity metadata
        if complexity_scores:
            result.metadata["avg_pipeline_complexity"] = round(
                sum(complexity_scores) / len(complexity_scores), 2
            )
            result.metadata["max_pipeline_complexity"] = max(complexity_scores)
            result.metadata["min_pipeline_complexity"] = min(complexity_scores)
        else:
            result.metadata["avg_pipeline_complexity"] = 0.0
            result.metadata["max_pipeline_complexity"] = 0
            result.metadata["min_pipeline_complexity"] = 0

        result.metadata["duplicate_patterns_found"] = duplicate_count

    def _calculate_pipeline_complexity(self, functions: List[Dict[str, Any]]) -> int:
        """
        Calculate complexity score for a pipeline.

        Factors:
        - Number of functions (2 points each)
        - Nested expressions/conditionals (5 points each level)
        - Function configuration complexity (1-3 points based on config size)

        Returns:
            Complexity score (0-100+, higher = more complex)
        """
        if not functions:
            return 0

        complexity = 0

        # Base complexity from function count
        complexity += len(functions) * 2

        # Analyze each function's configuration
        for func in functions:
            func_conf = func.get("conf", {})

            # Check for nested conditions/filters
            filter_expr = func_conf.get("filter", "")
            if filter_expr:
                # Count nesting depth by parentheses
                max_depth = 0
                current_depth = 0
                for char in filter_expr:
                    if char == '(':
                        current_depth += 1
                        max_depth = max(max_depth, current_depth)
                    elif char == ')':
                        current_depth -= 1

                complexity += max_depth * 5

            # Complex eval expressions
            eval_expr = func_conf.get("expression", "")
            if eval_expr and len(eval_expr) > 50:
                complexity += 3

            # Large configuration objects indicate complexity
            if len(func_conf) > 5:
                complexity += 2

        return min(complexity, 100)  # Cap at 100

    def _get_pipeline_pattern(self, functions: List[Dict[str, Any]]) -> str:
        """
        Generate a pattern signature for a pipeline based on function sequence.

        Used to detect duplicate or very similar pipelines.

        Args:
            functions: List of function configurations

        Returns:
            Pattern hash string
        """
        if not functions:
            return ""

        # Create a simplified pattern based on function IDs and key config
        import hashlib

        pattern_parts = []
        for func in functions:
            func_id = func.get("id", "unknown")
            # Include key configuration that affects behavior
            conf = func.get("conf", {})

            # For pattern matching, we care about:
            # - Function type (id)
            # - Presence of filter (not exact value)
            # - Major config keys
            has_filter = "yes" if conf.get("filter") else "no"
            has_expression = "yes" if conf.get("expression") else "no"

            pattern_parts.append(f"{func_id}:{has_filter}:{has_expression}")

        pattern_str = "|".join(pattern_parts)

        # Hash for compact comparison
        return hashlib.md5(pattern_str.encode()).hexdigest()

    async def _check_advanced_security(
        self,
        pipelines: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Perform advanced security checks (Phase 2E).

        Checks:
        - PII/sensitive data handling in pipelines
        - Data masking configurations
        - Encryption in transit for outputs
        - Sensitive field exposure
        """
        pii_issues = 0
        masking_issues = 0
        encryption_issues = 0

        # Common PII field patterns
        pii_patterns = {
            "ssn": ["ssn", "social_security", "social security number"],
            "credit_card": ["ccn", "credit_card", "creditcard", "card_number", "cardnumber"],
            "email": ["email", "email_address"],
            "phone": ["phone", "telephone", "phone_number"],
            "ip_address": ["ip", "ip_addr", "ipaddress", "client_ip"],
            "password": ["password", "passwd", "pwd"],
            "api_key": ["api_key", "apikey", "api_token", "access_token"],
        }

        # Check pipelines for PII handling
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])

            # Track fields being processed
            fields_processed = set()
            masked_fields = set()

            for func in functions:
                func_id = func.get("id", "")
                func_conf = func.get("conf", {})

                # Collect fields being processed
                if "field" in func_conf:
                    fields_processed.add(func_conf["field"].lower())
                if "fields" in func_conf:
                    for field in func_conf.get("fields", []):
                        if isinstance(field, str):
                            fields_processed.add(field.lower())

                # Track masked fields
                if func_id in ["mask", "redact"]:
                    if "fields" in func_conf:
                        for field in func_conf.get("fields", []):
                            if isinstance(field, str):
                                masked_fields.add(field.lower())

                # Check eval expressions for PII references
                if "expression" in func_conf:
                    expr = func_conf["expression"].lower()
                    for pii_type, patterns in pii_patterns.items():
                        for pattern in patterns:
                            if pattern in expr and pattern not in str(masked_fields):
                                pii_issues += 1
                                result.add_finding(
                                    Finding(
                                        id=f"config-sec-pii-{pii_type}-{pipeline_id}",
                                        category="security",
                                        severity="high",
                                        title=f"Potential {pii_type.upper()} Exposure: {pipeline_id}",
                                        description=f"Pipeline '{pipeline_id}' references potential PII field '{pattern}' without masking",
                                        affected_components=[f"pipeline-{pipeline_id}"],
                                        remediation_steps=[
                                            f"Review if field '{pattern}' in pipeline '{pipeline_id}' contains PII",
                                            "Add mask/redact function before sending to outputs",
                                            "Ensure compliance with data protection regulations (GDPR, CCPA)",
                                            "Consider using encryption for sensitive data in transit"
                                        ],
                                        documentation_links=[
                                            "https://docs.cribl.io/stream/mask-function/",
                                            "https://docs.cribl.io/stream/redact-function/",
                                            "https://docs.cribl.io/stream/data-privacy/"
                                        ],
                                        estimated_impact="Potential PII leakage - regulatory compliance risk",
                                        confidence_level="medium",
                                        metadata={
                                            "pipeline_id": pipeline_id,
                                            "pii_type": pii_type,
                                            "field_pattern": pattern
                                        }
                                    )
                                )

            # Check for unmasked PII fields
            for field in fields_processed:
                for pii_type, patterns in pii_patterns.items():
                    if any(pattern in field for pattern in patterns):
                        if field not in masked_fields:
                            masking_issues += 1
                            result.add_finding(
                                Finding(
                                    id=f"config-sec-unmasked-{field}-{pipeline_id}",
                                    category="security",
                                    severity="medium",
                                    title=f"Unmasked Sensitive Field: {pipeline_id}",
                                    description=f"Pipeline '{pipeline_id}' processes field '{field}' which may contain {pii_type} without masking",
                                    affected_components=[f"pipeline-{pipeline_id}"],
                                    remediation_steps=[
                                        f"Add masking for field '{field}' in pipeline '{pipeline_id}'",
                                        "Use mask or redact function to protect sensitive data",
                                        "Verify field contents before removing masking"
                                    ],
                                    documentation_links=[
                                        "https://docs.cribl.io/stream/mask-function/"
                                    ],
                                    estimated_impact="Sensitive data may be exposed in logs/outputs",
                                    confidence_level="medium",
                                    metadata={
                                        "pipeline_id": pipeline_id,
                                        "field": field,
                                        "pii_type": pii_type
                                    }
                                )
                            )

        # Store security metadata
        result.metadata["pii_exposure_risks"] = pii_issues
        result.metadata["unmasked_sensitive_fields"] = masking_issues
        result.metadata["encryption_issues"] = encryption_issues

    def _calculate_compliance_score(self, result: AnalyzerResult) -> float:
        """
        Calculate configuration compliance score (0-100).

        Deducts points based on finding severity:
        - Critical: -20 points each
        - High: -10 points each
        - Medium: -5 points each
        - Low: -2 points each

        Args:
            result: AnalyzerResult with findings

        Returns:
            Compliance score from 0.0 to 100.0
        """
        base_score = 100.0

        for finding in result.findings:
            if finding.severity == "critical":
                base_score -= 20
            elif finding.severity == "high":
                base_score -= 10
            elif finding.severity == "medium":
                base_score -= 5
            elif finding.severity == "low":
                base_score -= 2

        # Ensure score stays within 0-100 range
        return max(0.0, min(100.0, round(base_score, 2)))

    def _generate_recommendations(self, result: AnalyzerResult) -> None:
        """
        Generate actionable recommendations based on findings.

        Groups related findings and creates recommendations for:
        - Cleaning up unused components
        - Migrating deprecated functions
        - Securing credentials
        - Fixing syntax errors

        Args:
            result: AnalyzerResult to add recommendations to
        """
        # Recommendation 1: Clean up unused components
        unused_findings = [f for f in result.findings if "unused" in f.id.lower()]
        if unused_findings:
            unused_pipelines = [f for f in unused_findings if "pipeline" in f.id.lower()]
            unused_outputs = [f for f in unused_findings if "output" in f.id.lower()]

            result.add_recommendation(
                Recommendation(
                    id="rec-config-cleanup-unused",
                    type="optimization",
                    priority="p3",
                    title="Remove Unused Configuration Components",
                    description=f"Remove {len(unused_pipelines)} unused pipelines and {len(unused_outputs)} unused outputs to reduce configuration complexity",
                    rationale="Unused components increase configuration maintenance burden and can cause confusion during troubleshooting",
                    implementation_steps=[
                        "Review list of unused components and verify they are truly not needed",
                        "Document any components being kept for future use",
                        "Remove unused pipelines from configuration",
                        "Remove unused outputs from configuration",
                        "Commit configuration changes with clear documentation",
                        "Monitor for any unexpected issues after cleanup"
                    ],
                    before_state=f"Configuration contains {len(unused_pipelines)} unused pipelines and {len(unused_outputs)} unused outputs",
                    after_state="Configuration contains only actively-used components",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Faster configuration load and validation",
                        cost_savings=f"Reduced idle connections from {len(unused_outputs)} unused outputs",
                        time_to_implement="30-60 minutes"
                    ),
                    implementation_effort="low",
                    related_findings=[f.id for f in unused_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/pipelines/",
                        "https://docs.cribl.io/stream/destinations/"
                    ]
                )
            )

        # Recommendation 2: Migrate deprecated functions
        deprecated_findings = [f for f in result.findings if "deprecated" in f.id.lower()]
        if deprecated_findings:
            result.add_recommendation(
                Recommendation(
                    id="rec-config-migrate-deprecated",
                    type="best_practice",
                    priority="p2",
                    title="Migrate Deprecated Functions to Modern Replacements",
                    description=f"Update {len(deprecated_findings)} deprecated function(s) to their modern replacements",
                    rationale="Deprecated functions may have degraded performance and will eventually be removed in future Cribl versions",
                    implementation_steps=[
                        "Review each deprecated function and its replacement",
                        "Test replacement functions in non-production environment",
                        "Update pipeline configurations with new function types",
                        "Verify behavior matches expectations with sample data",
                        "Deploy updated pipelines to production",
                        "Monitor for any processing differences"
                    ],
                    before_state=f"{len(deprecated_findings)} pipelines use deprecated functions",
                    after_state="All pipelines use current, supported function types",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="5-10% improvement in pipeline processing speed",
                        risk_reduction="Eliminates future compatibility issues",
                        time_to_implement="1-2 hours per deprecated function"
                    ),
                    implementation_effort="medium",
                    related_findings=[f.id for f in deprecated_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/functions/",
                        "https://docs.cribl.io/stream/pipelines/"
                    ]
                )
            )

        # Recommendation 3: Fix security issues
        security_findings = [f for f in result.findings if "security" in f.id.lower()]
        if security_findings:
            hardcoded_creds = [f for f in security_findings if "hardcoded" in f.id.lower()]
            tls_issues = [f for f in security_findings if "tls" in f.id.lower()]

            result.add_recommendation(
                Recommendation(
                    id="rec-config-fix-security",
                    type="security",
                    priority="p0" if hardcoded_creds else "p1",
                    title="Address Security Misconfigurations",
                    description=f"Fix {len(security_findings)} security issue(s) including {len(hardcoded_creds)} hardcoded credentials and {len(tls_issues)} unencrypted connections",
                    rationale="Security misconfigurations expose sensitive data and credentials, increasing risk of data breaches",
                    implementation_steps=[
                        "IMMEDIATE: Remove all hardcoded credentials from configurations",
                        "Migrate credentials to environment variables or secrets management",
                        "Enable TLS/HTTPS for all external connections",
                        "Review and update authentication mechanisms",
                        "Conduct security audit of all output configurations",
                        "Implement credential rotation policy"
                    ],
                    before_state=f"{len(security_findings)} security misconfigurations detected",
                    after_state="All credentials secured, all connections encrypted",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Eliminates credential exposure risk, meets SOC2/PCI-DSS requirements",
                        time_to_implement="2-4 hours"
                    ),
                    implementation_effort="medium",
                    related_findings=[f.id for f in security_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/securing-cribl-stream/",
                        "https://docs.cribl.io/stream/environment-variables/"
                    ]
                )
            )

        # Recommendation 4: Fix critical syntax errors
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        if critical_findings:
            result.add_recommendation(
                Recommendation(
                    id="rec-config-fix-critical",
                    type="bug_fix",
                    priority="p0",
                    title="Fix Critical Configuration Errors",
                    description=f"Address {len(critical_findings)} critical configuration error(s) that prevent deployment",
                    rationale="Critical errors prevent configurations from being deployed and can cause data processing failures",
                    implementation_steps=[
                        "Review each critical error and its impact",
                        "Fix syntax errors in pipeline configurations",
                        "Validate configuration in Cribl UI",
                        "Test configurations with sample data",
                        "Deploy fixes immediately to prevent data loss"
                    ],
                    before_state=f"{len(critical_findings)} critical errors blocking deployment",
                    after_state="All configurations valid and deployable",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Prevents data processing failures",
                        time_to_implement="Immediate (< 1 hour)"
                    ),
                    implementation_effort="high",
                    related_findings=[f.id for f in critical_findings],
                    documentation_links=[
                        "https://docs.cribl.io/stream/pipelines/",
                        "https://docs.cribl.io/stream/routes/"
                    ]
                )
            )

    def _add_clean_config_finding(
        self,
        result: AnalyzerResult,
        client: CriblAPIClient,
        pipelines: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]]
    ) -> None:
        """
        Add a positive finding when configuration passes all checks.

        Only adds the finding if:
        - No high or critical severity findings exist
        - At least some configuration was analyzed
        - No syntax errors, deprecated functions, or unused components detected

        Args:
            result: AnalyzerResult to potentially add positive finding to
            client: API client with product type information
            pipelines: List of analyzed pipelines
            routes: List of analyzed routes
            inputs: List of analyzed inputs
            outputs: List of analyzed outputs
        """
        # Count findings by severity
        critical_count = len([f for f in result.findings if f.severity == "critical"])
        high_count = len([f for f in result.findings if f.severity == "high"])
        medium_count = len([f for f in result.findings if f.severity == "medium"])
        low_count = len([f for f in result.findings if f.severity == "low"])

        # Count specific issue types
        syntax_errors = result.metadata.get("syntax_errors", 0)
        deprecated = result.metadata.get("deprecated_functions", 0)
        unused = result.metadata.get("unused_components", 0)
        security_issues = result.metadata.get("security_issues", 0)

        # Only add positive finding if:
        # 1. Some configuration was analyzed (total_components > 0)
        # 2. No critical, high, or medium severity issues exist
        # 3. No syntax errors or security issues detected
        # Low-severity findings (like best practice suggestions) are acceptable for "clean" status
        total_components = len(pipelines) + len(routes) + len(inputs) + len(outputs)
        has_significant_issues = (critical_count > 0 or high_count > 0 or medium_count > 0 or
                                 syntax_errors > 0 or security_issues > 0)

        if total_components > 0 and not has_significant_issues:
            # Determine product-specific messaging
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            product_context = (
                "Edge deployments typically maintain clean configurations by design, "
                "with minimal processing logic and straightforward routing to Stream leaders."
                if client.is_edge else
                "This Stream deployment maintains clean configuration practices with "
                "descriptive naming and minimal technical debt."
            )

            # Build summary of what was checked
            checks_summary = []
            if len(pipelines) > 0:
                checks_summary.append(f"{len(pipelines)} pipeline{'s' if len(pipelines) != 1 else ''} with descriptive names")
            if len(routes) > 0:
                checks_summary.append(f"{len(routes)} route{'s' if len(routes) != 1 else ''} actively used")
            if len(outputs) > 0:
                checks_summary.append(f"{len(outputs)} output{'s' if len(outputs) != 1 else ''} properly configured")

            # Mention any low-severity findings if present
            minor_issues_note = ""
            if low_count > 0:
                minor_issues_note = (
                    f"\n\nNote: {low_count} low-priority improvement "
                    f"opportunit{'ies' if low_count != 1 else 'y'} identified for optimization."
                )

            result.add_finding(
                Finding(
                    id="config-clean-deployment",
                    category="config",
                    severity="info",
                    title=f"Clean {product_name} Configuration Detected",
                    description=(
                        f"Configuration analysis completed successfully with no critical "
                        f"or high-severity issues detected.\n\n"
                        f"**Analysis Summary:**\n"
                        f"- {', '.join(checks_summary) if checks_summary else 'Configuration analyzed'}\n"
                        f"- No syntax errors or deprecated functions\n"
                        f"- No security misconfigurations\n"
                        f"- No unused components cluttering configuration\n\n"
                        f"{product_context}{minor_issues_note}"
                    ),
                    affected_components=["configuration"],
                    remediation_steps=[
                        "Continue following current configuration best practices",
                        "Maintain descriptive naming conventions for new components",
                        "Review and remove unused components as they accumulate",
                        "Keep configurations up-to-date with latest Cribl releases"
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/edge/" if client.is_edge else "https://docs.cribl.io/stream/",
                        "https://docs.cribl.io/stream/pipelines/",
                        "https://docs.cribl.io/stream/routes/"
                    ],
                    estimated_impact="Configuration follows best practices and requires no immediate action",
                    confidence_level="high",
                    metadata={
                        "product_type": client.product_type,
                        "pipelines_analyzed": len(pipelines),
                        "routes_analyzed": len(routes),
                        "inputs_analyzed": len(inputs),
                        "outputs_analyzed": len(outputs),
                        "clean_config": True,
                        "low_findings": low_count
                    }
                )
            )
