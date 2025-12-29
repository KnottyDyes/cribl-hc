"""
Data Flow Topology Analyzer for Cribl Stream Health Check.

Analyzes the data flow topology to identify:
- Route configuration issues
- Disconnected or orphaned routes
- Pipeline connectivity problems
- Source to destination path analysis
- Potential data loss points
"""

from typing import Any, Dict, List, Set, Tuple
from collections import defaultdict

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger


class DataFlowTopologyAnalyzer(BaseAnalyzer):
    """
    Analyzer for data flow topology and routing.

    Phase 10 - Data Quality & Topology

    Checks:
    - Route connectivity and ordering
    - Orphaned inputs/outputs
    - Pipeline references
    - Data path validation
    - Cloning and fan-out patterns
    """

    # Maximum recommended routes before performance concerns
    MAX_RECOMMENDED_ROUTES = 50
    MAX_CLONE_DESTINATIONS = 5

    def __init__(self):
        """Initialize the data flow topology analyzer."""
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "dataflow_topology"

    @property
    def supported_products(self) -> List[str]:
        """Dataflow analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Data flow topology analysis, route validation, and connectivity checking"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: routes(1) + pipelines(1) + inputs(1) + outputs(1) = 4.
        """
        return 4

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:routes",
            "read:pipelines",
            "read:inputs",
            "read:outputs"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform data flow topology analysis.

        Args:
            client: Cribl API client

        Returns:
            AnalyzerResult with findings and recommendations
        """
        result = self.create_result()

        try:
            # Fetch all configuration
            routes = await client.get_routes()
            pipelines = await client.get_pipelines()
            inputs = await client.get_inputs()
            outputs = await client.get_outputs()

            result.metadata["route_count"] = len(routes)
            result.metadata["pipeline_count"] = len(pipelines)
            result.metadata["input_count"] = len(inputs)
            result.metadata["output_count"] = len(outputs)

            # Build topology graph
            topology = self._build_topology(routes, pipelines, inputs, outputs)
            result.metadata["topology_edges"] = len(topology["edges"])

            # Analyze routes
            self._analyze_routes(result, routes, pipelines, outputs)

            # Check for orphaned configurations
            self._check_orphaned_configs(result, routes, pipelines, inputs, outputs)

            # Analyze data paths
            self._analyze_data_paths(result, topology)

            # Check for cloning patterns
            self._analyze_cloning(result, routes, pipelines)

            # Check route ordering
            self._analyze_route_ordering(result, routes)

            # Add summary finding
            self._add_summary_finding(result, routes, pipelines, inputs, outputs)

            self.log.info(
                "dataflow_topology_analysis_completed",
                route_count=len(routes),
                pipeline_count=len(pipelines)
            )

        except Exception as e:
            self.log.error("dataflow_topology_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _build_topology(
        self,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a topology graph of data flow.

        Returns a structure with:
        - nodes: All sources, pipelines, and destinations
        - edges: Connections between nodes
        """
        nodes = set()
        edges = []

        # Add all inputs as source nodes
        for inp in inputs:
            input_id = inp.get("id", "unknown")
            nodes.add(f"input:{input_id}")

        # Add all outputs as destination nodes
        for out in outputs:
            output_id = out.get("id", "unknown")
            nodes.add(f"output:{output_id}")

        # Add all pipelines as processing nodes
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            nodes.add(f"pipeline:{pipeline_id}")

        # Build edges from routes
        for route in routes:
            route_id = route.get("id", "unknown")
            pipeline_id = route.get("pipeline", "")
            output_id = route.get("output", "")

            # Route connects to pipeline
            if pipeline_id:
                edges.append({
                    "from": f"route:{route_id}",
                    "to": f"pipeline:{pipeline_id}",
                    "type": "route_to_pipeline"
                })
                nodes.add(f"route:{route_id}")

            # Route connects to output
            if output_id:
                source = f"pipeline:{pipeline_id}" if pipeline_id else f"route:{route_id}"
                edges.append({
                    "from": source,
                    "to": f"output:{output_id}",
                    "type": "to_output"
                })

        # Check inputs with QuickConnect
        for inp in inputs:
            input_id = inp.get("id", "unknown")
            connections = inp.get("connections", []) or []

            for conn in connections:
                output_id = conn.get("output", "")
                pipeline_id = conn.get("pipeline", "")

                if pipeline_id:
                    edges.append({
                        "from": f"input:{input_id}",
                        "to": f"pipeline:{pipeline_id}",
                        "type": "quickconnect"
                    })
                if output_id:
                    source = f"pipeline:{pipeline_id}" if pipeline_id else f"input:{input_id}"
                    edges.append({
                        "from": source,
                        "to": f"output:{output_id}",
                        "type": "quickconnect"
                    })

        return {
            "nodes": nodes,
            "edges": edges
        }

    def _analyze_routes(
        self,
        result: AnalyzerResult,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]]
    ) -> None:
        """Analyze route configuration for issues."""
        pipeline_ids = {p.get("id") for p in pipelines if p.get("id")}
        output_ids = {o.get("id") for o in outputs if o.get("id")}

        # API uses 'disabled' field (True means disabled), not 'enabled'
        enabled_routes = [r for r in routes if not r.get("disabled", False)]
        disabled_routes = len(routes) - len(enabled_routes)

        result.metadata["enabled_routes"] = len(enabled_routes)
        result.metadata["disabled_routes"] = disabled_routes

        # Check for too many routes
        if len(enabled_routes) > self.MAX_RECOMMENDED_ROUTES:
            result.add_finding(
                Finding(
                    id="routes-too-many",
                    title="Many Routes Configured",
                    description=f"Found {len(enabled_routes)} enabled routes. "
                               f"More than {self.MAX_RECOMMENDED_ROUTES} routes may impact performance.",
                    severity="medium",
                    category="dataflow_topology",
                    confidence_level="medium",
                    affected_components=["routes:count"],
                    estimated_impact="Many routes increase filter evaluation time for each event",
                    remediation_steps=[
                        "Consider consolidating similar routes",
                        "Use packs to organize related routes",
                        "Evaluate if all routes are necessary"
                    ],
                    metadata={
                        "route_count": len(enabled_routes),
                        "threshold": self.MAX_RECOMMENDED_ROUTES
                    }
                )
            )

        # Check each route
        catch_all_routes = []
        for route in routes:
            route_id = route.get("id", "unknown")
            # API uses 'disabled' field (True means disabled)
            disabled = route.get("disabled", False)
            pipeline_id = route.get("pipeline", "")
            output_id = route.get("output", "")
            filter_expr = route.get("filter", "true")

            # Check for missing pipeline reference
            if pipeline_id and pipeline_id not in pipeline_ids:
                result.add_finding(
                    Finding(
                        id=f"route-missing-pipeline-{route_id}",
                        title=f"Route References Missing Pipeline: {route_id}",
                        description=f"Route '{route_id}' references pipeline '{pipeline_id}' which doesn't exist.",
                        severity="high",
                        category="dataflow_topology",
                        confidence_level="high",
                        affected_components=[f"route:{route_id}"],
                        estimated_impact="Data will not be processed as expected",
                        remediation_steps=[
                            f"Create the missing pipeline '{pipeline_id}'",
                            f"Or update route '{route_id}' to use an existing pipeline"
                        ],
                        metadata={
                            "route_id": route_id,
                            "missing_pipeline": pipeline_id
                        }
                    )
                )

            # Check for missing output reference
            if output_id and output_id not in output_ids:
                result.add_finding(
                    Finding(
                        id=f"route-missing-output-{route_id}",
                        title=f"Route References Missing Output: {route_id}",
                        description=f"Route '{route_id}' references output '{output_id}' which doesn't exist.",
                        severity="high",
                        category="dataflow_topology",
                        confidence_level="high",
                        affected_components=[f"route:{route_id}"],
                        estimated_impact="Data cannot be delivered to destination",
                        remediation_steps=[
                            f"Create the missing output '{output_id}'",
                            f"Or update route '{route_id}' to use an existing output"
                        ],
                        metadata={
                            "route_id": route_id,
                            "missing_output": output_id
                        }
                    )
                )

            # Check for catch-all routes (no filter or filter=true)
            if not disabled and (not filter_expr or filter_expr == "true"):
                catch_all_routes.append(route_id)

        # Warn about catch-all routes not at the end
        if catch_all_routes and len(catch_all_routes) > 1:
            result.add_finding(
                Finding(
                    id="routes-multiple-catchall",
                    title="Multiple Catch-All Routes",
                    description=f"Found {len(catch_all_routes)} routes with no filter (catch-all): "
                               f"{', '.join(catch_all_routes[:3])}{'...' if len(catch_all_routes) > 3 else ''}. "
                               f"Only the first catch-all route will receive events.",
                    severity="medium",
                    category="dataflow_topology",
                    confidence_level="high",
                    affected_components=[f"route:{r}" for r in catch_all_routes[:5]],
                    estimated_impact="Subsequent catch-all routes will never receive data",
                    remediation_steps=[
                        "Add filters to distinguish routes",
                        "Keep only one catch-all route at the end"
                    ],
                    metadata={
                        "catch_all_routes": catch_all_routes
                    }
                )
            )

    def _check_orphaned_configs(
        self,
        result: AnalyzerResult,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]]
    ) -> None:
        """Check for orphaned configurations not referenced by routes."""
        # Find all referenced pipelines and outputs
        referenced_pipelines = set()
        referenced_outputs = set()

        for route in routes:
            if not route.get("disabled", False):
                pipeline = route.get("pipeline", "")
                output = route.get("output", "")
                if pipeline:
                    referenced_pipelines.add(pipeline)
                if output:
                    referenced_outputs.add(output)

        # Check inputs with QuickConnect
        for inp in inputs:
            connections = inp.get("connections", []) or []
            for conn in connections:
                pipeline = conn.get("pipeline", "")
                output = conn.get("output", "")
                if pipeline:
                    referenced_pipelines.add(pipeline)
                if output:
                    referenced_outputs.add(output)

        # Find orphaned pipelines
        all_pipelines = {p.get("id") for p in pipelines if p.get("id")}
        orphaned_pipelines = all_pipelines - referenced_pipelines

        # Filter out packs (they have different referencing)
        orphaned_pipelines = {p for p in orphaned_pipelines if not p.startswith("pack:")}

        if orphaned_pipelines:
            result.add_finding(
                Finding(
                    id="pipelines-orphaned",
                    title=f"Orphaned Pipelines ({len(orphaned_pipelines)})",
                    description=f"Found {len(orphaned_pipelines)} pipeline(s) not referenced by any route: "
                               f"{', '.join(sorted(orphaned_pipelines)[:5])}{'...' if len(orphaned_pipelines) > 5 else ''}",
                    severity="low",
                    category="dataflow_topology",
                    confidence_level="medium",
                    affected_components=[f"pipeline:{p}" for p in list(orphaned_pipelines)[:10]],
                    estimated_impact="Orphaned pipelines may be unused or referenced by packs",
                    remediation_steps=[
                        "Verify pipelines are not used by packs",
                        "Remove truly unused pipelines"
                    ],
                    metadata={
                        "orphaned_pipelines": sorted(orphaned_pipelines)
                    }
                )
            )

        # Find orphaned outputs
        all_outputs = {o.get("id") for o in outputs if o.get("id")}
        orphaned_outputs = all_outputs - referenced_outputs

        if orphaned_outputs:
            result.add_finding(
                Finding(
                    id="outputs-orphaned",
                    title=f"Orphaned Outputs ({len(orphaned_outputs)})",
                    description=f"Found {len(orphaned_outputs)} output(s) not referenced by any route: "
                               f"{', '.join(sorted(orphaned_outputs)[:5])}{'...' if len(orphaned_outputs) > 5 else ''}",
                    severity="low",
                    category="dataflow_topology",
                    confidence_level="medium",
                    affected_components=[f"output:{o}" for o in list(orphaned_outputs)[:10]],
                    estimated_impact="Orphaned outputs waste resources and may cause confusion",
                    remediation_steps=[
                        "Verify outputs are not used by packs or external systems",
                        "Remove truly unused outputs"
                    ],
                    metadata={
                        "orphaned_outputs": sorted(orphaned_outputs)
                    }
                )
            )

        result.metadata["orphaned_pipelines"] = len(orphaned_pipelines)
        result.metadata["orphaned_outputs"] = len(orphaned_outputs)

    def _analyze_data_paths(self, result: AnalyzerResult, topology: Dict[str, Any]) -> None:
        """Analyze data paths for potential issues."""
        edges = topology["edges"]

        # Count connections per output
        output_connections = defaultdict(int)
        for edge in edges:
            if edge["to"].startswith("output:"):
                output_connections[edge["to"]] += 1

        # Check for outputs with many incoming connections
        busy_outputs = {k: v for k, v in output_connections.items() if v > 10}
        if busy_outputs:
            for output, count in busy_outputs.items():
                output_name = output.replace("output:", "")
                result.add_finding(
                    Finding(
                        id=f"output-many-sources-{output_name}",
                        title=f"Output Has Many Sources: {output_name}",
                        description=f"Output '{output_name}' receives data from {count} sources. "
                                   f"Consider if this is intentional or if consolidation is needed.",
                        severity="info",
                        category="dataflow_topology",
                        confidence_level="medium",
                        affected_components=[output],
                        estimated_impact="Many sources to one output can cause bottlenecks",
                        remediation_steps=[
                            "Verify this fan-in pattern is intentional",
                            "Monitor output for backpressure"
                        ],
                        metadata={
                            "output_id": output_name,
                            "source_count": count
                        }
                    )
                )

    def _analyze_cloning(
        self,
        result: AnalyzerResult,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]]
    ) -> None:
        """Analyze cloning patterns for data fan-out."""
        # Check for clone functions in pipelines
        clone_count = 0

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "unknown")
            functions = pipeline.get("conf", {}).get("functions", [])

            for func in functions:
                if func.get("id") == "clone":
                    clone_count += 1
                    clones = func.get("conf", {}).get("clones", [])

                    if len(clones) > self.MAX_CLONE_DESTINATIONS:
                        result.add_finding(
                            Finding(
                                id=f"pipeline-excessive-cloning-{pipeline_id}",
                                title=f"Excessive Cloning in Pipeline: {pipeline_id}",
                                description=f"Pipeline '{pipeline_id}' clones to {len(clones)} destinations. "
                                           f"Excessive cloning can impact performance.",
                                severity="medium",
                                category="dataflow_topology",
                                confidence_level="high",
                                affected_components=[f"pipeline:{pipeline_id}"],
                                estimated_impact="Each clone multiplies processing overhead",
                                remediation_steps=[
                                    "Evaluate if all clone destinations are necessary",
                                    "Consider using a dedicated cloning pipeline",
                                    "Monitor pipeline performance"
                                ],
                                metadata={
                                    "pipeline_id": pipeline_id,
                                    "clone_count": len(clones)
                                }
                            )
                        )

        result.metadata["clone_functions"] = clone_count

    def _analyze_route_ordering(self, result: AnalyzerResult, routes: List[Dict[str, Any]]) -> None:
        """Analyze route ordering for potential issues."""
        enabled_routes = [r for r in routes if not r.get("disabled", False)]

        # Check for routes that might never match due to ordering
        seen_outputs = set()
        overlapping_routes = []

        for route in enabled_routes:
            route_id = route.get("id", "unknown")
            output = route.get("output", "")
            filter_expr = route.get("filter", "true")
            is_final = route.get("final", True)

            # If a route is final and has no filter, subsequent routes to same output are unreachable
            if is_final and (not filter_expr or filter_expr == "true"):
                if output in seen_outputs:
                    overlapping_routes.append(route_id)

            if output:
                seen_outputs.add(output)

        if overlapping_routes:
            result.add_finding(
                Finding(
                    id="routes-unreachable",
                    title=f"Potentially Unreachable Routes ({len(overlapping_routes)})",
                    description=f"Found {len(overlapping_routes)} route(s) that may be unreachable due to earlier catch-all routes: "
                               f"{', '.join(overlapping_routes[:3])}{'...' if len(overlapping_routes) > 3 else ''}",
                    severity="medium",
                    category="dataflow_topology",
                    confidence_level="medium",
                    affected_components=[f"route:{r}" for r in overlapping_routes[:5]],
                    estimated_impact="Unreachable routes will never receive data",
                    remediation_steps=[
                        "Review route ordering",
                        "Add specific filters to earlier routes",
                        "Remove duplicate or unreachable routes"
                    ],
                    metadata={
                        "unreachable_routes": overlapping_routes
                    }
                )
            )

    def _add_summary_finding(
        self,
        result: AnalyzerResult,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]]
    ) -> None:
        """Add summary finding for data flow topology."""
        issues = len([f for f in result.findings if f.severity in ("high", "critical", "medium")])
        enabled_routes = len([r for r in routes if not r.get("disabled", False)])

        if issues == 0:
            severity = "info"
            status = "Healthy"
            description = f"Data flow topology is well configured. {enabled_routes} routes, {len(pipelines)} pipelines."
        elif issues <= 2:
            severity = "medium"
            status = "Minor Issues"
            description = f"Found {issues} topology issue(s). Review recommendations."
        else:
            severity = "high"
            status = "Needs Attention"
            description = f"Found {issues} topology issue(s). Data flow review recommended."

        result.add_finding(
            Finding(
                id="dataflow-topology-summary",
                title=f"Data Flow Topology: {status}",
                description=description,
                severity=severity,
                category="dataflow_topology",
                confidence_level="high",
                affected_components=["topology:summary"],
                estimated_impact=f"Topology: {len(inputs)} inputs -> {enabled_routes} routes -> {len(pipelines)} pipelines -> {len(outputs)} outputs",
                remediation_steps=[] if severity == "info" else ["Review topology findings"],
                metadata={
                    "route_count": len(routes),
                    "enabled_routes": enabled_routes,
                    "pipeline_count": len(pipelines),
                    "input_count": len(inputs),
                    "output_count": len(outputs),
                    "issue_count": issues
                }
            )
        )
