"""
Analyzes team structure and permission configurations to identify security risks and optimization opportunities.
"""

import contextlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.recommendation import ImpactEstimate


class UserInfo(BaseModel):
    """Represents a user and their permissions/roles."""

    id: str
    username: str
    roles: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_active: bool = True

    @property
    def has_admin_access(self) -> bool:
        """Check if user has any admin-level permissions."""
        admin_roles = {"admin", "superuser", "owner"}
        return any(role.lower() in admin_roles for role in self.roles)

    @property
    def has_write_access(self) -> bool:
        """Check if user has write/modify permissions."""
        write_roles = {"write", "edit", "modify", "update"}
        return any(role.lower() in write_roles for role in self.roles)

    @property
    def days_since_last_login(self) -> Optional[int]:
        """Calculate days since last login."""
        if not self.last_login:
            return None
        return (datetime.now() - self.last_login).days


class RoleDefinition(BaseModel):
    """Represents a role definition with permissions."""

    id: str
    name: str
    permissions: list[str] = Field(default_factory=list)
    description: Optional[str] = None

    @property
    def is_admin_role(self) -> bool:
        """Check if this is an administrative role."""
        admin_permissions = {"admin", "superuser", "manage_users", "manage_roles"}
        return any(perm in admin_permissions for perm in self.permissions)


class TeamInfo(BaseModel):
    """Represents a team and its members."""

    id: str
    name: str
    members: list[str] = Field(default_factory=list)  # user IDs
    description: Optional[str] = None

    @property
    def member_count(self) -> int:
        """Get number of team members."""
        return len(self.members)


class PermissionUsage(BaseModel):
    """Tracks permission usage patterns."""

    permission: str
    users_with_access: set[str] = Field(default_factory=set)
    last_used: Optional[datetime] = None
    usage_count: int = 0


class EnhancedTeamPermissionsAnalyzer(BaseAnalyzer):
    """
    Analyzes team structure and permission configurations to identify overly permissive roles,
    unused permissions, and potential security risks in team access patterns.
    """

    @property
    def objective_name(self) -> str:
        return "enhanced-team-permissions"

    def get_description(self) -> str:
        return "Analyzes team structure and permission configurations for security risks and optimization opportunities."

    def get_required_permissions(self) -> list[str]:
        return ["read:auth", "read:users", "read:roles", "read:teams", "read:audit"]

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge", "lake", "search"]  # Applies to all products

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis on team permissions and security posture.
        """
        result = self.create_result()

        try:
            # Collect all required data
            users = await self._get_users(client)
            roles = await self._get_roles(client)
            teams = await self._get_teams(client)
            permission_usage = await self._get_permission_usage(client)

            if not users:
                result.add_finding(
                    self.create_finding(
                        id="no-users-found",
                        category="Configuration",
                        severity="info",
                        title="No User Data Available",
                        description="Unable to retrieve user information for permission analysis.",
                        recommendation="Verify API access and authentication for user management endpoints.",
                    )
                )
                return result

            # Perform various security and optimization checks
            self._check_overly_permissive_admins(result, users)
            self._check_unused_high_privilege_permissions(result, users, permission_usage)
            self._check_permission_drift(result, users, roles)
            self._check_team_membership_hygiene(result, users, teams)
            self._check_role_consistency(result, users, roles)
            self._analyze_security_posture(result, users, roles, teams)

        except Exception as e:
            self.log.error(f"Error during enhanced team permissions analysis: {e}", exc_info=True)
            result.success = False
            result.error = str(e)

        return result

    async def _get_users(self, client: CriblAPIClient) -> list[UserInfo]:
        """Fetch all users and their role information."""
        try:
            users_data = await client.get("auth/users")
            users = []

            for user_data in users_data.get("items", []):
                # Parse last login if available
                last_login = None
                if login_str := user_data.get("lastLogin"):
                    with contextlib.suppress(ValueError, TypeError):
                        last_login = datetime.fromisoformat(login_str.replace("Z", "+00:00"))

                # Parse creation date if available
                created_at = None
                if created_str := user_data.get("createdAt"):
                    with contextlib.suppress(ValueError, TypeError):
                        created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

                user = UserInfo(
                    id=user_data.get("id", ""),
                    username=user_data.get("username", ""),
                    roles=user_data.get("roles", []),
                    teams=user_data.get("teams", []),
                    last_login=last_login,
                    created_at=created_at,
                    is_active=user_data.get("active", True),
                )
                users.append(user)

            return users

        except Exception as e:
            self.log.warning(f"Failed to fetch users: {e}")
            return []

    async def _get_roles(self, client: CriblAPIClient) -> list[RoleDefinition]:
        """Fetch all role definitions and their permissions."""
        try:
            roles_data = await client.get("auth/roles")
            roles = []

            for role_data in roles_data.get("items", []):
                role = RoleDefinition(
                    id=role_data.get("id", ""),
                    name=role_data.get("name", ""),
                    permissions=role_data.get("permissions", []),
                    description=role_data.get("description"),
                )
                roles.append(role)

            return roles

        except Exception as e:
            self.log.warning(f"Failed to fetch roles: {e}")
            return []

    async def _get_teams(self, client: CriblAPIClient) -> list[TeamInfo]:
        """Fetch all teams and their memberships."""
        try:
            teams_data = await client.get("auth/teams")
            teams = []

            for team_data in teams_data.get("items", []):
                team = TeamInfo(
                    id=team_data.get("id", ""),
                    name=team_data.get("name", ""),
                    members=team_data.get("members", []),
                    description=team_data.get("description"),
                )
                teams.append(team)

            return teams

        except Exception as e:
            self.log.warning(f"Failed to fetch teams: {e}")
            return []

    async def _get_permission_usage(self, client: CriblAPIClient) -> dict[str, PermissionUsage]:
        """Fetch permission usage patterns from audit logs."""
        usage_map = {}

        try:
            # Try to get recent audit logs for permission usage analysis
            audit_data = await client.get(
                "system/audit", params={"limit": 1000, "action": "permission"}
            )

            for entry in audit_data.get("items", []):
                permission = entry.get("permission", "")
                user_id = entry.get("userId", "")
                timestamp_str = entry.get("timestamp", "")

                if permission and user_id:
                    if permission not in usage_map:
                        usage_map[permission] = PermissionUsage(permission=permission)

                    usage_map[permission].users_with_access.add(user_id)
                    usage_map[permission].usage_count += 1

                    # Update last used timestamp
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                            if (
                                not usage_map[permission].last_used
                                or timestamp > usage_map[permission].last_used
                            ):
                                usage_map[permission].last_used = timestamp
                        except (ValueError, TypeError):
                            pass

        except Exception as e:
            # Audit logs might not be available, continue with empty usage data
            self.log.debug(f"Audit logs not available for permission usage analysis: {e}")

        return usage_map

    def _check_overly_permissive_admins(
        self, result: AnalyzerResult, users: list[UserInfo]
    ) -> None:
        """Check for overly permissive admin users."""
        admin_users = [u for u in users if u.has_admin_access and u.is_active]

        for user in admin_users:
            days_since_login = user.days_since_last_login

            # Critical: Admin users inactive for 90+ days
            if days_since_login and days_since_login > 90:
                result.add_finding(
                    self.create_finding(
                        id=f"stale-admin-user-{user.id}",
                        category="Security",
                        severity="critical",
                        title="Stale Administrative User",
                        description=f"User '{user.username}' has administrative access but hasn't logged in for {days_since_login} days.",
                        recommendation="Review administrative access for inactive users. Consider revoking admin privileges or removing the account.",
                        impact=ImpactEstimate(
                            severity="critical",
                            scope="organization",
                            affected_components=["user_access", "security_posture"],
                        ),
                    )
                )

            # High: Admin users with no team membership
            if not user.teams:
                result.add_finding(
                    self.create_finding(
                        id=f"orphaned-admin-user-{user.id}",
                        category="Security",
                        severity="high",
                        title="Orphaned Administrative User",
                        description=f"User '{user.username}' has administrative access but belongs to no teams.",
                        recommendation="Assign administrative users to appropriate teams for oversight and accountability.",
                        impact=ImpactEstimate(
                            severity="high",
                            scope="organization",
                            affected_components=["user_access", "accountability"],
                        ),
                    )
                )

    def _check_unused_high_privilege_permissions(
        self,
        result: AnalyzerResult,
        users: list[UserInfo],
        permission_usage: dict[str, PermissionUsage],
    ) -> None:
        """Check for unused high-privilege permissions."""
        high_privilege_perms = {
            "admin",
            "superuser",
            "manage_users",
            "manage_roles",
            "write",
            "delete",
        }

        for perm_name, usage in permission_usage.items():
            if any(hp in perm_name.lower() for hp in high_privilege_perms):
                days_since_used = None
                if usage.last_used:
                    days_since_used = (datetime.now() - usage.last_used).days

                # High: High-privilege permissions unused for 60+ days
                if days_since_used and days_since_used > 60:
                    user_list = list(usage.users_with_access)[:5]  # Show first 5 users
                    user_display = ", ".join(user_list)
                    if len(usage.users_with_access) > 5:
                        user_display += f" (+{len(usage.users_with_access) - 5} more)"

                    result.add_finding(
                        self.create_finding(
                            id=f"unused-high-privilege-permission-{perm_name.replace(':', '-')}",
                            category="Security",
                            severity="high",
                            title="Unused High-Privilege Permission",
                            description=f"Permission '{perm_name}' has not been used for {days_since_used} days but is granted to {len(usage.users_with_access)} user(s): {user_display}.",
                            recommendation="Review and potentially revoke unused high-privilege permissions to reduce security risk.",
                            impact=ImpactEstimate(
                                severity="high",
                                scope="organization",
                                affected_components=["permissions", "security_posture"],
                            ),
                        )
                    )

    def _check_permission_drift(
        self, result: AnalyzerResult, users: list[UserInfo], roles: list[RoleDefinition]
    ) -> None:
        """Check for permission drift from standard role definitions."""
        # Group users by role patterns
        role_user_map = {}
        for user in users:
            if user.is_active:
                role_key = tuple(sorted(user.roles))
                if role_key not in role_user_map:
                    role_user_map[role_key] = []
                role_user_map[role_key].append(user)

        # Find roles with very few users (potential drift)
        for role_combo, user_list in role_user_map.items():
            if len(user_list) == 1 and len(role_combo) > 1:
                # Single user with multiple roles - potential custom configuration
                user = user_list[0]
                result.add_finding(
                    self.create_finding(
                        id=f"unique-permission-combination-{user.id}",
                        category="Configuration",
                        severity="medium",
                        title="Unique Permission Combination",
                        description=f"User '{user.username}' has a unique combination of roles that no other user has: {', '.join(role_combo)}.",
                        recommendation="Review if this unique permission set is intentional or indicates permission drift from standard roles.",
                        impact=ImpactEstimate(
                            severity="medium",
                            scope="user",
                            affected_components=["permissions", "role_consistency"],
                        ),
                    )
                )

    def _check_team_membership_hygiene(
        self, result: AnalyzerResult, users: list[UserInfo], teams: list[TeamInfo]
    ) -> None:
        """Check team membership patterns and hygiene."""
        active_users = [u for u in users if u.is_active]

        # Check for teams with problematic sizes
        for team in teams:
            if team.member_count == 0:
                result.add_finding(
                    self.create_finding(
                        id=f"empty-team-{team.id}",
                        category="Organization",
                        severity="medium",
                        title="Empty Team",
                        description=f"Team '{team.name}' has no members.",
                        recommendation="Remove empty teams or assign appropriate members.",
                        impact=ImpactEstimate(
                            severity="low", scope="team", affected_components=["team_structure"]
                        ),
                    )
                )
            elif team.member_count == 1:
                result.add_finding(
                    self.create_finding(
                        id=f"single-member-team-{team.id}",
                        category="Organization",
                        severity="medium",
                        title="Single-Member Team",
                        description=f"Team '{team.name}' has only 1 member, reducing accountability and redundancy.",
                        recommendation="Consider adding additional team members for better oversight.",
                        impact=ImpactEstimate(
                            severity="medium",
                            scope="team",
                            affected_components=["accountability", "redundancy"],
                        ),
                    )
                )
            elif team.member_count > 50:
                result.add_finding(
                    self.create_finding(
                        id=f"large-team-{team.id}",
                        category="Organization",
                        severity="medium",
                        title="Very Large Team",
                        description=f"Team '{team.name}' has {team.member_count} members, which may impact coordination and oversight.",
                        recommendation="Consider splitting large teams into smaller, more focused groups.",
                        impact=ImpactEstimate(
                            severity="medium",
                            scope="team",
                            affected_components=["coordination", "oversight"],
                        ),
                    )
                )

        # Check for users not in any teams
        users_without_teams = [u for u in active_users if not u.teams]
        if users_without_teams:
            user_list = [u.username for u in users_without_teams[:5]]
            user_display = ", ".join(user_list)
            if len(users_without_teams) > 5:
                user_display += f" (+{len(users_without_teams) - 5} more)"

            result.add_finding(
                self.create_finding(
                    id="users-without-teams",
                    category="Organization",
                    severity="medium",
                    title="Users Without Team Membership",
                    description=f"{len(users_without_teams)} active user(s) are not members of any teams: {user_display}.",
                    recommendation="Assign users to appropriate teams for better organization and access control.",
                    impact=ImpactEstimate(
                        severity="medium",
                        scope="organization",
                        affected_components=["team_structure", "access_control"],
                    ),
                )
            )

    def _check_role_consistency(
        self, result: AnalyzerResult, users: list[UserInfo], roles: list[RoleDefinition]
    ) -> None:
        """Check for role consistency and patterns."""
        # Count users per role
        role_usage = {}
        for role_def in roles:
            role_usage[role_def.id] = 0

        for user in users:
            if user.is_active:
                for role in user.roles:
                    if role in role_usage:
                        role_usage[role] += 1

        # Find underutilized roles
        for role_def in roles:
            user_count = role_usage.get(role_def.id, 0)
            if user_count > 0 and user_count < 3:
                result.add_finding(
                    self.create_finding(
                        id=f"underutilized-role-{role_def.id}",
                        category="Organization",
                        severity="low",
                        title="Underutilized Role",
                        description=f"Role '{role_def.name}' is assigned to only {user_count} user(s).",
                        recommendation="Consider consolidating underutilized roles or removing unused role definitions.",
                        impact=ImpactEstimate(
                            severity="low",
                            scope="organization",
                            affected_components=["role_management"],
                        ),
                    )
                )

    def _analyze_security_posture(
        self,
        result: AnalyzerResult,
        users: list[UserInfo],
        roles: list[RoleDefinition],
        teams: list[TeamInfo],
    ) -> None:
        """Perform overall security posture analysis."""
        active_users = [u for u in users if u.is_active]
        admin_users = [u for u in active_users if u.has_admin_access]

        # Calculate security metrics
        admin_ratio = len(admin_users) / len(active_users) if active_users else 0
        len([u for u in active_users if not u.teams])

        # Critical: Too many admins
        if admin_ratio > 0.1:  # More than 10% admins
            result.add_finding(
                self.create_finding(
                    id="high-admin-ratio",
                    category="Security",
                    severity="high",
                    title="High Administrative User Ratio",
                    description=".1f",
                    recommendation="Review administrative access assignments. Consider implementing role-based access control with more granular permissions.",
                    impact=ImpactEstimate(
                        severity="high",
                        scope="organization",
                        affected_components=["security_posture", "access_control"],
                    ),
                )
            )

        # Overall security posture summary
        security_score = self._calculate_security_score(users, roles, teams)

        if security_score < 60:
            result.add_finding(
                self.create_finding(
                    id="poor-security-posture",
                    category="Security",
                    severity="medium",
                    title="Poor Security Posture",
                    description=f"Overall permission security score: {security_score}/100. Multiple security issues detected.",
                    recommendation="Address identified permission and team structure issues to improve security posture.",
                    impact=ImpactEstimate(
                        severity="medium",
                        scope="organization",
                        affected_components=["security_posture", "permissions", "team_structure"],
                    ),
                )
            )

    def _calculate_security_score(
        self, users: list[UserInfo], roles: list[RoleDefinition], teams: list[TeamInfo]
    ) -> int:
        """Calculate an overall security score based on various factors."""
        score = 100
        active_users = [u for u in users if u.is_active]

        if not active_users:
            return 50  # Can't assess without user data

        # Deduct for various security issues
        admin_users = [u for u in active_users if u.has_admin_access]
        admin_ratio = len(admin_users) / len(active_users)

        # High admin ratio
        if admin_ratio > 0.1:
            score -= 20
        elif admin_ratio > 0.05:
            score -= 10

        # Users without teams
        teamless_ratio = len([u for u in active_users if not u.teams]) / len(active_users)
        if teamless_ratio > 0.2:
            score -= 15
        elif teamless_ratio > 0.1:
            score -= 8

        # Stale admin accounts
        stale_admins = sum(
            1 for u in admin_users if u.days_since_last_login and u.days_since_last_login > 90
        )
        if stale_admins > 0:
            score -= min(stale_admins * 5, 20)

        # Empty teams (indicates poor organization)
        empty_teams = sum(1 for t in teams if t.member_count == 0)
        if empty_teams > 0:
            score -= min(empty_teams * 2, 10)

        return max(0, min(100, score))
