"""
Base analyzer interface for all health check analyzers.

All analyzers must inherit from BaseAnalyzer and implement the analyze() method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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

    Product Tracking:
        Automatically tracks findings and recommendations by product tag.
        Use get_product_summary() for aggregated counts.
    """

    # Valid product names
    PRODUCTS = ["stream", "edge", "lake", "search"]

    def __init__(
        self,
        objective: str,
        findings: Optional[List[Finding]] = None,
        recommendations: Optional[List[Recommendation]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
        source_analyzer: Optional[str] = None,
        default_product_tags: Optional[List[str]] = None,
    ):
        self.objective = objective
        self.findings = findings or []
        self.recommendations = recommendations or []
        self.metadata = metadata or {}
        self.success = success
        self.error = error

        # Store analyzer context for auto-tagging findings
        self._source_analyzer = source_analyzer or objective
        self._default_product_tags = default_product_tags or self.PRODUCTS.copy()

        # Initialize product counters
        self._findings_by_product: Dict[str, int] = {p: 0 for p in self.PRODUCTS}
        self._recommendations_by_product: Dict[str, int] = {p: 0 for p in self.PRODUCTS}

        # Count any pre-existing findings/recommendations
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

        If the finding has no source_analyzer set, it will be tagged with
        this result's source analyzer. If it has no product_tags, it will
        inherit the default product tags from this result.
        """
        # Auto-tag with source analyzer if not set
        if not finding.source_analyzer:
            # Create a new finding with source_analyzer set (Finding is immutable)
            finding = finding.model_copy(update={"source_analyzer": self._source_analyzer})

        # Auto-tag with product tags if empty
        if not finding.product_tags:
            finding = finding.model_copy(update={"product_tags": self._default_product_tags.copy()})

        self.findings.append(finding)
        self._increment_finding_counts(finding)

    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Add a recommendation to the results and update product counts."""
        self.recommendations.append(recommendation)
        self._increment_recommendation_counts(recommendation)

    def get_critical_findings(self) -> List[Finding]:
        """Get only critical severity findings."""
        return [f for f in self.findings if f.severity == "critical"]

    def get_high_findings(self) -> List[Finding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == "high"]

    def sort_findings_by_severity(self) -> None:
        """
        Sort findings by severity (critical > high > medium > low > info).

        Modifies self.findings in-place.
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        self.findings.sort(key=lambda f: severity_order.get(f.severity, 99))

    def sort_recommendations_by_priority(self) -> None:
        """
        Sort recommendations by priority (p0 > p1 > p2 > p3).

        Modifies self.recommendations in-place.
        """
        priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
        self.recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

    def filter_by_product(self, product: str) -> "AnalyzerResult":
        """
        Filter findings and recommendations by product tag.

        Args:
            product: Product name (e.g., "stream", "edge", "lake", "search")

        Returns:
            New AnalyzerResult with filtered findings and recommendations
        """
        filtered_result = AnalyzerResult(
            objective=self.objective,
            findings=[f for f in self.findings if product in f.product_tags],
            recommendations=[r for r in self.recommendations if product in r.product_tags],
            metadata=self.metadata.copy(),
            success=self.success,
            error=self.error
        )
        return filtered_result

    def get_product_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get summary of findings and recommendations by product.

        Returns:
            Dict with product names as keys and counts as values:
            {
                "stream": {"findings": 5, "recommendations": 3},
                "edge": {"findings": 2, "recommendations": 1},
                "lake": {"findings": 3, "recommendations": 2},
                "search": {"findings": 4, "recommendations": 2}
            }

        Example:
            >>> result = analyzer.analyze(client)
            >>> summary = result.get_product_summary()
            >>> print(f"Stream findings: {summary['stream']['findings']}")
        """
        return {
            product: {
                "findings": self._findings_by_product[product],
                "recommendations": self._recommendations_by_product[product]
            }
            for product in self.PRODUCTS
        }

    def get_findings_by_product(self) -> Dict[str, int]:
        """
        Get count of findings by product.

        Returns:
            Dict with product names as keys and finding counts as values.
        """
        return self._findings_by_product.copy()

    def get_recommendations_by_product(self) -> Dict[str, int]:
        """
        Get count of recommendations by product.

        Returns:
            Dict with product names as keys and recommendation counts as values.
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

    Each analyzer focuses on a specific objective (e.g., health, configuration, sizing).
    Analyzers use the API client to fetch data and generate findings/recommendations.

    Example:
        >>> class MyAnalyzer(BaseAnalyzer):
        ...     @property
        ...     def objective_name(self) -> str:
        ...         return "custom"
        ...
        ...     async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        ...         result = AnalyzerResult(objective=self.objective_name)
        ...         # ... perform analysis ...
        ...         return result
    """

    def __init__(self):
        """Initialize base analyzer."""
        self.log = get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def objective_name(self) -> str:
        """
        Return the objective name for this analyzer.

        This should be a short, lowercase identifier like "health", "config", "sizing".

        Returns:
            Objective name string
        """
        pass

    @property
    def supported_products(self) -> List[str]:
        """
        Return list of products this analyzer supports.

        Returns:
            List of product names (default: ["stream", "edge", "lake", "search"])

        Example:
            >>> class StreamOnlyAnalyzer(BaseAnalyzer):
            ...     @property
            ...     def supported_products(self) -> List[str]:
            ...         return ["stream"]
        """
        return ["stream", "edge", "lake", "search"]

    @abstractmethod
    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis using the provided API client.

        This method should:
        1. Fetch necessary data from Cribl API using the client
        2. Analyze the data according to the analyzer's objective
        3. Generate findings and recommendations
        4. Return an AnalyzerResult

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult containing findings and recommendations

        Raises:
            Exception: If analysis fails critically (should be caught by orchestrator)

        Example:
            >>> async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
            ...     result = AnalyzerResult(objective=self.objective_name)
            ...
            ...     # Fetch data
            ...     workers = await client.get_workers()
            ...
            ...     # Analyze
            ...     for worker in workers:
            ...         if worker['cpu_usage'] > 90:
            ...             result.add_finding(Finding(
            ...                 title="High CPU on worker",
            ...                 description=f"Worker {worker['id']} at {worker['cpu_usage']}%",
            ...                 severity="high",
            ...                 category="performance",
            ...             ))
            ...
            ...     return result
        """
        pass

    def get_description(self) -> str:
        """
        Get human-readable description of what this analyzer does.

        Returns:
            Description string
        """
        return f"Analyzer for {self.objective_name} objective"

    def supports_partial_results(self) -> bool:
        """
        Whether this analyzer supports returning partial results on errors.

        If True, the analyzer should catch exceptions internally and return
        partial results in the AnalyzerResult. If False, exceptions will
        propagate to the orchestrator.

        Returns:
            True if partial results are supported (default: True)
        """
        return True

    def get_required_permissions(self) -> List[str]:
        """
        Get list of API permissions required by this analyzer.

        Returns:
            List of required permission strings (default: empty list)
        """
        return []

    def get_estimated_api_calls(self) -> int:
        """
        Estimate number of API calls this analyzer will make.

        This helps the orchestrator plan API call budget allocation.

        Returns:
            Estimated number of API calls (default: 5)
        """
        return 5

    async def pre_analyze_check(self, client: CriblAPIClient) -> bool:
        """
        Optional pre-flight check before running analysis.

        This can be used to verify permissions, check API availability, etc.

        Args:
            client: Authenticated Cribl API client

        Returns:
            True if analyzer is ready to run, False otherwise (default: True)
        """
        return True

    async def post_analyze_cleanup(self) -> None:
        """
        Optional cleanup after analysis completes.

        This can be used to close resources, clear caches, etc.
        """
        pass

    def create_result(self) -> "AnalyzerResult":
        """
        Create an AnalyzerResult bound to this analyzer.

        The returned result will automatically tag findings with this
        analyzer's name and supported products.

        Returns:
            AnalyzerResult configured for this analyzer
        """
        return AnalyzerResult(
            objective=self.objective_name,
            source_analyzer=self.objective_name,
            default_product_tags=self.supported_products
        )

    def create_finding(self, **kwargs) -> Finding:
        """
        Create a Finding automatically tagged with this analyzer's info.

        This is a convenience method that sets source_analyzer and product_tags
        automatically based on this analyzer's configuration.

        Args:
            **kwargs: All Finding field arguments

        Returns:
            Finding with source_analyzer and product_tags set

        Example:
            >>> finding = self.create_finding(
            ...     id="health-issue-1",
            ...     category="health",
            ...     severity="high",
            ...     title="Worker CPU High",
            ...     description="Worker has high CPU usage",
            ...     confidence_level="high",
            ... )
        """
        # Set source_analyzer if not provided
        if "source_analyzer" not in kwargs:
            kwargs["source_analyzer"] = self.objective_name

        # Set product_tags if not provided
        if "product_tags" not in kwargs:
            kwargs["product_tags"] = self.supported_products.copy()

        return Finding(**kwargs)
