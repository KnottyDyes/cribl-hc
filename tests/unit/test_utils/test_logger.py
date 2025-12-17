"""
Unit tests for structured logging functionality.
"""

import json
from io import StringIO
import sys

import pytest
import structlog

from cribl_hc.utils.logger import (
    configure_logging,
    get_logger,
    AuditLogger,
)


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_json_output(self):
        """Test configuring logger with JSON output."""
        configure_logging(level="INFO", json_output=True, include_timestamp=True)
        log = get_logger("test")

        # Verify logger is configured
        assert log is not None
        # structlog returns a BoundLoggerLazyProxy, not BoundLogger directly
        assert hasattr(log, 'info')
        assert hasattr(log, 'error')

    def test_configure_logging_console_output(self):
        """Test configuring logger with console output."""
        configure_logging(level="DEBUG", json_output=False, include_timestamp=False)
        log = get_logger("test")

        assert log is not None

    def test_get_logger_with_name(self):
        """Test getting a named logger."""
        log = get_logger("test_module")
        assert log is not None

    def test_get_logger_without_name(self):
        """Test getting root logger."""
        log = get_logger()
        assert log is not None


class TestAuditLogger:
    """Test audit logging functionality."""

    def test_audit_logger_initialization(self):
        """Test audit logger initialization."""
        audit = AuditLogger("test_audit")
        assert audit.log is not None

    def test_log_api_call_success(self, capfd):
        """Test logging successful API call."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_api_call(
            method="GET",
            endpoint="/api/v1/workers",
            status_code=200,
            duration_ms=125.5,
            deployment_id="prod",
        )

        captured = capfd.readouterr()
        assert "api_call" in captured.out
        assert "GET" in captured.out
        assert "/api/v1/workers" in captured.out

    def test_log_api_call_with_error(self, capfd):
        """Test logging failed API call."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_api_call(
            method="GET",
            endpoint="/api/v1/workers",
            status_code=500,
            duration_ms=50.0,
            error="Internal Server Error",
        )

        captured = capfd.readouterr()
        assert "api_call" in captured.out
        assert "error" in captured.out.lower()

    def test_log_api_call_client_error(self, capfd):
        """Test logging API call with client error (4xx)."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_api_call(
            method="GET",
            endpoint="/api/v1/workers",
            status_code=404,
            duration_ms=25.0,
        )

        captured = capfd.readouterr()
        # Should log as warning for 4xx codes
        assert "api_call" in captured.out

    def test_log_analysis_start(self, capfd):
        """Test logging analysis start."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_analysis_start(
            deployment_id="prod",
            objectives=["health", "config"],
        )

        captured = capfd.readouterr()
        assert "analysis_started" in captured.out
        assert "prod" in captured.out
        assert "health" in captured.out

    def test_log_analysis_complete_success(self, capfd):
        """Test logging successful analysis completion."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_analysis_complete(
            deployment_id="prod",
            duration_seconds=125.5,
            api_calls_used=45,
            health_score=85.5,
            findings_count=3,
        )

        captured = capfd.readouterr()
        assert "analysis_completed" in captured.out
        assert "prod" in captured.out
        assert "125.5" in captured.out or "125.50" in captured.out
        assert "45" in captured.out

    def test_log_analysis_complete_with_error(self, capfd):
        """Test logging failed analysis completion."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_analysis_complete(
            deployment_id="prod",
            duration_seconds=10.0,
            api_calls_used=5,
            error="Connection timeout",
        )

        captured = capfd.readouterr()
        assert "analysis_completed" in captured.out
        assert "error" in captured.out.lower()
        assert "timeout" in captured.out.lower()

    def test_log_credential_operation_success(self, capfd):
        """Test logging successful credential operation."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_credential_operation(
            operation="store",
            deployment_id="prod",
            success=True,
        )

        captured = capfd.readouterr()
        assert "credential_operation" in captured.out
        assert "store" in captured.out
        assert "prod" in captured.out

    def test_log_credential_operation_failure(self, capfd):
        """Test logging failed credential operation."""
        configure_logging(level="INFO", json_output=True)
        audit = AuditLogger("test")

        audit.log_credential_operation(
            operation="retrieve",
            deployment_id="prod",
            success=False,
            error="Decryption failed",
        )

        captured = capfd.readouterr()
        assert "credential_operation" in captured.out
        assert "error" in captured.out.lower()
        assert "decryption" in captured.out.lower()


class TestStructuredLogging:
    """Test structured logging capabilities."""

    def test_log_with_context(self, capfd):
        """Test logging with structured context."""
        configure_logging(level="INFO", json_output=True)
        log = get_logger("test")

        log.info("test_event", key1="value1", key2=42, key3=True)

        captured = capfd.readouterr()
        assert "test_event" in captured.out
        assert "value1" in captured.out
        assert "42" in captured.out

    def test_log_levels(self, capfd):
        """Test different log levels."""
        configure_logging(level="DEBUG", json_output=True)
        log = get_logger("test")

        log.debug("debug_message")
        log.info("info_message")
        log.warning("warning_message")
        log.error("error_message")

        captured = capfd.readouterr()
        assert "debug_message" in captured.out
        assert "info_message" in captured.out
        assert "warning_message" in captured.out
        assert "error_message" in captured.out

    def test_json_output_format(self, capfd):
        """Test that JSON output is valid."""
        configure_logging(level="INFO", json_output=True, include_timestamp=True)
        log = get_logger("test")

        log.info("test_event", test_key="test_value")

        captured = capfd.readouterr()
        # Should be valid JSON
        try:
            # Each line should be a JSON object
            for line in captured.out.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    # Check for expected fields
                    assert "event" in data
                    assert data["event"] == "test_event"
        except json.JSONDecodeError:
            pytest.fail("Log output is not valid JSON")

    def test_console_output_format(self, capfd):
        """Test console output format (human-readable)."""
        configure_logging(level="INFO", json_output=False, include_timestamp=False)
        log = get_logger("test")

        log.info("test_event", key="value")

        captured = capfd.readouterr()
        # Should be human-readable, not JSON
        assert "test_event" in captured.out
        # Should not look like JSON
        assert not captured.out.strip().startswith('{')
