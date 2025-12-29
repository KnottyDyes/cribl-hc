"""
Security Posture Analyzer for Cribl Health Check.

Analyzes security configurations including TLS/mTLS, credential exposure,
and authentication mechanisms. Calculates overall security posture score.

Priority: P2 (Security - critical for compliance and data protection)
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import structlog

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class SecurityAnalyzer(BaseAnalyzer):
    """
    Analyzer for security posture assessment.

    Identifies:
    - TLS/mTLS configuration issues (disabled TLS, weak versions, missing cert validation)
    - Hardcoded secrets and credentials in configurations
    - Weak or missing authentication mechanisms
    - Overall security posture score (0-100)

    Priority: P2 (Security - critical for compliance)

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = SecurityAnalyzer()
        ...     result = await analyzer.analyze(client)
        ...     score = result.metadata.get('security_posture_score', 0)
        ...     print(f"Security Score: {score}/100")
    """

    # TLS version constants
    WEAK_TLS_VERSIONS = ["TLSv1", "TLSv1.0", "TLSv1.1", "SSLv2", "SSLv3"]
    SECURE_TLS_VERSIONS = ["TLSv1.2", "TLSv1.3"]

    # Secret patterns (conservative - avoid false positives)
    SECRET_PATTERNS = {
        "password": re.compile(r'"password"\s*:\s*"([^"]{8,})"', re.IGNORECASE),
        "api_key": re.compile(r'"(?:api[_-]?key|apikey)"\s*:\s*"([^"]{16,})"', re.IGNORECASE),
        "secret": re.compile(r'"secret"\s*:\s*"([^"]{16,})"', re.IGNORECASE),
        "token": re.compile(r'"(?:auth[_-]?token|token)"\s*:\s*"([^"]{20,})"', re.IGNORECASE),
        "private_key": re.compile(r'"(?:private[_-]?key|privatekey)"\s*:\s*"([^"]+)"', re.IGNORECASE),
    }

    # Environment variable patterns (these are OK - not hardcoded)
    ENV_VAR_PATTERN = re.compile(r'\$\{[A-Z_][A-Z0-9_]*\}')

    # Security score weights
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
        Estimate API calls: outputs(1) + inputs(1) + auth(1) + system(1) = 4.
        """
        return 4

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:outputs",
            "read:inputs",
            "read:auth",
            "read:system"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze security posture and identify vulnerabilities.

        Automatically adapts based on detected product type.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with security findings and remediation recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            # Detect product type
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            log.info("security_analysis_started", product=client.product_type, product_name=product_name)

            # Fetch data
            outputs = await self._fetch_outputs(client)
            inputs = await self._fetch_inputs(client)
            auth_config = await self._fetch_auth_config(client)
            system_settings = await self._fetch_system_settings(client)

            # Analyze security aspects
            tls_issues = self._analyze_tls_configuration(outputs, inputs, result)
            secret_issues = self._analyze_secrets(outputs, inputs, result)
            auth_issues = self._analyze_authentication(auth_config, result)

            # Calculate security posture score
            security_score = self._calculate_security_score(
                outputs, inputs, auth_config, tls_issues, secret_issues, auth_issues
            )

            # Generate recommendations
            self._generate_security_recommendations(
                outputs, inputs, auth_config, tls_issues, secret_issues, auth_issues, result
            )

            # Set metadata
            result.metadata.update({
                "product_type": client.product_type,
                "outputs_analyzed": len(outputs),
                "inputs_analyzed": len(inputs),
                "security_posture_score": security_score,
                "tls_issues_count": len(tls_issues),
                "secret_issues_count": len(secret_issues),
                "auth_issues_count": len(auth_issues),
                "total_bytes": 0,  # Required by base analyzer
                "analyzed_at": datetime.utcnow().isoformat(),
            })

            result.success = True
            log.info(
                "security_analysis_completed",
                product=client.product_type,
                outputs=len(outputs),
                inputs=len(inputs),
                findings=len(result.findings),
                recommendations=len(result.recommendations),
                security_score=security_score,
            )

        except Exception as e:
            log.error("security_analysis_failed", error=str(e), exc_info=True)
            # Graceful degradation
            result.metadata.update({
                "product_type": getattr(client, "product_type", "unknown"),
                "outputs_analyzed": 0,
                "inputs_analyzed": 0,
                "security_posture_score": 0,
                "tls_issues_count": 0,
                "secret_issues_count": 0,
                "auth_issues_count": 0,
                "total_bytes": 0,
                "error": str(e),
            })
            result.success = True  # Graceful degradation

        return result

    # === Data Fetching ===

    async def _fetch_outputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch output configurations."""
        try:
            return await client.get_outputs() or []
        except Exception as e:
            log.warning("failed_to_fetch_outputs", error=str(e))
            return []

    async def _fetch_inputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch input configurations."""
        try:
            return await client.get_inputs() or []
        except Exception as e:
            log.warning("failed_to_fetch_inputs", error=str(e))
            return []

    async def _fetch_auth_config(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch authentication configuration."""
        try:
            return await client.get_auth_config() or {}
        except Exception as e:
            log.warning("failed_to_fetch_auth_config", error=str(e))
            return {}

    async def _fetch_system_settings(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch system settings."""
        try:
            return await client.get_system_settings() or {}
        except Exception as e:
            log.warning("failed_to_fetch_system_settings", error=str(e))
            return {}

    # === TLS Analysis ===

    def _analyze_tls_configuration(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> List[Dict[str, Any]]:
        """
        Analyze TLS configuration for outputs and inputs.

        Returns list of TLS issues found.
        """
        tls_issues = []

        # Check outputs
        for output in outputs:
            output_id = output.get("id", "unknown")
            output_type = output.get("type", "unknown")
            conf = output.get("conf", {})
            tls_conf = conf.get("tls", {})

            # Check if TLS is disabled
            if tls_conf.get("disabled") is True:
                tls_issues.append({
                    "component": output_id,
                    "type": "output",
                    "issue": "tls_disabled",
                })
                result.add_finding(
                    Finding(
                        id=f"security-tls-disabled-output-{output_id}",
                        category="security",
                        severity="high",
                        title=f"TLS Disabled on Output: {output_id}",
                        description=(
                            f"Output '{output_id}' ({output_type}) has TLS disabled, "
                            f"transmitting data in plaintext. This exposes sensitive data "
                            f"to interception and violates security best practices."
                        ),
                        affected_components=[output_id],
                        confidence_level="high",
                        estimated_impact="Sensitive data transmitted in plaintext vulnerable to interception",
                        remediation_steps=[
                            f"Navigate to Outputs → {output_id}",
                            "Enable TLS by setting tls.disabled = false or removing the disabled flag",
                            "Configure valid TLS certificates and keys",
                            "Set minimum TLS version to TLSv1.2",
                            "Test connectivity to ensure successful TLS handshake",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/outputs",
                        ],
                        metadata={
                            "output_id": output_id,
                            "output_type": output_type,
                            "tls_disabled": True,
                        },
                    )
                )

            # Check for weak TLS versions
            tls_version = tls_conf.get("minVersion") or tls_conf.get("version")
            if tls_version in self.WEAK_TLS_VERSIONS:
                tls_issues.append({
                    "component": output_id,
                    "type": "output",
                    "issue": "weak_tls_version",
                    "version": tls_version,
                })
                result.add_finding(
                    Finding(
                        id=f"security-weak-tls-output-{output_id}",
                        category="security",
                        severity="medium",
                        title=f"Weak TLS Version on Output: {output_id}",
                        description=(
                            f"Output '{output_id}' uses weak TLS version '{tls_version}'. "
                            f"Upgrade to TLSv1.2 or TLSv1.3 to protect against known vulnerabilities."
                        ),
                        affected_components=[output_id],
                        confidence_level="high",
                        remediation_steps=[
                            f"Navigate to Outputs → {output_id}",
                            "Update tls.minVersion to 'TLSv1.2' or 'TLSv1.3'",
                            "Verify downstream systems support TLSv1.2+",
                            "Test connectivity after upgrade",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/outputs",
                        ],
                        metadata={
                            "output_id": output_id,
                            "tls_version": tls_version,
                            "recommended_version": "TLSv1.2 or TLSv1.3",
                        },
                    )
                )

            # Check if certificate validation is disabled
            if tls_conf.get("rejectUnauthorized") is False or tls_conf.get("validateCert") is False:
                tls_issues.append({
                    "component": output_id,
                    "type": "output",
                    "issue": "cert_validation_disabled",
                })
                result.add_finding(
                    Finding(
                        id=f"security-cert-validation-disabled-output-{output_id}",
                        category="security",
                        severity="medium",
                        title=f"Certificate Validation Disabled on Output: {output_id}",
                        description=(
                            f"Output '{output_id}' has certificate validation disabled, "
                            f"making it vulnerable to man-in-the-middle attacks. "
                            f"Enable certificate validation for secure communication."
                        ),
                        affected_components=[output_id],
                        confidence_level="high",
                        remediation_steps=[
                            f"Navigate to Outputs → {output_id}",
                            "Enable certificate validation (set tls.rejectUnauthorized = true)",
                            "Ensure valid CA certificates are configured",
                            "Test connectivity with certificate validation enabled",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/outputs",
                        ],
                        metadata={
                            "output_id": output_id,
                            "cert_validation_disabled": True,
                        },
                    )
                )

        # Check inputs
        for input_conf in inputs:
            input_id = input_conf.get("id", "unknown")
            input_type = input_conf.get("type", "unknown")
            conf = input_conf.get("conf", {})
            tls_conf = conf.get("tls", {})

            # Check if TLS is disabled
            if tls_conf.get("disabled") is True:
                tls_issues.append({
                    "component": input_id,
                    "type": "input",
                    "issue": "tls_disabled",
                })
                result.add_finding(
                    Finding(
                        id=f"security-tls-disabled-input-{input_id}",
                        category="security",
                        severity="high",
                        title=f"TLS Disabled on Input: {input_id}",
                        description=(
                            f"Input '{input_id}' ({input_type}) has TLS disabled, "
                            f"receiving data in plaintext. Enable TLS to protect "
                            f"data in transit from interception."
                        ),
                        affected_components=[input_id],
                        confidence_level="high",
                        estimated_impact="Data received in plaintext vulnerable to interception",
                        remediation_steps=[
                            f"Navigate to Inputs → {input_id}",
                            "Enable TLS by setting tls.disabled = false",
                            "Configure valid TLS certificates and keys",
                            "Test connectivity with TLS enabled",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/inputs",
                        ],
                        metadata={
                            "input_id": input_id,
                            "input_type": input_type,
                            "tls_disabled": True,
                        },
                    )
                )

            # Check for weak TLS versions on inputs
            tls_version = tls_conf.get("minVersion") or tls_conf.get("version")
            if tls_version in self.WEAK_TLS_VERSIONS:
                tls_issues.append({
                    "component": input_id,
                    "type": "input",
                    "issue": "weak_tls_version",
                    "version": tls_version,
                })
                result.add_finding(
                    Finding(
                        id=f"security-weak-tls-input-{input_id}",
                        category="security",
                        severity="medium",
                        title=f"Weak TLS Version on Input: {input_id}",
                        description=(
                            f"Input '{input_id}' uses weak TLS version '{tls_version}'. "
                            f"Upgrade to TLSv1.2 or TLSv1.3."
                        ),
                        affected_components=[input_id],
                        confidence_level="high",
                        remediation_steps=[
                            f"Navigate to Inputs → {input_id}",
                            "Update tls.minVersion to 'TLSv1.2' or 'TLSv1.3'",
                            "Test connectivity after upgrade",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/inputs",
                        ],
                        metadata={
                            "input_id": input_id,
                            "tls_version": tls_version,
                        },
                    )
                )

        return tls_issues

    # === Secret Scanning ===

    def _analyze_secrets(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> List[Dict[str, Any]]:
        """
        Scan configurations for hardcoded secrets.

        Returns list of secret issues found.
        """
        secret_issues = []

        # Scan outputs
        for output in outputs:
            output_id = output.get("id", "unknown")
            secrets = self._scan_for_secrets(output, output_id, "output")
            secret_issues.extend(secrets)

            for secret in secrets:
                result.add_finding(
                    Finding(
                        id=f"security-hardcoded-secret-output-{output_id}",
                        category="security",
                        severity="critical",
                        title=f"Hardcoded {secret['secret_type'].title()} in Output: {output_id}",
                        description=(
                            f"Output '{output_id}' contains a hardcoded {secret['secret_type']}. "
                            f"Hardcoded credentials should be replaced with environment variables "
                            f"or secrets management systems (e.g., HashiCorp Vault, AWS Secrets Manager)."
                        ),
                        affected_components=[output_id],
                        confidence_level="high",
                        estimated_impact="Credential exposure in configuration backups and version control",
                        remediation_steps=[
                            f"Navigate to Outputs → {output_id}",
                            f"Replace hardcoded {secret['secret_type']} with environment variable reference",
                            "Store credential in secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager)",
                            "Update configuration to use ${ENV_VAR_NAME} syntax",
                            "Rotate the exposed credential immediately",
                            "Implement secrets scanning in CI/CD pipeline",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/environment-variables",
                        ],
                        metadata={
                            "output_id": output_id,
                            "secret_type": secret["secret_type"],
                            "field": secret.get("field", "unknown"),
                        },
                    )
                )

        # Scan inputs
        for input_conf in inputs:
            input_id = input_conf.get("id", "unknown")
            secrets = self._scan_for_secrets(input_conf, input_id, "input")
            secret_issues.extend(secrets)

            for secret in secrets:
                result.add_finding(
                    Finding(
                        id=f"security-hardcoded-secret-input-{input_id}",
                        category="security",
                        severity="critical",
                        title=f"Hardcoded {secret['secret_type'].title()} in Input: {input_id}",
                        description=(
                            f"Input '{input_id}' contains a hardcoded {secret['secret_type']}. "
                            f"Replace with environment variables or secrets management."
                        ),
                        affected_components=[input_id],
                        confidence_level="high",
                        estimated_impact="Credential exposure in configuration backups and version control",
                        remediation_steps=[
                            f"Navigate to Inputs → {input_id}",
                            f"Replace hardcoded {secret['secret_type']} with environment variable reference",
                            "Store credential in secrets manager",
                            "Update configuration to use ${ENV_VAR_NAME} syntax",
                            "Rotate the exposed credential immediately",
                        ],
                        documentation_links=[
                            "https://docs.cribl.io/stream/environment-variables",
                        ],
                        metadata={
                            "input_id": input_id,
                            "secret_type": secret["secret_type"],
                            "field": secret.get("field", "unknown"),
                        },
                    )
                )

        return secret_issues

    def _scan_for_secrets(
        self,
        config: Dict[str, Any],
        component_id: str,
        component_type: str
    ) -> List[Dict[str, Any]]:
        """
        Scan a configuration object for hardcoded secrets.

        Returns list of secrets found.
        """
        import json
        secrets_found = []

        try:
            # Convert config to JSON string for pattern matching
            config_str = json.dumps(config)

            # Check each secret pattern
            for secret_type, pattern in self.SECRET_PATTERNS.items():
                matches = pattern.finditer(config_str)
                for match in matches:
                    secret_value = match.group(1)

                    # Skip if it's an environment variable reference
                    if self.ENV_VAR_PATTERN.search(secret_value):
                        continue

                    # Skip if it's a placeholder or example value
                    if self._is_placeholder(secret_value):
                        continue

                    secrets_found.append({
                        "component": component_id,
                        "type": component_type,
                        "secret_type": secret_type,
                        "field": match.group(0).split('"')[1],  # Extract field name
                    })

        except Exception as e:
            log.warning(
                "secret_scan_failed",
                component=component_id,
                error=str(e)
            )

        return secrets_found

    def _is_placeholder(self, value: str) -> bool:
        """Check if a value is a placeholder or example."""
        placeholder_indicators = [
            "example",
            "placeholder",
            "your_",
            "your-",
            "changeme",
            "change_me",
            "replace",
            "xxx",
            "****",
            "redacted",
        ]
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in placeholder_indicators)

    # === Authentication Analysis ===

    def _analyze_authentication(
        self,
        auth_config: Dict[str, Any],
        result: AnalyzerResult
    ) -> List[Dict[str, Any]]:
        """
        Analyze authentication configuration.

        Returns list of authentication issues found.
        """
        auth_issues = []

        # Check if authentication is disabled
        auth_disabled = auth_config.get("disabled") is True
        if auth_disabled:
            auth_issues.append({
                "issue": "auth_disabled",
            })
            result.add_finding(
                Finding(
                    id="security-auth-disabled",
                    category="security",
                    severity="high",
                    title="Authentication Disabled",
                    description=(
                        "System authentication is disabled, allowing unauthenticated access. "
                        "Enable authentication to protect against unauthorized access."
                    ),
                    affected_components=["system"],
                    confidence_level="high",
                    estimated_impact="Unauthorized access to sensitive data and configurations",
                    remediation_steps=[
                        "Navigate to Settings → Authentication",
                        "Enable authentication",
                        "Configure authentication method (SAML, OAuth, or LDAP recommended)",
                        "Set up user accounts and roles",
                        "Test access controls",
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/authentication",
                    ],
                    metadata={
                        "auth_disabled": True,
                    },
                )
            )

        # Check authentication method
        auth_method = auth_config.get("type") or auth_config.get("method")
        if auth_method == "basic":
            auth_issues.append({
                "issue": "weak_auth_method",
                "method": "basic",
            })
            result.add_finding(
                Finding(
                    id="security-basic-auth",
                    category="security",
                    severity="low",
                    title="Basic Authentication in Use",
                    description=(
                        "System uses basic authentication. Consider upgrading to "
                        "more secure methods like SAML, OAuth, or LDAP for better security."
                    ),
                    affected_components=["system"],
                    confidence_level="high",
                    metadata={
                        "auth_method": "basic",
                        "recommended_methods": ["SAML", "OAuth", "LDAP"],
                    },
                )
            )

        return auth_issues

    # === Security Score Calculation ===

    def _calculate_security_score(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        auth_config: Dict[str, Any],
        tls_issues: List[Dict[str, Any]],
        secret_issues: List[Dict[str, Any]],
        auth_issues: List[Dict[str, Any]]
    ) -> int:
        """
        Calculate overall security posture score (0-100).

        Higher is better. Deducts points for security issues.
        """
        score = 100  # Start with perfect score

        total_components = len(outputs) + len(inputs)
        if total_components == 0:
            return 0  # No components to score

        # Deduct for TLS issues
        tls_disabled_count = len([i for i in tls_issues if i["issue"] == "tls_disabled"])
        weak_tls_count = len([i for i in tls_issues if i["issue"] == "weak_tls_version"])
        cert_validation_count = len([i for i in tls_issues if i["issue"] == "cert_validation_disabled"])

        # TLS disabled is critical - deduct heavily
        score -= (tls_disabled_count / total_components) * self.SCORE_WEIGHTS["tls_enabled"]

        # Weak TLS version
        score -= (weak_tls_count / total_components) * self.SCORE_WEIGHTS["strong_tls_version"]

        # Certificate validation disabled
        score -= (cert_validation_count / total_components) * self.SCORE_WEIGHTS["cert_validation"]

        # Deduct for hardcoded secrets (critical)
        if secret_issues:
            score -= min(len(secret_issues) * 5, self.SCORE_WEIGHTS["no_hardcoded_secrets"])

        # Deduct for authentication issues
        if auth_issues:
            auth_disabled_count = len([i for i in auth_issues if i["issue"] == "auth_disabled"])
            if auth_disabled_count > 0:
                score -= self.SCORE_WEIGHTS["authentication_configured"]
            else:
                # Weak auth method - smaller deduction
                score -= 5

        # Ensure score stays in 0-100 range
        return max(0, min(100, int(score)))

    # === Recommendations ===

    def _generate_security_recommendations(
        self,
        outputs: List[Dict[str, Any]],
        inputs: List[Dict[str, Any]],
        auth_config: Dict[str, Any],
        tls_issues: List[Dict[str, Any]],
        secret_issues: List[Dict[str, Any]],
        auth_issues: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Generate security recommendations based on findings."""

        # Recommendation: Enable TLS
        tls_disabled_components = [
            i["component"] for i in tls_issues if i["issue"] == "tls_disabled"
        ]
        if tls_disabled_components:
            result.add_recommendation(
                Recommendation(
                    id="security-enable-tls",
                    type="security",
                    priority="p1",
                    title="Enable TLS Encryption",
                    description=(
                        f"Enable TLS encryption on {len(tls_disabled_components)} component(s) "
                        f"to protect data in transit from interception."
                    ),
                    rationale="TLS encryption protects sensitive data during transmission and prevents man-in-the-middle attacks",
                    implementation_steps=[
                        f"Review TLS configuration for: {', '.join(tls_disabled_components[:5])}",
                        "Enable TLS by setting tls.disabled = false",
                        "Configure valid certificates and keys",
                        "Set minimum TLS version to TLSv1.2 or higher",
                        "Enable certificate validation",
                        "Test connectivity after changes",
                    ],
                    implementation_effort="medium",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Protects sensitive data from interception during transmission",
                    ),
                    before_state=f"{len(tls_disabled_components)} component(s) transmitting data in plaintext",
                    after_state="All components using encrypted TLS connections",
                )
            )

        # Recommendation: Upgrade TLS version
        weak_tls_components = [
            i["component"] for i in tls_issues if i["issue"] == "weak_tls_version"
        ]
        if weak_tls_components:
            result.add_recommendation(
                Recommendation(
                    id="security-upgrade-tls-version",
                    type="security",
                    priority="p2",
                    title="Upgrade to Strong TLS Versions",
                    description=(
                        f"Upgrade {len(weak_tls_components)} component(s) from weak TLS versions "
                        f"to TLSv1.2 or TLSv1.3."
                    ),
                    rationale="Weak TLS versions have known vulnerabilities (POODLE, BEAST, etc.) that can be exploited",
                    implementation_steps=[
                        f"Identify components using weak TLS: {', '.join(weak_tls_components[:5])}",
                        "Update tls.minVersion to 'TLSv1.2' or 'TLSv1.3'",
                        "Verify downstream systems support TLSv1.2+",
                        "Test connectivity after upgrade",
                    ],
                    implementation_effort="low",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Protects against known TLS vulnerabilities (POODLE, BEAST, etc.)",
                    ),
                    before_state=f"{len(weak_tls_components)} component(s) using weak TLS versions",
                    after_state="All components using TLSv1.2 or TLSv1.3",
                )
            )

        # Recommendation: Replace hardcoded secrets
        if secret_issues:
            affected = list(set([s["component"] for s in secret_issues]))
            result.add_recommendation(
                Recommendation(
                    id="security-remove-hardcoded-secrets",
                    type="security",
                    priority="p0",
                    title="Remove Hardcoded Credentials",
                    description=(
                        f"Replace {len(secret_issues)} hardcoded credential(s) with "
                        f"environment variables or secrets management."
                    ),
                    rationale="Hardcoded credentials in configurations can be exposed through backups, version control, or unauthorized access",
                    implementation_steps=[
                        f"Audit components with hardcoded secrets: {', '.join(affected[:5])}",
                        "Store credentials in environment variables or secrets manager",
                        "Update configurations to reference ${ENV_VAR} instead of literal values",
                        "Rotate exposed credentials immediately",
                        "Implement secrets scanning in CI/CD pipeline",
                    ],
                    implementation_effort="medium",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Prevents credential exposure in configuration backups and version control",
                    ),
                    before_state=f"{len(secret_issues)} hardcoded credential(s) in configurations",
                    after_state="All credentials stored securely in secrets manager",
                )
            )

        # Recommendation: Enable authentication
        if any(i["issue"] == "auth_disabled" for i in auth_issues):
            result.add_recommendation(
                Recommendation(
                    id="security-enable-authentication",
                    type="security",
                    priority="p1",
                    title="Enable System Authentication",
                    description="Enable authentication to prevent unauthorized access to the system.",
                    rationale="Unauthenticated systems allow anyone to access sensitive data and modify configurations",
                    implementation_steps=[
                        "Configure authentication method (SAML, OAuth, or LDAP recommended)",
                        "Set up user accounts and roles",
                        "Enable authentication in system settings",
                        "Test access controls",
                        "Document authentication procedures",
                    ],
                    implementation_effort="medium",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Prevents unauthorized access to sensitive data and configurations",
                    ),
                    before_state="Unauthenticated access allowed",
                    after_state="Authentication required for all access",
                )
            )
