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

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "config"

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

        # Detect product type and log appropriately
        product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
        self.log.info("config_analysis_started", product=client.product_type, product_name=product_name)

        try:
            # Fetch configuration data
            pipelines = await self._fetch_pipelines(client)
            routes = await self._fetch_routes(client)
            inputs = await self._fetch_inputs(client)
            outputs = await self._fetch_outputs(client)

            # Store product type in metadata
            result.metadata["product_type"] = client.product_type

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

            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(result)

            # Generate recommendations
            self._generate_recommendations(result)

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
                        title="Pipeline Missing Required 'id' Field",
                        description="Pipeline configuration is missing required 'id' field",
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
                        metadata={"pipeline": pipeline}
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
                        title=f"Pipeline Missing 'functions' Field: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' is missing required 'functions' field",
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
                        metadata={"pipeline_id": pipeline_id}
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
                        title=f"Pipeline 'functions' Must Be Array: {pipeline_id}",
                        description=f"Pipeline '{pipeline_id}' has invalid 'functions' field (must be array)",
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
                        metadata={"pipeline_id": pipeline_id, "functions_type": type(functions).__name__}
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
                            title=f"Invalid Function Type in Pipeline: {pipeline_id}",
                            description=f"Function at index {func_idx} in pipeline '{pipeline_id}' is not an object",
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
                                "function_type": type(function).__name__
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
                            title=f"Function Missing 'id' Field: {pipeline_id}",
                            description=f"Function at index {func_idx} in pipeline '{pipeline_id}' is missing 'id' field",
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
                                "function": function
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
                        title=f"Route References Non-Existent Pipeline: {route_id}",
                        description=f"Route '{route_id}' references pipeline '{pipeline_ref}' which does not exist",
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
                            "available_pipelines": sorted(valid_pipeline_ids)
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
                        title=f"Route Missing Output Destination: {route_id}",
                        description=f"Route '{route_id}' does not specify an output destination",
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
                            "route_id": route_id
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
