"""
Pydantic data models for Cribl Health Check.

All models provide:
- Strong type validation
- Automatic JSON serialization/deserialization
- Field validation with custom validators
- Clear data contracts for API boundaries
"""

from .analysis import AnalysisRun
from .config import ConfigurationElement
from .deployment import Deployment
from .finding import Finding
from .health import ComponentScore, HealthScore
from .recommendation import ImpactEstimate, Recommendation
from .rule import BestPracticeRule
from .trend import DataPoint, HistoricalTrend
from .worker import ResourceUtilization, WorkerNode

__all__ = [
    # Core entities
    "Deployment",
    "AnalysisRun",
    "HealthScore",
    "ComponentScore",
    "Finding",
    "Recommendation",
    "ImpactEstimate",
    "WorkerNode",
    "ResourceUtilization",
    "ConfigurationElement",
    "HistoricalTrend",
    "DataPoint",
    "BestPracticeRule",
]
