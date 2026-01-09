import re
from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.utils.logger import get_logger


class SensitiveDataAnalyzer(BaseAnalyzer):
    PATTERNS = {
        "ssn": {
            "regex": re.compile(
                r"\b(?!000|666|9\d{2})([0-8]\d{2})[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b"
            ),
            "name": "Social Security Number",
            "severity": "critical",
        },
        "credit_card": {
            "regex": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
            "name": "Credit Card Number",
            "severity": "critical",
        },
        "aws_key": {
            "regex": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "name": "AWS Access Key",
            "severity": "high",
        },
        "private_key": {
            "regex": re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
            "name": "Private Key",
            "severity": "critical",
        },
        "generic_api_key": {
            "regex": re.compile(
                r"(?i)(?:key|token|secret|password|passwd)[\"\']?\s*[:=]\s*[\"\']?([a-zA-Z0-9_\-]{16,})[\"\']?"
            ),
            "name": "Generic API Key/Secret",
            "severity": "high",
        },
    }

    def __init__(self):
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        return "sensitive_data"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return "Detects unmasked sensitive data (PII, PCI, Secrets) in live event streams"

    def get_estimated_api_calls(self) -> int:
        return 1

    def get_required_permissions(self) -> list[str]:
        return ["read:system", "execute:capture"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            events = await client.capture_events(
                filter_expr="true", max_events=50, duration=5, level=1
            )

            result.metadata["events_scanned"] = len(events)

            if not events:
                self.log.info("no_events_captured")
                return result

            findings_count = 0

            for event in events:
                raw_data = str(event.get("_raw", str(event)))

                for key, pattern_def in self.PATTERNS.items():
                    matches = pattern_def["regex"].findall(raw_data)

                    if matches:
                        findings_count += 1
                        if findings_count > 10:
                            break

                        source_info = event.get("cribl_pipe", event.get("source", "unknown"))
                        input_id = event.get("input", "unknown")

                        components = []
                        if input_id != "unknown":
                            components.append(f"input:{input_id}")
                        if source_info != "unknown":
                            components.append(f"pipeline:{source_info}")
                        if not components:
                            components = ["event-stream:live-capture"]

                        result.add_finding(
                            Finding(
                                id=f"sensitive-data-{key}",
                                title=f"Sensitive Data Detected: {pattern_def['name']}",
                                description=f"Found potential {pattern_def['name']} in live event stream during system capture. "
                                f"This sensitive data was detected in unmasked form, indicating a masking or encryption gap. "
                                f"Check the affected components to identify where masking should be applied.",
                                severity=pattern_def["severity"],
                                category="security",
                                confidence_level="medium",
                                affected_components=components,
                                estimated_impact="Data Leakage, Compliance Violation (PCI/HIPAA/GDPR)",
                                remediation_steps=[
                                    "Identify which pipeline is processing this data from the affected components",
                                    "Apply Masking function early in the pipeline before any outputs",
                                    "Encrypt sensitive fields before ingestion if possible",
                                    "Filter out sensitive events at the source if they shouldn't be collected",
                                    "Verify masking is applied before data reaches any destination",
                                ],
                                metadata={
                                    "pattern_type": key,
                                    "match_count": len(matches),
                                    "source": source_info,
                                    "input": input_id,
                                },
                            )
                        )

                if findings_count > 10:
                    break

            if findings_count == 0:
                result.add_finding(
                    Finding(
                        id="sensitive-data-clean",
                        title="No Sensitive Data Detected",
                        description=f"Scanned {len(events)} events and found no PII/Secrets patterns.",
                        severity="info",
                        category="security",
                        confidence_level="medium",
                        affected_components=["pipeline:processing"],
                        estimated_impact="None",
                        remediation_steps=[],
                        metadata={"events_scanned": len(events)},
                    )
                )

        except Exception as e:
            self.log.error("sensitive_data_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result
