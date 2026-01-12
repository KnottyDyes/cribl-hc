"""
Security Posture Analyzer for Cribl Health Check.

Analyzes security configurations including TLS/mTLS, credential exposure,
and authentication mechanisms. Calculates overall security posture score.

Priority: P2 (Security - critical for compliance and data protection)
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SecurityAnalyzer(BaseAnalyzer):
    """
    Analyzer for security posture assessment.

    Identifies:
    - TLS/mTLS configuration issues
    - Hardcoded secrets and credentials
    - Weak or missing authentication mechanisms
    - User activity and RBAC issues
    - Certificate expiration and management
    """

    WEAK_TLS_VERSIONS = ["TLSv1", "TLSv1.0", "TLSv1.1", "SSLv2", "SSLv3"]
    SECURE_TLS_VERSIONS = ["TLSv1.2", "TLSv1.3"]

    SECRET_PATTERNS = {
        "password": re.compile(r'"(password)"\s*:\s*"([^"]{8,})"', re.IGNORECASE),
        "api_key": re.compile(r'"((?:api[_-]?key|apikey))"\s*:\s*"([^"]{16,})"', re.IGNORECASE),
        "secret": re.compile(r'"(secret)"\s*:\s*"([^"]{16,})"', re.IGNORECASE),
        "token": re.compile(r'"((?:auth[_-]?token|token))"\s*:\s*"([^"]{20,})"', re.IGNORECASE),
        "private_key": re.compile(
            r'"((?:private[_-]?key|privatekey))"\s*:\s*"([^"]+)"', re.IGNORECASE
        ),
    }

    ENV_VAR_PATTERN = re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}")

    SCORE_WEIGHTS = {
        "tls_enabled": 30,
        "strong_tls_version": 20,
        "cert_validation": 15,
        "no_hardcoded_secrets": 25,
        "authentication_configured": 10,
    }

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "security"

    @property
    def supported_products(self) -> List[str]:
        """Security analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls needed.
        """
        return 10

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:outputs",
            "read:inputs",
            "read:auth",
            "read:security",
            "read:certificates",
            "read:roles",
            "read:users",
            "read:keys",
            "read:teams",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze security posture and identify vulnerabilities.
        """
        result = self.create_result()

        try:
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            log.info(
                "security_analysis_started", product=client.product_type, product_name=product_name
            )

            try:
                outputs = await client.get_outputs() or []
            except Exception as e:
                log.warning("outputs_fetch_failed", error=str(e))
                outputs = []

            try:
                inputs = await client.get_inputs() or []
            except Exception as e:
                log.warning("inputs_fetch_failed", error=str(e))
                inputs = []

            try:
                auth_config = await client.get_auth_config() or {}
            except Exception as e:
                log.warning("auth_config_fetch_failed", error=str(e))
                auth_config = {}

            try:
                security_settings = await client.get_security_settings() or {}
            except Exception as e:
                log.warning("security_settings_fetch_failed", error=str(e))
                security_settings = {}

            try:
                certificates = await client.get_certificates() or []
            except Exception as e:
                log.warning("certificates_fetch_failed", error=str(e))
                certificates = []

            try:
                roles = await client.get_roles() or []
            except Exception as e:
                log.warning("roles_fetch_failed", error=str(e))
                roles = []

            try:
                users = await client.get_users() or []
            except Exception as e:
                log.warning("users_fetch_failed", error=str(e))
                users = []

            try:
                api_keys = await client.get_api_keys() or []
            except Exception as e:
                log.warning("api_keys_fetch_failed", error=str(e))
                api_keys = []

            try:
                teams = await client.get_teams() or []
            except Exception as e:
                log.warning("teams_fetch_failed", error=str(e))
                teams = []

            tls_issues = self._analyze_tls_configuration(outputs, inputs, result, client)
            secret_issues = self._analyze_secrets(outputs, inputs, result, client)
            auth_issues = self._analyze_authentication(auth_config, result, client)
            self._analyze_certificates(certificates, result, client)
            self._analyze_rbac(roles, users, result, client)
            self._analyze_api_keys(api_keys, result, client)
            self._analyze_teams(teams, result, client)
            self._analyze_guard_policies(security_settings, result, client)

            security_score = self._calculate_security_score(
                outputs, inputs, auth_config, tls_issues, secret_issues, auth_issues
            )

            self._generate_security_recommendations(
                outputs, inputs, auth_config, tls_issues, secret_issues, auth_issues, result
            )

            result.metadata.update(
                {
                    "product_type": client.product_type,
                    "outputs_analyzed": len(outputs),
                    "inputs_analyzed": len(inputs),
                    "security_posture_score": security_score,
                    "tls_issues_count": len(tls_issues),
                    "secret_issues_count": len(secret_issues),
                    "auth_issues_count": len(auth_issues),
                    "certificates_analyzed": len(certificates),
                    "roles_analyzed": len(roles),
                    "users_analyzed": len(users),
                    "api_keys_analyzed": len(api_keys),
                    "teams_analyzed": len(teams),
                    "analyzed_at": datetime.utcnow().isoformat(),
                }
            )

            result.success = True
            log.info("security_analysis_completed", security_score=security_score)

        except Exception as e:
            log.error("security_analysis_failed", error=str(e), exc_info=True)
            result.metadata.update({"error": str(e)})
            result.success = False

        return result

    def _analyze_tls_configuration(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> List[Dict[str, Any]]:
        """Analyze TLS configuration for outputs and inputs."""
        tls_issues = []

        for output in outputs:
            output_id = output.get("id", "unknown")
            tls_conf = output.get("conf", {}).get("tls", {})

            if tls_conf.get("disabled") is True:
                tls_issues.append(
                    {"component": output_id, "type": "output", "issue": "tls_disabled"}
                )
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-tls-disabled-output-{output_id}",
                        category="security",
                        severity="high",
                        title=f"TLS Disabled on Output: {output_id}",
                        description=f"Output '{output_id}' has TLS disabled, transmitting data in plaintext.",
                        affected_components=[output_id],
                        confidence_level="high",
                        remediation_steps=[f"Enable TLS for output '{output_id}'"],
                        estimated_impact="Data transmitted in plaintext",
                    )
                )

            if tls_conf.get("rejectUnauthorized") is False:
                tls_issues.append(
                    {"component": output_id, "type": "output", "issue": "cert_validation_disabled"}
                )
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-cert-validation-disabled-output-{output_id}",
                        category="security",
                        severity="high",
                        title=f"Certificate Validation Disabled: {output_id}",
                        description=f"Output '{output_id}' disables certificate validation (rejectUnauthorized=false).",
                        affected_components=[output_id],
                        confidence_level="high",
                        remediation_steps=[
                            f"Enable certificate validation for output '{output_id}'",
                            "Verify destination certificates are trusted",
                        ],
                        estimated_impact="Increased risk of man-in-the-middle attacks",
                    )
                )

            tls_version = tls_conf.get("minVersion") or tls_conf.get("version")
            if tls_version in self.WEAK_TLS_VERSIONS:
                tls_issues.append(
                    {"component": output_id, "type": "output", "issue": "weak_tls_version"}
                )
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-weak-tls-output-{output_id}",
                        category="security",
                        severity="medium",
                        title=f"Weak TLS Version on Output: {output_id}",
                        description=f"Output '{output_id}' uses weak TLS version '{tls_version}'.",
                        affected_components=[output_id],
                        confidence_level="high",
                        remediation_steps=[
                            f"Update TLS minVersion to TLSv1.2+ for output '{output_id}'"
                        ],
                        estimated_impact="Potentially vulnerable TLS configuration",
                    )
                )

        return tls_issues

    def _analyze_secrets(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> List[Dict[str, Any]]:
        """Scan configurations for hardcoded secrets."""
        secret_issues = []

        for comp_list, comp_type in [(outputs, "output"), (inputs, "input")]:
            for comp in comp_list:
                comp_id = comp.get("id", "unknown")
                comp_str = json.dumps(comp)

                for secret_type, pattern in self.SECRET_PATTERNS.items():
                    for match in pattern.finditer(comp_str):
                        field_name = match.group(1)
                        val = match.group(2)
                        if self.ENV_VAR_PATTERN.search(val) or self._is_placeholder(val):
                            continue

                        secret_issues.append(
                            {
                                "component": comp_id,
                                "type": comp_type,
                                "secret_type": secret_type,
                                "field_name": field_name,
                            }
                        )
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"security-hardcoded-secret-{comp_type}-{comp_id}-{field_name}",
                                grouping_id="security-hardcoded-secret",
                                category="security",
                                severity="critical",
                                title=f"{comp_id}: Hardcoded {secret_type.title()} Detected",
                                description=f"Component '{comp_id}' contains a hardcoded {secret_type} in the '{field_name}' field.",
                                affected_components=[comp_id],
                                confidence_level="high",
                                remediation_steps=[
                                    f"Replace hardcoded {secret_type} in field '{field_name}' with environment variable",
                                    f"Review all credential fields in '{comp_id}' configuration",
                                ],
                                estimated_impact="Credentials exposed in configuration",
                                metadata={
                                    "secret_type": secret_type,
                                    "component_id": comp_id,
                                    "component_type": comp_type,
                                    "field_name": field_name,
                                },
                            )
                        )

        return secret_issues

    def _is_placeholder(self, value: str) -> bool:
        """Check if a value is a placeholder."""
        placeholders = ["example", "placeholder", "changeme", "xxx", "****", "redacted"]
        return any(p in value.lower() for p in placeholders)

    def _analyze_authentication(
        self, auth_config: Dict[str, Any], result: AnalyzerResult, client: CriblAPIClient
    ) -> List[Dict[str, Any]]:
        """Analyze authentication configuration."""
        issues = []
        if auth_config.get("disabled") is True:
            issues.append({"issue": "auth_disabled"})
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="security-auth-disabled",
                    category="security",
                    severity="high",
                    title="Authentication Disabled",
                    description="System authentication is disabled, allowing unauthenticated access.",
                    affected_components=["system"],
                    confidence_level="high",
                    remediation_steps=["Enable authentication in system settings"],
                    estimated_impact="Unauthorized access to system",
                )
            )

        auth_method = auth_config.get("type") or auth_config.get("method")
        if auth_method == "basic":
            issues.append({"issue": "weak_auth_method"})
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="security-basic-auth",
                    category="security",
                    severity="low",
                    title="Basic Authentication in Use",
                    description="System uses basic authentication instead of SAML/OIDC.",
                    affected_components=["system"],
                    confidence_level="high",
                    remediation_steps=["Consider upgrading to SAML or OIDC"],
                    estimated_impact="Weaker authentication security",
                )
            )
        return issues

    def _analyze_certificates(
        self,
        certificates: List[Dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> List[Dict[str, Any]]:
        """Analyze certificate configurations for expiration."""
        issues = []
        now = datetime.utcnow()

        for cert in certificates:
            cert_id = cert.get("id", "unknown")
            expires_at_str = cert.get("expiresAt") or cert.get("notAfter")
            if not expires_at_str:
                continue

            try:
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00").split("+")[0]
                )
                days_until = (expires_at - now).days

                if days_until < 0:
                    issues.append({"cert_id": cert_id, "issue": "expired"})
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"security-cert-expired-{cert_id}",
                            category="security",
                            severity="critical",
                            title=f"Certificate Expired: {cert_id}",
                            description=f"Certificate '{cert_id}' expired {abs(days_until)} days ago.",
                            confidence_level="high",
                            affected_components=[cert_id],
                            remediation_steps=[f"Renew certificate '{cert_id}' immediately"],
                            estimated_impact="Service disruption for components using this certificate",
                        )
                    )
                elif days_until <= 30:
                    issues.append({"cert_id": cert_id, "issue": "expiring_soon"})
                    severity = "high" if days_until <= 7 else "medium"
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"security-cert-expiring-{cert_id}",
                            category="security",
                            severity=severity,
                            title=f"Certificate Expiring Soon: {cert_id}",
                            description=f"Certificate '{cert_id}' expires in {days_until} days.",
                            confidence_level="high",
                            affected_components=[cert_id],
                            remediation_steps=[f"Renew certificate '{cert_id}'"],
                            estimated_impact="Potential future service disruption",
                        )
                    )
            except Exception:
                log.warning("failed_to_parse_cert_expiry", cert=cert_id)

        return issues

    def _analyze_rbac(
        self,
        roles: List[Dict[str, Any]],
        users: List[Dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> List[Dict[str, Any]]:
        """Analyze RBAC and user activity."""
        issues: List[Dict[str, Any]] = []
        now = datetime.utcnow()

        admin_roles = set()
        for role in roles:
            role_id = role.get("id", "unknown")
            perms = role.get("permissions", [])
            if any(p == "admin" or "*" in str(p) for p in perms):
                admin_roles.add(role_id)
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-rbac-wildcard-{role_id}",
                        category="security",
                        severity="high",
                        title=f"Overly Permissive Role: {role_id}",
                        description=f"Role '{role_id}' has wildcard or admin permissions.",
                        confidence_level="high",
                        affected_components=[role_id],
                        remediation_steps=[f"Review and restrict permissions for role '{role_id}'"],
                        estimated_impact="Users with this role have excessive power",
                        metadata={"role_id": role_id, "permissions": perms},
                    )
                )

        inactive_users = 0
        admin_user_count = 0
        used_role_ids = set()
        for user in users:
            if user.get("disabled"):
                continue
            user_id = user.get("id", user.get("username", "unknown"))
            last_login_str = user.get("lastLogin") or user.get("last_login")

            user_roles = user.get("roles", [])
            used_role_ids.update(user_roles)
            if any(role in admin_roles for role in user_roles):
                admin_user_count += 1

            if last_login_str:
                try:
                    if isinstance(last_login_str, (int, float)):
                        last_login = datetime.utcfromtimestamp(last_login_str / 1000)
                    else:
                        last_login = datetime.fromisoformat(
                            last_login_str.replace("Z", "+00:00").split("+")[0]
                        )

                    days_inactive = (now - last_login).days
                    if days_inactive > 90:
                        inactive_users += 1
                        severity = "high" if days_inactive > 180 else "medium"
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"security-user-inactive-{user_id}",
                                category="security",
                                severity=severity,
                                title=f"Inactive User Account: {user_id}",
                                description=f"User '{user_id}' has not logged in for {days_inactive} days.",
                                confidence_level="medium",
                                affected_components=[user_id],
                                remediation_steps=[f"Disable or remove inactive user '{user_id}'"],
                                estimated_impact="Increased risk of credential misuse",
                            )
                        )
                except Exception:
                    pass
            else:
                created_at = user.get("created") or user.get("createdAt")
                if not created_at:
                    continue
                try:
                    if isinstance(created_at, (int, float)):
                        created_ts = datetime.utcfromtimestamp(created_at / 1000)
                    else:
                        created_ts = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00").split("+")[0]
                        )
                    days_since_created = (now - created_ts).days
                    if days_since_created > 30:
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"security-user-never-logged-in-{user_id}",
                                category="security",
                                severity="medium",
                                title=f"Never Logged In User: {user_id}",
                                description=f"User '{user_id}' has never logged in since creation ({days_since_created} days).",
                                confidence_level="medium",
                                affected_components=[user_id],
                                remediation_steps=[
                                    f"Review account '{user_id}' and disable if unused."
                                ],
                                estimated_impact="Unused accounts increase the attack surface.",
                                metadata={"created_at": created_at},
                            )
                        )
                except Exception:
                    pass

        admin_user_threshold = 3
        if admin_user_count > admin_user_threshold:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="security-rbac-too-many-admins",
                    category="security",
                    severity="medium",
                    title="High Number of Admin Users",
                    description=f"Found {admin_user_count} users with administrative privileges, which exceeds the recommended maximum of {admin_user_threshold}.",
                    confidence_level="high",
                    affected_components=[
                        user.get("id", user.get("username", "unknown"))
                        for user in users
                        if any(role in admin_roles for role in user.get("roles", []))
                    ],
                    remediation_steps=[
                        "Review the list of administrative users.",
                        "Remove unnecessary administrative privileges based on the principle of least privilege.",
                    ],
                    estimated_impact="Increased risk of unauthorized changes and security breaches.",
                )
            )

        if len(users) > 0 and (inactive_users / len(users)) > 0.25:
            result.add_recommendation(
                Recommendation(
                    id="rec-security-user-lifecycle",
                    type="security",
                    priority="p2",
                    title="Implement User Lifecycle Policy",
                    description=f"{(inactive_users / len(users)) * 100:.1f}% of users are inactive.",
                    rationale="Inactive accounts increase the attack surface if compromised.",
                    implementation_steps=[
                        "Review all inactive users",
                        "Disable accounts inactive for > 90 days",
                    ],
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Reduced attack surface",
                        cost_savings_annual=0.0,
                        storage_reduction_gb=0.0,
                        time_to_implement="2 hours",
                    ),
                    implementation_effort="low",
                    product_tags=["stream", "edge"],
                )
            )

        all_role_ids = {role.get("id") for role in roles if role.get("id")}
        orphaned_roles = all_role_ids - used_role_ids

        default_roles = {"default", "admin", "user"}
        orphaned_roles -= default_roles

        for role_id in orphaned_roles:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"security-rbac-orphaned-role-{role_id}",
                    category="security",
                    severity="low",
                    title=f"Orphaned Role: {role_id}",
                    description=f"Role '{role_id}' is defined but not assigned to any user.",
                    confidence_level="medium",
                    affected_components=[role_id],
                    remediation_steps=[
                        f"If role '{role_id}' is no longer needed, consider deleting it to simplify configuration."
                    ],
                    estimated_impact="Reduces configuration clutter and potential for misassignment.",
                )
            )

        return issues

    def _analyze_api_keys(
        self, api_keys: List[Dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> List[Dict[str, Any]]:
        """Analyze API key security."""
        issues: List[Dict[str, Any]] = []
        now = datetime.utcnow()

        for key in api_keys:
            key_id = key.get("id", "unknown")
            if not key.get("expiresAt") and not key.get("expires_at"):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-api-key-no-expiry-{key_id}",
                        category="security",
                        severity="medium",
                        title=f"API Key Without Expiration: {key_id}",
                        description=f"API key '{key_id}' does not have an expiration date.",
                        confidence_level="high",
                        affected_components=[key_id],
                        remediation_steps=[f"Set an expiration date for API key '{key_id}'"],
                        estimated_impact="API keys that never expire increase long-term risk",
                        metadata={"key_id": key_id},
                    )
                )

            last_used_str = key.get("lastUsed")
            if not last_used_str:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-api-key-never-used-{key_id}",
                        category="security",
                        severity="low",
                        title=f"API Key Never Used: {key_id}",
                        description=f"API key '{key_id}' has never been used.",
                        confidence_level="medium",
                        affected_components=[key_id],
                        remediation_steps=[
                            f"Validate if the API key '{key_id}' is still required. If not, delete it."
                        ],
                        estimated_impact="Reduces attack surface by removing unused credentials.",
                        metadata={"key_id": key_id},
                    )
                )
            else:
                try:
                    if isinstance(last_used_str, (int, float)):
                        last_used = datetime.utcfromtimestamp(last_used_str / 1000)
                    else:
                        last_used = datetime.fromisoformat(
                            last_used_str.replace("Z", "+00:00").split("+")[0]
                        )
                    days_since_used = (now - last_used).days
                    if days_since_used > 90:
                        result.add_finding(
                            self.create_finding(
                                client=client,
                                id=f"security-api-key-inactive-{key_id}",
                                category="security",
                                severity="medium",
                                title=f"Inactive API Key: {key_id}",
                                description=f"API key '{key_id}' has not been used in {days_since_used} days.",
                                confidence_level="medium",
                                affected_components=[key_id],
                                remediation_steps=[
                                    f"Consider rotating or deleting the inactive API key '{key_id}'."
                                ],
                                estimated_impact="Increased risk from potentially forgotten but active credentials.",
                                metadata={"key_id": key_id, "days_since_used": days_since_used},
                            )
                        )
                except Exception:
                    log.warning("failed_to_parse_api_key_last_used", key=key_id)

            perms = key.get("permissions", [])
            if any(p == "admin" or "*" in str(p) for p in perms):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-api-key-overly-permissive-{key_id}",
                        category="security",
                        severity="high",
                        title=f"Overly Permissive API Key: {key_id}",
                        description=f"API key '{key_id}' has wildcard or admin permissions.",
                        confidence_level="high",
                        affected_components=[key_id],
                        remediation_steps=[
                            f"Review and restrict permissions for API key '{key_id}' to the minimum required."
                        ],
                        estimated_impact="A compromised key could grant full administrative access.",
                    )
                )
        return issues

    def _analyze_teams(
        self, teams: List[Dict[str, Any]], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        """Analyze team configurations."""
        for team in teams:
            if not team.get("members"):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"security-team-empty-{team.get('id')}",
                        category="security",
                        severity="info",
                        title=f"Empty Team: {team.get('id')}",
                        description=f"Team '{team.get('id')}' has no members.",
                        confidence_level="high",
                        affected_components=[team.get("id", "unknown")],
                        remediation_steps=["Remove empty teams to simplify configuration"],
                        estimated_impact="Unnecessary configuration complexity",
                    )
                )

    def _analyze_guard_policies(
        self, security_settings: Dict[str, Any], result: AnalyzerResult, client: CriblAPIClient
    ) -> None:
        if not isinstance(security_settings, dict) or not security_settings:
            return

        policies: List[Dict[str, Any]] = []
        candidates = [security_settings]
        guard_settings = security_settings.get("guard")
        if isinstance(guard_settings, dict):
            candidates.append(guard_settings)
        masking_settings = security_settings.get("masking")
        if isinstance(masking_settings, dict):
            candidates.append(masking_settings)

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for key in ("maskingPolicies", "masking_policies", "policies", "maskingPoliciesList"):
                value = candidate.get(key)
                if isinstance(value, list):
                    policies = value
                    break
            if policies:
                break

        enabled_policies = [p for p in policies if p.get("enabled", True)]
        result.metadata["guard_policy_count"] = len(policies)
        result.metadata["guard_policy_enabled_count"] = len(enabled_policies)

        if enabled_policies:
            return

        affected = [p.get("id", "unknown") for p in policies] if policies else ["guard"]
        result.add_finding(
            self.create_finding(
                client=client,
                id="security-guard-masking-policies",
                grouping_id="security-guard-masking-policies",
                category="security",
                severity="medium",
                title="Cribl Guard Masking Policies Not Active",
                description="No enabled masking policies were detected for Cribl Guard.",
                confidence_level="high",
                affected_components=affected,
                remediation_steps=[
                    "Review Cribl Guard masking policies",
                    "Enable masking policies for high-risk sources",
                    "Verify Guard is configured for sensitive data",
                ],
                metadata={
                    "policy_count": len(policies),
                    "enabled_policy_count": len(enabled_policies),
                },
            )
        )

    def _calculate_security_score(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        auth_config: Dict[str, Any],
        tls_issues: List[Dict[str, Any]],
        secret_issues: List[Dict[str, Any]],
        auth_issues: List[Dict[str, Any]],
    ) -> int:
        """Calculate overall security score (0-100)."""
        score = 100
        if auth_config.get("disabled") is True:
            score -= self.SCORE_WEIGHTS["authentication_configured"]
        if tls_issues:
            score -= self.SCORE_WEIGHTS["tls_enabled"]
        if secret_issues:
            score -= self.SCORE_WEIGHTS["no_hardcoded_secrets"]
        if auth_issues:
            score -= min(len(auth_issues) * 5, self.SCORE_WEIGHTS["authentication_configured"])
        return max(0, min(100, int(score)))

    def _generate_security_recommendations(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        auth_config: Dict[str, Any],
        tls_issues: List[Dict[str, Any]],
        secret_issues: List[Dict[str, Any]],
        auth_issues: List[Dict[str, Any]],
        result: AnalyzerResult,
    ) -> None:
        """Generate security recommendations."""
        if secret_issues:
            result.add_recommendation(
                Recommendation(
                    id="security-remove-secrets",
                    type="security",
                    priority="p0",
                    title="Remove Hardcoded Credentials",
                    description="Replace hardcoded credentials in configurations with environment variables.",
                    rationale="Hardcoded credentials can be exposed in backups and version control.",
                    implementation_steps=[
                        "Identify components with secrets",
                        "Move secrets to env vars",
                    ],
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Better security posture",
                        cost_savings_annual=0.0,
                        storage_reduction_gb=0.0,
                        time_to_implement="4 hours",
                    ),
                    implementation_effort="medium",
                    product_tags=["stream", "edge"],
                )
            )
