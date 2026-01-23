from datetime import datetime

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SystemUserInfoAnalyzer(BaseAnalyzer):
    @property
    def objective_name(self) -> str:
        return "system_user_info"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        return 2

    def get_required_permissions(self) -> list[str]:
        return ["read:system", "read:iam"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            users = await client.get_users()
            roles = await client.get_roles()

            result.metadata.update(
                {
                    "user_count": len(users),
                    "role_count": len(roles),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not users:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-users-none",
                        category="system",
                        severity="high",  # Unusual to have 0 users if we are authenticated
                        title="No Users Found",
                        description="No users were retrieved from the system.",
                        affected_components=["iam"],
                        remediation_steps=[
                            "Verify that the API token has 'read:iam' or 'read:system' permissions.",
                            "Check for network issues preventing connection to the user management API endpoints.",
                        ],
                        confidence_level="medium",
                        estimated_impact="Unable to audit user access and permissions, potential security visibility gap",
                    )
                )

            admin_users = []
            users_without_roles = []

            for user in users:
                username = user.get("username", user.get("id", "unknown"))
                user_roles = user.get("roles", [])

                if "admin" in user_roles:
                    admin_users.append(username)

                if not user_roles:
                    users_without_roles.append(username)

            result.metadata["admin_users_count"] = len(admin_users)

            if len(admin_users) > 10:  # Arbitrary threshold for "too many admins"
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-users-excessive-admins",
                        category="security",
                        severity="low",
                        title="High Number of Admin Users",
                        description=f"Found {len(admin_users)} users with admin privileges.",
                        affected_components=["iam"],
                        confidence_level="medium",
                        metadata={"admin_count": len(admin_users)},
                    )
                )

            if users_without_roles:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="system-users-no-roles",
                        category="security",
                        severity="medium",
                        title="Users Without Roles",
                        description=f"Found {len(users_without_roles)} users with no assigned roles.",
                        affected_components=["iam"],
                        confidence_level="high",
                        remediation_steps=["Assign roles to users or remove them"],
                        metadata={"users": users_without_roles},
                    )
                )

            result.success = True
        except Exception as exc:
            log.error("system_user_info_failed", error=str(exc))
            result.success = False
            result.metadata["error"] = str(exc)
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="system-user-info-error",
                    category="system",
                    severity="critical",
                    title="User Info Analysis Failed",
                    description=f"Failed to analyze user info: {str(exc)}",
                    affected_components=["iam"],
                    remediation_steps=["Verify API connectivity"],
                    confidence_level="high",
                    estimated_impact="Cannot verify user info",
                )
            )

        return result
