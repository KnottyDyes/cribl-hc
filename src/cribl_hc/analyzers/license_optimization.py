"""
Analyzes license consumption patterns, drop rule effectiveness, and licensing efficiency.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class LicenseMetrics(BaseModel):
    """Represents license consumption metrics."""

    total_events: int = 0
    processed_events: int = 0
    dropped_events: int = 0
    license_used_percent: float = 0.0
    license_limit: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    @property
    def events_dropped_percent(self) -> float:
        """Calculate percentage of events dropped."""
        if self.total_events == 0:
            return 0.0
        return (self.dropped_events / self.total_events) * 100

    @property
    def license_remaining_percent(self) -> float:
        """Calculate remaining license percentage."""
        return 100.0 - self.license_used_percent

    @property
    def is_near_exhaustion(self) -> bool:
        """Check if license is near exhaustion."""
        return self.license_used_percent > 85


class DropRuleAnalysis(BaseModel):
    """Represents analysis of a drop rule."""

    pipeline_id: str
    pipeline_name: str
    drop_conditions: list[str] = Field(default_factory=list)
    estimated_dropped_events: int = 0
    effectiveness_score: float = 0.0  # 0-100, higher is better
    complexity_score: int = 0  # Rough complexity metric

    @property
    def is_ineffective(self) -> bool:
        """Check if drop rule is ineffective."""
        return self.effectiveness_score < 5.0  # Less than 5% effectiveness


class PipelineMetrics(BaseModel):
    """Represents processing metrics for a pipeline."""

    id: str
    name: str
    input_events: int = 0
    output_events: int = 0
    processing_time_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0

    @property
    def events_processed(self) -> int:
        """Get number of events processed."""
        return self.input_events

    @property
    def throughput_eps(self) -> float:
        """Calculate events per second throughput."""
        if self.processing_time_ms == 0:
            return 0.0
        return (self.input_events / self.processing_time_ms) * 1000

    @property
    def efficiency_score(self) -> float:
        """Calculate processing efficiency score."""
        if self.input_events == 0:
            return 100.0
        # Lower is better - events per CPU second
        return (self.input_events / max(self.cpu_usage_percent, 1)) * 0.01


class LicenseOptimizationAnalyzer(BaseAnalyzer):
    """
    Analyzes license consumption patterns, drop rule effectiveness, and licensing efficiency
    to identify cost optimization opportunities and ensure optimal license utilization.
    """

    @property
    def objective_name(self) -> str:
        return "license-optimization"

    def get_description(self) -> str:
        return "Analyzes license consumption patterns and identifies optimization opportunities."

    def get_required_permissions(self) -> list[str]:
        return ["read:license", "read:metrics", "read:pipelines", "read:routes", "read:system"]

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]  # License optimization applies to data processing products

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform license optimization analysis.
        """
        result = self.create_result()

        try:
            # Collect license and processing data
            current_license = await self._get_current_license_status(client)
            license_history = await self._get_license_history(client)
            pipelines = await client.get_pipelines()
            await client.get_routes()
            system_metrics = await client.get_metrics()

            if not current_license:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="no-license-data",
                        category="Configuration",
                        severity="info",
                        title="No License Data Available",
                        description="Unable to retrieve license information for analysis.",
                        confidence_level="high",
                        affected_components=["license_management"],
                        remediation_steps=[
                            "Verify API access to license endpoints.",
                            "Check if license monitoring is enabled.",
                        ],
                    )
                )
                return result

            # Perform analyses
            self._analyze_license_exhaustion_risk(result, current_license, license_history, client)
            self._analyze_drop_rule_effectiveness(result, pipelines, client)
            self._analyze_processing_efficiency(result, pipelines, system_metrics, client)
            self._identify_cost_optimization_opportunities(
                result, current_license, pipelines, client
            )
            self._assess_overall_license_health(result, current_license, license_history, client)

        except Exception as e:
            self.log.error(f"Error during license optimization analysis: {e}", exc_info=True)
            result.success = False
            result.error = str(e)

        return result

    async def _get_current_license_status(self, client: CriblAPIClient) -> Optional[LicenseMetrics]:
        """Get current license consumption status."""
        try:
            response = await client.get("system/license")
            data = response.json() if hasattr(response, "json") else response

            # Parse license data - this is a simplified structure
            license_data = data.get("license", {})

            metrics = LicenseMetrics(
                total_events=license_data.get("totalEvents", 0),
                processed_events=license_data.get("processedEvents", 0),
                dropped_events=license_data.get("droppedEvents", 0),
                license_used_percent=license_data.get("usedPercent", 0.0),
                license_limit=license_data.get("limit"),
            )

            # Parse period dates if available
            if period := license_data.get("period"):
                try:
                    metrics.period_start = datetime.fromisoformat(
                        period.get("start", "").replace("Z", "+00:00")
                    )
                    metrics.period_end = datetime.fromisoformat(
                        period.get("end", "").replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            return metrics

        except Exception as e:
            self.log.debug(f"Could not fetch license status: {e}")
            return None

    async def _get_license_history(self, client: CriblAPIClient) -> list[LicenseMetrics]:
        """Get historical license usage data."""
        history = []

        try:
            response = await client.get("system/license/history", params={"days": 30})
            data = response.json() if hasattr(response, "json") else response

            for entry in data.get("items", []):
                metrics = LicenseMetrics(
                    total_events=entry.get("totalEvents", 0),
                    processed_events=entry.get("processedEvents", 0),
                    dropped_events=entry.get("droppedEvents", 0),
                    license_used_percent=entry.get("usedPercent", 0.0),
                    license_limit=entry.get("limit"),
                )

                # Parse date
                if date_str := entry.get("date"):
                    try:
                        # Assume date is in YYYY-MM-DD format
                        metrics.period_start = datetime.strptime(date_str, "%Y-%m-%d")
                        metrics.period_end = metrics.period_start + timedelta(days=1)
                    except (ValueError, TypeError):
                        pass

                history.append(metrics)

        except Exception as e:
            self.log.debug(f"Could not fetch license history: {e}")

        return history

    def _analyze_license_exhaustion_risk(
        self,
        result: AnalyzerResult,
        current: LicenseMetrics,
        history: list[LicenseMetrics],
        client: CriblAPIClient,
    ) -> None:
        """Analyze risk of license exhaustion."""
        # Check current usage level
        if current.is_near_exhaustion:
            days_to_exhaustion = self._predict_exhaustion_days(current, history)

            severity = "critical" if days_to_exhaustion <= 7 else "high"

            result.add_finding(
                self.create_finding(
                    client=client,
                    id="license-exhaustion-risk",
                    category="License",
                    severity=severity,
                    title="License Exhaustion Risk",
                    description=f"License is {current.license_used_percent:.1f}% used. Projected exhaustion in {days_to_exhaustion} days.",
                    confidence_level="high",
                    affected_components=["license_management", "data_processing"],
                    remediation_steps=[
                        "Implement additional drop rules to reduce processed events.",
                        "Review and optimize high-volume pipelines.",
                        "Consider license upgrade if usage continues to grow.",
                        "Monitor license usage daily until resolved.",
                    ],
                )
            )

        # Check for unusual consumption spikes
        if len(history) >= 7:
            avg_usage = sum(h.license_used_percent for h in history[-7:]) / 7
            if current.license_used_percent > avg_usage * 1.5:
                spike_percent = ((current.license_used_percent - avg_usage) / avg_usage) * 100

                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="license-usage-spike",
                        category="License",
                        severity="medium",
                        title="Unusual License Usage Spike",
                        description=f"Current license usage ({current.license_used_percent:.1f}%) is {spike_percent:.0f}% above 7-day average.",
                        confidence_level="medium",
                        affected_components=["license_management"],
                        remediation_steps=[
                            "Investigate recent pipeline changes or data source additions.",
                            "Check for unexpected data volume increases.",
                            "Review recent configuration changes that may affect processing.",
                        ],
                    )
                )

    def _predict_exhaustion_days(
        self, current: LicenseMetrics, history: list[LicenseMetrics]
    ) -> int:
        """Predict days until license exhaustion based on trends."""
        if not history or len(history) < 3:
            # Rough estimate based on current usage
            if current.license_used_percent >= 100:
                return 0
            daily_usage_rate = current.license_used_percent / 30  # Assume 30-day period
            remaining_percent = 100 - current.license_used_percent
            return max(1, int(remaining_percent / daily_usage_rate))

        # Calculate trend from recent history
        recent_usage = [h.license_used_percent for h in history[-7:]]
        if len(recent_usage) >= 2:
            daily_increase = (recent_usage[-1] - recent_usage[0]) / (len(recent_usage) - 1)
            if daily_increase > 0:
                remaining_percent = 100 - current.license_used_percent
                return max(1, int(remaining_percent / daily_increase))

        # Fallback to simple average
        return 30  # Conservative estimate

    def _analyze_drop_rule_effectiveness(
        self, result: AnalyzerResult, pipelines: list[dict[str, Any]], client: CriblAPIClient
    ) -> None:
        """Analyze effectiveness of drop rules in pipelines."""
        drop_analyses = []

        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "")
            pipeline_name = pipeline.get("name", "Unknown")

            # Analyze pipeline configuration for drop rules
            drop_analysis = self._analyze_pipeline_drop_rules(pipeline)
            if drop_analysis:
                drop_analysis.pipeline_id = pipeline_id
                drop_analysis.pipeline_name = pipeline_name
                drop_analyses.append(drop_analysis)

        # Find ineffective drop rules
        ineffective_rules = [analysis for analysis in drop_analyses if analysis.is_ineffective]

        for analysis in ineffective_rules:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"ineffective-drop-rule-{analysis.pipeline_id}",
                    category="License",
                    severity="high",
                    title="Ineffective Drop Rule",
                    description=f"Drop rule in pipeline '{analysis.pipeline_name}' has low effectiveness ({analysis.effectiveness_score:.1f}%).",
                    confidence_level="high",
                    affected_components=["license_optimization", "data_processing"],
                    remediation_steps=[
                        "Review drop rule conditions for relevance.",
                        "Consider strengthening filter criteria.",
                        "Verify drop rule is positioned correctly in pipeline.",
                        f"Current conditions: {', '.join(analysis.drop_conditions[:3])}",
                    ],
                )
            )

        # Overall assessment
        total_dropped = sum(a.estimated_dropped_events for a in drop_analyses)
        if total_dropped < 1000 and len(ineffective_rules) > 0:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="low-overall-drop-effectiveness",
                    category="License",
                    severity="medium",
                    title="Low Overall Drop Rule Effectiveness",
                    description=f"Drop rules are removing minimal data volume. Only {total_dropped} events dropped across {len(drop_analyses)} pipelines.",
                    confidence_level="medium",
                    affected_components=["license_optimization"],
                    remediation_steps=[
                        "Audit all drop rules for effectiveness.",
                        f"Found {len(ineffective_rules)} ineffective drop rules.",
                        "Consider implementing more aggressive data filtering.",
                        "Review data retention policies.",
                    ],
                )
            )

    def _analyze_pipeline_drop_rules(self, pipeline: dict[str, Any]) -> Optional[DropRuleAnalysis]:
        """Analyze drop rules within a single pipeline."""
        config = pipeline.get("config", {})
        steps = config.get("steps", [])

        drop_conditions = []
        estimated_dropped = 0

        for step in steps:
            if step.get("type") == "filter" and step.get("action") == "drop":
                # Found a drop rule
                filter_expr = step.get("filter", "")
                drop_conditions.append(filter_expr)

                # Rough estimation of effectiveness (simplified)
                # In practice, this would require actual execution metrics
                estimated_dropped += self._estimate_drop_effectiveness(filter_expr)

        if not drop_conditions:
            return None

        # Calculate effectiveness score
        total_conditions = len(drop_conditions)
        avg_effectiveness = estimated_dropped / max(total_conditions, 1)

        # Complexity score based on filter complexity
        complexity_score = sum(len(condition) for condition in drop_conditions)

        return DropRuleAnalysis(
            pipeline_id="",  # Will be set by caller
            pipeline_name="",  # Will be set by caller
            drop_conditions=drop_conditions,
            estimated_dropped_events=estimated_dropped,
            effectiveness_score=min(avg_effectiveness, 100.0),
            complexity_score=complexity_score,
        )

    def _estimate_drop_effectiveness(self, filter_expr: str) -> float:
        """Roughly estimate drop rule effectiveness based on filter complexity."""
        # This is a simplified heuristic - real implementation would use actual metrics
        score = 10.0  # Base effectiveness

        # More specific filters are more effective
        if "==" in filter_expr:
            score += 20
        if ">" in filter_expr or "<" in filter_expr:
            score += 15
        if "contains" in filter_expr or "match" in filter_expr:
            score += 10
        if "AND" in filter_expr.upper():
            score += 25  # Complex conditions are more selective

        # Penalize overly broad filters
        if filter_expr.strip() == "*" or filter_expr.strip() == "true":
            score = 1.0

        return min(score, 100.0)

    def _analyze_processing_efficiency(
        self,
        result: AnalyzerResult,
        pipelines: list[dict[str, Any]],
        system_metrics: dict[str, Any],
        client: CriblAPIClient,
    ) -> None:
        """Analyze processing efficiency and resource usage."""
        pipeline_metrics = self._extract_pipeline_metrics(pipelines, system_metrics)

        # Find inefficient pipelines
        inefficient_pipelines = []
        for metrics in pipeline_metrics:
            if metrics.cpu_usage_percent > 80 and metrics.efficiency_score < 50:
                inefficient_pipelines.append(metrics)

        for metrics in inefficient_pipelines:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"inefficient-processing-{metrics.id}",
                    category="Performance",
                    severity="high",
                    title="Inefficient Data Processing",
                    description=f"Pipeline '{metrics.name}' shows high CPU usage ({metrics.cpu_usage_percent:.1f}%) with low efficiency score ({metrics.efficiency_score:.1f}).",
                    confidence_level="high",
                    affected_components=["data_processing", "resource_usage"],
                    remediation_steps=[
                        "Review pipeline functions for optimization opportunities.",
                        "Consider simplifying complex processing logic.",
                        "Evaluate if all processing steps are necessary.",
                        f"Processing {metrics.input_events} events with {metrics.processing_time_ms:.0f}ms total time.",
                    ],
                )
            )

        # Check for resource waste
        high_memory_pipelines = [m for m in pipeline_metrics if m.memory_usage_mb > 1000]  # >1GB
        if high_memory_pipelines:
            total_memory = sum(m.memory_usage_mb for m in high_memory_pipelines)

            result.add_finding(
                self.create_finding(
                    client=client,
                    id="high-memory-usage-pipelines",
                    category="Performance",
                    severity="medium",
                    title="High Memory Usage in Pipelines",
                    description=f"{len(high_memory_pipelines)} pipelines using {total_memory:.0f}MB total memory.",
                    confidence_level="medium",
                    affected_components=["memory_usage", "data_processing"],
                    remediation_steps=[
                        "Review memory-intensive pipeline functions.",
                        "Consider optimizing data structures and processing logic.",
                        "Evaluate pipeline parallelism settings.",
                        "Monitor for memory leaks in custom functions.",
                    ],
                )
            )

    def _extract_pipeline_metrics(
        self, pipelines: list[dict[str, Any]], system_metrics: dict[str, Any]
    ) -> list[PipelineMetrics]:
        """Extract processing metrics for pipelines."""
        metrics_list = []

        # This is a simplified extraction - real implementation would parse actual metrics
        for pipeline in pipelines:
            pipeline_id = pipeline.get("id", "")
            pipeline_name = pipeline.get("name", "Unknown")

            # Mock metrics extraction - in reality would parse from system_metrics
            metrics = PipelineMetrics(
                id=pipeline_id,
                name=pipeline_name,
                input_events=pipeline.get("metrics", {}).get("inputEvents", 0),
                output_events=pipeline.get("metrics", {}).get("outputEvents", 0),
                processing_time_ms=pipeline.get("metrics", {}).get("processingTimeMs", 0.0),
                cpu_usage_percent=pipeline.get("metrics", {}).get("cpuUsagePercent", 0.0),
                memory_usage_mb=pipeline.get("metrics", {}).get("memoryUsageMb", 0.0),
            )

            metrics_list.append(metrics)

        return metrics_list

    def _identify_cost_optimization_opportunities(
        self,
        result: AnalyzerResult,
        license: LicenseMetrics,
        pipelines: list[dict[str, Any]],
        client: CriblAPIClient,
    ) -> None:
        """Identify specific cost optimization opportunities."""
        # Check for underutilized license capacity
        if license.license_used_percent < 20:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="underutilized-license-capacity",
                    category="Cost",
                    severity="low",
                    title="Underutilized License Capacity",
                    description=f"License is only {license.license_used_percent:.1f}% utilized, indicating potential for increased data processing.",
                    confidence_level="high",
                    affected_components=["license_management", "cost_optimization"],
                    remediation_steps=[
                        "Consider increasing data processing volume if business needs allow.",
                        "Review if current license tier is appropriate.",
                        "Evaluate opportunities to process additional data sources.",
                    ],
                )
            )

        # Check for processing bottlenecks that could be optimized
        total_pipelines = len(pipelines)
        if total_pipelines > 50:  # Arbitrary threshold
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="high-pipeline-complexity",
                    category="Cost",
                    severity="medium",
                    title="High Pipeline Complexity",
                    description=f"Deployment has {total_pipelines} pipelines, which may increase operational complexity and costs.",
                    confidence_level="medium",
                    affected_components=["pipeline_management", "operational_cost"],
                    remediation_steps=[
                        "Review pipeline consolidation opportunities.",
                        "Consider using pipeline templates to reduce duplication.",
                        "Evaluate if all pipelines are still needed.",
                        "Implement pipeline performance monitoring.",
                    ],
                )
            )

    def _assess_overall_license_health(
        self,
        result: AnalyzerResult,
        current: LicenseMetrics,
        history: list[LicenseMetrics],
        client: CriblAPIClient,
    ) -> None:
        """Provide overall assessment of license health."""
        # Calculate health score
        health_score = self._calculate_license_health_score(current, history)

        if health_score < 60:
            risk_level = "high" if health_score < 40 else "medium"

            result.add_finding(
                self.create_finding(
                    client=client,
                    id="poor-license-health",
                    category="License",
                    severity=risk_level,
                    title="Poor License Health Score",
                    description=f"Overall license health score: {health_score}/100. Multiple optimization opportunities identified.",
                    confidence_level="high",
                    affected_components=["license_management", "cost_optimization"],
                    remediation_steps=[
                        "Implement recommended drop rules and optimizations.",
                        "Review pipeline efficiency and resource usage.",
                        "Monitor license usage trends regularly.",
                        "Consider license tier adjustment based on usage patterns.",
                    ],
                )
            )

    def _calculate_license_health_score(
        self, current: LicenseMetrics, history: list[LicenseMetrics]
    ) -> int:
        """Calculate overall license health score (0-100)."""
        score = 100

        # Deduct for high usage
        if current.license_used_percent > 90:
            score -= 30
        elif current.license_used_percent > 75:
            score -= 15
        elif current.license_used_percent > 50:
            score -= 5

        # Deduct for low drop effectiveness
        if current.events_dropped_percent < 10:
            score -= 20
        elif current.events_dropped_percent < 25:
            score -= 10

        # Deduct for usage volatility
        if len(history) >= 7:
            usage_values = [h.license_used_percent for h in history[-7:]]
            if usage_values:
                avg_usage = sum(usage_values) / len(usage_values)
                volatility = sum(abs(u - avg_usage) for u in usage_values) / len(usage_values)
                if volatility > 20:
                    score -= 15
                elif volatility > 10:
                    score -= 8

        return max(0, min(100, score))
