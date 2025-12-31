"""
Unit tests for VersionControlAnalyzer.

Tests cover:
- Uncommitted configuration change detection
- Pending deployment detection
- Configuration drift detection
- Git/GitOps configuration analysis
- Multi-product support (Stream, Edge, Lake, Search)
"""

import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.version_control import VersionControlAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestVersionControlAnalyzer:
    """Test suite for VersionControlAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create VersionControlAnalyzer instance."""
        return VersionControlAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        client.base_url = "https://cribl.example.com"
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        return client

    # === Basic Properties Tests ===

    def test_objective_name(self, analyzer):
        """Test that analyzer has correct objective name."""
        assert analyzer.objective_name == "version_control"

    def test_supported_products(self, analyzer):
        """Test that analyzer supports all Cribl products."""
        products = analyzer.supported_products
        assert "stream" in products
        assert "edge" in products
        assert "lake" in products
        assert "search" in products
        assert "core" in products

    def test_description(self, analyzer):
        """Test analyzer description."""
        desc = analyzer.get_description()
        assert "uncommitted" in desc.lower() or "configuration" in desc.lower()

    def test_estimated_api_calls(self, analyzer):
        """Test estimated API calls."""
        calls = analyzer.get_estimated_api_calls()
        assert calls > 0
        assert calls <= 10  # Should be reasonable

    # === Clean State Tests ===

    @pytest.mark.asyncio
    async def test_analyze_clean_state(self, analyzer, mock_client):
        """Test analysis when no uncommitted changes exist."""
        mock_client.get_version_info.return_value = {
            "enabled": True,
            "remote": "git@github.com:org/cribl-config.git",
            "branch": "main",
        }
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
            "commit": "abc123",
            "message": "Latest config update",
            "timestamp": "2024-01-15T10:00:00Z",
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [
                {"group": "default", "configVersion": "v1", "workerCount": 3, "deployingCount": 0, "hasDrift": False}
            ],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
            "totalGroups": 1,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["uncommitted_changes"] is False
        assert result.metadata["undeployed_commits"] is False
        assert result.metadata["git_enabled"] is True
        # Should have minimal or no findings in clean state
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(critical_findings) == 0
        assert len(high_findings) == 0

    # === Uncommitted Changes Tests ===

    @pytest.mark.asyncio
    async def test_analyze_uncommitted_pipeline_changes(self, analyzer, mock_client):
        """Test detection of uncommitted pipeline changes."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": True,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = [
            {"path": "groups/default/pipelines/main.yml", "status": "M"},
            {"path": "groups/default/pipelines/syslog.yml", "status": "A"},
        ]
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["uncommitted_changes"] is True
        assert result.metadata["uncommitted_file_count"] == 2

        # Should have finding about uncommitted data path changes
        pipeline_findings = [f for f in result.findings if "pipeline" in f.title.lower() or "data-path" in f.id]
        assert len(pipeline_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_uncommitted_security_changes(self, analyzer, mock_client):
        """Test detection of uncommitted security-related changes."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": True,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = [
            {"path": "auth/users.yml", "status": "M"},
            {"path": "certificates/tls.pem", "status": "A"},
        ]
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["uncommitted_changes"] is True

        # Should have critical finding for security-related changes
        security_findings = [f for f in result.findings if f.severity == "critical" and "security" in f.title.lower()]
        assert len(security_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_undeployed_commits(self, analyzer, mock_client):
        """Test detection of committed but undeployed changes."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": True,
            "commit": "def456",
            "message": "Updated pipeline config",
            "timestamp": "2024-01-15T12:00:00Z",
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [
                {"group": "default", "configVersion": "v1", "workerCount": 5, "deployingCount": 0, "hasDrift": False}
            ],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["undeployed_commits"] is True

        # Should have finding about undeployed commits
        undeployed_findings = [f for f in result.findings if "undeployed" in f.id.lower()]
        assert len(undeployed_findings) > 0
        assert undeployed_findings[0].severity == "high"

    # === Deployment Status Tests ===

    @pytest.mark.asyncio
    async def test_analyze_deployment_in_progress(self, analyzer, mock_client):
        """Test detection of active deployments."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [
                {"group": "default", "configVersion": "v2", "workerCount": 5, "deployingCount": 3, "hasDrift": False}
            ],
            "pendingDeployments": 1,
            "deployingWorkers": 3,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["deploying_workers"] == 3

        # Should have info finding about deployment in progress
        deploying_findings = [f for f in result.findings if "deployment" in f.id.lower() and "progress" in f.id.lower()]
        assert len(deploying_findings) > 0
        assert deploying_findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_analyze_config_drift(self, analyzer, mock_client):
        """Test detection of configuration drift between workers."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [
                {"group": "default", "configVersion": "v2", "workerCount": 5, "deployingCount": 0, "hasDrift": True},
                {"group": "secondary", "configVersion": "v1", "workerCount": 3, "deployingCount": 0, "hasDrift": True},
            ],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": True,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["config_drift"] is True

        # Should have high severity finding about drift
        drift_findings = [f for f in result.findings if "drift" in f.id.lower()]
        assert len(drift_findings) > 0
        assert drift_findings[0].severity == "high"

    # === Git Configuration Tests ===

    @pytest.mark.asyncio
    async def test_analyze_git_not_configured(self, analyzer, mock_client):
        """Test detection of missing Git configuration."""
        mock_client.get_version_info.return_value = {
            "enabled": False,
        }
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["git_enabled"] is False

        # Should have finding about Git not configured
        git_findings = [f for f in result.findings if "git" in f.id.lower()]
        assert len(git_findings) > 0

        # Should have recommendation for GitOps
        gitops_recs = [r for r in result.recommendations if "gitops" in r.id.lower()]
        assert len(gitops_recs) > 0

    @pytest.mark.asyncio
    async def test_analyze_git_local_only(self, analyzer, mock_client):
        """Test detection of Git without remote."""
        mock_client.get_version_info.return_value = {
            "enabled": True,
            "remote": None,  # No remote configured
        }
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["git_enabled"] is True
        assert result.metadata["git_remote"] is None

        # Should have finding about missing remote
        remote_findings = [f for f in result.findings if "remote" in f.id.lower() or "no-remote" in f.id.lower()]
        assert len(remote_findings) > 0

    # === Error Handling Tests ===

    @pytest.mark.asyncio
    async def test_analyze_api_error(self, analyzer, mock_client):
        """Test handling of API errors."""
        mock_client.get_version_info.side_effect = Exception("API connection failed")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_analyze_partial_api_failure(self, analyzer, mock_client):
        """Test handling of partial API failures."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []
        # Deployment status returns error but doesn't throw
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
            "error": "Worker groups unavailable",
        }

        result = await analyzer.analyze(mock_client)

        # Should still succeed with partial data
        assert result.success is True

    # === Summary Generation Tests ===

    @pytest.mark.asyncio
    async def test_summary_healthy_state(self, analyzer, mock_client):
        """Test summary generation for healthy state."""
        mock_client.get_version_info.return_value = {"enabled": True, "remote": "git@example.com"}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": False,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.summary is not None
        assert "healthy" in result.summary.lower() or "no uncommitted" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_summary_warning_state(self, analyzer, mock_client):
        """Test summary generation for warning state."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": True,
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = [
            {"path": "groups/default/data/lookups/test.csv", "status": "M"}
        ]
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.summary is not None
        assert result.metadata["summary_status"] in ["info", "warning", "critical"]


class TestVersionControlAnalyzerEdgeCases:
    """Edge case tests for VersionControlAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create VersionControlAnalyzer instance."""
        return VersionControlAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        return client

    @pytest.mark.asyncio
    async def test_empty_uncommitted_files_list(self, analyzer, mock_client):
        """Test handling of empty file list with uncommitted flag true."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": True,  # Flag says yes
            "undeployedCommits": False,
        }
        mock_client.get_uncommitted_files.return_value = []  # But list is empty
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should still report uncommitted changes based on flag

    @pytest.mark.asyncio
    async def test_large_number_of_uncommitted_files(self, analyzer, mock_client):
        """Test handling of many uncommitted files."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": True,
            "undeployedCommits": False,
        }
        # Simulate 50 uncommitted files
        mock_client.get_uncommitted_files.return_value = [
            {"path": f"groups/default/pipelines/pipe_{i}.yml", "status": "M"}
            for i in range(50)
        ]
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["uncommitted_file_count"] == 50
        # Metadata should limit stored files
        assert len(result.metadata["uncommitted_files"]) <= 10

    @pytest.mark.asyncio
    async def test_string_file_paths(self, analyzer, mock_client):
        """Test handling of file paths as strings instead of dicts."""
        mock_client.get_version_info.return_value = {"enabled": True}
        mock_client.get_version_status.return_value = {
            "uncommittedChanges": True,
            "undeployedCommits": False,
        }
        # Some APIs return just strings
        mock_client.get_uncommitted_files.return_value = [
            "groups/default/pipelines/main.yml",
            "groups/default/routes.yml",
        ]
        mock_client.get_deployment_status.return_value = {
            "groups": [],
            "pendingDeployments": 0,
            "deployingWorkers": 0,
            "configDrift": False,
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["uncommitted_file_count"] == 2
