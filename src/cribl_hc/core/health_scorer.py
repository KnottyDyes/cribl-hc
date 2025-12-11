"""
Health scoring utilities for Cribl Stream components.

Provides consistent scoring algorithms for:
- Worker health
- System components
- Overall deployment health
"""

from typing import Any, Dict, List, Optional

from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class ComponentHealth:
    """
    Health assessment for a single component.

    Attributes:
        name: Component name/identifier
        score: Health score (0-100)
        status: Health status (healthy, degraded, unhealthy, critical)
        issues: List of identified issues
        metrics: Raw metric values
    """

    def __init__(
        self,
        name: str,
        score: float,
        status: str,
        issues: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.score = score
        self.status = status
        self.issues = issues or []
        self.metrics = metrics or {}

    def is_healthy(self) -> bool:
        """Check if component is healthy (score >= 90)."""
        return self.score >= 90

    def is_critical(self) -> bool:
        """Check if component is critical (score < 50)."""
        return self.score < 50

    def __repr__(self) -> str:
        return f"ComponentHealth({self.name}: {self.score}/100 - {self.status})"


class HealthScorer:
    """
    Calculates health scores for Cribl Stream components.

    Uses consistent thresholds and algorithms across all analyzers.
    """

    # Health thresholds
    HEALTHY_THRESHOLD = 90.0
    DEGRADED_THRESHOLD = 70.0
    UNHEALTHY_THRESHOLD = 50.0

    # Resource usage thresholds
    CPU_WARNING_THRESHOLD = 80.0
    CPU_CRITICAL_THRESHOLD = 90.0
    MEMORY_WARNING_THRESHOLD = 80.0
    MEMORY_CRITICAL_THRESHOLD = 90.0
    DISK_WARNING_THRESHOLD = 80.0
    DISK_CRITICAL_THRESHOLD = 90.0

    def __init__(self):
        """Initialize health scorer."""
        self.log = get_logger(self.__class__.__name__)

    def score_worker_health(
        self,
        worker_id: str,
        cpu_usage: float,
        memory_usage: float,
        disk_usage: float,
    ) -> ComponentHealth:
        """
        Calculate health score for a worker node.

        Scoring algorithm:
        - Start at 100
        - Deduct points based on resource usage thresholds
        - Multiple critical thresholds result in critical status

        Args:
            worker_id: Worker identifier
            cpu_usage: CPU usage percentage (0-100)
            memory_usage: Memory usage percentage (0-100)
            disk_usage: Disk usage percentage (0-100)

        Returns:
            ComponentHealth with score and status

        Example:
            >>> scorer = HealthScorer()
            >>> health = scorer.score_worker_health("worker-1", 95.0, 85.0, 70.0)
            >>> print(health.status)
            'critical'
        """
        score = 100.0
        issues = []

        # CPU scoring
        if cpu_usage >= self.CPU_CRITICAL_THRESHOLD:
            score -= 40
            issues.append(f"CPU critical: {cpu_usage:.1f}%")
        elif cpu_usage >= self.CPU_WARNING_THRESHOLD:
            score -= 15
            issues.append(f"CPU high: {cpu_usage:.1f}%")

        # Memory scoring
        if memory_usage >= self.MEMORY_CRITICAL_THRESHOLD:
            score -= 40
            issues.append(f"Memory critical: {memory_usage:.1f}%")
        elif memory_usage >= self.MEMORY_WARNING_THRESHOLD:
            score -= 15
            issues.append(f"Memory high: {memory_usage:.1f}%")

        # Disk scoring
        if disk_usage >= self.DISK_CRITICAL_THRESHOLD:
            score -= 30
            issues.append(f"Disk critical: {disk_usage:.1f}%")
        elif disk_usage >= self.DISK_WARNING_THRESHOLD:
            score -= 10
            issues.append(f"Disk high: {disk_usage:.1f}%")

        # Ensure score doesn't go negative
        score = max(0.0, score)

        # Determine status
        status = self._score_to_status(score)

        return ComponentHealth(
            name=worker_id,
            score=score,
            status=status,
            issues=issues,
            metrics={
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
            },
        )

    def score_overall_health(
        self,
        component_healths: List[ComponentHealth]
    ) -> ComponentHealth:
        """
        Calculate overall health score from component scores.

        Uses weighted average with penalties for critical components.

        Args:
            component_healths: List of component health assessments

        Returns:
            Overall ComponentHealth

        Example:
            >>> worker1 = scorer.score_worker_health("w1", 50, 50, 50)
            >>> worker2 = scorer.score_worker_health("w2", 95, 85, 70)
            >>> overall = scorer.score_overall_health([worker1, worker2])
        """
        if not component_healths:
            return ComponentHealth(
                name="overall",
                score=0.0,
                status="unknown",
                issues=["No components to assess"],
            )

        # Calculate average score
        total_score = sum(c.score for c in component_healths)
        avg_score = total_score / len(component_healths)

        # Apply penalties for critical components
        critical_count = sum(1 for c in component_healths if c.is_critical())
        critical_penalty = (critical_count / len(component_healths)) * 20
        final_score = max(0.0, avg_score - critical_penalty)

        # Collect all issues
        all_issues = []
        for component in component_healths:
            if component.issues:
                all_issues.extend([f"{component.name}: {issue}" for issue in component.issues])

        status = self._score_to_status(final_score)

        return ComponentHealth(
            name="overall",
            score=round(final_score, 2),
            status=status,
            issues=all_issues,
            metrics={
                "total_components": len(component_healths),
                "critical_components": critical_count,
                "avg_component_score": round(avg_score, 2),
            },
        )

    def score_deployment_health(
        self,
        healthy_workers: int,
        total_workers: int,
        critical_findings: int = 0,
        high_findings: int = 0,
    ) -> ComponentHealth:
        """
        Calculate overall deployment health score.

        Considers:
        - Ratio of healthy to total workers
        - Number of critical findings
        - Number of high severity findings

        Args:
            healthy_workers: Count of healthy workers
            total_workers: Total worker count
            critical_findings: Number of critical findings
            high_findings: Number of high severity findings

        Returns:
            ComponentHealth for overall deployment

        Example:
            >>> health = scorer.score_deployment_health(
            ...     healthy_workers=8,
            ...     total_workers=10,
            ...     critical_findings=1,
            ...     high_findings=3
            ... )
        """
        if total_workers == 0:
            return ComponentHealth(
                name="deployment",
                score=0.0,
                status="unknown",
                issues=["No workers detected"],
            )

        # Base score from worker health ratio
        worker_health_ratio = healthy_workers / total_workers
        base_score = worker_health_ratio * 100

        # Deduct points for findings
        critical_penalty = critical_findings * 15
        high_penalty = high_findings * 5

        final_score = max(0.0, base_score - critical_penalty - high_penalty)

        # Build issues list
        issues = []
        unhealthy_workers = total_workers - healthy_workers

        if unhealthy_workers > 0:
            issues.append(f"{unhealthy_workers}/{total_workers} workers unhealthy")

        if critical_findings > 0:
            issues.append(f"{critical_findings} critical findings")

        if high_findings > 0:
            issues.append(f"{high_findings} high severity findings")

        status = self._score_to_status(final_score)

        return ComponentHealth(
            name="deployment",
            score=round(final_score, 2),
            status=status,
            issues=issues,
            metrics={
                "total_workers": total_workers,
                "healthy_workers": healthy_workers,
                "unhealthy_workers": unhealthy_workers,
                "critical_findings": critical_findings,
                "high_findings": high_findings,
            },
        )

    def _score_to_status(self, score: float) -> str:
        """
        Convert numeric score to status string.

        Args:
            score: Health score (0-100)

        Returns:
            Status string (healthy, degraded, unhealthy, critical)
        """
        if score >= self.HEALTHY_THRESHOLD:
            return "healthy"
        elif score >= self.DEGRADED_THRESHOLD:
            return "degraded"
        elif score >= self.UNHEALTHY_THRESHOLD:
            return "unhealthy"
        else:
            return "critical"

    def get_status_color(self, status: str) -> str:
        """
        Get terminal color code for status display.

        Args:
            status: Health status string

        Returns:
            ANSI color code
        """
        colors = {
            "healthy": "\033[92m",  # Green
            "degraded": "\033[93m",  # Yellow
            "unhealthy": "\033[91m",  # Red
            "critical": "\033[95m",  # Magenta
            "unknown": "\033[90m",  # Gray
        }
        return colors.get(status, "\033[0m")  # Default: reset

    def format_health_summary(self, health: ComponentHealth) -> str:
        """
        Format health assessment as colored terminal string.

        Args:
            health: ComponentHealth to format

        Returns:
            Formatted string with ANSI colors

        Example:
            >>> summary = scorer.format_health_summary(health)
            >>> print(summary)
            '\\033[92mHealthy\\033[0m (95/100)'
        """
        color = self.get_status_color(health.status)
        reset = "\033[0m"

        status_upper = health.status.upper()
        return f"{color}{status_upper}{reset} ({health.score:.0f}/100)"


# Convenience function for simple health checks

def calculate_worker_health(
    worker_id: str,
    cpu_usage: float,
    memory_usage: float,
    disk_usage: float,
) -> ComponentHealth:
    """
    Convenience function to calculate worker health.

    Args:
        worker_id: Worker identifier
        cpu_usage: CPU usage percentage
        memory_usage: Memory usage percentage
        disk_usage: Disk usage percentage

    Returns:
        ComponentHealth assessment

    Example:
        >>> from cribl_hc.core.health_scorer import calculate_worker_health
        >>> health = calculate_worker_health("worker-1", 85.0, 70.0, 60.0)
        >>> print(health.status)
        'degraded'
    """
    scorer = HealthScorer()
    return scorer.score_worker_health(worker_id, cpu_usage, memory_usage, disk_usage)
