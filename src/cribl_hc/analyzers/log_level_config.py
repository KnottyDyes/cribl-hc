"""
Log Level Configuration Analyzer for Cribl Health Check.

Analyzes logging configuration for production safety.

Priority: P3 (Production logging safety)
"""

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class LogLevelConfigurationAnalyzer(BaseAnalyzer):
    """Analyzer for logging configuration validation."""

    # Log level severity thresholds
    SILLY_LEVELS = {"silly"}
    DEBUG_LEVELS = {"debug", "trace"}
    INFO_LEVELS = {"info", "information", "informational"}
    WARN_LEVELS = {"warn", "warning", "warnings"}
    ERROR_LEVELS = {"error", "errors"}
    FATAL_LEVELS = {"fatal", "critical"}

    # Recommended retention in days
    RETENTION_WARNING_DAYS = 30
    RETENTION_CRITICAL_DAYS = 90

    @property
    def objective_name(self) -> str:
        return "log_level_config"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge", "lake", "search"]

    def get_description(self) -> str:
        return "Validates logging configuration for production safety, including log levels and retention"

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:system:settings"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            log.info("log_level_config_analysis_started")

            # Get system settings which contain log configuration
            system_settings = await client.get_system_settings()

            if not system_settings:
                log.info("no_system_settings")
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="log-config-unavailable",
                        category="system",
                        severity="info",
                        title="Log Configuration Unavailable",
                        description="Log configuration could not be retrieved from system settings.",
                        affected_components=["system"],
                        confidence_level="medium",
                    )
                )
                result.success = True
                return result

            # 1. Check log level
            log_level = self._extract_log_level(system_settings)

            if log_level:
                self._validate_log_level(log_level, result, client)

            # 2. Check log rotation settings
            self._validate_log_rotation(system_settings, result, client)

            # 3. Check log retention
            self._validate_log_retention(system_settings, result, client)

            result.metadata.update(
                {
                    "log_level": log_level or "unknown",
                    "log_config_analyzed": True,
                }
            )
            result.success = True

        except Exception as exc:
            error_str = str(exc)
            log.error("log_level_config_failed", error=error_str)
            result.success = False
            result.metadata["error"] = error_str
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-config-analysis-error",
                    category="system",
                    severity="critical",
                    title="Log Configuration Analysis Failed",
                    description=f"Failed to analyze log configuration: {error_str}",
                    affected_components=["System"],
                    remediation_steps=["Verify API connectivity and permissions"],
                    estimated_impact="Log configuration validation unavailable",
                    confidence_level="high",
                )
            )

        return result

    def _extract_log_level(self, settings: dict) -> str:
        """Extract log level from various possible settings locations."""
        # Try various possible field names for log level
        log_level = (
            settings.get("logLevel")
            or settings.get("log_level")
            or settings.get("logging", {}).get("level")
            or settings.get("logger", {}).get("level")
            or ""
        )
        return log_level.lower() if log_level else ""

    def _validate_log_level(
        self, log_level: str, result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Validate log level for production safety."""
        if not log_level:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-level-unknown",
                    category="system",
                    severity="info",
                    title="Log Level: Not configured",
                    description="Log level could not be determined from configuration.",
                    affected_components=["System"],
                    confidence_level="medium",
                )
            )
            return

        if log_level in self.SILLY_LEVELS:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-level-silly",
                    category="system",
                    severity="critical",
                    title="Log Level: 'silly' in production",
                    description=f"Log level is set to '{log_level}', which will generate excessive log output. "
                    f"This can overwhelm infrastructure with disk I/O and fill storage quickly.",
                    affected_components=["System"],
                    remediation_steps=[
                        "Change log level to 'warn' or 'error' for production",
                        "Only use 'silly' for troubleshooting specific issues",
                    ],
                    estimated_impact="Disk fill, performance degradation, storage exhaustion",
                    confidence_level="high",
                )
            )
        elif log_level in self.DEBUG_LEVELS:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-level-debug",
                    category="system",
                    severity="high",
                    title=f"Log Level: '{log_level}' in production",
                    description=f"Log level is set to '{log_level}', which generates verbose output. "
                    f"This can impact performance and use significant disk space over time.",
                    affected_components=["System"],
                    remediation_steps=[
                        "Change log level to 'warn' for production workloads",
                        "Only use 'debug' when actively troubleshooting",
                    ],
                    estimated_impact="Performance impact, increased disk usage",
                    confidence_level="high",
                )
            )
        elif log_level in self.INFO_LEVELS:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-level-info",
                    category="system",
                    severity="low",
                    title=f"Log Level: '{log_level}' could be reduced",
                    description=f"Log level is set to '{log_level}'. Consider using 'warn' "
                    f"for production to reduce log volume while maintaining visibility.",
                    affected_components=["System"],
                    remediation_steps=["Consider changing log level to 'warn' for production"],
                    confidence_level="medium",
                )
            )

    def _validate_log_rotation(
        self, settings: dict, result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Validate log rotation settings."""
        # Check for log rotation configuration
        # Various possible locations for rotation settings
        rotation_config = (
            settings.get("logRotation")
            or settings.get("log_rotation")
            or settings.get("logging", {}).get("rotation")
            or settings.get("logger", {}).get("rotation")
            or {}
        )

        # Check if rotation is enabled
        rotation_enabled = rotation_config.get("enabled", True)

        if not rotation_enabled:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-rotation-disabled",
                    category="system",
                    severity="medium",
                    title="Log Rotation: Disabled",
                    description="Log rotation is disabled. Log files will grow indefinitely "
                    f"and will eventually fill available disk space.",
                    affected_components=["System"],
                    remediation_steps=[
                        "Enable log rotation in system settings",
                        "Configure rotation size or time limits",
                    ],
                    estimated_impact="Disk will eventually fill, system may become unresponsive",
                    confidence_level="high",
                )
            )
        # Check rotation size limit
        max_size_bytes = rotation_config.get("maxSizeBytes") or rotation_config.get(
            "max_size_bytes"
        )
        if max_size_bytes:
            max_size_mb = max_size_bytes / (1024 * 1024)
            if max_size_mb > 1000:  # > 1GB
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="log-rotation-size-large",
                        category="system",
                        severity="low",
                        title=f"Log Rotation: Large file size limit ({max_size_mb:.1f} MB)",
                        description=f"Log rotation maximum file size is {max_size_mb:.1f} MB. "
                        f"Large log files can impact performance and take longer to rotate.",
                        affected_components=["system"],
                        remediation_steps=["Consider reducing max log file size to 100-500 MB"],
                        confidence_level="medium",
                    )
                )

    def _validate_log_retention(
        self, settings: dict, result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Validate log retention settings."""
        # Check for retention configuration
        retention_config = (
            settings.get("logRetention")
            or settings.get("log_retention")
            or settings.get("logging", {}).get("retention")
            or settings.get("logger", {}).get("retention")
            or {}
        )

        # Check retention in days
        retention_days = retention_config.get("days") or retention_config.get("maxAgeDays")

        if retention_days:
            if retention_days > self.RETENTION_CRITICAL_DAYS:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="log-retention-critical",
                        category="system",
                        severity="high",
                        title=f"Log Retention: Too long ({retention_days} days)",
                        description=f"Log retention is configured for {retention_days} days. "
                        f"This can consume significant disk space and increase backup costs.",
                        affected_components=["system"],
                        remediation_steps=[
                            f"Reduce log retention to {self.RETENTION_WARNING_DAYS} days or less",
                            "Archive old logs to cold storage if needed",
                        ],
                        estimated_impact="Increased storage costs, disk space exhaustion",
                        confidence_level="high",
                    )
                )
            elif retention_days > self.RETENTION_WARNING_DAYS:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="log-retention-warning",
                        category="system",
                        severity="medium",
                        title=f"Log Retention: Long ({retention_days} days)",
                        description=f"Log retention is configured for {retention_days} days. "
                        f"Consider reducing to {self.RETENTION_WARNING_DAYS} days to save disk space.",
                        affected_components=["system"],
                        remediation_steps=[
                            f"Consider reducing log retention to {self.RETENTION_WARNING_DAYS} days"
                        ],
                        confidence_level="medium",
                    )
                )
        else:
            # No explicit retention configured
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="log-retention-not-set",
                    category="system",
                    severity="medium",
                    title="Log Retention: Not explicitly configured",
                    description="Log retention period is not explicitly configured. "
                    f"Logs may accumulate indefinitely until disk space is exhausted.",
                    affected_components=["System"],
                    remediation_steps=[
                        "Configure explicit log retention period in system settings",
                        f"Set retention to {self.RETENTION_WARNING_DAYS} days or less",
                    ],
                    estimated_impact="Disk will eventually fill",
                    confidence_level="medium",
                )
            )
