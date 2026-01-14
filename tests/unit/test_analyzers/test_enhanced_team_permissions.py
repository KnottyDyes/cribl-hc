"""
Unit tests for EnhancedTeamPermissionsAnalyzer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from cribl_hc.analyzers.enhanced_team_permissions import (
    EnhancedTeamPermissionsAnalyzer,
    UserInfo,
    RoleDefinition,
    TeamInfo,
    PermissionUsage,
)
from cribl_hc.core.api_client import CriblAPIClient


class TestEnhancedTeamPermissionsAnalyzer:
    """Test EnhancedTeamPermissionsAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return EnhancedTeamPermissionsAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        return client

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "enhanced-team-permissions"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        assert analyzer.supported_products == ["stream", "edge", "lake", "search"]

    def test_required_permissions(self, analyzer):
        """Test required permissions."""
        expected = ["read:auth", "read:users", "read:roles", "read:teams", "read:audit"]
        assert analyzer.get_required_permissions() == expected

    @pytest.mark.asyncio
    async def test_analyze_no_users(self, analyzer, mock_client):
        """Test analysis with no user data."""
        # Mock empty responses
        mock_client.get.side_effect = [
            {"items": []},  # users
            {"items": []},  # roles
            {"items": []},  # teams
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "No User Data Available" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_stale_admin_users(self, analyzer, mock_client):
        """Test detection of stale admin users."""
        # Create test data with stale admin
        stale_date = datetime.now() - timedelta(days=100)
        users_data = {
            "items": [
                {
                    "id": "user1",
                    "username": "admin_user",
                    "roles": ["admin", "superuser"],
                    "teams": ["team1"],
                    "lastLogin": stale_date.isoformat(),
                    "active": True,
                }
            ]
        }

        mock_client.get.side_effect = [
            users_data,  # users
            {"items": []},  # roles
            {"items": []},  # teams
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) == 1
        assert "Stale Administrative User" in critical_findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_orphaned_admin_users(self, analyzer, mock_client):
        """Test detection of orphaned admin users."""
        users_data = {
            "items": [
                {
                    "id": "user1",
                    "username": "admin_user",
                    "roles": ["admin"],
                    "teams": [],  # No teams
                    "active": True,
                }
            ]
        }

        mock_client.get.side_effect = [
            users_data,  # users
            {"items": []},  # roles
            {"items": []},  # teams
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) == 1
        assert "Orphaned Administrative User" in high_findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_unused_privileges(self, analyzer, mock_client):
        """Test detection of unused high-privilege permissions."""
        # Mock audit data showing unused admin permission
        audit_data = {
            "items": [
                {
                    "permission": "admin",
                    "userId": "user1",
                    "timestamp": (datetime.now() - timedelta(days=70)).isoformat(),
                }
            ]
        }

        users_data = {
            "items": [
                {
                    "id": "user1",
                    "username": "test_user",
                    "roles": ["admin"],
                    "teams": ["team1"],
                    "active": True,
                }
            ]
        }

        mock_client.get.side_effect = [
            users_data,  # users
            {"items": []},  # roles
            {"items": []},  # teams
            audit_data,  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 1
        # Should find unused high-privilege permission

    @pytest.mark.asyncio
    async def test_analyze_team_hygiene(self, analyzer, mock_client):
        """Test team membership hygiene analysis."""
        users_data = {
            "items": [
                {
                    "id": "user1",
                    "username": "user1",
                    "roles": ["user"],
                    "teams": ["team1"],
                    "active": True,
                },
                {
                    "id": "user2",
                    "username": "user2",
                    "roles": ["user"],
                    "teams": [],
                    "active": True,
                },
            ]
        }

        teams_data = {
            "items": [
                {"id": "team1", "name": "Team 1", "members": ["user1"]},  # Single member
                {"id": "empty_team", "name": "Empty Team", "members": []},  # Empty team
            ]
        }

        mock_client.get.side_effect = [
            users_data,  # users
            {"items": []},  # roles
            teams_data,  # teams
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 2  # Empty team and single-member team

    @pytest.mark.asyncio
    async def test_analyze_role_consistency(self, analyzer, mock_client):
        """Test role consistency analysis."""
        roles_data = {
            "items": [
                {"id": "role1", "name": "Role 1", "permissions": ["read"]},
                {"id": "role2", "name": "Role 2", "permissions": ["read"]},
            ]
        }

        users_data = {
            "items": [
                {
                    "id": "user1",
                    "username": "user1",
                    "roles": ["role1"],
                    "teams": ["team1"],
                    "active": True,
                },
            ]
        }

        mock_client.get.side_effect = [
            users_data,  # users
            roles_data,  # roles
            {"items": []},  # teams
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should find underutilized roles (only 1 user per role)

    @pytest.mark.asyncio
    async def test_analyze_security_posture_high_admin_ratio(self, analyzer, mock_client):
        """Test security posture analysis with high admin ratio."""
        users_data = {
            "items": [
                {
                    "id": "admin1",
                    "username": "admin1",
                    "roles": ["admin"],
                    "teams": ["team1"],
                    "active": True,
                },
                {
                    "id": "admin2",
                    "username": "admin2",
                    "roles": ["admin"],
                    "teams": ["team1"],
                    "active": True,
                },
                {
                    "id": "admin3",
                    "username": "admin3",
                    "roles": ["admin"],
                    "teams": ["team1"],
                    "active": True,
                },
                {
                    "id": "user1",
                    "username": "user1",
                    "roles": ["user"],
                    "teams": ["team1"],
                    "active": True,
                },
            ]  # 75% admin ratio
        }

        mock_client.get.side_effect = [
            users_data,  # users
            {"items": []},  # roles
            {"items": []},  # teams
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 1
        # Should find high admin ratio security issue

    def test_user_info_properties(self):
        """Test UserInfo property methods."""
        user = UserInfo(
            id="test",
            username="testuser",
            roles=["admin", "user"],
            teams=["team1"],
            last_login=datetime.now() - timedelta(days=5),
        )

        assert user.has_admin_access is True
        assert user.has_write_access is False  # No write permissions
        assert user.days_since_last_login == 5

    def test_role_definition_properties(self):
        """Test RoleDefinition property methods."""
        role = RoleDefinition(
            id="admin", name="Administrator", permissions=["admin", "manage_users", "read"]
        )

        assert role.is_admin_role is True

        user_role = RoleDefinition(id="user", name="User", permissions=["read"])

        assert user_role.is_admin_role is False

    def test_team_info_properties(self):
        """Test TeamInfo property methods."""
        team = TeamInfo(id="team1", name="Test Team", members=["user1", "user2"])

        assert team.member_count == 2

    def test_permission_usage_tracking(self):
        """Test PermissionUsage data structure."""
        usage = PermissionUsage(permission="admin")
        usage.users_with_access.add("user1")
        usage.usage_count = 5
        usage.last_used = datetime.now()

        assert "user1" in usage.users_with_access
        assert usage.usage_count == 5
        assert usage.last_used is not None
