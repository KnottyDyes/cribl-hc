"""
HEC Validation Analyzer for Cribl Health Check.

Validates Splunk HTTP Event Collector (HEC) output configurations including:
- URL format validation
- Token presence and format
- SSL/TLS configuration
- Acknowledgment settings
- Index configuration
- Load balancing recommendations
- Compression settings
- CrowdStrike/LogScale detection
"""

import re
from typing import Any, Optional

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)

# UUID v4 regex pattern for HEC token validation
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)

# Valid HEC URL patterns:
# - /services/collector/event (Splunk default)
# - /services/collector/raw (raw endpoint)
# - /services/collector/s2s (S2S endpoint)
# - /services/collector (CrowdStrike/LogScale base path)
HEC_URL_PATTERN = re.compile(r"/services/collector(?:/(event|raw|s2s))?$")

# Placeholder tokens that indicate configuration hasn't been completed
PLACEHOLDER_TOKENS = [
    "your-token-here",
    "your_token_here",
    "YOUR_TOKEN_HERE",
    "token",
    "changeme",
    "CHANGEME",
    "placeholder",
    "PLACEHOLDER",
    "xxx",
    "XXX",
]

# CrowdStrike/LogScale URL patterns
CROWDSTRIKE_URL_PATTERNS = [
    r"crowdstrike",
    r"logscale",
    r"humio",
    r"falcon",
]


class HECValidationAnalyzer(BaseAnalyzer):
    """
    Analyzer for validating Splunk HEC output configurations.
    """

    # Acknowledgment timeout thresholds (in seconds)
    ACK_TIMEOUT_CRITICAL = 30
    ACK_TIMEOUT_WARNING = 60

    @property
    def objective_name(self) -> str:
        return "hec_validation"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return "Validates Splunk HEC output configurations"

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:outputs"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            log.info("hec_validation_analysis_started")

            outputs = await client.get_outputs()
            hec_outputs = [o for o in outputs if o.get("type") == "splunk_hec"]
            total_hec = len(hec_outputs)

            if total_hec == 0:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="hec-no-outputs",
                        title="No HEC Outputs Configured",
                        description="No Splunk HEC outputs were found in the configuration.",
                        severity="info",
                        category="hec_validation",
                        remediation_steps=[
                            "Configure Splunk HEC outputs if data needs to be sent to Splunk.",
                        ],
                    )
                )
            else:
                for hec_output in hec_outputs:
                    if hec_output.get("disabled", False):
                        continue

                    output_id = hec_output.get("id", "unknown")

                    # 1. Check URL presence and format
                    self._check_url(hec_output, result, client)

                    # 2. Check SSL configuration
                    self._check_ssl(hec_output, result, client)

                    # 3. Check token configuration
                    self._check_token(hec_output, result, client)

                    # 4. Check acknowledgment settings (skip for CrowdStrike)
                    if not self._is_crowdstrike_url(hec_output.get("url", "")):
                        self._check_acknowledgment(hec_output, result, client)

                    # 5. Check index configuration (skip for CrowdStrike)
                    if not self._is_crowdstrike_url(hec_output.get("url", "")):
                        self._check_index(hec_output, result, client)

                    # 6. Check load balancing
                    self._check_load_balancing(hec_output, result, client)

                    # 7. Check compression
                    self._check_compression(hec_output, result, client)

                    # 8. Check for CrowdStrike/LogScale misconfiguration
                    self._check_crowdstrike_destination_type(hec_output, result, client)

            result.metadata.update(
                {
                    "hec_outputs_total": total_hec,
                    "hec_outputs_analyzed": len(
                        [o for o in hec_outputs if not o.get("disabled", False)]
                    ),
                }
            )
            result.success = True

            log.info(
                "hec_validation_analysis_completed",
                outputs=total_hec,
                findings=len(result.findings),
            )

        except Exception as e:
            log.error("hec_validation_analysis_failed", error=str(e))
            result.success = False
            result.error = f"HEC validation analysis failed: {str(e)}"
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="hec-analysis-error",
                    title="HEC Validation Analysis Failed",
                    description=f"Unable to complete HEC validation analysis: {str(e)}",
                    severity="info",
                    category="hec_validation",
                )
            )

        return result

    def _is_crowdstrike_url(self, url: str) -> bool:
        """Check if the URL appears to be a CrowdStrike/LogScale endpoint."""
        if not url:
            return False
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in CROWDSTRIKE_URL_PATTERNS)

    def _check_url(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check HEC URL presence and format."""
        output_id = hec_output.get("id", "unknown")
        url = hec_output.get("url", "")

        if not url:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-url-missing-{output_id}",
                    title=f"HEC URL Missing: {output_id}",
                    description=f"HEC output '{output_id}' does not have a URL configured.",
                    severity="critical",
                    category="hec_validation",
                    estimated_impact="Data cannot be sent to Splunk without a configured URL",
                    remediation_steps=[
                        "Configure the HEC URL in the output settings.",
                        "URL should be in format: https://splunk-host:8088/services/collector/event",
                    ],
                    metadata={"output_id": output_id},
                )
            )
            return

        # Check if URL has valid HEC path
        if not HEC_URL_PATTERN.search(url):
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-url-invalid-{output_id}",
                    title=f"HEC URL Invalid Format: {output_id}",
                    description=(
                        f"HEC output '{output_id}' has an invalid URL format. Current URL: {url}"
                    ),
                    severity="high",
                    category="hec_validation",
                    estimated_impact="Data may fail to reach Splunk due to incorrect endpoint path",
                    remediation_steps=[
                        "Update URL to include valid HEC path.",
                        "Valid formats: /services/collector/event, /services/collector/raw, "
                        "/services/collector/s2s, or /services/collector (for CrowdStrike/LogScale)",
                    ],
                    metadata={"output_id": output_id, "current_url": url},
                )
            )

    def _check_ssl(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check SSL/TLS configuration."""
        output_id = hec_output.get("id", "unknown")
        url = hec_output.get("url", "")
        ssl_disabled = hec_output.get("disableSsl", False)

        if url.startswith("https://") and ssl_disabled:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-ssl-disabled-{output_id}",
                    title=f"SSL Verification Disabled: {output_id}",
                    description=(
                        f"HEC output '{output_id}' uses HTTPS but has SSL verification disabled. "
                        "This poses a security risk as it allows man-in-the-middle attacks."
                    ),
                    severity="high",
                    category="hec_validation",
                    estimated_impact="Security vulnerability - data in transit not properly validated",
                    remediation_steps=[
                        "Enable SSL verification by setting disableSsl to false.",
                        "Ensure the Splunk server has a valid SSL certificate.",
                        "If using self-signed certificates, configure proper CA trust.",
                    ],
                    metadata={"output_id": output_id},
                )
            )

    def _check_token(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check HEC token presence and format."""
        output_id = hec_output.get("id", "unknown")
        token = hec_output.get("token", "")

        if not token:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-token-missing-{output_id}",
                    title=f"HEC Token Missing: {output_id}",
                    description=f"HEC output '{output_id}' does not have a token configured.",
                    severity="critical",
                    category="hec_validation",
                    estimated_impact="Data cannot be sent to Splunk without authentication token",
                    remediation_steps=[
                        "Configure a valid HEC token from Splunk.",
                        "Generate a new HEC token in Splunk if needed.",
                    ],
                    metadata={"output_id": output_id},
                )
            )
            return

        # Check for placeholder tokens
        if token.lower() in [p.lower() for p in PLACEHOLDER_TOKENS]:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-token-placeholder-{output_id}",
                    title=f"HEC Token Placeholder Detected: {output_id}",
                    description=(
                        f"HEC output '{output_id}' has a placeholder token that needs to be replaced."
                    ),
                    severity="critical",
                    category="hec_validation",
                    estimated_impact="Data cannot be sent to Splunk with placeholder token",
                    remediation_steps=[
                        "Replace placeholder token with actual HEC token from Splunk.",
                    ],
                    metadata={"output_id": output_id},
                )
            )
            return

        # Check token format (should be UUID v4)
        if not UUID_PATTERN.match(token):
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-token-invalid-{output_id}",
                    title=f"HEC Token Invalid Format: {output_id}",
                    description=(
                        f"HEC output '{output_id}' has a token that does not match UUID format."
                    ),
                    severity="medium",
                    category="hec_validation",
                    remediation_steps=[
                        "Verify the HEC token is correctly copied from Splunk.",
                        "HEC tokens are typically UUIDs (e.g., 550e8400-e29b-41d4-a716-446655440000).",
                    ],
                    metadata={"output_id": output_id},
                )
            )

    def _check_acknowledgment(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check HEC acknowledgment settings."""
        output_id = hec_output.get("id", "unknown")
        ack_enabled = hec_output.get("acknowledgment", False)
        ack_timeout = hec_output.get("ackTimeout", 180)

        if not ack_enabled:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-ack-disabled-{output_id}",
                    title=f"HEC Acknowledgment Disabled: {output_id}",
                    description=(
                        f"HEC output '{output_id}' does not have acknowledgment enabled. "
                        "Without acknowledgment, data loss may go undetected."
                    ),
                    severity="medium",
                    category="hec_validation",
                    remediation_steps=[
                        "Enable acknowledgment for reliable delivery confirmation.",
                        "Configure appropriate ackTimeout based on your environment.",
                    ],
                    metadata={"output_id": output_id},
                )
            )
            return

        # Check ack timeout
        if ack_timeout < self.ACK_TIMEOUT_CRITICAL:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-ack-timeout-critical-{output_id}",
                    title=f"HEC Ack Timeout Too Low: {output_id}",
                    description=(
                        f"HEC output '{output_id}' has ack timeout of {ack_timeout}s which may cause "
                        "false delivery failures under load."
                    ),
                    severity="high",
                    category="hec_validation",
                    estimated_impact="False delivery failures under load, potential data loss",
                    remediation_steps=[
                        f"Increase ackTimeout to at least {self.ACK_TIMEOUT_CRITICAL}s.",
                        "Consider 60-180s for high-latency environments.",
                    ],
                    metadata={"output_id": output_id, "current_timeout": ack_timeout},
                )
            )
        elif ack_timeout < self.ACK_TIMEOUT_WARNING:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-ack-timeout-warning-{output_id}",
                    title=f"HEC Ack Timeout Low: {output_id}",
                    description=(
                        f"HEC output '{output_id}' has ack timeout of {ack_timeout}s which may be "
                        "insufficient for high-latency environments."
                    ),
                    severity="low",
                    category="hec_validation",
                    remediation_steps=[
                        f"Consider increasing ackTimeout to at least {self.ACK_TIMEOUT_WARNING}s.",
                    ],
                    metadata={"output_id": output_id, "current_timeout": ack_timeout},
                )
            )

    def _check_index(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check HEC index configuration."""
        output_id = hec_output.get("id", "unknown")
        index = hec_output.get("index", "")

        if not index:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-index-missing-{output_id}",
                    title=f"HEC Index Not Configured: {output_id}",
                    description=(
                        f"HEC output '{output_id}' does not have a default index configured. "
                        "Data will be sent to the default index associated with the HEC token."
                    ),
                    severity="low",
                    category="hec_validation",
                    remediation_steps=[
                        "Configure a default index for better data organization.",
                        "Alternatively, ensure the HEC token has the correct default index in Splunk.",
                    ],
                    metadata={"output_id": output_id},
                )
            )

    def _check_load_balancing(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check load balancing configuration."""
        output_id = hec_output.get("id", "unknown")
        url = hec_output.get("url", "")
        urls = hec_output.get("urls", [])

        # If only single URL and no load balancer in URL
        if not urls and url:
            # Check if URL appears to be a load balancer (common patterns)
            lb_patterns = ["lb", "load", "vip", "cluster", "pool"]
            is_lb = any(pattern in url.lower() for pattern in lb_patterns)

            if not is_lb:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"hec-lb-single-{output_id}",
                        title=f"Single HEC Endpoint: {output_id}",
                        description=(
                            f"HEC output '{output_id}' is configured with a single endpoint. "
                            "Consider using a load balancer or multiple endpoints for high availability."
                        ),
                        severity="low",
                        category="hec_validation",
                        remediation_steps=[
                            "Configure multiple HEC endpoints for failover.",
                            "Use a load balancer in front of Splunk indexers.",
                        ],
                        metadata={"output_id": output_id},
                    )
                )

    def _check_compression(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check compression settings."""
        output_id = hec_output.get("id", "unknown")
        compression = hec_output.get("compression", True)

        if compression is False:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-compression-disabled-{output_id}",
                    title=f"HEC Compression Disabled: {output_id}",
                    description=(
                        f"HEC output '{output_id}' has compression disabled. "
                        "Enabling compression can reduce bandwidth usage significantly."
                    ),
                    severity="low",
                    category="hec_validation",
                    remediation_steps=[
                        "Enable compression to reduce bandwidth usage.",
                        "Compression typically provides 5-10x reduction in data size.",
                    ],
                    metadata={"output_id": output_id},
                )
            )

    def _check_crowdstrike_destination_type(
        self,
        hec_output: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        """Check if CrowdStrike/LogScale URL is using correct destination type."""
        output_id = hec_output.get("id", "unknown")
        url = hec_output.get("url", "")
        output_type = hec_output.get("type", "")

        if self._is_crowdstrike_url(url) and output_type == "splunk_hec":
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"hec-crowdstrike-destination-type-{output_id}",
                    title=f"CrowdStrike URL with Splunk HEC Type: {output_id}",
                    description=(
                        f"HEC output '{output_id}' appears to be a CrowdStrike/LogScale endpoint "
                        f"but is configured as 'splunk_hec' type. This may work but consider using "
                        "a dedicated CrowdStrike/LogScale destination type if available."
                    ),
                    severity="low",
                    category="hec_validation",
                    remediation_steps=[
                        "Consider using a dedicated CrowdStrike Falcon LogScale destination if available.",
                        "If using splunk_hec type, note that Splunk-specific features (ack, indexer "
                        "acknowledgment) may not work as expected.",
                    ],
                    metadata={
                        "output_id": output_id,
                        "current_type": output_type,
                        "detected_destination": "crowdstrike_logscale",
                    },
                )
            )
