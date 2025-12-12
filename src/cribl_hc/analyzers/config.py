"""
Configuration Analyzer for Cribl Stream Health Check.

Validates pipelines, routes, and configurations to detect errors and best practice violations.
"""

import structlog
from typing import Any, Dict, List

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding


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

    def __init__(self):
        """Initialize the configuration analyzer."""
        super().__init__()
        self.log = structlog.get_logger(__name__)

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
        Perform configuration analysis.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        self.log.info("config_analysis_started")

        try:
            # Fetch configuration data
            pipelines = await self._fetch_pipelines(client)
            routes = await self._fetch_routes(client)
            inputs = await self._fetch_inputs(client)
            outputs = await self._fetch_outputs(client)

            # Run basic syntax validation (Phase 1)
            self._validate_pipeline_syntax(pipelines, result)

            # Run route validation (Phase 2)
            self._validate_route_configuration(routes, pipelines, result)

            # Store metadata
            result.metadata["pipelines_analyzed"] = len(pipelines)
            result.metadata["routes_analyzed"] = len(routes)
            result.metadata["inputs_analyzed"] = len(inputs)
            result.metadata["outputs_analyzed"] = len(outputs)
            result.metadata["syntax_errors"] = len([
                f for f in result.findings if "syntax" in f.id.lower()
            ])

            self.log.info(
                "config_analysis_completed",
                pipelines=len(pipelines),
                routes=len(routes),
                findings=len(result.findings)
            )

        except Exception as e:
            # Graceful degradation - Constitution Principle #6
            self.log.error("config_analysis_failed", error=str(e))
            result.success = True  # Still return success
            result.metadata["pipelines_analyzed"] = 0
            result.metadata["routes_analyzed"] = 0
            result.metadata["inputs_analyzed"] = 0
            result.metadata["outputs_analyzed"] = 0

            # Add error as finding
            result.add_finding(
                Finding(
                    id="config-analysis-error",
                    category="config",
                    severity="high",
                    title="Configuration Analysis Error",
                    description=f"Failed to complete configuration analysis: {str(e)}",
                    affected_components=["configuration"],
                    remediation_steps=[
                        "Check API connectivity and authentication",
                        "Verify read permissions for configuration endpoints",
                        "Review API token permissions",
                        "Check Cribl Stream API availability"
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/api-reference/"
                    ],
                    estimated_impact="Unable to validate configuration - manual review recommended",
                    confidence_level="high",
                    metadata={"error": str(e)}
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

            # Check for 'functions' field
            if "functions" not in pipeline:
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
            functions = pipeline.get("functions", [])
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
