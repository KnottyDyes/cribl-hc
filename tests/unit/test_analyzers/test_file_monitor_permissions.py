"""
Tests for FileMonitorPermissionAnalyzer.

Tests file monitor source permission validation, path accessibility checks,
glob pattern validation, and common misconfiguration detection.
"""

from unittest.mock import AsyncMock, patch

import pytest

from cribl_hc.analyzers.file_monitor_permissions import FileMonitorPermissionAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_file_monitor_source(
    source_id: str,
    path: str | list[str] | None = None,
    source_type: str = "file",
    disabled: bool = False,
    poll_interval: float | None = None,
    recursive: bool = False,
    max_depth: int | None = None,
) -> dict:
    """Helper to create file monitor source configuration."""
    source = {
        "id": source_id,
        "type": source_type,
        "disabled": disabled,
    }
    if path is not None:
        if isinstance(path, list):
            source["paths"] = path
        else:
            source["path"] = path
    if poll_interval is not None:
        source["pollInterval"] = poll_interval
    if recursive:
        source["recursive"] = recursive
    if max_depth is not None:
        source["maxDepth"] = max_depth
    return source


class TestFileMonitorPermissionAnalyzer:
    """Test suite for FileMonitorPermissionAnalyzer."""

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_inputs = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def analyzer(self):
        return FileMonitorPermissionAnalyzer()

    @pytest.mark.asyncio
    async def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "file_monitor_permissions"

    @pytest.mark.asyncio
    async def test_supported_products(self, analyzer):
        """Test supported products."""
        assert "stream" in analyzer.supported_products
        assert "edge" in analyzer.supported_products

    @pytest.mark.asyncio
    async def test_no_file_monitors_no_findings(self, mock_client, analyzer):
        """Test that no file monitor sources produces no findings."""
        mock_client.get_inputs.return_value = [
            {"id": "splunk-input", "type": "splunk", "disabled": False},
            {"id": "kafka-input", "type": "kafka", "disabled": False},
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["file_monitors_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_disabled_file_monitor_skipped(self, mock_client, analyzer):
        """Test that disabled file monitors are skipped."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("disabled-fm", path="/var/log/*.log", disabled=True),
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["file_monitors_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_placeholder_path_critical(self, mock_client, analyzer):
        """Test that placeholder paths are flagged as CRITICAL."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("placeholder-fm", path="/path/to/logs/*.log"),
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert "Placeholder Path" in finding.title
        assert "placeholder-fm" in finding.title

    @pytest.mark.asyncio
    async def test_placeholder_path_example(self, mock_client, analyzer):
        """Test example path patterns are detected."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("example-fm", path="/var/log/example/*.log"),
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        assert result.findings[0].severity == "critical"
        assert "Placeholder" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_placeholder_variable_syntax(self, mock_client, analyzer):
        """Test ${variable} placeholder syntax detection."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("var-fm", path="${LOG_DIR}/*.log"),
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        assert result.findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_invalid_glob_just_wildcards(self, mock_client, analyzer):
        """Test that '**' alone is flagged as invalid glob."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("bad-glob-fm", path="**"),
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert "Invalid Glob" in finding.title

    @pytest.mark.asyncio
    async def test_invalid_glob_excessive_wildcards(self, mock_client, analyzer):
        """Test that excessive wildcards are flagged."""
        path_with_many_wildcards = "/var/*/*/*/*/*/*/*/*/*/*/*/log"
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("many-wildcards-fm", path=path_with_many_wildcards),
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        assert "Invalid Glob" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_invalid_glob_unbalanced_brackets(self, mock_client, analyzer):
        """Test that unbalanced brackets are flagged."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("brackets-fm", path="/var/log/[a-z.log"),
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_no_paths_configured_high(self, mock_client, analyzer):
        """Test that file monitor with no paths is flagged as HIGH."""
        mock_client.get_inputs.return_value = [
            {"id": "no-path-fm", "type": "file", "disabled": False},
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert "No Paths Configured" in finding.title

    @pytest.mark.asyncio
    async def test_fast_poll_interval_medium(self, mock_client, analyzer):
        """Test that very fast poll interval is flagged as MEDIUM."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("fast-poll-fm", path="/tmp/test.log", poll_interval=0.1),
        ]

        with patch("os.access", return_value=True):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_symlink", return_value=False):
                    with patch("pathlib.Path.is_dir", return_value=False):
                        result = await analyzer.analyze(mock_client)

        poll_findings = [f for f in result.findings if "Poll Interval" in f.title]
        assert len(poll_findings) == 1
        assert poll_findings[0].severity == "medium"
        assert poll_findings[0].metadata["poll_interval"] == 0.1

    @pytest.mark.asyncio
    async def test_unbounded_recursion_medium(self, mock_client, analyzer):
        """Test that unbounded recursive monitoring is flagged as MEDIUM."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source(
                "recursive-fm",
                path="/var",
                recursive=True,
            ),
        ]

        with patch("os.access", return_value=True):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_symlink", return_value=False):
                    with patch("pathlib.Path.is_dir", return_value=False):
                        result = await analyzer.analyze(mock_client)

        recursion_findings = [f for f in result.findings if "Recursive" in f.title]
        assert len(recursion_findings) == 1
        assert recursion_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_bounded_recursion_no_finding(self, mock_client, analyzer):
        """Test that bounded recursive monitoring has no finding."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source(
                "bounded-fm",
                path="/var/log",
                recursive=True,
                max_depth=3,
            ),
        ]

        with patch("os.access", return_value=True):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_symlink", return_value=False):
                    with patch("pathlib.Path.is_dir", return_value=False):
                        result = await analyzer.analyze(mock_client)

        recursion_findings = [f for f in result.findings if "Recursive" in f.title]
        assert len(recursion_findings) == 0

    @pytest.mark.asyncio
    async def test_path_not_found_critical(self, mock_client, analyzer):
        """Test that non-existent path is flagged as CRITICAL."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("missing-fm", path="/nonexistent/path/*.log"),
        ]

        with patch("pathlib.Path.exists", return_value=False):
            result = await analyzer.analyze(mock_client)

        path_findings = [f for f in result.findings if "Path Not Found" in f.title]
        assert len(path_findings) == 1
        assert path_findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_no_read_permission_critical(self, mock_client, analyzer):
        """Test that path without read permission is flagged as CRITICAL."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("no-read-fm", path="/etc/shadow"),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("os.access", return_value=False):
                result = await analyzer.analyze(mock_client)

        perm_findings = [f for f in result.findings if "No Read Permission" in f.title]
        assert len(perm_findings) == 1
        assert perm_findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_broken_symlink_high(self, mock_client, analyzer):
        """Test that broken symlink is flagged as HIGH."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("symlink-fm", path="/var/log/current"),
        ]

        from pathlib import Path
        from unittest.mock import MagicMock

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_symlink.return_value = True
        mock_resolved = MagicMock(spec=Path)
        mock_resolved.exists.return_value = False
        mock_path.resolve.return_value = mock_resolved

        with patch("cribl_hc.analyzers.file_monitor_permissions.Path", return_value=mock_path):
            with patch("os.access", return_value=True):
                result = await analyzer.analyze(mock_client)

        symlink_findings = [f for f in result.findings if "Broken Symlink" in f.title]
        assert len(symlink_findings) == 1
        assert symlink_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_no_matching_files_medium(self, mock_client, analyzer):
        """Test that pattern matching no files is flagged as MEDIUM."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("empty-fm", path="/tmp/logs/*.jsonl"),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("pathlib.Path.is_symlink", return_value=False):
                    with patch("pathlib.Path.is_dir", return_value=True):
                        with patch("pathlib.Path.glob", return_value=[]):
                            result = await analyzer.analyze(mock_client)

        no_match_findings = [f for f in result.findings if "No Matching Files" in f.title]
        assert len(no_match_findings) == 1
        assert no_match_findings[0].severity == "medium"
        assert no_match_findings[0].confidence_level == "low"

    @pytest.mark.asyncio
    async def test_multiple_paths_analyzed(self, mock_client, analyzer):
        """Test that multiple paths in source are all analyzed."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source(
                "multi-path-fm",
                path=["/path/to/first", "/path/to/second"],
            ),
        ]

        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 2
        assert all(f.severity == "critical" for f in result.findings)

    @pytest.mark.asyncio
    async def test_different_source_types_detected(self, mock_client, analyzer):
        """Test that various file monitor types are detected."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("fm1", path="/path/to/a", source_type="file"),
            create_file_monitor_source("fm2", path="/path/to/b", source_type="file_monitor"),
            create_file_monitor_source("fm3", path="/path/to/c", source_type="syslog_file"),
            create_file_monitor_source("fm4", path="/path/to/d", source_type="journald"),
        ]

        result = await analyzer.analyze(mock_client)

        assert result.metadata["file_monitors_analyzed"] == 4

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client, analyzer):
        """Test graceful handling of API errors."""
        mock_client.get_inputs.side_effect = Exception("Connection refused")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "Connection refused" in result.error
        assert len(result.findings) == 1
        assert result.findings[0].id == "file-monitor-analysis-error"

    @pytest.mark.asyncio
    async def test_valid_configuration_no_findings(self, mock_client, analyzer):
        """Test that valid configuration produces no findings."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source(
                "valid-fm",
                path="/var/log/app/*.log",
                poll_interval=10,
            ),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("os.access", return_value=True):
                with patch("pathlib.Path.is_symlink", return_value=False):
                    with patch("pathlib.Path.is_dir", return_value=True):
                        with patch("pathlib.Path.glob", return_value=["/var/log/app/test.log"]):
                            result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["file_monitors_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_metadata_includes_counts(self, mock_client, analyzer):
        """Test that metadata includes proper counts."""
        mock_client.get_inputs.return_value = [
            create_file_monitor_source("fm1", path="/path/to/logs"),
            create_file_monitor_source("fm2", path="**"),
        ]

        result = await analyzer.analyze(mock_client)

        assert "file_monitors_analyzed" in result.metadata
        assert "issues_found" in result.metadata
        assert "critical_findings" in result.metadata
        assert "high_findings" in result.metadata


class TestFileMonitorPermissionAnalyzerHelpers:
    """Test helper methods of FileMonitorPermissionAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return FileMonitorPermissionAnalyzer()

    def test_extract_monitored_paths_single(self, analyzer):
        """Test extracting single path."""
        source = {"path": "/var/log/*.log"}
        paths = analyzer._extract_monitored_paths(source)
        assert paths == ["/var/log/*.log"]

    def test_extract_monitored_paths_list(self, analyzer):
        """Test extracting list of paths."""
        source = {"paths": ["/var/log/*.log", "/app/logs/*.json"]}
        paths = analyzer._extract_monitored_paths(source)
        assert len(paths) == 2
        assert "/var/log/*.log" in paths
        assert "/app/logs/*.json" in paths

    def test_extract_monitored_paths_multiple_fields(self, analyzer):
        """Test extracting paths from multiple field names."""
        source = {
            "path": "/var/log/*.log",
            "directory": "/app/logs",
        }
        paths = analyzer._extract_monitored_paths(source)
        assert len(paths) == 2

    def test_is_placeholder_path_true(self, analyzer):
        """Test placeholder detection returns True."""
        assert analyzer._is_placeholder_path("/path/to/logs") is True
        assert analyzer._is_placeholder_path("/var/log/example/app.log") is True
        assert analyzer._is_placeholder_path("C:\\example\\logs") is True
        assert analyzer._is_placeholder_path("<LOG_PATH>/*.log") is True
        assert analyzer._is_placeholder_path("${HOME}/logs/*.log") is True

    def test_is_placeholder_path_false(self, analyzer):
        """Test placeholder detection returns False for real paths."""
        assert analyzer._is_placeholder_path("/var/log/syslog") is False
        assert analyzer._is_placeholder_path("/app/logs/*.log") is False
        assert analyzer._is_placeholder_path("/home/cribl/data") is False

    def test_is_invalid_glob_true(self, analyzer):
        """Test invalid glob detection returns True."""
        assert analyzer._is_invalid_glob("**") is True
        assert analyzer._is_invalid_glob("...") is True
        assert analyzer._is_invalid_glob("/a/*/*/*/*/*/*/*/*/*/*/*/b") is True
        assert analyzer._is_invalid_glob("/var/log/[unclosed") is True

    def test_is_invalid_glob_false(self, analyzer):
        """Test invalid glob detection returns False for valid patterns."""
        assert analyzer._is_invalid_glob("/var/log/*.log") is False
        assert analyzer._is_invalid_glob("/app/**/*.json") is False
        assert analyzer._is_invalid_glob("/logs/[a-z]*.txt") is False

    def test_get_base_path_no_glob(self, analyzer):
        """Test base path extraction without glob."""
        assert analyzer._get_base_path("/var/log/syslog") == "/var/log/syslog"

    def test_get_base_path_with_glob(self, analyzer):
        """Test base path extraction with glob."""
        assert analyzer._get_base_path("/var/log/*.log") == "/var/log"
        assert analyzer._get_base_path("/app/logs/**/*.json") == "/app/logs"
        assert analyzer._get_base_path("/tmp/[a-z]*.txt") == "/tmp"

    def test_get_base_path_glob_at_start(self, analyzer):
        """Test base path extraction when glob at start."""
        assert analyzer._get_base_path("*.log") == "."

    def test_get_glob_pattern(self, analyzer):
        """Test glob pattern extraction."""
        assert analyzer._get_glob_pattern("/var/log/*.log") == "*.log"
        assert analyzer._get_glob_pattern("/var/log/syslog") == "*"

    def test_path_to_id(self, analyzer):
        """Test path to ID conversion."""
        result = analyzer._path_to_id("/var/log/*.log")
        assert "/" not in result
        assert "*" not in result
        assert "-" in result
        assert len(result) <= 50
