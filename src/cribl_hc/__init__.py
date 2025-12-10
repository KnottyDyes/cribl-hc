"""
Cribl Health Check - Comprehensive health checking tool for Cribl Stream deployments.

This package provides a library-first API for analyzing Cribl Stream deployments
with a focus on health assessment, configuration validation, performance optimization,
security auditing, and cost management.

Constitution Principles:
- Read-Only by Default: All operations use read-only API access
- Actionability First: Clear remediation steps for all findings
- API-First Design: Core library with thin CLI wrapper
- Stateless Analysis: Independent analysis runs, optional historical data
- Performance Efficiency: <5 min analysis, <100 API calls per run

Example:
    ```python
    from cribl_hc import analyze_deployment, Deployment

    deployment = Deployment(
        id="prod",
        url="https://cribl.example.com",
        auth_token="your-token",
        environment_type="self-hosted"
    )

    result = await analyze_deployment(deployment, objectives=["health"])
    print(f"Health Score: {result.health_score.overall_score}")
    ```
"""

__version__ = "1.0.0"
__author__ = "Cribl Health Check Project"
__license__ = "MIT"

# Version tuple for programmatic access
VERSION = tuple(map(int, __version__.split(".")))

# Public API exports (will be populated as features are implemented)
__all__ = [
    "__version__",
    "VERSION",
]
