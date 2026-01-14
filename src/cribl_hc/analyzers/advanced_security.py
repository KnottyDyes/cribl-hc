"""
Advanced Security & Compliance Analyzer for Cribl Health Check.

Enhanced security analysis with healthcare codes, financial data patterns,
custom compliance frameworks, and advanced threat detection capabilities.
"""

import re
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger


@dataclass
class ComplianceFramework:
    """Represents a compliance framework with its requirements."""

    name: str
    description: str
    required_patterns: List[str]
    severity_mapping: Dict[str, str]
    remediation_guidance: str


@dataclass
class CustomPattern:
    """Represents a custom sensitive data pattern."""

    name: str
    pattern: str
    description: str
    severity: str
    category: str
    remediation: str


class AdvancedSecurityAnalyzer(BaseAnalyzer):
    """
    Advanced security and compliance analyzer with healthcare codes,
    financial data patterns, and custom compliance frameworks.

    Phase 13 - Enterprise Operations

    Extends basic sensitive data detection with:
    - Healthcare codes (ICD, CPT, NDC, DEA numbers)
    - Financial data patterns (ABA routing, SWIFT codes)
    - Custom pattern configuration
    - Compliance framework validation (SOC2, HIPAA, GDPR, etc.)
    - Advanced threat detection
    """

    # Healthcare patterns
    HEALTHCARE_PATTERNS = {
        "icd_10": {
            "pattern": r"\b[A-Z]\d{2}(?:\.\d{1,3})?\b",
            "description": "ICD-10 diagnostic codes",
            "severity": "medium",
            "category": "healthcare",
        },
        "cpt_codes": {
            "pattern": r"\b\d{5}\b",
            "description": "CPT procedure codes",
            "severity": "medium",
            "category": "healthcare",
        },
        "ndc_codes": {
            "pattern": r"\b\d{4,6}-\d{3,4}-\d{1,2}\b",
            "description": "NDC drug codes",
            "severity": "medium",
            "category": "healthcare",
        },
        "dea_numbers": {
            "pattern": r"\b[A-Z]{2}\d{7}\b",
            "description": "DEA registration numbers",
            "severity": "high",
            "category": "healthcare",
        },
    }

    # Financial patterns
    FINANCIAL_PATTERNS = {
        "aba_routing": {
            "pattern": r"\b\d{9}\b",
            "description": "ABA routing numbers",
            "severity": "medium",
            "category": "financial",
        },
        "swift_codes": {
            "pattern": r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",
            "description": "SWIFT/BIC codes",
            "severity": "medium",
            "category": "financial",
        },
        "iban_codes": {
            "pattern": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
            "description": "IBAN codes",
            "severity": "medium",
            "category": "financial",
        },
        "credit_card_bins": {
            "pattern": r"\b(?:3[47]\d{13}|4\d{12}(?:\d{3})?|5[1-5]\d{14}|6(?:011|5\d{2})\d{12}|3(?:0[0-5]|[68]\d)\d{11}|2131|1800|35\d{3})\d{8,12}\b",
            "description": "Credit card BIN patterns",
            "severity": "high",
            "category": "financial",
        },
    }

    # Compliance frameworks
    COMPLIANCE_FRAMEWORKS = {
        "hipaa": ComplianceFramework(
            name="HIPAA",
            description="Health Insurance Portability and Accountability Act",
            required_patterns=["dea_numbers", "icd_10", "healthcare_records"],
            severity_mapping={"healthcare": "high", "personal": "critical"},
            remediation_guidance="Implement HIPAA-compliant data handling, encryption, and access controls",
        ),
        "soc2": ComplianceFramework(
            name="SOC 2",
            description="System and Organization Controls 2",
            required_patterns=["financial_data", "personal_data", "system_logs"],
            severity_mapping={"financial": "high", "personal": "high", "security": "critical"},
            remediation_guidance="Implement SOC 2 controls for security, availability, and confidentiality",
        ),
        "gdpr": ComplianceFramework(
            name="GDPR",
            description="General Data Protection Regulation",
            required_patterns=["personal_data", "consent_records", "data_subject_rights"],
            severity_mapping={"personal": "critical", "consent": "high"},
            remediation_guidance="Implement GDPR-compliant data processing, consent management, and subject rights",
        ),
    }

    def __init__(self) -> None:
        """Initialize the advanced security analyzer."""
        super().__init__()
        self.log = get_logger(__name__)
        self.custom_patterns: List[CustomPattern] = self._load_custom_patterns()
        self.active_frameworks: Set[str] = set()

    @property
    def objective_name(self) -> str:
        """
        Return the objective name for this analyzer.
        """
        return "advanced_security"

    @property
    def category(self) -> str:
        """
        Return the category this analyzer belongs to.
        """
        return "enterprise"

    @property
    def supported_products(self) -> list[str]:
        """Advanced security applies to all products."""
        return ["stream", "edge", "lake", "search"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Advanced security analysis with healthcare codes, financial data, and compliance frameworks"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: event sampling for pattern analysis."""
        return 2  # Event sampling for advanced pattern detection

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:system", "execute:capture"]

    def _load_custom_patterns(self) -> List[CustomPattern]:
        """
        Load custom sensitive data patterns from configuration file.
        """
        import yaml
        from pathlib import Path

        patterns = []
        config_file = Path(__file__).parent.parent / "rules" / "custom_pii_patterns.yaml"

        try:
            if config_file.exists():
                with open(config_file, "r") as f:
                    data = yaml.safe_load(f)

                if data and "custom_patterns" in data:
                    for pattern_data in data["custom_patterns"]:
                        if pattern_data.get("enabled", True):
                            try:
                                pattern = CustomPattern(
                                    name=pattern_data["name"],
                                    pattern=pattern_data["pattern"],
                                    description=pattern_data["description"],
                                    severity=pattern_data["severity"],
                                    category=pattern_data["category"],
                                    remediation=pattern_data["remediation"],
                                )
                                patterns.append(pattern)
                            except KeyError as e:
                                self.log.warning(
                                    f"Invalid custom pattern configuration: missing required field {e}",
                                    pattern_name=pattern_data.get("name", "unknown"),
                                )
                            except re.error as e:
                                self.log.warning(
                                    f"Invalid regex pattern in custom pattern '{pattern_data.get('name', 'unknown')}': {e}"
                                )

                self.log.info(f"Loaded {len(patterns)} custom sensitive data patterns")
            else:
                self.log.info("Custom PII patterns file not found, using defaults only")

        except Exception as e:
            self.log.error(f"Failed to load custom PII patterns: {e}")

        return patterns

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform advanced security and compliance analysis.

        Strategy:
        1. Sample events for pattern analysis
        2. Check healthcare code exposure
        3. Validate financial data handling
        4. Assess compliance framework adherence
        5. Check custom pattern violations
        6. Generate compliance recommendations
        """
        result = self.create_result()

        try:
            # Sample events for analysis
            events = await client.capture_events(
                filter_expr="true", max_events=200, duration=15, level=1
            )

            result.metadata["events_analyzed"] = len(events)

            if len(events) < 10:
                result.add_finding(
                    self.create_finding(
                        id="advanced-security-insufficient-data",
                        title="Insufficient Data for Advanced Security Analysis",
                        description=f"Only {len(events)} events captured. Need at least 10 for meaningful security pattern analysis.",
                        severity="info",
                        category="security",
                        confidence_level="medium",
                        affected_components=["data:security"],
                        remediation_steps=[
                            "Ensure adequate data flow for security analysis",
                            "Check if event sampling is working correctly",
                            "Verify data sources are active and producing events",
                        ],
                        metadata={"events_captured": len(events)},
                    )
                )
                return result

            # Analyze healthcare data exposure
            healthcare_findings = self._analyze_healthcare_patterns(events)
            for finding in healthcare_findings:
                result.add_finding(finding)

            # Analyze financial data handling
            financial_findings = self._analyze_financial_patterns(events)
            for finding in financial_findings:
                result.add_finding(finding)

            # Check compliance frameworks
            compliance_findings = self._analyze_compliance_frameworks(events)
            for finding in compliance_findings:
                result.add_finding(finding)

            # Check custom patterns
            custom_findings = self._analyze_custom_patterns(events)
            for finding in custom_findings:
                result.add_finding(finding)

            # Generate summary findings
            summary_findings = self._generate_security_summary(events, result.findings)
            for finding in summary_findings:
                result.add_finding(finding)

            result.metadata.update(
                {
                    "healthcare_patterns_checked": len(self.HEALTHCARE_PATTERNS),
                    "financial_patterns_checked": len(self.FINANCIAL_PATTERNS),
                    "compliance_frameworks_checked": len(self.active_frameworks),
                    "custom_patterns_checked": len(self.custom_patterns),
                }
            )

        except Exception as e:
            self.log.error("advanced_security_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _analyze_healthcare_patterns(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Analyze healthcare data patterns in events."""
        findings = []

        for event in events:
            for field_name, field_value in event.items():
                if field_name.startswith("_"):  # Skip internal fields
                    continue

                if not isinstance(field_value, str):
                    continue

                for pattern_name, pattern_config in self.HEALTHCARE_PATTERNS.items():
                    if re.search(pattern_config["pattern"], field_value, re.IGNORECASE):
                        findings.append(
                            self.create_finding(
                                id=f"healthcare-pattern-{pattern_name}-{field_name}",
                                title=f"Healthcare Data Exposure: {pattern_config['description']}",
                                description=f"Detected {pattern_config['description']} in field '{field_name}'. "
                                f"This may violate healthcare privacy regulations.",
                                severity=pattern_config["severity"],
                                category="security",
                                confidence_level="high",
                                affected_components=["data:healthcare"],
                                estimated_impact="Potential HIPAA violations, privacy breaches, and regulatory fines",
                                remediation_steps=[
                                    f"Mask or encrypt field '{field_name}' containing healthcare data",
                                    "Implement healthcare data handling policies",
                                    "Review data retention and access controls",
                                    "Consider data minimization for healthcare fields",
                                    "Ensure HIPAA compliance for healthcare data processing",
                                ],
                                metadata={
                                    "pattern_type": pattern_name,
                                    "field_name": field_name,
                                    "detected_value": field_value[:50] + "..."
                                    if len(field_value) > 50
                                    else field_value,
                                    "compliance_framework": "HIPAA",
                                },
                            )
                        )

        return findings

    def _analyze_financial_patterns(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Analyze financial data patterns in events."""
        findings = []

        for event in events:
            for field_name, field_value in event.items():
                if field_name.startswith("_"):  # Skip internal fields
                    continue

                if not isinstance(field_value, str):
                    continue

                for pattern_name, pattern_config in self.FINANCIAL_PATTERNS.items():
                    if re.search(pattern_config["pattern"], field_value):
                        findings.append(
                            self.create_finding(
                                id=f"financial-pattern-{pattern_name}-{field_name}",
                                title=f"Financial Data Exposure: {pattern_config['description']}",
                                description=f"Detected {pattern_config['description']} in field '{field_name}'. "
                                f"This may expose sensitive financial information.",
                                severity=pattern_config["severity"],
                                category="security",
                                confidence_level="high",
                                affected_components=["data:financial"],
                                estimated_impact="Potential fraud, financial loss, and regulatory compliance issues",
                                remediation_steps=[
                                    f"Mask or tokenize field '{field_name}' containing financial data",
                                    "Implement PCI DSS compliance measures",
                                    "Review data encryption and access controls",
                                    "Consider data minimization for financial fields",
                                    "Implement financial data handling policies",
                                ],
                                metadata={
                                    "pattern_type": pattern_name,
                                    "field_name": field_name,
                                    "detected_value": field_value[:50] + "..."
                                    if len(field_value) > 50
                                    else field_value,
                                    "compliance_framework": "PCI DSS",
                                },
                            )
                        )

        return findings

    def _analyze_compliance_frameworks(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Analyze compliance with various frameworks."""
        findings = []

        # Check HIPAA compliance
        hipaa_findings = self._check_hipaa_compliance(events)
        findings.extend(hipaa_findings)

        # Check SOC 2 compliance
        soc2_findings = self._check_soc2_compliance(events)
        findings.extend(soc2_findings)

        # Check GDPR compliance
        gdpr_findings = self._check_gdpr_compliance(events)
        findings.extend(gdpr_findings)

        return findings

    def _check_hipaa_compliance(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Check HIPAA compliance requirements."""
        findings = []

        # Check for healthcare data without proper safeguards
        healthcare_events = []
        for event in events:
            has_healthcare_data = False
            for field_name, field_value in event.items():
                if isinstance(field_value, str):
                    for pattern_config in self.HEALTHCARE_PATTERNS.values():
                        if re.search(pattern_config["pattern"], field_value, re.IGNORECASE):
                            has_healthcare_data = True
                            break
                if has_healthcare_data:
                    healthcare_events.append(event)
                    break

        if healthcare_events:
            # Check if data is encrypted or masked
            unencrypted_healthcare = []
            for event in healthcare_events:
                # Simple check: if healthcare data is in plain text
                for field_name, field_value in event.items():
                    if isinstance(field_value, str) and len(field_value) > 10:
                        # Assume unencrypted if we can detect patterns
                        for pattern_config in self.HEALTHCARE_PATTERNS.values():
                            if re.search(pattern_config["pattern"], field_value, re.IGNORECASE):
                                unencrypted_healthcare.append((field_name, field_value))
                                break

            if unencrypted_healthcare:
                findings.append(
                    self.create_finding(
                        id="hipaa-unencrypted-healthcare-data",
                        title="HIPAA Violation: Unencrypted Healthcare Data",
                        description=f"Detected {len(unencrypted_healthcare)} instances of unencrypted healthcare data. "
                        f"HIPAA requires encryption of protected health information (PHI).",
                        severity="critical",
                        category="compliance",
                        confidence_level="high",
                        affected_components=["data:healthcare", "compliance:hipaa"],
                        estimated_impact="HIPAA violations, regulatory fines, legal liability",
                        remediation_steps=[
                            "Implement encryption for all healthcare data fields",
                            "Use TLS 1.3+ for data transmission",
                            "Implement proper key management for encryption",
                            "Conduct HIPAA compliance audit",
                            "Implement healthcare data handling procedures",
                        ],
                        metadata={
                            "compliance_framework": "HIPAA",
                            "unencrypted_instances": len(unencrypted_healthcare),
                            "affected_fields": len(
                                set(field for field, _ in unencrypted_healthcare)
                            ),
                        },
                    )
                )

        return findings

    def _check_soc2_compliance(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Check SOC 2 compliance requirements."""
        findings = []

        # SOC 2 focuses on security, availability, and confidentiality
        # Check for potential security issues

        # Look for system logs with sensitive information
        sensitive_logs = []
        for event in events:
            if any(
                keyword in str(event).lower() for keyword in ["password", "key", "token", "secret"]
            ):
                sensitive_logs.append(event)

        if sensitive_logs:
            findings.append(
                self.create_finding(
                    id="soc2-sensitive-data-in-logs",
                    title="SOC 2 Violation: Sensitive Data in System Logs",
                    description=f"Detected sensitive data (passwords, keys, tokens) in {len(sensitive_logs)} log entries. "
                    f"SOC 2 requires proper handling of sensitive information.",
                    severity="high",
                    category="compliance",
                    confidence_level="medium",
                    affected_components=["logs:security", "compliance:soc2"],
                    estimated_impact="Security audit failures, trust erosion, compliance violations",
                    remediation_steps=[
                        "Implement log sanitization to remove sensitive data",
                        "Use structured logging with proper field masking",
                        "Implement log encryption for sensitive entries",
                        "Regular security audits of log data",
                        "Implement SOC 2 Type II controls",
                    ],
                    metadata={
                        "compliance_framework": "SOC 2",
                        "sensitive_log_entries": len(sensitive_logs),
                    },
                )
            )

        return findings

    def _check_gdpr_compliance(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Check GDPR compliance requirements."""
        findings = []

        # GDPR focuses on personal data protection
        # Check for personal data without consent indicators

        personal_data_events = []
        for event in events:
            has_personal_data = False
            has_consent = False

            for field_name, field_value in event.items():
                if isinstance(field_value, str):
                    # Simple personal data indicators
                    if any(
                        indicator in field_value.lower()
                        for indicator in ["email", "phone", "address", "name", "ssn", "birth"]
                    ):
                        has_personal_data = True

                    # Check for consent indicators
                    if any(
                        consent_word in field_value.lower()
                        for consent_word in ["consent", "gdpr", "opt-in", "opt-out", "privacy"]
                    ):
                        has_consent = True

            if has_personal_data and not has_consent:
                personal_data_events.append(event)

        if personal_data_events:
            findings.append(
                self.create_finding(
                    id="gdpr-missing-consent",
                    title="GDPR Violation: Personal Data Without Consent",
                    description=f"Detected {len(personal_data_events)} events with personal data but no consent indicators. "
                    f"GDPR requires explicit consent for personal data processing.",
                    severity="critical",
                    category="compliance",
                    confidence_level="medium",
                    affected_components=["data:personal", "compliance:gdpr"],
                    estimated_impact="GDPR fines up to 4% of global revenue, legal liability",
                    remediation_steps=[
                        "Implement explicit consent mechanisms",
                        "Document legal basis for data processing",
                        "Implement data subject rights (access, rectification, erasure)",
                        "Conduct GDPR compliance assessment",
                        "Implement proper consent management systems",
                    ],
                    metadata={
                        "compliance_framework": "GDPR",
                        "events_without_consent": len(personal_data_events),
                    },
                )
            )

        return findings

    def _analyze_custom_patterns(self, events: List[Dict[str, Any]]) -> List[Any]:
        """Analyze custom sensitive data patterns."""
        findings = []

        for pattern in self.custom_patterns:
            for event in events:
                for field_name, field_value in event.items():
                    if field_name.startswith("_"):  # Skip internal fields
                        continue

                    if isinstance(field_value, str):
                        if re.search(pattern.pattern, field_value, re.IGNORECASE):
                            findings.append(
                                self.create_finding(
                                    id=f"custom-pattern-{pattern.name}-{field_name}",
                                    title=f"Custom Security Violation: {pattern.name}",
                                    description=f"Detected custom sensitive pattern '{pattern.name}' in field '{field_name}': "
                                    f"{pattern.description}",
                                    severity=pattern.severity,
                                    category="security",
                                    confidence_level="high",
                                    affected_components=["data:custom"],
                                    estimated_impact=pattern.remediation,
                                    remediation_steps=[
                                        pattern.remediation,
                                        f"Review field '{field_name}' data handling",
                                        "Implement appropriate security controls",
                                        "Consider data masking or encryption",
                                    ],
                                    metadata={
                                        "pattern_name": pattern.name,
                                        "field_name": field_name,
                                        "custom_pattern": True,
                                        "category": pattern.category,
                                    },
                                )
                            )

        return findings

    def _generate_security_summary(
        self, events: List[Dict[str, Any]], all_findings: List[Any]
    ) -> List[Any]:
        """Generate summary findings for security analysis."""
        findings = []

        # Count findings by category
        category_counts = {}
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for finding in all_findings:
            category = getattr(finding, "category", "unknown")
            severity = getattr(finding, "severity", "info")

            category_counts[category] = category_counts.get(category, 0) + 1
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Determine overall security posture
        critical_issues = severity_counts["critical"]
        high_issues = severity_counts["high"]

        if critical_issues > 0:
            overall_severity = "critical"
            status = "Critical Security Issues"
            description = f"Critical security violations detected ({critical_issues} critical, {high_issues} high priority issues)"
        elif high_issues > 5:
            overall_severity = "high"
            status = "High Security Risk"
            description = f"Multiple high-priority security issues detected ({high_issues} high priority issues)"
        elif high_issues > 0:
            overall_severity = "medium"
            status = "Moderate Security Concerns"
            description = (
                f"Security issues detected requiring attention ({high_issues} high priority issues)"
            )
        else:
            overall_severity = "low"
            status = "Good Security Posture"
            description = "No significant security issues detected in the analyzed data"

        findings.append(
            self.create_finding(
                id="advanced-security-summary",
                title=f"Advanced Security Analysis: {status}",
                description=f"{description}. Analyzed {len(events)} events across healthcare, financial, and compliance patterns.",
                severity=overall_severity,
                category="security",
                confidence_level="high",
                affected_components=["data:security"],
                metadata={
                    "events_analyzed": len(events),
                    "total_findings": len(all_findings),
                    "category_breakdown": category_counts,
                    "severity_breakdown": severity_counts,
                    "healthcare_patterns": len(
                        [
                            f
                            for f in all_findings
                            if getattr(f, "metadata", {}).get("compliance_framework") == "HIPAA"
                        ]
                    ),
                    "financial_patterns": len(
                        [f for f in all_findings if getattr(f, "category", "") == "financial"]
                    ),
                    "compliance_violations": len(
                        [f for f in all_findings if getattr(f, "category", "") == "compliance"]
                    ),
                },
            )
        )

        return findings

    def add_custom_pattern(self, pattern: CustomPattern) -> None:
        """Add a custom sensitive data pattern."""
        self.custom_patterns.append(pattern)

    def enable_compliance_framework(self, framework_name: str) -> None:
        """Enable a specific compliance framework for analysis."""
        if framework_name.lower() in self.COMPLIANCE_FRAMEWORKS:
            self.active_frameworks.add(framework_name.lower())

    async def post_analyze_cleanup(self) -> None:
        """Optional cleanup after analysis completes."""
        pass
