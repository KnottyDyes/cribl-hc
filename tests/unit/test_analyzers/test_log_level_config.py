"""
Unit tests for LogLevelConfigurationAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.log_level_config import LogLevelConfigurationAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestLogLevelConfigurationAnalyzer:
    @pytest.fixture
    def analyzer(self) -> LogLevelConfigurationAnalyzer:
        return LogLevelConfigurationAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_system_settings = AsyncMock(return_value={})
        return client

    def test_objective_name(self, analyzer: LogLevelConfigurationAnalyzer) -> None:
        assert analyzer.objective_name == "log_level_config"

    def test_supported_products(self, analyzer: LogLevelConfigurationAnalyzer) -> None:
        products = analyzer.supported_products
        assert "stream" in products
        assert "edge" in products
        assert "lake" in products
        assert "search" in products

    def test_required_permissions(self, analyzer: LogLevelConfigurationAnalyzer) -> None:
        assert "read:system:settings" in analyzer.get_required_permissions()

    @pytest.mark.asyncio
    async def test_no_system_settings(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(return_value=None)
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-config-unavailable" for f in result.findings)

    @pytest.mark.asyncio
    async def test_silly_log_level(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={"logLevel": "silly"}
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-level-silly" for f in result.findings)
        assert result.metadata["log_level"] == "silly"

    @pytest.mark.asyncio
    async def test_debug_log_level(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={"logLevel": "debug"}
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-level-debug" for f in result.findings)

    @pytest.mark.asyncio
    async def test_info_log_level(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={"logLevel": "info"}
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-level-info" for f in result.findings)

    @pytest.mark.asyncio
    async def test_warn_log_level(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={"logLevel": "warn"}
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Warn level should be OK (no findings for log level)
        assert not any("log-level-" in f.id for f in result.findings if f.severity in ["critical", "high"])

    @pytest.mark.asyncio
    async def test_error_log_level(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={"logLevel": "error"}
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Error level should be OK
        assert not any("log-level-" in f.id for f in result.findings if f.severity in ["critical", "high"])

    @pytest.mark.asyncio
    async def test_log_rotation_disabled(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRotation": {"enabled": False}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-rotation-disabled" for f in result.findings)

    @pytest.mark.asyncio
    async def test_log_rotation_enabled(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRotation": {"enabled": True}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Should not have rotation disabled finding
        assert not any("log-rotation-disabled" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_log_rotation_size_large(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRotation": {
                    "enabled": True,
                    "maxSizeBytes": 2 * 1024 * 1024 * 1024  # 2GB
                }
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-rotation-size-large" for f in result.findings)

    @pytest.mark.asyncio
    async def test_log_retention_too_long_critical(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRetention": {"days": 45}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-retention-warning" for f in result.findings)

    @pytest.mark.asyncio
    async def test_log_retention_too_long_warning(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRetention": {"days": 45}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-retention-warning" for f in result.findings)

    @pytest.mark.asyncio
    async def test_log_retention_ok(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRetention": {"days": 14}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Should not have retention warnings
        assert not any("log-retention" in f.id for f in result.findings)

    @pytest.mark.asyncio
    async def test_log_retention_not_set(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRetention": {}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-retention-not-set" for f in result.findings)

    @pytest.mark.asyncio
    async def test_nested_logging_config(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logging": {
                    "level": "silly",
                    "rotation": {"enabled": True},
                    "retention": {"days": 15}
                }
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        assert any(f.id == "log-level-silly" for f in result.findings)

    @pytest.mark.asyncio
    async def test_multiple_issues(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "debug",
                "logRotation": {"enabled": False},
                "logRetention": {"days": 60}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Should have multiple findings
        assert any(f.id == "log-level-debug" for f in result.findings)
        assert any(f.id == "log-rotation-disabled" for f in result.findings)
        assert any(f.id == "log-retention-warning" for f in result.findings)

    @pytest.mark.asyncio
    async def test_good_config(
        self, analyzer: LogLevelConfigurationAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        mock_client.get_system_settings = AsyncMock(
            return_value={
                "logLevel": "warn",
                "logRotation": {
                    "enabled": True,
                    "maxSizeBytes": 100 * 1024 * 1024  # 100MB
                },
                "logRetention": {"days": 14}
            }
        )
        result = await analyzer.analyze(mock_client)
        assert result.success
        # Should have minimal findings (info about warn level is OK)
        findings_with_warnings = [f for f in result.findings if f.severity in ["critical", "high", "medium"]]
        assert len(findings_with_warnings) == 0
