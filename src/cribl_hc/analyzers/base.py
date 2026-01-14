"""
Base analyzer interface for all health check analyzers.

All analyzers must inherit from BaseAnalyzer and implement the analyze() method.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class AnalyzerResult:
    """
    Result from running an analyzer.

    Attributes:
        objective: The analysis objective that was run
        findings: List of findings discovered
        recommendations: List of recommendations generated
        metadata: Additional metadata about the analysis
        success: Whether analysis completed successfully
        error: Error message if analysis failed
    """

    PRODUCTS = ["stream", "edge", "lake", "search"]

    def __init__(
        self,
        objective: str,
        findings: Optional[list[Finding]] = None,
        recommendations: Optional[list[Recommendation]] = None,
        metadata: Optional[dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
        source_analyzer: Optional[str] = None,
        default_product_tags: Optional[list[str]] = None,
    ):
        self.objective = objective
        self.findings = findings or []
        self.recommendations = recommendations or []
        self.metadata = metadata or {}
        self.success = success
        self.error = error

        self._source_analyzer = source_analyzer or objective
        self._default_product_tags = default_product_tags or self.PRODUCTS.copy()

        self._findings_by_product: dict[str, int] = dict.fromkeys(self.PRODUCTS, 0)
        self._recommendations_by_product: dict[str, int] = dict.fromkeys(self.PRODUCTS, 0)

        for finding in self.findings:
            self._increment_finding_counts(finding)
        for rec in self.recommendations:
            self._increment_recommendation_counts(rec)

    def _increment_finding_counts(self, finding: Finding) -> None:
        """Increment product counters for a finding."""
        for product in finding.product_tags:
            if product in self._findings_by_product:
                self._findings_by_product[product] += 1

    def _increment_recommendation_counts(self, recommendation: Recommendation) -> None:
        """Increment product counters for a recommendation."""
        for product in recommendation.product_tags:
            if product in self._recommendations_by_product:
                self._recommendations_by_product[product] += 1

    def add_finding(self, finding: Finding) -> None:
        """
        Add a finding to the results and update product counts.
        """
        if not finding.source_analyzer:
            finding = finding.model_copy(update={"source_analyzer": self._source_analyzer})

        if not finding.product_tags:
            finding = finding.model_copy(update={"product_tags": self._default_product_tags.copy()})

        self.findings.append(finding)
        self._increment_finding_counts(finding)

    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Add a recommendation to the results and update product counts."""
        self.recommendations.append(recommendation)
        self._increment_recommendation_counts(recommendation)

    def get_critical_findings(self) -> list[Finding]:
        """Get only critical severity findings."""
        return [f for f in self.findings if f.severity == "critical"]

    def get_high_findings(self) -> list[Finding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == "high"]

    def sort_findings_by_severity(self) -> None:
        """
        Sort findings by severity (critical > high > medium > low > info).
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        self.findings.sort(key=lambda f: severity_order.get(f.severity, 99))

    def sort_recommendations_by_priority(self) -> None:
        """
        Sort recommendations by priority (p0 > p1 > p2 > p3).
        """
        priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
        self.recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

    def filter_by_product(self, product: str) -> "AnalyzerResult":
        """
        Filter findings and recommendations by product tag.
        """
        filtered_result = AnalyzerResult(
            objective=self.objective,
            findings=[f for f in self.findings if product in f.product_tags],
            recommendations=[r for r in self.recommendations if product in r.product_tags],
            metadata=self.metadata.copy(),
            success=self.success,
            error=self.error,
        )
        return filtered_result

    def get_product_summary(self) -> dict[str, dict[str, int]]:
        """
        Get summary of findings and recommendations by product.
        """
        return {
            product: {
                "findings": self._findings_by_product[product],
                "recommendations": self._recommendations_by_product[product],
            }
            for product in self.PRODUCTS
        }

    def get_findings_by_product(self) -> dict[str, int]:
        """
        Get count of findings by product.
        """
        return self._findings_by_product.copy()

    def get_recommendations_by_product(self) -> dict[str, int]:
        """
        Get count of recommendations by product.
        """
        return self._recommendations_by_product.copy()

    def __repr__(self) -> str:
        return (
            f"AnalyzerResult(objective={self.objective}, "
            f"findings={len(self.findings)}, "
            f"recommendations={len(self.recommendations)}, "
            f"success={self.success})"
        )


class BaseAnalyzer(ABC):
    """
    Abstract base class for all analyzers.
    """

    def __init__(self) -> None:
        """Initialize base analyzer."""
        self.log = get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def objective_name(self) -> str:
        """
        Return the objective name for this analyzer.
        """
        pass

    @property
    def supported_products(self) -> list[str]:
        """
        Return list of products this analyzer supports.
        """
        return ["stream", "edge", "lake", "search"]

    @abstractmethod
    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis using the provided API client.
        """
        pass

    def get_description(self) -> str:
        """
        Get human-readable description of what this analyzer does.
        """
        return f"Analyzer for {self.objective_name} objective"

    def supports_partial_results(self) -> bool:
        """
        Whether this analyzer supports returning partial results on errors.
        """
        return True

    def get_required_permissions(self) -> list[str]:
        """
        Get list of API permissions required by this analyzer.
        """
        return []

    def get_estimated_api_calls(self) -> int:
        """
        Estimate number of API calls this analyzer will make.
        """
        return 5

    async def pre_analyze_check(self, client: CriblAPIClient) -> bool:
        """
        Optional pre-flight check before running analysis.
        """
        return True

    @abstractmethod
    async def post_analyze_cleanup(self) -> None:
        """
        Optional cleanup after analysis completes.
        """
        pass

    def create_result(self) -> "AnalyzerResult":
        """
        Create an AnalyzerResult bound to this analyzer.
        """
        return AnalyzerResult(
            objective=self.objective_name,
            source_analyzer=self.objective_name,
            default_product_tags=self.supported_products,
        )

    def create_finding(self, client: Optional[CriblAPIClient] = None, **kwargs) -> Finding:
        """
        Create a Finding automatically tagged with this analyzer's info.

        Auto-generates grouping_id from title pattern if not explicitly provided.
        For titles like "Pattern: {variable}", uses "pattern" as grouping_id.
        This enables automatic grouping of similar findings in the UI.
        """
        if "confidence_level" not in kwargs:
            kwargs["confidence_level"] = "high"

        if "source_analyzer" not in kwargs:
            kwargs["source_analyzer"] = self.objective_name

        if "product_tags" not in kwargs:
            kwargs["product_tags"] = self.supported_products.copy()

        # Extract worker_group from metadata if present and not explicitly provided
        if "worker_group" not in kwargs:
            if "metadata" in kwargs and "worker_group_id" in kwargs["metadata"]:
                kwargs["worker_group"] = kwargs["metadata"]["worker_group_id"]
            elif (
                client and hasattr(client, "worker_group") and isinstance(client.worker_group, str)
            ):
                kwargs["worker_group"] = client.worker_group

        # Auto-generate grouping_id from title pattern if not explicitly provided
        if "grouping_id" not in kwargs and "title" in kwargs:
            title = kwargs["title"]
            # Extract pattern from titles like "Pattern: value" or "Pattern Name: value"
            if ":" in title:
                pattern = title.split(":")[0].strip().lower()
                # Convert to snake_case and prefix with objective for uniqueness
                pattern_id = pattern.replace(" ", "-")
                kwargs["grouping_id"] = f"{self.objective_name}-{pattern_id}"

        finding = Finding(**kwargs)

        # Ensure metadata has worker_group if it was found
        if finding.worker_group and "worker_group_id" not in finding.metadata:
            finding.metadata["worker_group_id"] = finding.worker_group

        return finding

    def create_finding_with_context(
        self, client: Optional[CriblAPIClient] = None, **kwargs
    ) -> Finding:
        """
        Deprecated: Use create_finding(client=client, ...) instead.
        """
        return self.create_finding(client=client, **kwargs)
