"""
File Monitor Permission Analyzer for Cribl Health Check.

Audits file monitor source configurations for permission issues, path accessibility,
and common misconfigurations that cause silent data collection failures.

Community Source: https://knowledge.cribl.io/general-7/troubleshooting-file-monitor-permission-issue-1182
"""

import os
import re
from pathlib import Path
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class FileMonitorPermissionAnalyzer(BaseAnalyzer):
    """
    Analyzer for file monitor source permissions and accessibility.

    Checks:
    - Path existence and accessibility
    - Read permissions for monitored paths
    - Symlink resolution and target accessibility
    - Glob pattern validity and matching
    - Common misconfiguration patterns
    """

    INVALID_GLOB_PATTERNS = [
        r"^\*\*$",
        r"^\.+$",
    ]

    PLACEHOLDER_PATTERNS = [
        r"^/path/to/",
        r"^/var/log/example",
        r"^C:\\example",
        r"<.*>",
        r"\$\{.*\}",
    ]

    @property
    def objective_name(self) -> str:
        return "file_monitor_permissions"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return (
            "Audits file monitor source permissions, path accessibility, and configuration validity"
        )

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return [
            "read:sources",
            "read:system",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze file monitor sources for permission and accessibility issues.
        """
        result = self.create_result()

        try:
            log.info("file_monitor_permission_analysis_started")

            sources = await client.get_inputs()
            file_monitor_sources = self._filter_file_monitor_sources(sources)

            if not file_monitor_sources:
                log.info("no_file_monitor_sources_found")
                result.metadata["file_monitors_analyzed"] = 0
                result.metadata["message"] = "No file monitor sources configured"
                result.success = True
                return result

            issues_found = 0
            for source in file_monitor_sources:
                issues_found += await self._analyze_file_monitor(source, result, client)

            result.metadata.update(
                {
                    "file_monitors_analyzed": len(file_monitor_sources),
                    "issues_found": issues_found,
                    "critical_findings": len(result.get_critical_findings()),
                    "high_findings": len(result.get_high_findings()),
                }
            )

            result.success = True
            log.info(
                "file_monitor_permission_analysis_completed",
                sources=len(file_monitor_sources),
                findings=len(result.findings),
                issues=issues_found,
            )

        except Exception as e:
            log.error("file_monitor_permission_analysis_failed", error=str(e))
            result.success = False
            result.error = f"File monitor permission analysis failed: {str(e)}"
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="file-monitor-analysis-error",
                    title="File Monitor Analysis Failed",
                    description=f"Unable to complete file monitor analysis: {str(e)}",
                    severity="high",
                    category="file_monitor_permissions",
                    confidence_level="high",
                    affected_components=["file_monitor_analyzer"],
                    estimated_impact="Unable to assess file monitor health",
                    remediation_steps=[
                        "Check API connectivity",
                        "Verify authentication token has read:sources permission",
                        "Review error logs for details",
                    ],
                    metadata={"error": str(e)},
                )
            )

        return result

    def _filter_file_monitor_sources(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter sources to only file monitor types."""
        file_monitor_types = [
            "file",
            "file_monitor",
            "filemonitor",
            "syslog_file",
            "journald",
        ]
        return [
            s
            for s in sources
            if s.get("type", "").lower() in file_monitor_types and not s.get("disabled", False)
        ]

    async def _analyze_file_monitor(
        self,
        source: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        """
        Analyze a single file monitor source for issues.

        Returns count of issues found.
        """
        issues = 0
        source_id = source.get("id", "unknown")
        source_type = source.get("type", "unknown")
        paths = self._extract_monitored_paths(source)

        if not paths:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"file-monitor-no-paths-{source_id}",
                    title=f"No Paths Configured: {source_id}",
                    description=f"File monitor source '{source_id}' has no monitored paths configured.",
                    severity="high",
                    category="file_monitor_permissions",
                    confidence_level="high",
                    affected_components=[source_id],
                    estimated_impact="Source will not collect any data",
                    remediation_steps=[
                        "Add at least one path pattern to the source configuration",
                        "Example: /var/log/app/*.log",
                    ],
                    metadata={
                        "source_id": source_id,
                        "source_type": source_type,
                    },
                )
            )
            issues += 1
            return issues

        for path in paths:
            if self._is_placeholder_path(path):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"file-monitor-placeholder-{source_id}-{self._path_to_id(path)}",
                        title=f"Placeholder Path Detected: {source_id}",
                        description=f"File monitor '{source_id}' contains what appears to be a placeholder path: '{path}'",
                        severity="critical",
                        category="file_monitor_permissions",
                        confidence_level="high",
                        affected_components=[source_id],
                        estimated_impact="Source will not collect any data with placeholder path",
                        remediation_steps=[
                            "Replace placeholder path with actual file path",
                            "Verify the path exists on worker nodes",
                        ],
                        metadata={
                            "source_id": source_id,
                            "path": path,
                        },
                    )
                )
                issues += 1
                continue

            if self._is_invalid_glob(path):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"file-monitor-invalid-glob-{source_id}-{self._path_to_id(path)}",
                        title=f"Invalid Glob Pattern: {source_id}",
                        description=f"File monitor '{source_id}' has invalid glob pattern: '{path}'",
                        severity="high",
                        category="file_monitor_permissions",
                        confidence_level="high",
                        affected_components=[source_id],
                        estimated_impact="Pattern will not match files correctly",
                        remediation_steps=[
                            "Fix the glob pattern syntax",
                            "Example valid patterns: /var/log/*.log, /app/logs/**/*.json",
                        ],
                        metadata={
                            "source_id": source_id,
                            "path": path,
                        },
                    )
                )
                issues += 1
                continue

            path_issues = self._check_path_accessibility(path, source_id, client, result)
            issues += path_issues

        issues += self._check_common_misconfigurations(source, result, client)

        return issues

    def _extract_monitored_paths(self, source: dict[str, Any]) -> list[str]:
        """Extract all monitored paths from source configuration."""
        paths = []
        path_fields = [
            "path",
            "paths",
            "filename",
            "filenames",
            "directory",
            "directories",
            "watchPath",
            "watchPaths",
        ]

        for field in path_fields:
            value = source.get(field)
            if value:
                if isinstance(value, str):
                    paths.append(value)
                elif isinstance(value, list):
                    paths.extend([p for p in value if isinstance(p, str)])

        return paths

    def _is_placeholder_path(self, path: str) -> bool:
        """Check if path appears to be a placeholder/example value."""
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False

    def _is_invalid_glob(self, path: str) -> bool:
        """Check if glob pattern is invalid."""
        for pattern in self.INVALID_GLOB_PATTERNS:
            if re.match(pattern, path):
                return True

        if path.count("*") > 10:
            return True

        if path.count("[") != path.count("]"):
            return True

        return False

    def _check_path_accessibility(
        self,
        path: str,
        source_id: str,
        client: CriblAPIClient,
        result: AnalyzerResult,
    ) -> int:
        """
        Check if path is accessible on the local filesystem.

        Note: This only works when cribl-hc is running on the same system as Cribl.
        For remote deployments, we can only validate configuration syntax.

        Returns count of issues found.
        """
        issues = 0
        base_path = self._get_base_path(path)

        try:
            path_obj = Path(base_path)

            if not path_obj.exists():
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"file-monitor-path-missing-{source_id}-{self._path_to_id(path)}",
                        title=f"Path Not Found: {source_id}",
                        description=f"File monitor '{source_id}' references non-existent path: '{base_path}'",
                        severity="critical",
                        category="file_monitor_permissions",
                        confidence_level="medium",
                        affected_components=[source_id],
                        estimated_impact="Source cannot collect data - directory does not exist",
                        remediation_steps=[
                            f"Create the directory: mkdir -p {base_path}",
                            "Verify path is correct on all worker nodes",
                            "Check if path should be different (e.g., different mount point)",
                        ],
                        metadata={
                            "source_id": source_id,
                            "configured_path": path,
                            "base_path": base_path,
                        },
                    )
                )
                issues += 1
                return issues

            if not os.access(base_path, os.R_OK):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"file-monitor-no-read-{source_id}-{self._path_to_id(path)}",
                        title=f"No Read Permission: {source_id}",
                        description=f"File monitor '{source_id}' cannot read path: '{base_path}'",
                        severity="critical",
                        category="file_monitor_permissions",
                        confidence_level="medium",
                        affected_components=[source_id],
                        estimated_impact="Source cannot collect data - permission denied",
                        remediation_steps=[
                            f"Grant read access: chmod +r {base_path}",
                            "Verify Cribl process user has read permissions",
                            f"Check ACLs: getfacl {base_path}",
                        ],
                        metadata={
                            "source_id": source_id,
                            "configured_path": path,
                            "base_path": base_path,
                        },
                    )
                )
                issues += 1

            if path_obj.is_symlink():
                try:
                    resolved = path_obj.resolve()
                    if not resolved.exists():
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"file-monitor-broken-symlink-{source_id}-{self._path_to_id(path)}",
                                title=f"Broken Symlink: {source_id}",
                                description=f"File monitor '{source_id}' path is a broken symlink: '{base_path}' -> '{resolved}'",
                                severity="high",
                                category="file_monitor_permissions",
                                confidence_level="medium",
                                affected_components=[source_id],
                                estimated_impact="Source cannot follow broken symlink",
                                remediation_steps=[
                                    f"Fix or remove broken symlink: rm {base_path}",
                                    "Recreate symlink to valid target",
                                    "Or update source to use actual path",
                                ],
                                metadata={
                                    "source_id": source_id,
                                    "symlink_path": base_path,
                                    "target_path": str(resolved),
                                },
                            )
                        )
                        issues += 1
                except (OSError, RuntimeError):
                    pass

            if path_obj.is_dir():
                try:
                    matching_files = list(path_obj.glob(self._get_glob_pattern(path)))
                    if not matching_files:
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"file-monitor-no-matches-{source_id}-{self._path_to_id(path)}",
                                title=f"No Matching Files: {source_id}",
                                description=f"File monitor '{source_id}' pattern matches no files: '{path}'",
                                severity="medium",
                                category="file_monitor_permissions",
                                confidence_level="low",
                                affected_components=[source_id],
                                estimated_impact="Source may not be collecting expected data",
                                remediation_steps=[
                                    "Verify files exist matching the pattern",
                                    "Check if pattern is too restrictive",
                                    "Files may not have been created yet (could be normal)",
                                ],
                                metadata={
                                    "source_id": source_id,
                                    "configured_path": path,
                                    "base_path": base_path,
                                },
                            )
                        )
                        issues += 1
                except (OSError, ValueError):
                    pass

        except PermissionError:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"file-monitor-permission-denied-{source_id}-{self._path_to_id(path)}",
                    title=f"Permission Denied: {source_id}",
                    description=f"Cannot check path '{base_path}' - permission denied",
                    severity="high",
                    category="file_monitor_permissions",
                    confidence_level="medium",
                    affected_components=[source_id],
                    estimated_impact="Unable to verify path accessibility",
                    remediation_steps=[
                        "Run cribl-hc with appropriate permissions",
                        "Or manually verify path accessibility on Cribl workers",
                    ],
                    metadata={
                        "source_id": source_id,
                        "configured_path": path,
                        "base_path": base_path,
                    },
                )
            )
            issues += 1
        except Exception:
            pass

        return issues

    def _check_common_misconfigurations(
        self,
        source: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> int:
        """Check for common file monitor misconfigurations."""
        issues = 0
        source_id = source.get("id", "unknown")

        interval = source.get("pollInterval") or source.get("interval")
        if interval is not None:
            try:
                interval_sec = float(interval)
                if interval_sec < 1:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"file-monitor-fast-poll-{source_id}",
                            title=f"Very Fast Poll Interval: {source_id}",
                            description=f"File monitor '{source_id}' has very fast poll interval ({interval_sec}s)",
                            severity="medium",
                            category="file_monitor_permissions",
                            confidence_level="high",
                            affected_components=[source_id],
                            estimated_impact="May cause high disk I/O on worker nodes",
                            remediation_steps=[
                                "Consider increasing poll interval to 10s or higher",
                                "Use inotify-based monitoring if supported",
                            ],
                            metadata={
                                "source_id": source_id,
                                "poll_interval": interval_sec,
                            },
                        )
                    )
                    issues += 1
            except (ValueError, TypeError):
                pass

        recursive = source.get("recursive", False)
        max_depth = source.get("maxDepth") or source.get("recursionDepth")
        if recursive and max_depth is None:
            paths = self._extract_monitored_paths(source)
            for path in paths:
                if path.startswith("/") and path.count("/") <= 2:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"file-monitor-unbounded-recursion-{source_id}",
                            title=f"Unbounded Recursive Monitoring: {source_id}",
                            description=f"File monitor '{source_id}' has recursive monitoring enabled without depth limit on '{path}'",
                            severity="medium",
                            category="file_monitor_permissions",
                            confidence_level="medium",
                            affected_components=[source_id],
                            estimated_impact="May consume excessive resources monitoring many subdirectories",
                            remediation_steps=[
                                "Set maxDepth to limit recursion depth",
                                "Or use more specific path patterns",
                            ],
                            metadata={
                                "source_id": source_id,
                                "recursive": recursive,
                                "path": path,
                            },
                        )
                    )
                    issues += 1
                    break

        return issues

    def _get_base_path(self, path: str) -> str:
        """Extract the base directory from a glob pattern."""
        glob_chars = ["*", "?", "["]
        min_idx = len(path)
        for char in glob_chars:
            idx = path.find(char)
            if idx != -1 and idx < min_idx:
                min_idx = idx

        if min_idx < len(path):
            base = path[:min_idx]
            if "/" in base:
                return base.rsplit("/", 1)[0] or "/"
            return "."
        return path

    def _get_glob_pattern(self, path: str) -> str:
        """Extract glob pattern portion from full path."""
        base = self._get_base_path(path)
        if path.startswith(base):
            pattern = path[len(base) :].lstrip("/")
            return pattern if pattern else "*"
        return "*"

    def _path_to_id(self, path: str) -> str:
        """Convert a path to a safe ID string."""
        safe = re.sub(r"[^a-zA-Z0-9]", "-", path)
        safe = re.sub(r"-+", "-", safe)
        return safe[:50].strip("-")
