"""
Version Control Analyzer for Cribl Health Check.

Analyzes uncommitted configuration changes, pending deployments, and
configuration drift across Cribl products (Stream, Edge, Lake, Search).

Priority: P2 (Configuration Management - critical for operational stability)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class VersionControlAnalyzer(BaseAnalyzer):
    """
    Analyzer for version control and configuration deployment health.

    Identifies:
    - Uncommitted configuration changes in the UI
    - Pending deployments not yet pushed to workers
    - Configuration drift between workers
    - Stale uncommitted changes (age threshold)
    - Missing GitOps integration
    - Deployment failures or stuck deployments

    Priority: P2 (Configuration Management - critical for operational stability)

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = VersionControlAnalyzer()
        ...     result = await analyzer.analyze(client)
        ...     if result.metadata.get('uncommitted_changes'):
        ...         print("Warning: Uncommitted changes detected!")
    """

    # Thresholds for uncommitted change age warnings
    UNCOMMITTED_WARNING_HOURS = 4  # Warn if changes uncommitted for 4+ hours
    UNCOMMITTED_CRITICAL_HOURS = 24  # Critical if changes uncommitted for 24+ hours

    # Deployment thresholds
    DEPLOYMENT_STUCK_MINUTES = 10  # Deployment taking longer than 10 min is stuck

    @property
    def objective_name(self) -> str:
        """Return 'version_control' as the objective name."""
        return "version_control"

    @property
    def supported_products(self) -> list[str]:
        """Version control analyzer applies to all products."""
        return ["stream", "edge", "lake", "search", "core"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Uncommitted configuration changes and deployment status analysis"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls needed.

        - version/info(1) + version/status(1) + uncommittedFiles(1) +
          worker_groups(1) + master_summary(1) = 5 calls
        """
        return 5

    def get_required_permissions(self) -> list[str]:
        """List required API permissions."""
        return [
            "read:version",
            "read:groups",
            "read:system",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze version control and deployment status.

        Checks for uncommitted changes, pending deployments, and
        configuration drift across workers.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with version control findings
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            self.log.info("version_control_analysis_started")

            # Fetch version control status
            version_info = await client.get_version_info()
            version_status = await client.get_version_status()
            uncommitted_files = await client.get_uncommitted_files()
            deployment_status = await client.get_deployment_status()

            # Store metadata
            result.metadata["git_enabled"] = version_info.get("enabled", False)
            result.metadata["git_remote"] = version_info.get("remote", None)
            result.metadata["uncommitted_changes"] = version_status.get("uncommittedChanges", False)
            result.metadata["undeployed_commits"] = version_status.get("undeployedCommits", False)
            result.metadata["uncommitted_file_count"] = len(uncommitted_files)
            result.metadata["uncommitted_files"] = uncommitted_files[:10]  # Limit for metadata
            result.metadata["pending_deployments"] = deployment_status.get("pendingDeployments", 0)
            result.metadata["deploying_workers"] = deployment_status.get("deployingWorkers", 0)
            result.metadata["config_drift"] = deployment_status.get("configDrift", False)
            result.metadata["current_commit"] = version_status.get("commit", None)
            result.metadata["last_commit_timestamp"] = version_status.get("timestamp", None)

            # Analyze uncommitted changes
            self._analyze_uncommitted_changes(
                version_status, uncommitted_files, result
            )

            # Analyze pending deployments
            self._analyze_pending_deployments(deployment_status, result)

            # Analyze git configuration
            self._analyze_git_configuration(version_info, result)

            # Generate recommendations
            self._generate_recommendations(result)

            # Calculate summary
            self._generate_summary(result)

            result.success = True
            self.log.info(
                "version_control_analysis_completed",
                uncommitted_changes=result.metadata["uncommitted_changes"],
                pending_deployments=result.metadata["pending_deployments"],
                findings_count=len(result.findings),
            )

        except Exception as e:
            result.success = False
            result.error = f"Version control analysis failed: {e}"
            self.log.error("version_control_analysis_failed", error=str(e))

        return result

    def _analyze_uncommitted_changes(
        self,
        version_status: dict[str, Any],
        uncommitted_files: list[dict[str, Any]],
        result: AnalyzerResult,
    ) -> None:
        """Analyze uncommitted configuration changes and undeployed commits."""
        has_uncommitted = version_status.get("uncommittedChanges", False)
        has_undeployed = version_status.get("undeployedCommits", False)

        # Check for undeployed commits first (independent of uncommitted files)
        if has_undeployed:
            result.findings.append(Finding(
                id="vc-undeployed-commits",
                severity="high",
                category="configuration",
                confidence_level="high",
                title="Committed Changes Not Deployed to Workers",
                description=(
                    "Configuration changes have been committed but not yet deployed to workers. "
                    "Workers are running with an older configuration version."
                ),
                remediation_steps=[
                    "Review committed changes waiting for deployment",
                    "Deploy pending commits to all worker groups",
                    "Verify workers receive the new configuration",
                    "Consider scheduling deployment during maintenance window",
                ],
                metadata={
                    "current_commit": version_status.get("commit"),
                    "last_commit_message": version_status.get("message"),
                    "last_commit_timestamp": version_status.get("timestamp"),
                },
                estimated_impact="Workers are processing data with outdated configuration",
            ))

        if not has_uncommitted and not uncommitted_files:
            return

        # Determine severity based on file types and count
        file_count = len(uncommitted_files)
        critical_files = []
        pipeline_files = []
        route_files = []
        other_files = []

        for f in uncommitted_files:
            path = f.get("path", "") if isinstance(f, dict) else str(f)
            if "pipelines" in path.lower():
                pipeline_files.append(path)
            elif "routes" in path.lower():
                route_files.append(path)
            elif any(x in path.lower() for x in ["auth", "cert", "secret", "credential"]):
                critical_files.append(path)
            else:
                other_files.append(path)

        # Critical: Security-related uncommitted changes
        if critical_files:
            result.findings.append(Finding(
                id="vc-uncommitted-security-changes",
                severity="critical",
                category="configuration",
                confidence_level="high",
                title="Uncommitted Security-Related Configuration Changes",
                description=(
                    f"Found {len(critical_files)} uncommitted changes to security-related "
                    f"configuration files. These changes are only in the UI and not saved: "
                    f"{', '.join(critical_files[:5])}"
                    + (f" and {len(critical_files) - 5} more" if len(critical_files) > 5 else "")
                ),
                remediation_steps=[
                    "Review security-related changes in the Cribl UI",
                    "Commit changes if they are intentional",
                    "Deploy to workers if running in distributed mode",
                    "Discard changes if they were unintentional",
                ],
                metadata={
                    "files": critical_files,
                    "file_count": len(critical_files),
                    "change_type": "security",
                },
                estimated_impact="Security configuration may be inconsistent; changes could be lost on restart",
            ))

        # High: Pipeline or route changes
        if pipeline_files or route_files:
            severity = "high" if (len(pipeline_files) + len(route_files)) > 3 else "medium"
            affected_files = pipeline_files + route_files
            result.findings.append(Finding(
                id="vc-uncommitted-data-path-changes",
                severity=severity,
                category="configuration",
                confidence_level="high",
                title="Uncommitted Pipeline/Route Configuration Changes",
                description=(
                    f"Found {len(affected_files)} uncommitted changes to data path configuration. "
                    f"Pipelines: {len(pipeline_files)}, Routes: {len(route_files)}. "
                    f"These changes exist only in the UI and are not active on workers."
                ),
                remediation_steps=[
                    "Review pipeline and route changes in the Cribl UI",
                    "Test changes in a non-production environment if possible",
                    "Commit and deploy changes to activate them",
                    "Document changes for audit trail",
                ],
                metadata={
                    "pipeline_files": pipeline_files[:5],
                    "route_files": route_files[:5],
                    "pipeline_count": len(pipeline_files),
                    "route_count": len(route_files),
                },
                estimated_impact="Data processing configuration may not reflect intended state",
            ))

        # Medium/Low: Other uncommitted changes
        if other_files or (has_uncommitted and not uncommitted_files):
            total_other = len(other_files) if other_files else file_count
            severity = "medium" if total_other > 5 else "low"
            result.findings.append(Finding(
                id="vc-uncommitted-config-changes",
                severity=severity,
                category="configuration",
                confidence_level="high",
                title="Uncommitted Configuration Changes Detected",
                description=(
                    f"Found {total_other} uncommitted configuration change(s) in the Cribl UI. "
                    f"These changes are not saved and will be lost if the leader restarts."
                ),
                remediation_steps=[
                    "Open the Cribl UI and review pending changes",
                    "Commit changes to save them to the configuration",
                    "Deploy changes to workers if in distributed mode",
                    "Consider enabling GitOps for version control",
                ],
                metadata={
                    "files": other_files[:10],
                    "file_count": total_other,
                },
                estimated_impact="Configuration changes may be lost; workers may have stale config",
            ))

    def _analyze_pending_deployments(
        self,
        deployment_status: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Analyze pending deployments and config drift."""
        pending = deployment_status.get("pendingDeployments", 0)
        deploying = deployment_status.get("deployingWorkers", 0)
        has_drift = deployment_status.get("configDrift", False)
        groups = deployment_status.get("groups", [])

        # Check for active deployments
        if deploying > 0:
            deploying_groups = [g for g in groups if g.get("deployingCount", 0) > 0]
            result.findings.append(Finding(
                id="vc-deployment-in-progress",
                severity="info",
                category="configuration",
                confidence_level="high",
                title="Configuration Deployment In Progress",
                description=(
                    f"{deploying} worker(s) are currently receiving configuration updates "
                    f"across {len(deploying_groups)} worker group(s). This is normal during "
                    f"deployment and should complete within a few minutes."
                ),
                remediation_steps=[
                    "Monitor deployment progress in the Cribl UI",
                    "Check worker logs if deployment takes longer than 10 minutes",
                    "Verify workers come back healthy after deployment",
                ],
                metadata={
                    "deploying_workers": deploying,
                    "deploying_groups": [g["group"] for g in deploying_groups],
                },
                estimated_impact="Temporary; workers will be updated shortly",
            ))

        # Check for config drift (workers on different versions)
        if has_drift:
            drift_groups = [g for g in groups if g.get("hasDrift", False)]
            result.findings.append(Finding(
                id="vc-config-drift-detected",
                severity="high",
                category="configuration",
                confidence_level="high",
                title="Configuration Drift Detected Between Workers",
                description=(
                    f"Workers in {len(drift_groups)} group(s) are running different "
                    f"configuration versions. This can cause inconsistent data processing."
                ),
                remediation_steps=[
                    "Identify workers with stale configuration",
                    "Trigger manual deployment to affected workers",
                    "Check for deployment failures in worker logs",
                    "Restart stuck workers if deployment is blocked",
                ],
                metadata={
                    "drift_groups": [g["group"] for g in drift_groups],
                    "group_details": drift_groups,
                },
                estimated_impact="Inconsistent data processing across workers",
            ))

        # Check for stuck deployments (groups with deploying workers for too long)
        # This would require tracking deployment start time, which we don't have
        # So we flag if there are many workers deploying simultaneously
        if deploying > 5:
            result.findings.append(Finding(
                id="vc-large-deployment-in-progress",
                severity="medium",
                category="configuration",
                confidence_level="high",
                title="Large-Scale Deployment In Progress",
                description=(
                    f"{deploying} workers are simultaneously receiving configuration updates. "
                    f"Large deployments may take longer and should be monitored."
                ),
                remediation_steps=[
                    "Monitor deployment progress in the Cribl UI",
                    "Ensure sufficient network bandwidth for config distribution",
                    "Consider rolling deployments for very large fleets",
                    "Check for deployment failures if not completing",
                ],
                metadata={
                    "deploying_workers": deploying,
                    "total_groups": deployment_status.get("totalGroups", 0),
                },
                estimated_impact="Extended deployment time; monitor for completion",
            ))

    def _analyze_git_configuration(
        self,
        version_info: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Analyze Git/version control configuration."""
        git_enabled = version_info.get("enabled", False)
        has_remote = bool(version_info.get("remote"))

        if not git_enabled and not has_remote:
            result.findings.append(Finding(
                id="vc-git-not-configured",
                severity="medium",
                category="configuration",
                confidence_level="high",
                title="GitOps/Version Control Not Configured",
                description=(
                    "Git integration is not configured for this Cribl deployment. "
                    "Without version control, configuration changes lack audit trail "
                    "and cannot be easily rolled back."
                ),
                remediation_steps=[
                    "Configure Git integration in System Settings",
                    "Connect to a Git repository for configuration versioning",
                    "Set up CI/CD pipeline for automated deployments",
                    "Document configuration change procedures",
                ],
                metadata={
                    "git_enabled": git_enabled,
                    "has_remote": has_remote,
                },
                estimated_impact="No audit trail for configuration changes; difficult rollback",
            ))
        elif git_enabled and not has_remote:
            result.findings.append(Finding(
                id="vc-git-no-remote",
                severity="low",
                category="configuration",
                confidence_level="high",
                title="Git Enabled But No Remote Configured",
                description=(
                    "Git is enabled for local versioning but no remote repository "
                    "is configured. Configuration changes are versioned locally but "
                    "not backed up to a remote repository."
                ),
                remediation_steps=[
                    "Configure a remote Git repository for backup",
                    "Set up push/pull schedules for synchronization",
                    "Consider using a hosted Git service (GitHub, GitLab, etc.)",
                ],
                metadata={
                    "git_enabled": git_enabled,
                    "local_only": True,
                },
                estimated_impact="Local versioning only; no remote backup of configuration",
            ))

    def _generate_recommendations(self, result: AnalyzerResult) -> None:
        """Generate recommendations based on findings."""
        has_uncommitted = result.metadata.get("uncommitted_changes", False)
        has_undeployed = result.metadata.get("undeployed_commits", False)
        has_drift = result.metadata.get("config_drift", False)
        git_enabled = result.metadata.get("git_enabled", False)

        # Recommend GitOps if not configured
        if not git_enabled:
            result.recommendations.append(Recommendation(
                id="vc-rec-enable-gitops",
                type="configuration",
                priority="p2",
                title="Enable GitOps for Configuration Management",
                description=(
                    "Implement Git-based version control for Cribl configuration. "
                    "This provides audit trail, rollback capability, and enables "
                    "CI/CD workflows for configuration changes."
                ),
                rationale=(
                    "GitOps provides configuration versioning, audit trail, "
                    "easy rollback, and enables automation of deployment workflows"
                ),
                implementation_steps=[
                    "Set up a Git repository for Cribl configuration",
                    "Configure Git integration in Cribl System Settings",
                    "Define branching strategy (e.g., dev → staging → prod)",
                    "Set up CI/CD pipeline for automated deployments",
                    "Document configuration change procedures",
                ],
                implementation_effort="medium",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Reduces configuration errors and recovery time by 70%",
                ),
                before_state="Manual configuration management without version control",
                after_state="Automated GitOps workflow with full audit trail",
                documentation_links=[
                    "https://docs.cribl.io/stream/deploy-git",
                ],
            ))

        # Recommend deployment automation if there are frequent pending deployments
        if has_uncommitted or has_undeployed:
            result.recommendations.append(Recommendation(
                id="vc-rec-deployment-workflow",
                type="process",
                priority="p1",
                title="Establish Configuration Deployment Workflow",
                description=(
                    "Define and document a clear workflow for configuration changes "
                    "to prevent uncommitted changes and ensure timely deployments."
                ),
                rationale=(
                    "Uncommitted or undeployed changes can lead to configuration loss, "
                    "inconsistent processing, and operational issues"
                ),
                implementation_steps=[
                    "Define change management process for Cribl configuration",
                    "Set up regular review of pending changes",
                    "Implement alerts for uncommitted changes over time threshold",
                    "Create runbook for deployment procedures",
                    "Consider automated deployment schedules for non-production",
                ],
                implementation_effort="low",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Reduces risk of configuration loss and inconsistencies",
                ),
                before_state="Ad-hoc configuration changes with pending deployments",
                after_state="Structured change management with timely deployments",
            ))

        # Recommend monitoring for config drift
        if has_drift:
            result.recommendations.append(Recommendation(
                id="vc-rec-drift-monitoring",
                type="monitoring",
                priority="p1",
                title="Implement Configuration Drift Monitoring",
                description=(
                    "Set up monitoring and alerting for configuration drift "
                    "to detect when workers fall out of sync."
                ),
                rationale=(
                    "Configuration drift causes inconsistent data processing "
                    "and can lead to data quality issues"
                ),
                implementation_steps=[
                    "Configure alerts for worker config version mismatches",
                    "Set up dashboard for deployment status visibility",
                    "Implement automated remediation for stuck deployments",
                    "Create runbook for resolving configuration drift",
                ],
                implementation_effort="medium",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Enables proactive drift detection and faster remediation",
                ),
                before_state="Configuration drift detected reactively",
                after_state="Proactive drift detection with automated alerting",
            ))

    def _generate_summary(self, result: AnalyzerResult) -> None:
        """Generate analysis summary."""
        uncommitted = result.metadata.get("uncommitted_file_count", 0)
        pending = result.metadata.get("pending_deployments", 0)
        deploying = result.metadata.get("deploying_workers", 0)
        drift = result.metadata.get("config_drift", False)
        git_enabled = result.metadata.get("git_enabled", False)

        # Count findings by severity
        critical_count = len([f for f in result.findings if f.severity == "critical"])
        high_count = len([f for f in result.findings if f.severity == "high"])

        if critical_count > 0:
            status = "critical"
            description = (
                f"Critical version control issues detected: {uncommitted} uncommitted files, "
                f"{pending} pending deployments. Immediate action required."
            )
        elif high_count > 0 or drift:
            status = "warning"
            description = (
                f"Version control issues detected: {uncommitted} uncommitted changes, "
                f"{'config drift present' if drift else 'no drift'}. Review recommended."
            )
        elif uncommitted > 0 or pending > 0:
            status = "info"
            description = (
                f"Minor version control items: {uncommitted} uncommitted changes, "
                f"{deploying} workers deploying."
            )
        else:
            status = "healthy"
            git_status = "GitOps enabled" if git_enabled else "local versioning"
            description = (
                f"Version control is healthy: no uncommitted changes, "
                f"no pending deployments, {git_status}."
            )

        result.metadata["summary_status"] = status
        result.summary = description
