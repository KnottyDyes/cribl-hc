"""
Storage Optimization Analyzer for Cribl Health Check.

Analyzes storage consumption by destination and identifies data reduction
opportunities including sampling, filtering, and aggregation.

Priority: P3 (Optimization)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class StorageAnalyzer(BaseAnalyzer):
    """
    Analyzer for storage optimization and cost reduction.

    Identifies:
    - High-volume destinations consuming significant storage
    - Data reduction opportunities (sampling, filtering, aggregation)
    - ROI for storage optimizations (GB saved, $ saved, effort)
    - Before/after storage projections

    Priority: P3 (Optimization - significant cost savings potential)

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = StorageAnalyzer()
        ...     result = await analyzer.analyze(client)
        ...     savings_gb = result.metadata.get('potential_savings_gb', 0)
        ...     print(f"Potential savings: {savings_gb:.2f} GB/day")
    """

    # Storage thresholds
    HIGH_VOLUME_THRESHOLD_GB = 1000.0  # 1TB+ per destination
    SAMPLING_CANDIDATE_THRESHOLD_GB = 500.0  # 500GB+ suggests sampling
    FILTERING_CANDIDATE_THRESHOLD_GB = 300.0  # 300GB+ suggests filtering

    # ROI constants (estimated)
    S3_STORAGE_COST_PER_GB_MONTH = 0.023  # AWS S3 Standard
    SPLUNK_STORAGE_COST_PER_GB_DAY = 0.15  # Splunk Cloud ingest pricing
    DEFAULT_STORAGE_COST_PER_GB_MONTH = 0.05  # Generic cloud storage

    # Data reduction estimates (conservative)
    SAMPLING_REDUCTION_PCT = 75  # 75% reduction with 1:4 sampling
    FILTERING_REDUCTION_PCT = 40  # 40% reduction with basic filtering
    AGGREGATION_REDUCTION_PCT = 90  # 90% reduction for metrics

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "storage"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: routes(1) + outputs(1) + pipelines(1) + metrics(1) = 4.
        """
        return 4

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:routes",
            "read:outputs",
            "read:pipelines",
            "read:metrics"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze storage consumption and identify optimization opportunities.

        Automatically adapts based on detected product type.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with storage findings and cost-saving recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            # Detect product type
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            log.info("storage_analysis_started", product=client.product_type, product_name=product_name)

            # Fetch data
            outputs = await self._fetch_outputs(client)
            routes = await self._fetch_routes(client)
            pipelines = await self._fetch_pipelines(client)
            metrics = await self._fetch_metrics(client)

            # Store metadata
            result.metadata["product_type"] = client.product_type
            result.metadata["analysis_timestamp"] = datetime.utcnow().isoformat()
            result.metadata["destination_count"] = len(outputs)

            # Analyze storage consumption
            storage_by_dest = self._calculate_storage_by_destination(outputs)
            result.metadata["storage_by_destination"] = storage_by_dest
            result.metadata["total_bytes"] = sum(storage_by_dest.values())

            # Identify high-volume destinations
            self._identify_high_volume_destinations(outputs, storage_by_dest, result)

            # Identify data reduction opportunities
            self._identify_sampling_opportunities(routes, outputs, storage_by_dest, result)
            self._identify_filtering_opportunities(routes, outputs, storage_by_dest, result)
            self._identify_aggregation_opportunities(routes, pipelines, outputs, storage_by_dest, result)

            # Generate storage optimization recommendations
            self._generate_storage_recommendations(
                outputs, routes, pipelines, storage_by_dest, result
            )

            # Calculate potential savings
            self._calculate_potential_savings(result)

            log.info(
                "storage_analysis_completed",
                product=client.product_type,
                total_bytes=result.metadata["total_bytes"],
                destinations=len(outputs),
                findings=len(result.findings)
            )

        except Exception as e:
            # Graceful degradation
            log.error("storage_analysis_failed", product=client.product_type, error=str(e))
            result.success = True  # Still return success
            result.metadata["total_bytes"] = 0
            result.metadata["destination_count"] = 0

            # Add error finding
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            result.add_finding(
                Finding(
                    id="storage-analysis-error",
                    category="storage",
                    severity="high",
                    title=f"Storage Analysis Error ({product_name})",
                    description=f"Failed to complete storage analysis: {str(e)}",
                    affected_components=["storage"],
                    remediation_steps=[
                        "Check API connectivity",
                        "Verify permissions for metrics and outputs endpoints",
                        f"Review {product_name} API availability"
                    ],
                    estimated_impact="Unable to assess storage optimization opportunities",
                    confidence_level="high",
                    metadata={"error": str(e), "product_type": client.product_type}
                )
            )

        return result

    async def _fetch_outputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch output destinations."""
        try:
            outputs = await client.get_outputs()
            log.debug("outputs_fetched", count=len(outputs))
            return outputs
        except Exception as e:
            log.warning("outputs_fetch_failed", error=str(e))
            return []

    async def _fetch_routes(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch routes."""
        try:
            routes = await client.get_routes()
            log.debug("routes_fetched", count=len(routes))
            return routes
        except Exception as e:
            log.warning("routes_fetch_failed", error=str(e))
            return []

    async def _fetch_pipelines(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch pipelines."""
        try:
            pipelines = await client.get_pipelines()
            log.debug("pipelines_fetched", count=len(pipelines))
            return pipelines
        except Exception as e:
            log.warning("pipelines_fetch_failed", error=str(e))
            return []

    async def _fetch_metrics(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch metrics data."""
        try:
            metrics = await client.get_system_status()
            log.debug("metrics_fetched")
            return metrics
        except Exception as e:
            log.warning("metrics_fetch_failed", error=str(e))
            return {}

    def _calculate_storage_by_destination(
        self, outputs: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Calculate storage consumption by destination."""
        storage_by_dest = {}

        for output in outputs:
            output_id = output.get("id", "unknown")
            stats = output.get("stats", {})
            out_bytes = stats.get("out_bytes_total", 0)

            if out_bytes > 0:
                storage_by_dest[output_id] = out_bytes

        return storage_by_dest

    def _identify_high_volume_destinations(
        self,
        outputs: List[Dict[str, Any]],
        storage_by_dest: Dict[str, int],
        result: AnalyzerResult
    ) -> None:
        """Identify destinations consuming significant storage."""
        high_volume_threshold_bytes = self.HIGH_VOLUME_THRESHOLD_GB * 1_000_000_000

        for output_id, bytes_total in storage_by_dest.items():
            if bytes_total >= high_volume_threshold_bytes:
                gb_total = bytes_total / 1_000_000_000

                result.add_finding(
                    Finding(
                        id=f"storage-high-volume-{output_id}",
                        category="storage",
                        severity="info",
                        title=f"High-Volume Destination: {output_id}",
                        description=(
                            f"Destination '{output_id}' has consumed {gb_total:.2f} GB of storage. "
                            f"Consider data reduction techniques to optimize costs."
                        ),
                        affected_components=[output_id],
                        remediation_steps=[
                            "Review data being sent to this destination",
                            "Evaluate sampling opportunities for non-critical data",
                            "Implement filtering to remove unnecessary events",
                            "Consider aggregation for metrics or repetitive data",
                            "Review retention policies and lifecycle management"
                        ],
                        estimated_impact=f"Potential cost savings through optimization of {gb_total:.2f} GB",
                        confidence_level="high",
                        metadata={
                            "bytes_total": bytes_total,
                            "gb_total": gb_total,
                            "destination": output_id
                        }
                    )
                )

    def _identify_sampling_opportunities(
        self,
        routes: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        storage_by_dest: Dict[str, int],
        result: AnalyzerResult
    ) -> None:
        """Identify routes that could benefit from sampling."""
        sampling_threshold_bytes = self.SAMPLING_CANDIDATE_THRESHOLD_GB * 1_000_000_000

        # Build output ID to type mapping
        output_types = {o.get("id"): o.get("type") for o in outputs}

        for route in routes:
            route_id = route.get("id", "unknown")
            output_id = route.get("output")
            filter_expr = route.get("filter", "true")

            if not output_id or output_id not in storage_by_dest:
                continue

            dest_bytes = storage_by_dest[output_id]
            dest_type = output_types.get(output_id, "unknown")

            # Check if destination is high-volume and route has no sampling
            if dest_bytes >= sampling_threshold_bytes:
                # Check for sampling function in route's pipeline
                pipeline_id = route.get("pipeline")
                has_sampling = "sample" in filter_expr.lower() if filter_expr else False

                if not has_sampling and pipeline_id != "sampling":
                    gb_current = dest_bytes / 1_000_000_000
                    gb_saved = gb_current * (self.SAMPLING_REDUCTION_PCT / 100)

                    result.add_finding(
                        Finding(
                            id=f"storage-sampling-opportunity-{route_id}",
                            category="storage",
                            severity="low",
                            title=f"Sampling Opportunity: {route_id} → {output_id}",
                            description=(
                                f"Route '{route_id}' sends all events to '{output_id}' "
                                f"({gb_current:.2f} GB). Consider sampling for non-critical use cases "
                                f"to reduce storage costs."
                            ),
                            affected_components=[route_id, output_id],
                            remediation_steps=[
                                f"Add sampling to route '{route_id}' or its pipeline",
                                "Configure sample rate (e.g., 1:4 for 25% of events)",
                                "Ensure sampled data meets analytical requirements",
                                "Monitor impact on downstream dashboards/alerts",
                                "Implement gradual rollout to verify effectiveness"
                            ],
                            estimated_impact=(
                                f"Potential savings: ~{gb_saved:.2f} GB "
                                f"({self.SAMPLING_REDUCTION_PCT}% reduction with 1:4 sampling)"
                            ),
                            confidence_level="medium",
                            documentation_links=[
                                "https://docs.cribl.io/stream/sampling-function/",
                                "https://docs.cribl.io/stream/routes/"
                            ],
                            metadata={
                                "route_id": route_id,
                                "output_id": output_id,
                                "current_gb": gb_current,
                                "potential_savings_gb": gb_saved,
                                "reduction_pct": self.SAMPLING_REDUCTION_PCT
                            }
                        )
                    )

    def _identify_filtering_opportunities(
        self,
        routes: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        storage_by_dest: Dict[str, int],
        result: AnalyzerResult
    ) -> None:
        """Identify routes that could benefit from filtering."""
        filtering_threshold_bytes = self.FILTERING_CANDIDATE_THRESHOLD_GB * 1_000_000_000

        for route in routes:
            route_id = route.get("id", "unknown")
            output_id = route.get("output")
            filter_expr = route.get("filter", "true")

            if not output_id or output_id not in storage_by_dest:
                continue

            dest_bytes = storage_by_dest[output_id]

            # Check if destination is high-volume and route has minimal filtering
            if dest_bytes >= filtering_threshold_bytes and filter_expr == "true":
                gb_current = dest_bytes / 1_000_000_000
                gb_saved = gb_current * (self.FILTERING_REDUCTION_PCT / 100)

                result.add_finding(
                    Finding(
                        id=f"storage-filtering-opportunity-{route_id}",
                        category="storage",
                        severity="low",
                        title=f"Filtering Opportunity: {route_id}",
                        description=(
                            f"Route '{route_id}' forwards all events without filtering "
                            f"({gb_current:.2f} GB to '{output_id}'). Review if all events are needed."
                        ),
                        affected_components=[route_id, output_id],
                        remediation_steps=[
                            "Review events being forwarded by this route",
                            "Identify unnecessary event types, sources, or severities",
                            "Add filter expression to route configuration",
                            "Consider dedicated routes for different event priorities",
                            "Monitor downstream impact before full deployment"
                        ],
                        estimated_impact=(
                            f"Potential savings: ~{gb_saved:.2f} GB "
                            f"({self.FILTERING_REDUCTION_PCT}% reduction with targeted filtering)"
                        ),
                        confidence_level="medium",
                        documentation_links=[
                            "https://docs.cribl.io/stream/routes/",
                            "https://docs.cribl.io/stream/cribl-search/"
                        ],
                        metadata={
                            "route_id": route_id,
                            "output_id": output_id,
                            "current_gb": gb_current,
                            "potential_savings_gb": gb_saved,
                            "reduction_pct": self.FILTERING_REDUCTION_PCT
                        }
                    )
                )

    def _identify_aggregation_opportunities(
        self,
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        storage_by_dest: Dict[str, int],
        result: AnalyzerResult
    ) -> None:
        """Identify opportunities for aggregation/rollup (primarily metrics)."""
        # Build pipeline ID to functions mapping
        pipeline_functions = {}
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id")
            conf = pipeline.get("conf", {})
            functions = conf.get("functions", [])
            pipeline_functions[pipeline_id] = functions

        # Look for metrics routes without aggregation
        for route in routes:
            route_id = route.get("id", "unknown")
            filter_expr = route.get("filter", "")
            pipeline_id = route.get("pipeline")
            output_id = route.get("output")

            # Skip if not a metrics route
            if "metric" not in filter_expr.lower():
                continue

            if not output_id or output_id not in storage_by_dest:
                continue

            # Check if pipeline has aggregation
            functions = pipeline_functions.get(pipeline_id, [])
            has_aggregation = any(
                f.get("id") in ["aggregation", "rollup", "aggregator"]
                for f in functions
            )

            if not has_aggregation:
                dest_bytes = storage_by_dest[output_id]
                gb_current = dest_bytes / 1_000_000_000

                # Only suggest if significant volume
                if gb_current > 10:  # 10GB threshold for aggregation suggestion
                    gb_saved = gb_current * (self.AGGREGATION_REDUCTION_PCT / 100)

                    result.add_finding(
                        Finding(
                            id=f"storage-aggregation-opportunity-{route_id}",
                            category="storage",
                            severity="low",
                            title=f"Aggregation Opportunity: {route_id} (Metrics)",
                            description=(
                                f"Metrics route '{route_id}' forwards high-resolution data "
                                f"({gb_current:.2f} GB) without aggregation. Consider rollup "
                                f"for long-term storage."
                            ),
                            affected_components=[route_id, output_id],
                            remediation_steps=[
                                "Evaluate if full-resolution metrics are needed for all use cases",
                                "Implement aggregation/rollup pipeline for long-term storage",
                                "Configure rollup intervals (e.g., 1min → 5min → 1hour)",
                                "Route high-res metrics to hot storage, rollups to cold storage",
                                "Verify dashboards and alerts work with aggregated data"
                            ],
                            estimated_impact=(
                                f"Potential savings: ~{gb_saved:.2f} GB "
                                f"({self.AGGREGATION_REDUCTION_PCT}% reduction with aggregation)"
                            ),
                            confidence_level="medium",
                            documentation_links=[
                                "https://docs.cribl.io/stream/aggregation-function/",
                                "https://docs.cribl.io/stream/rollup-function/"
                            ],
                            metadata={
                                "route_id": route_id,
                                "output_id": output_id,
                                "current_gb": gb_current,
                                "potential_savings_gb": gb_saved,
                                "reduction_pct": self.AGGREGATION_REDUCTION_PCT
                            }
                        )
                    )

    def _generate_storage_recommendations(
        self,
        outputs: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        pipelines: List[Dict[str, Any]],
        storage_by_dest: Dict[str, int],
        result: AnalyzerResult
    ) -> None:
        """Generate actionable storage optimization recommendations."""
        # Find all storage-related findings
        storage_findings = [
            f for f in result.findings
            if "sampling" in f.id or "filtering" in f.id or "aggregation" in f.id
        ]

        if not storage_findings:
            return

        # Calculate total potential savings
        total_savings_gb = sum(
            f.metadata.get("potential_savings_gb", 0)
            for f in storage_findings
        )

        # Calculate cost savings (use S3 as default)
        monthly_cost_savings = total_savings_gb * self.S3_STORAGE_COST_PER_GB_MONTH
        annual_cost_savings = monthly_cost_savings * 12

        # Calculate current total storage
        total_gb = sum(storage_by_dest.values()) / 1_000_000_000

        # Group findings by type
        sampling_findings = [f for f in storage_findings if "sampling" in f.id]
        filtering_findings = [f for f in storage_findings if "filtering" in f.id]
        aggregation_findings = [f for f in storage_findings if "aggregation" in f.id]

        # Create comprehensive recommendation
        result.add_recommendation(
            Recommendation(
                id="rec-storage-optimization",
                type="optimization",
                priority="p2",
                title="Implement Data Reduction Strategies",
                description=(
                    f"Optimize storage consumption across {len(storage_findings)} routes "
                    f"to reduce costs and improve performance. Current storage: {total_gb:.2f} GB, "
                    f"potential savings: {total_savings_gb:.2f} GB ({(total_savings_gb/total_gb*100):.1f}%)."
                ),
                rationale=(
                    "Data reduction techniques (sampling, filtering, aggregation) can "
                    "significantly reduce storage costs without sacrificing analytical value. "
                    "Many use cases don't require full-resolution data retention."
                ),
                implementation_steps=[
                    f"Review {len(sampling_findings)} sampling opportunities for non-critical data",
                    f"Implement filtering on {len(filtering_findings)} high-volume routes",
                    f"Add aggregation to {len(aggregation_findings)} metrics pipelines",
                    "Start with non-production routes to validate effectiveness",
                    "Monitor downstream impact on dashboards and alerts",
                    "Gradually roll out to production with stakeholder approval",
                    "Document data retention policies and reduction rationale"
                ],
                before_state=f"{total_gb:.2f} GB current storage consumption",
                after_state=f"~{(total_gb - total_savings_gb):.2f} GB after optimization ({total_savings_gb:.2f} GB reduction)",
                impact_estimate=ImpactEstimate(
                    performance_improvement=f"{total_savings_gb:.2f} GB storage reduction",
                    cost_savings=f"${annual_cost_savings:.2f}/year (estimated S3 pricing)",
                    time_to_implement="1-2 weeks for phased rollout"
                ),
                implementation_effort="medium",
                related_findings=[f.id for f in storage_findings],
                documentation_links=[
                    "https://docs.cribl.io/stream/sampling-function/",
                    "https://docs.cribl.io/stream/routes/",
                    "https://docs.cribl.io/stream/aggregation-function/"
                ]
            )
        )

    def _calculate_potential_savings(self, result: AnalyzerResult) -> None:
        """Calculate and store potential savings in metadata."""
        # Sum up all potential savings from findings
        total_savings_gb = sum(
            f.metadata.get("potential_savings_gb", 0)
            for f in result.findings
            if f.metadata.get("potential_savings_gb")
        )

        total_gb = result.metadata.get("total_bytes", 0) / 1_000_000_000

        if total_gb > 0:
            savings_pct = (total_savings_gb / total_gb) * 100
        else:
            savings_pct = 0

        result.metadata["potential_savings_gb"] = total_savings_gb
        result.metadata["potential_savings_pct"] = savings_pct
        result.metadata["savings_opportunities"] = len([
            f for f in result.findings
            if "sampling" in f.id or "filtering" in f.id or "aggregation" in f.id
        ])

        log.debug(
            "potential_savings_calculated",
            savings_gb=total_savings_gb,
            savings_pct=savings_pct,
            opportunities=result.metadata["savings_opportunities"]
        )
