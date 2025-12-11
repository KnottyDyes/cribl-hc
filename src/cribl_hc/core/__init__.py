"""
Core infrastructure for Cribl health check.

This module provides the fundamental building blocks:
- API client for Cribl Stream REST API
- Connection testing utilities
- Health scoring algorithms
- Analyzer orchestration
"""

from cribl_hc.core.api_client import ConnectionTestResult, CriblAPIClient
from cribl_hc.core.health_scorer import ComponentHealth, HealthScorer, calculate_worker_health

# Lazy import to avoid circular dependency
# (orchestrator imports from analyzers, which imports from core.api_client)
def __getattr__(name):
    if name == "AnalyzerOrchestrator":
        from cribl_hc.core.orchestrator import AnalyzerOrchestrator
        return AnalyzerOrchestrator
    elif name == "AnalysisProgress":
        from cribl_hc.core.orchestrator import AnalysisProgress
        return AnalysisProgress
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "CriblAPIClient",
    "ConnectionTestResult",
    "ComponentHealth",
    "HealthScorer",
    "calculate_worker_health",
    "AnalyzerOrchestrator",
    "AnalysisProgress",
]
