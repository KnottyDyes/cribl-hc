"""
Analyzers for different health check objectives.

This module provides a registry of all available analyzers that can be used
to assess different aspects of a Cribl Stream deployment.

Available Objectives:
- health: Overall health assessment, worker monitoring, critical issues
- config: Configuration validation, best practices, anti-patterns
- resource: Resource sizing, over/under-provisioning, scaling recommendations
- storage: Storage optimization, data reduction, cost savings
- security: Security posture, compliance, credential exposure
- cost: License tracking, cost forecasting, TCO analysis
- fleet: Multi-deployment management, configuration drift detection
- predictive: Predictive analytics, capacity forecasting, anomaly detection
- backpressure: Queue monitoring, backpressure detection, flow control
- pipeline_performance: Pipeline efficiency, function analysis, bottleneck detection
- lookup_health: Lookup table sizes, memory optimization, orphan detection
- schema_quality: Parser analysis, regex optimization, schema mapping
- schema_drift: Schema change detection, field disappearances, type changes
- dataflow_topology: Route validation, connectivity checking, data path analysis
- multi_deployment_comparison: Compare health analysis results across multiple deployments
- advanced_security: Enhanced security analysis with healthcare codes, financial data, and compliance frameworks
- alerting: Notification targets, alert configuration, alerting infrastructure health
- end_to_end_freshness: End-to-end pipeline latency, processing time analysis
- scripts: Script inventory and validation signals
- lake_storage_locations: Lake storage location (BYOS) health
- search_usage_groups: Search usage group allocation hygiene
- search_healthcheck: Search healthcheck status
- search_job_metrics: Search job metrics summary
- search_dataset_stats: Search dataset stats and usage
- search_dataset_providers: Search dataset providers and usage
- search_dataset_provider_types: Search dataset provider types availability
- search_field_stats: Search dataset field statistics and quality
- system_messages: Core system message visibility
- system_banners: System banner visibility
- system_certificates: System certificate expiration
- system_logs: System log error summary
- system_policies: System policy inventory
- system_settings: System settings inventory
- system_license_usage: License usage and expiration
- system_user_info: User role hygiene
- version_control: Uncommitted changes, pending deployments, configuration drift
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Optional
from typing import Dict as DictType
from typing import List as ListType
from typing import Type as TypeType

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class AnalyzerRegistry:
    """
    Registry for managing available analyzers.

    The registry allows dynamic registration and retrieval of analyzer classes
    based on their objective names.

    Example:
        >>> # Register an analyzer
        >>> registry = AnalyzerRegistry()
        >>> registry.register(MyCustomAnalyzer)
        >>>
        >>> # Get analyzer by objective
        >>> analyzer = registry.get_analyzer("health")
        >>> if analyzer:
        ...     result = await analyzer.analyze(client)
    """

    def __init__(self):
        """Initialize empty analyzer registry."""
        self._analyzers: dict[str, type[BaseAnalyzer]] = {}
        self._analyzer_classes: list[type[BaseAnalyzer]] = []

    def register(self, analyzer_class: type[BaseAnalyzer]) -> None:
        """
        Register an analyzer class.

        Args:
            analyzer_class: Analyzer class to register (must inherit BaseAnalyzer)

        Raises:
            ValueError: If analyzer_class doesn't inherit from BaseAnalyzer
            ValueError: If objective name already registered

        Example:
            >>> class HealthAnalyzer(BaseAnalyzer):
            ...     @property
            ...     def objective_name(self) -> str:
            ...         return "health"
            ...     async def analyze(self, client):
            ...         pass
            >>>
            >>> registry.register(HealthAnalyzer)
        """
        if not issubclass(analyzer_class, BaseAnalyzer):
            raise ValueError(f"{analyzer_class.__name__} must inherit from BaseAnalyzer")

        # Create temporary instance to get objective name
        # (we can't access the property without an instance)
        try:
            temp_instance = analyzer_class()
            objective = temp_instance.objective_name
        except Exception as e:
            raise ValueError(
                f"Failed to get objective_name from {analyzer_class.__name__}: {e}"
            ) from e

        # Register primary analyzer (first one loaded per objective) and track all
        if objective not in self._analyzers:
            self._analyzers[objective] = analyzer_class

        self._analyzer_classes.append(analyzer_class)
        # Note: Logging removed to avoid logger initialization issues during import
        # log.info("analyzer_registered", objective=objective, analyzer_class=analyzer_class.__name__)

    def unregister(self, objective: str) -> bool:
        """
        Unregister an analyzer by objective name.

        Args:
            objective: Objective name to unregister

        Returns:
            True if analyzer was unregistered, False if not found
        """
        if objective in self._analyzers:
            self._analyzers.pop(objective)
            # Note: Logging removed to avoid logger initialization issues
            # log.info("analyzer_unregistered", objective=objective, analyzer_class=analyzer_class.__name__)
            return True
        return False

    def get_analyzer(self, objective: str) -> Optional[BaseAnalyzer]:
        """
        Get an analyzer instance by objective name.

        Args:
            objective: Objective name (e.g., "health", "config")

        Returns:
            Analyzer instance if found, None otherwise

        Example:
            >>> analyzer = registry.get_analyzer("health")
            >>> if analyzer:
            ...     result = await analyzer.analyze(client)
        """
        analyzer_class = self._analyzers.get(objective)
        if analyzer_class:
            return analyzer_class()
        return None

    def get_analyzer_class(self, objective: str) -> Optional[type[BaseAnalyzer]]:
        """
        Get an analyzer class (not instance) by objective name.

        Args:
            objective: Objective name

        Returns:
            Analyzer class if found, None otherwise
        """
        return self._analyzers.get(objective)

    def list_objectives(self) -> list[str]:
        """
        Get list of all registered objective names.

        Returns:
            List of objective name strings

        Example:
            >>> registry.list_objectives()
            ['health', 'config', 'sizing']
        """
        return sorted(self._analyzers.keys())

    def list_analyzers(self) -> list[type[BaseAnalyzer]]:
        """
        Get list of all registered analyzer classes.

        Returns:
            List of analyzer classes
        """
        return list(self._analyzers.values())

    def has_analyzer(self, objective: str) -> bool:
        """
        Check if an analyzer is registered for the given objective.

        Args:
            objective: Objective name to check

        Returns:
            True if analyzer exists, False otherwise
        """
        return objective in self._analyzers

    def clear(self) -> None:
        """Clear all registered analyzers."""
        self._analyzers.clear()
        # Note: Logging removed to avoid logger initialization issues
        # log.info("analyzer_registry_cleared")

    def __len__(self) -> int:
        """Get number of registered analyzers."""
        return len(self._analyzers)

    def __repr__(self) -> str:
        objectives = ", ".join(self.list_objectives())
        return f"AnalyzerRegistry({len(self)} analyzers: {objectives})"


# Global registry instance
_global_registry = AnalyzerRegistry()


def get_global_registry() -> AnalyzerRegistry:
    """
    Get the global analyzer registry.

    Returns:
        Global AnalyzerRegistry instance

    Example:
        >>> from cribl_hc.analyzers import get_global_registry
        >>> registry = get_global_registry()
        >>> analyzer = registry.get_analyzer("health")
    """
    return _global_registry


def register_analyzer(analyzer_class: type[BaseAnalyzer]) -> None:
    """
    Register an analyzer in the global registry.

    Args:
        analyzer_class: Analyzer class to register

    Example:
        >>> from cribl_hc.analyzers import register_analyzer
        >>> register_analyzer(MyCustomAnalyzer)
    """
    _global_registry.register(analyzer_class)


def get_analyzer(objective: str) -> Optional[BaseAnalyzer]:
    """
    Get an analyzer from the global registry.

    Args:
        objective: Objective name

    Returns:
        Analyzer instance if found, None otherwise

    Example:
        >>> from cribl_hc.analyzers import get_analyzer
        >>> analyzer = get_analyzer("health")
    """
    return _global_registry.get_analyzer(objective)


def list_objectives() -> list[str]:
    """
    List all available objectives from the global registry.

    Returns:
        List of objective names

    Example:
        >>> from cribl_hc.analyzers import list_objectives
        >>> print(list_objectives())
        ['config', 'health', 'sizing']
    """
    return _global_registry.list_objectives()


__all__ = [
    "BaseAnalyzer",
    "AnalyzerResult",
    "AnalyzerRegistry",
    "get_global_registry",
    "register_analyzer",
    "get_analyzer",
    "list_objectives",
    # Manually add analyzers to __all__ to control public API
    "HealthAnalyzer",
    "ConfigAnalyzer",
    "ResourceAnalyzer",
    "StorageAnalyzer",
    "SecurityAnalyzer",
    "CostAnalyzer",
    "FleetAnalyzer",
    "PredictiveAnalyzer",
    "BackpressureAnalyzer",
    "PipelinePerformanceAnalyzer",
    "LookupHealthAnalyzer",
    "SchemaQualityAnalyzer",
    "DataFlowTopologyAnalyzer",
    "AlertingAnalyzer",
    "ScriptsAnalyzer",
    "LakeHealthAnalyzer",
    "LakeStorageAnalyzer",
    "LakeStorageLocationsAnalyzer",
    "SearchUsageGroupsAnalyzer",
    "SearchHealthcheckAnalyzer",
    "SearchJobMetricsAnalyzer",
    "SearchDatasetStatsAnalyzer",
    "SearchDatasetProvidersAnalyzer",
    "SearchDatasetProviderTypesAnalyzer",
    "SearchFieldStatsAnalyzer",
    "SystemMessagesAnalyzer",
    "SystemBannersAnalyzer",
    "SystemCertificatesAnalyzer",
    "SystemLogsAnalyzer",
    "SystemPoliciesAnalyzer",
    "SystemSettingsAnalyzer",
    "SystemLicenseUsageAnalyzer",
    "SystemUserInfoAnalyzer",
    "VersionControlAnalyzer",
    "FreshnessAnalyzer",
    "SensitiveDataAnalyzer",
    "InputSourceAnalyzer",
    "OutputDestinationAnalyzer",
    "RoutePerformanceAnalyzer",
    "SchemaDriftAnalyzer",
    "EndToEndFreshnessAnalyzer",
    "MultiDeploymentComparisonAnalyzer",
    "AdvancedSecurityAnalyzer",
    "LibraryAndResourceAnalyzer",
    "SearchWorkspaceOptimizationAnalyzer",
    "LicenseOptimizationAnalyzer",
]


def _auto_discover_and_register_analyzers() -> None:
    package_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name in ("base", "__init__"):
            continue
        try:
            module = importlib.import_module(f"cribl_hc.analyzers.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseAnalyzer)
                    and attr is not BaseAnalyzer
                ):
                    register_analyzer(attr)
        except Exception as e:
            import sys

            print(
                f"Warning: Failed to auto-discover analyzers from {module_name}: {e}",
                file=sys.stderr,
            )


_auto_discover_and_register_analyzers()
