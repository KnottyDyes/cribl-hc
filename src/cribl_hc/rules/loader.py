"""
Rule loading and evaluation engine for configuration validation.

This module provides a configuration-driven approach to validating Cribl
deployments against best practices, security standards, and performance guidelines.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml
from packaging import version

from cribl_hc.models.rule import BestPracticeRule

logger = structlog.get_logger(__name__)


class RuleLoader:
    """Loads and filters best practice rules from YAML configuration."""

    def __init__(self, rules_dir: Optional[Path] = None):
        """
        Initialize the rule loader.

        Args:
            rules_dir: Directory containing YAML rule files. If None, uses default bundled rules.
        """
        if rules_dir is None:
            # Use default bundled rules directory
            rules_dir = Path(__file__).parent

        self.rules_dir = rules_dir
        self._cache: Optional[List[BestPracticeRule]] = None

    def load_rules_from_yaml(self, filename: str = "cribl_rules.yaml") -> List[BestPracticeRule]:
        """
        Load rules from a specific YAML file.

        Args:
            filename: Name of the YAML file to load. Defaults to "cribl_rules.yaml".

        Returns:
            List of BestPracticeRule objects.
        """
        rules_path = self.rules_dir / filename

        if not rules_path.exists():
            logger.warning("Rules file not found, returning empty list", path=str(rules_path))
            return []

        try:
            with open(rules_path, "r") as f:
                data = yaml.safe_load(f)

            if not data or "rules" not in data:
                logger.warning("No rules found in YAML file", path=str(rules_path))
                return []

            # Convert to BestPracticeRule objects
            rules = []
            for rule_data in data["rules"]:
                try:
                    rule = BestPracticeRule(**rule_data)
                    rules.append(rule)
                except Exception as e:
                    logger.warning(
                        "Failed to parse rule, skipping",
                        rule_id=rule_data.get("id", "unknown"),
                        error=str(e),
                    )
                    continue

            logger.info("Loaded rules from YAML", count=len(rules), path=str(rules_path))
            return rules

        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML", path=str(rules_path), error=str(e))
            return []

    def load_all_rules(self, cache: bool = True) -> List[BestPracticeRule]:
        """
        Load all rules from all YAML files in the rules directory.

        Args:
            cache: Whether to cache loaded rules. Defaults to True.

        Returns:
            List of all BestPracticeRule objects.
        """
        if cache and self._cache is not None:
            return self._cache

        # For now, just load from the main cribl_rules.yaml file
        rules = self.load_rules_from_yaml()

        if cache:
            self._cache = rules

        return rules

    def filter_by_version(
        self, rules: List[BestPracticeRule], cribl_version: str
    ) -> List[BestPracticeRule]:
        """
        Filter rules applicable to a specific Cribl version.

        Args:
            rules: List of rules to filter.
            cribl_version: Cribl version string (e.g., "4.5.0").

        Returns:
            Filtered list of rules applicable to the version.
        """
        if not cribl_version:
            return rules

        filtered = []
        try:
            ver = version.parse(cribl_version)
        except Exception:
            logger.warning("Invalid version string, returning all rules", version=cribl_version)
            return rules

        for rule in rules:
            # Check min_version
            if rule.cribl_version_min:
                try:
                    min_ver = version.parse(rule.cribl_version_min)
                    if ver < min_ver:
                        continue
                except Exception:
                    logger.warning(
                        "Invalid min_version in rule, skipping version check",
                        rule_id=rule.id,
                        min_version=rule.cribl_version_min,
                    )

            # Check max_version
            if rule.cribl_version_max:
                try:
                    max_ver = version.parse(rule.cribl_version_max)
                    if ver > max_ver:
                        continue
                except Exception:
                    logger.warning(
                        "Invalid max_version in rule, skipping version check",
                        rule_id=rule.id,
                        max_version=rule.cribl_version_max,
                    )

            filtered.append(rule)

        logger.debug(
            "Filtered rules by version",
            original_count=len(rules),
            filtered_count=len(filtered),
            version=cribl_version,
        )
        return filtered

    def filter_by_category(
        self, rules: List[BestPracticeRule], categories: List[str]
    ) -> List[BestPracticeRule]:
        """
        Filter rules by category.

        Args:
            rules: List of rules to filter.
            categories: List of category names to include.

        Returns:
            Filtered list of rules matching the categories.
        """
        if not categories:
            return rules

        filtered = [rule for rule in rules if rule.category in categories]

        logger.debug(
            "Filtered rules by category",
            original_count=len(rules),
            filtered_count=len(filtered),
            categories=categories,
        )
        return filtered

    def filter_enabled_only(self, rules: List[BestPracticeRule]) -> List[BestPracticeRule]:
        """
        Filter to only enabled rules.

        Args:
            rules: List of rules to filter.

        Returns:
            List of enabled rules only.
        """
        filtered = [rule for rule in rules if rule.enabled]

        logger.debug(
            "Filtered enabled rules",
            original_count=len(rules),
            filtered_count=len(filtered),
        )
        return filtered


class RuleEvaluator:
    """Evaluates configuration against loaded rules."""

    def evaluate_rule(
        self, rule: BestPracticeRule, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Evaluate a single rule against configuration.

        Args:
            rule: The rule to evaluate.
            config: Configuration dictionary to check.
            context: Optional context (metrics, relationships, etc.).

        Returns:
            True if rule is violated, False otherwise.
        """
        # Skip disabled rules
        if not rule.enabled:
            return False

        # Delegate to specific evaluators based on check_type
        if rule.check_type == "config_pattern":
            return self._evaluate_config_pattern(rule, config)
        elif rule.check_type == "metric_threshold":
            metrics = context.get("metrics", {}) if context else {}
            return self._evaluate_metric_threshold(rule, metrics)
        elif rule.check_type == "relationship":
            return self._evaluate_relationship(rule, config, context or {})
        else:
            logger.warning("Unknown check_type, skipping rule", rule_id=rule.id, check_type=rule.check_type)
            return False

    def _evaluate_config_pattern(self, rule: BestPracticeRule, config: Dict[str, Any]) -> bool:
        """
        Evaluate config_pattern rule.

        Supports simple patterns like:
        - "exists:field_name" - Check if field exists (violated if missing)
        - "field equals: value" - Check if field equals value (violated if not equal)
        - "field matches: regex" - Check if field matches regex pattern (violated if doesn't match)
        - "field not_matches: regex" - Check if field does NOT match regex (violated if matches)

        Returns:
            True if rule is violated.
        """
        logic = rule.validation_logic

        # Handle "exists:field" or "field exists: field" pattern
        if "exists:" in logic:
            if logic.startswith("exists:"):
                field_name = logic.split(":", 1)[1].strip()
            else:
                # Format: "output exists: output" (weird but in tests)
                parts = logic.split("exists:", 1)
                field_name = parts[1].strip()
            
            exists = self._field_exists(config, field_name)
            # Rule wants field to exist - violated if it doesn't
            return not exists

        # Handle "field equals: value" pattern
        if " equals: " in logic:
            parts = logic.split(" equals: ", 1)
            field_path = parts[0].strip()
            expected_value = parts[1].strip()
            actual_value = self._get_field(config, field_path)
            # Violated if NOT equal
            return str(actual_value) != expected_value

        # Handle "field matches: regex" pattern
        if " matches: " in logic:
            parts = logic.split(" matches: ", 1)
            field_path = parts[0].strip()
            pattern = parts[1].strip()
            
            # Special handling for array length checks
            if field_path.endswith(".length"):
                base_path = field_path[:-7]  # Remove ".length"
                array = self._get_field(config, base_path)
                if isinstance(array, list):
                    length = len(array)
                    # Handle operators in pattern like "> 15"
                    if pattern.startswith(">"):
                        threshold = int(pattern[1:].strip())
                        # Violated if length > threshold
                        return length > threshold
                    elif pattern.startswith("<"):
                        threshold = int(pattern[1:].strip())
                        # Violated if length < threshold
                        return length < threshold
                return False
            
            value = self._get_field(config, field_path)
            if value is None:
                return True  # Field missing = violation
            
            try:
                match = re.search(pattern, str(value))
                # Violated if does NOT match
                return not bool(match)
            except re.error:
                logger.warning("Invalid regex pattern", pattern=pattern, rule_id=rule.id)
                return False

        # Handle "field not_matches: regex" pattern
        if " not_matches: " in logic:
            parts = logic.split(" not_matches: ", 1)
            field_path = parts[0].strip()
            pattern = parts[1].strip()
            value = self._get_field(config, field_path)
            if value is None:
                return False  # Field missing = no violation for not_matches
            
            try:
                match = re.search(pattern, str(value))
                # Violated if DOES match
                return bool(match)
            except re.error:
                logger.warning("Invalid regex pattern", pattern=pattern, rule_id=rule.id)
                return False

        # Handle "regex_count <= N" pattern
        if "regex_count" in logic:
            functions = config.get("functions", [])
            regex_count = sum(1 for f in functions if "regex" in f.get("id", ""))
            
            if "<=" in logic:
                threshold = int(logic.split("<=")[1].strip())
                # Violated if count EXCEEDS threshold
                return regex_count > threshold
            elif ">=" in logic:
                threshold = int(logic.split(">=")[1].strip())
                # Violated if count is BELOW threshold
                return regex_count < threshold
            elif "==" in logic:
                threshold = int(logic.split("==")[1].strip())
                # Violated if count doesn't match
                return regex_count != threshold
            
        # Handle direct comparison expressions like "field.length > N" or "field > N"
        for operator in [">=", "<=", ">", "<", "=="]:
            if operator in logic:
                parts = logic.split(operator, 1)
                if len(parts) == 2:
                    field_path = parts[0].strip()
                    threshold_str = parts[1].strip()
                    
                    try:
                        threshold = float(threshold_str)
                        
                        # Special handling for .length
                        if field_path.endswith(".length"):
                            base_path = field_path[:-7]
                            array = self._get_field(config, base_path)
                            if isinstance(array, list):
                                actual_value = float(len(array))
                            else:
                                return False  # Not an array
                        else:
                            actual_value = self._get_field(config, field_path)
                            if actual_value is None:
                                return False
                            actual_value = float(actual_value)
                        
                        # Evaluate the comparison
                        if operator == ">" and actual_value > threshold:
                            return True
                        elif operator == "<" and actual_value < threshold:
                            return True
                        elif operator == ">=" and actual_value >= threshold:
                            return True
                        elif operator == "<=" and actual_value <= threshold:
                            return True
                        elif operator == "==" and actual_value == threshold:
                            return True
                        
                        return False
                        
                    except (ValueError, TypeError):
                        # Not a numeric comparison
                        continue
                break  # Found an operator, stop looking

        return False

    def _evaluate_metric_threshold(self, rule: BestPracticeRule, metrics: Dict[str, Any]) -> bool:
        """
        Evaluate metric_threshold rule.

        The validation_logic expresses a THRESHOLD CONDITION that triggers a violation.
        For example: "cpu.usage > 80" means "violated if cpu.usage exceeds 80".

        Returns:
            True if rule is violated (threshold condition is TRUE).
        """
        logic = rule.validation_logic

        # Parse threshold logic
        for operator in [">=", "<=", "==", ">", "<"]:
            if operator in logic:
                parts = logic.split(operator, 1)
                if len(parts) == 2:
                    metric_path = parts[0].strip()
                    threshold_str = parts[1].strip()

                    try:
                        threshold = float(threshold_str)
                        actual_value = self._get_field(metrics, metric_path)

                        if actual_value is None:
                            return False  # Metric missing = no violation

                        actual_value = float(actual_value)

                        # Check if the threshold condition is TRUE (= violation)
                        if operator == ">" and actual_value > threshold:
                            return True
                        elif operator == "<" and actual_value < threshold:
                            return True
                        elif operator == ">=" and actual_value >= threshold:
                            return True
                        elif operator == "<=" and actual_value <= threshold:
                            return True
                        elif operator == "==" and actual_value == threshold:
                            return True

                        return False

                    except (ValueError, TypeError):
                        logger.warning(
                            "Failed to evaluate metric threshold",
                            rule_id=rule.id,
                            metric=metric_path,
                        )
                        return False
                break

        return False

    def _evaluate_relationship(
        self, rule: BestPracticeRule, config: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate relationship rule.

        Checks cross-component relationships like:
        - "references:pipelines" - Check if referenced pipeline exists

        Returns:
            True if rule is violated.
        """
        logic = rule.validation_logic

        if logic.startswith("references:"):
            resource_type = logic.split(":", 1)[1].strip()
            
            # Get the reference from config (e.g., "pipeline" field)
            reference_field = resource_type.rstrip("s")  # "pipelines" -> "pipeline"
            referenced_id = config.get(reference_field)
            
            if not referenced_id:
                return False  # No reference = no violation
            
            # Check if resource exists in context
            available_resources = context.get(resource_type, [])
            resource_ids = [r.get("id") for r in available_resources if isinstance(r, dict)]
            
            # Violated if referenced resource doesn't exist
            return referenced_id not in resource_ids

        return False

    def _field_exists(self, config: Any, field_path: str) -> bool:
        """
        Check if a field exists in config (supports nested paths like "conf.functions.0.id").

        Args:
            config: Configuration to search.
            field_path: Dot-separated path.

        Returns:
            True if field exists.
        """
        return self._get_field(config, field_path) is not None

    def _get_field(self, config: Any, field_path: str) -> Any:
        """
        Get a field value from config using dot notation.

        Supports:
        - Nested objects: "level1.level2.level3"
        - Array indices: "array.0", "array.1"

        Args:
            config: Configuration dictionary.
            field_path: Dot-separated path.

        Returns:
            Field value or None if not found.
        """
        parts = field_path.split(".")
        value = config

        for part in parts:
            if value is None:
                return None

            # Handle array index access
            if isinstance(value, list):
                try:
                    index = int(part)
                    if 0 <= index < len(value):
                        value = value[index]
                    else:
                        return None
                except ValueError:
                    return None
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value
