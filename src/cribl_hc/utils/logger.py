"""
Structured logging using structlog with JSON output for audit trail.

This module provides a configured structured logger for the Cribl health check tool.
All logs include timestamps, context, and are formatted as JSON for easy parsing.
"""

import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    include_timestamp: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Whether to output JSON format (default: True)
        include_timestamp: Whether to include timestamps (default: True)

    Example:
        >>> configure_logging(level="DEBUG", json_output=True)
        >>> log = get_logger("my_module")
        >>> log.info("operation_complete", deployment_id="prod", duration_ms=1250)
    """
    # Define processors for log formatting
    processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        # Note: add_logger_name removed - incompatible with PrintLoggerFactory
        # PrintLogger doesn't have a .name attribute
    ]

    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    # Add context processors
    processors.extend(
        [
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
    )

    # Add final renderer
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically module name: __name__)
              If None, uses root logger

    Returns:
        Configured structured logger

    Example:
        >>> log = get_logger(__name__)
        >>> log.info("api_call", endpoint="/api/v1/workers", status_code=200)
        {"event": "api_call", "endpoint": "/api/v1/workers", "status_code": 200, ...}
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


class AuditLogger:
    """
    Audit logger for tracking all API calls and sensitive operations.

    This logger ensures all operations are tracked for compliance and debugging.
    """

    def __init__(self, logger_name: str = "audit"):
        """
        Initialize audit logger.

        Args:
            logger_name: Name for the audit logger (default: "audit")
        """
        self.log = get_logger(logger_name)

    def log_api_call(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        deployment_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Log an API call for audit trail.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            deployment_id: Deployment identifier (optional)
            error: Error message if request failed (optional)
        """
        log_data: Dict[str, Any] = {
            "event": "api_call",
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        if deployment_id:
            log_data["deployment_id"] = deployment_id

        if error:
            log_data["error"] = error
            self.log.error(**log_data)
        elif status_code >= 400:
            self.log.warning(**log_data)
        else:
            self.log.info(**log_data)

    def log_analysis_start(
        self,
        deployment_id: str,
        objectives: list[str],
    ) -> None:
        """
        Log the start of an analysis run.

        Args:
            deployment_id: Deployment being analyzed
            objectives: List of objectives being analyzed
        """
        self.log.info(
            "analysis_started",
            deployment_id=deployment_id,
            objectives=objectives,
        )

    def log_analysis_complete(
        self,
        deployment_id: str,
        duration_seconds: float,
        api_calls_used: int,
        health_score: Optional[float] = None,
        findings_count: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """
        Log the completion of an analysis run.

        Args:
            deployment_id: Deployment that was analyzed
            duration_seconds: Total analysis duration
            api_calls_used: Number of API calls made
            health_score: Overall health score (if calculated)
            findings_count: Number of findings identified
            error: Error message if analysis failed
        """
        log_data: Dict[str, Any] = {
            "event": "analysis_completed",
            "deployment_id": deployment_id,
            "duration_seconds": round(duration_seconds, 2),
            "api_calls_used": api_calls_used,
            "findings_count": findings_count,
        }

        if health_score is not None:
            log_data["health_score"] = round(health_score, 2)

        if error:
            log_data["error"] = error
            self.log.error(**log_data)
        else:
            self.log.info(**log_data)

    def log_credential_operation(
        self,
        operation: str,
        deployment_id: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Log credential operations (store, retrieve, delete).

        Args:
            operation: Operation type (store, retrieve, delete)
            deployment_id: Deployment ID
            success: Whether operation succeeded
            error: Error message if operation failed
        """
        log_data: Dict[str, Any] = {
            "event": "credential_operation",
            "operation": operation,
            "deployment_id": deployment_id,
            "success": success,
        }

        if error:
            log_data["error"] = error
            self.log.error(**log_data)
        else:
            self.log.info(**log_data)


# Initialize default configuration on module import
configure_logging()
