"""
Integration tests for Core API endpoints.

Tests the 20 Core control plane API methods added for RBAC, fleet management,
notifications, certificates, and library resources.
"""

import pytest
import respx
from httpx import Response

from cribl_hc.core.api_client import CriblAPIClient


# =============================================================================
# Fleet Management Tests
# =============================================================================


class TestWorkerGroups:
    """Tests for get_worker_groups endpoint."""

    @pytest.mark.asyncio
    async def test_get_worker_groups_success(self):
        """Test successful retrieval of worker groups."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/master/groups").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "default", "configVersion": "v1.2.3"},
                            {"id": "production", "configVersion": "v1.2.4"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_worker_groups()

                assert isinstance(result, list)
                assert len(result) == 2
                assert result[0]["id"] == "default"

    @pytest.mark.asyncio
    async def test_get_worker_groups_404(self):
        """Test get_worker_groups returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/master/groups").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_worker_groups()

                assert result == []


class TestWorkerGroupSummary:
    """Tests for get_worker_group_summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_worker_group_summary_success(self):
        """Test successful retrieval of worker group summary."""
        with respx.mock:
            respx.get(
                "https://cribl.example.com:9000/api/v1/products/stream/groups/default/summary"
            ).mock(
                return_value=Response(
                    200,
                    json={"workerCount": 5, "healthyCount": 4, "unhealthyCount": 1},
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_worker_group_summary("default")

                assert isinstance(result, dict)
                assert result["workerCount"] == 5

    @pytest.mark.asyncio
    async def test_get_worker_group_summary_fallback_to_legacy(self):
        """Test fallback to legacy endpoint on 404."""
        with respx.mock:
            # First endpoint returns 404
            respx.get(
                "https://cribl.example.com:9000/api/v1/products/stream/groups/default/summary"
            ).mock(return_value=Response(404, json={"error": "Not Found"}))

            # Legacy endpoint succeeds
            respx.get(
                "https://cribl.example.com:9000/api/v1/master/groups/default"
            ).mock(
                return_value=Response(
                    200, json={"id": "default", "workerCount": 3}
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_worker_group_summary("default")

                assert isinstance(result, dict)
                assert result["id"] == "default"


class TestMasterSummary:
    """Tests for get_master_summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_master_summary_success(self):
        """Test successful retrieval of master summary."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/master/summary").mock(
                return_value=Response(
                    200,
                    json={
                        "workerCount": 10,
                        "groupCount": 3,
                        "healthyWorkers": 9,
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_master_summary()

                assert isinstance(result, dict)
                assert result["workerCount"] == 10

    @pytest.mark.asyncio
    async def test_get_master_summary_404(self):
        """Test get_master_summary returns empty dict on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/master/summary").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_master_summary()

                assert result == {}


# =============================================================================
# RBAC Tests
# =============================================================================


class TestRoles:
    """Tests for get_roles endpoint."""

    @pytest.mark.asyncio
    async def test_get_roles_success(self):
        """Test successful retrieval of roles."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/roles").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "admin", "permissions": ["*"]},
                            {"id": "reader", "permissions": ["read:*"]},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_roles()

                assert isinstance(result, list)
                assert len(result) == 2
                assert result[0]["id"] == "admin"

    @pytest.mark.asyncio
    async def test_get_roles_404(self):
        """Test get_roles returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/roles").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_roles()

                assert result == []


class TestUsers:
    """Tests for get_users endpoint."""

    @pytest.mark.asyncio
    async def test_get_users_success(self):
        """Test successful retrieval of users."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/users").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "admin@example.com", "roles": ["admin"]},
                            {"id": "user@example.com", "roles": ["reader"]},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_users()

                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_users_404(self):
        """Test get_users returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/users").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_users()

                assert result == []


class TestTeams:
    """Tests for get_teams endpoint."""

    @pytest.mark.asyncio
    async def test_get_teams_success(self):
        """Test successful retrieval of teams."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/teams").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "engineering", "members": ["user1", "user2"]},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_teams()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["id"] == "engineering"

    @pytest.mark.asyncio
    async def test_get_teams_404(self):
        """Test get_teams returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/teams").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_teams()

                assert result == []


class TestPolicies:
    """Tests for get_policies endpoint."""

    @pytest.mark.asyncio
    async def test_get_policies_success(self):
        """Test successful retrieval of policies."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/policies").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "default-policy", "description": "Default access policy"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_policies()

                assert isinstance(result, list)
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_policies_404(self):
        """Test get_policies returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/policies").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_policies()

                assert result == []


# =============================================================================
# Security Tests
# =============================================================================


class TestCertificates:
    """Tests for get_certificates endpoint."""

    @pytest.mark.asyncio
    async def test_get_certificates_success(self):
        """Test successful retrieval of certificates."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/certificates").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "default-cert",
                                "expiresAt": "2026-01-01T00:00:00Z",
                            },
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_certificates()

                assert isinstance(result, list)
                assert len(result) == 1
                assert "expiresAt" in result[0]

    @pytest.mark.asyncio
    async def test_get_certificates_404(self):
        """Test get_certificates returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/certificates").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_certificates()

                assert result == []


class TestAPIKeys:
    """Tests for get_api_keys endpoint."""

    @pytest.mark.asyncio
    async def test_get_api_keys_success(self):
        """Test successful retrieval of API keys."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/keys").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "key-1", "lastUsed": "2025-12-01T00:00:00Z"},
                            {"id": "key-2", "lastUsed": None},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_api_keys()

                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_api_keys_404(self):
        """Test get_api_keys returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/keys").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_api_keys()

                assert result == []


# =============================================================================
# Notification Tests
# =============================================================================


class TestNotificationTargets:
    """Tests for get_notification_targets endpoint."""

    @pytest.mark.asyncio
    async def test_get_notification_targets_success(self):
        """Test successful retrieval of notification targets."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/notification-targets").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "slack-alerts", "type": "slack"},
                            {"id": "email-alerts", "type": "email"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_notification_targets()

                assert isinstance(result, list)
                assert len(result) == 2
                assert result[0]["type"] == "slack"

    @pytest.mark.asyncio
    async def test_get_notification_targets_404(self):
        """Test get_notification_targets returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/notification-targets").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_notification_targets()

                assert result == []


class TestNotifications:
    """Tests for get_notifications endpoint."""

    @pytest.mark.asyncio
    async def test_get_notifications_success(self):
        """Test successful retrieval of notifications."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/notifications").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "high-cpu-alert", "enabled": True},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_notifications()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_notifications_404(self):
        """Test get_notifications returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/notifications").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_notifications()

                assert result == []


# =============================================================================
# System Tests
# =============================================================================


class TestSystemInstance:
    """Tests for get_system_instance endpoint."""

    @pytest.mark.asyncio
    async def test_get_system_instance_success(self):
        """Test successful retrieval of system instance."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/instance").mock(
                return_value=Response(
                    200,
                    json={
                        "id": "cribl-leader-001",
                        "mode": "leader",
                        "version": "5.0.0",
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_system_instance()

                assert isinstance(result, dict)
                assert result["id"] == "cribl-leader-001"

    @pytest.mark.asyncio
    async def test_get_system_instance_404(self):
        """Test get_system_instance returns empty dict on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/instance").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_system_instance()

                assert result == {}


class TestSystemMessages:
    """Tests for get_system_messages endpoint."""

    @pytest.mark.asyncio
    async def test_get_system_messages_success(self):
        """Test successful retrieval of system messages."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/messages").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"severity": "warning", "message": "High memory usage"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_system_messages()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_get_system_messages_404(self):
        """Test get_system_messages returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/messages").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_system_messages()

                assert result == []


class TestBanners:
    """Tests for get_banners endpoint."""

    @pytest.mark.asyncio
    async def test_get_banners_success(self):
        """Test successful retrieval of banners."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/banners").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"message": "Maintenance scheduled", "enabled": True},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_banners()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_banners_404(self):
        """Test get_banners returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/banners").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_banners()

                assert result == []


# =============================================================================
# Library Tests
# =============================================================================


class TestScripts:
    """Tests for get_scripts endpoint."""

    @pytest.mark.asyncio
    async def test_get_scripts_success(self):
        """Test successful retrieval of scripts."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/scripts").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "custom-parser", "code": "function() {}"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_scripts()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["id"] == "custom-parser"

    @pytest.mark.asyncio
    async def test_get_scripts_404(self):
        """Test get_scripts returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/scripts").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_scripts()

                assert result == []


class TestGrokPatterns:
    """Tests for get_grok_patterns endpoint."""

    @pytest.mark.asyncio
    async def test_get_grok_patterns_success(self):
        """Test successful retrieval of grok patterns."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/lib/grok").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "SYSLOG", "pattern": "%{SYSLOGBASE}%{GREEDYDATA}"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_grok_patterns()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["id"] == "SYSLOG"

    @pytest.mark.asyncio
    async def test_get_grok_patterns_404(self):
        """Test get_grok_patterns returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/lib/grok").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_grok_patterns()

                assert result == []


class TestRegexLibrary:
    """Tests for get_regex_library endpoint."""

    @pytest.mark.asyncio
    async def test_get_regex_library_success(self):
        """Test successful retrieval of regex library."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/lib/regex").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "ip-address", "lib": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_regex_library()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["id"] == "ip-address"

    @pytest.mark.asyncio
    async def test_get_regex_library_404(self):
        """Test get_regex_library returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/lib/regex").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_regex_library()

                assert result == []


class TestFunctions:
    """Tests for get_functions endpoint."""

    @pytest.mark.asyncio
    async def test_get_functions_success(self):
        """Test successful retrieval of functions."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/functions").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "eval", "description": "Evaluate expressions"},
                            {"id": "regex_extract", "description": "Extract using regex"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_functions()

                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_functions_404(self):
        """Test get_functions returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/functions").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_functions()

                assert result == []


# =============================================================================
# Collector Tests
# =============================================================================


class TestCollectors:
    """Tests for get_collectors endpoint."""

    @pytest.mark.asyncio
    async def test_get_collectors_success(self):
        """Test successful retrieval of collectors."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/collectors").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "s3-collector", "enabled": True},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_collectors()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_collectors_404(self):
        """Test get_collectors returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/collectors").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_collectors()

                assert result == []


class TestExecutors:
    """Tests for get_executors endpoint."""

    @pytest.mark.asyncio
    async def test_get_executors_success(self):
        """Test successful retrieval of executors."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/executors").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {"id": "default-executor", "type": "collection"},
                        ]
                    },
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_executors()

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]["type"] == "collection"

    @pytest.mark.asyncio
    async def test_get_executors_404(self):
        """Test get_executors returns empty list on 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/executors").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token",
            ) as client:
                result = await client.get_executors()

                assert result == []
