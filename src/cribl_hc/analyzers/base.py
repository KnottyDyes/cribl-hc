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
    """

    def __init__(
        self,
        objective: str,
        findings: Optional[List[Finding]] = None,
        recommendations: Optional[List[Recommendation]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
    ):
        self.objective = objective
        self.findings = findings or []
        self.recommendations = recommendations or []
        self.metadata = metadata or {}
        self.success = success
        self.error = error

    def add_finding(self, finding: Finding) -> None:
        """Add a finding to the results."""
        self.findings.append(finding)

    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Add a recommendation to the results."""
        self.recommendations.append(recommendation)

    def get_critical_findings(self) -> List[Finding]:
        """Get only critical severity findings."""
        return [f for f in self.findings if f.severity == "critical"]

    def get_high_findings(self) -> List[Finding]:
        """Get high severity findings."""
        return [f for f in self.findings if f.severity == "high"]

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
