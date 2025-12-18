"""
Rule loader and evaluator for best practice validation.

This module provides functionality to load, filter, and evaluate BestPracticeRules
from YAML configuration files.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from cribl_hc.models.rule import BestPracticeRule
from cribl_hc.utils.logger import get_logger
from cribl_hc.utils.version import parse_version


log = get_logger(__name__)


class RuleLoader:
    """
    Loads and manages best practice rules from YAML files.

    Example:
        >>> loader = RuleLoader()
        >>> rules = loader.load_rules_from_yaml("cribl_rules.yaml")
        >>> filtered = loader.filter_by_version(rules, "4.5.0")
    """

    def __init__(self, rules_dir: Optional[Path] = None):
        """
        Initialize the rule loader.

        Args:
            rules_dir: Directory containing rule YAML files.
                      Defaults to package rules directory.
        """
        if rules_dir is None:
            # Default to package rules directory
            rules_dir = Path(__file__).parent

        self.rules_dir = Path(rules_dir)
        self._rules_cache: Optional[List[BestPracticeRule]] = None

    def load_rules_from_yaml(self, filename: str = "cribl_rules.yaml") -> List[BestPracticeRule]:
        """
        Load best practice rules from a YAML file.

        Args:
            filename: Name of the YAML file in rules directory

        Returns:
            List of BestPracticeRule objects

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValueError: If rule validation fails
        """
        filepath = self.rules_dir / filename

        if not filepath.exists():
            log.warning("rules_file_not_found", filepath=str(filepath))
            return []

        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)

            if not data or "rules" not in data:
                log.warning("rules_file_empty_or_invalid", filepath=str(filepath))
                return []

            rules = []
            for rule_data in data["rules"]:
                try:
                    rule = BestPracticeRule(**rule_data)
                    rules.append(rule)
                except Exception as e:
                    log.error(
                        "rule_validation_failed",
                        rule_id=rule_data.get("id", "unknown"),
                        error=str(e)
                    )
                    # Continue loading other rules
                    continue

            log.info("rules_loaded", count=len(rules), filepath=str(filepath))
            return rules

        except yaml.YAMLError as e:
            log.error("yaml_parse_error", filepath=str(filepath), error=str(e))
            raise
        except Exception as e:
            log.error("rules_load_failed", filepath=str(filepath), error=str(e))
            raise

    def load_all_rules(self, cache: bool = True) -> List[BestPracticeRule]:
        """
        Load all rules from default cribl_rules.yaml file.

        Args:
            cache: Whether to cache loaded rules

        Returns:
            List of all available best practice rules
        """
        if cache and self._rules_cache is not None:
            log.debug("returning_cached_rules", count=len(self._rules_cache))
            return self._rules_cache

        rules = self.load_rules_from_yaml()

        if cache:
            self._rules_cache = rules

        return rules

    def filter_by_version(
        self,
        rules: List[BestPracticeRule],
        cribl_version: str
    ) -> List[BestPracticeRule]:
        """
        Filter rules applicable to a specific Cribl version.

        Args:
            rules: List of rules to filter
            cribl_version: Cribl version string (e.g., "4.5.2")

        Returns:
            List of rules applicable to the version
        """
        try:
            version = parse_version(cribl_version)
        except Exception as e:
            log.warning("version_parse_failed", version=cribl_version, error=str(e))
            # If version parsing fails, return all rules
            return rules

        filtered = []
        for rule in rules:
            # Check minimum version
            if rule.cribl_version_min:
                try:
                    min_version = parse_version(rule.cribl_version_min)
                    if version < min_version:
                        continue
                except Exception:
                    pass

            # Check maximum version
            if rule.cribl_version_max:
                try:
                    max_version = parse_version(rule.cribl_version_max)
                    if version > max_version:
                        continue
                except Exception:
                    pass

            filtered.append(rule)

        log.debug(
            "rules_filtered_by_version",
            total=len(rules),
            filtered=len(filtered),
            version=cribl_version
        )
        return filtered

    def filter_by_category(
        self,
        rules: List[BestPracticeRule],
        categories: List[str]
    ) -> List[BestPracticeRule]:
        """
        Filter rules by category.

        Args:
            rules: List of rules to filter
            categories: List of categories to include

        Returns:
            List of rules matching any of the categories
        """
        filtered = [r for r in rules if r.category in categories]

        log.debug(
            "rules_filtered_by_category",
            total=len(rules),
            filtered=len(filtered),
            categories=categories
        )
        return filtered

    def filter_enabled_only(self, rules: List[BestPracticeRule]) -> List[BestPracticeRule]:
        """
        Filter to only enabled rules.

        Args:
            rules: List of rules to filter

        Returns:
            List of enabled rules
        """
        return [r for r in rules if r.enabled]


class RuleEvaluator:
    """
    Evaluates best practice rules against configurations.

    Example:
        >>> evaluator = RuleEvaluator()
        >>> violated = evaluator.evaluate_rule(rule, pipeline_config)
    """

    def evaluate_rule(
        self,
        rule: BestPracticeRule,
        config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Evaluate a single rule against a configuration.

        Args:
            rule: Rule to evaluate
            config: Configuration to check
            context: Additional context (metrics, relationships, etc.)

        Returns:
            True if rule is violated, False if passed
        """
        if not rule.enabled:
            return False

        try:
            if rule.check_type == "config_pattern":
                return self.evaluate_config_pattern(rule, config)
            elif rule.check_type == "metric_threshold":
                metrics = context.get("metrics", {}) if context else {}
                return self.evaluate_metric_threshold(rule, metrics)
            elif rule.check_type == "relationship":
                return self.evaluate_relationship(rule, config, context or {})
            else:
                log.warning("unknown_check_type", rule_id=rule.id, check_type=rule.check_type)
                return False

        except Exception as e:
            log.error(
                "rule_evaluation_failed",
                rule_id=rule.id,
                error=str(e)
            )
            # Fail safe: don't report violations on evaluation errors
            return False

    def evaluate_config_pattern(
        self,
        rule: BestPracticeRule,
        config: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a config_pattern rule.

        Uses simple pattern matching on configuration fields.

        Args:
            rule: Rule with check_type="config_pattern"
            config: Configuration dictionary

        Returns:
            True if pattern indicates violation
        """
        validation_logic = rule.validation_logic

        # Simple keyword-based evaluation
        # For Phase 2A, we use basic checks. Can expand to JSONPath later.

        # Check for field existence patterns
        if "exists:" in validation_logic:
            # Format: "exists:field.path"
            field_path = validation_logic.split("exists:", 1)[1].strip()
            return not self._field_exists(config, field_path)

        # Check for value patterns
        if "equals:" in validation_logic:
            # Format: "field.path equals: value"
            parts = validation_logic.split("equals:")
            if len(parts) == 2:
                field_path = parts[0].strip()
                expected_value = parts[1].strip().strip('"\'')
                actual_value = self._get_field(config, field_path)
                return str(actual_value) != expected_value

        # Check for regex patterns
        if "matches:" in validation_logic:
            # Format: "field.path matches: regex_pattern"
            parts = validation_logic.split("matches:")
            if len(parts) == 2:
                field_path = parts[0].strip()
                pattern = parts[1].strip().strip('"\'')
                value = self._get_field(config, field_path)
                if value:
                    return not bool(re.search(pattern, str(value)))
                return True  # No value = violation

        # Fallback: return False (no violation)
        log.debug(
            "config_pattern_not_evaluated",
            rule_id=rule.id,
            validation_logic=validation_logic
        )
        return False

    def evaluate_metric_threshold(
        self,
        rule: BestPracticeRule,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a metric_threshold rule.

        Args:
            rule: Rule with check_type="metric_threshold"
            metrics: Metrics dictionary

        Returns:
            True if threshold exceeded (violation)
        """
        validation_logic = rule.validation_logic

        # Format: "metric.path > 80" or "metric.path < 10"
        for operator in [">", "<", ">=", "<=", "==", "!="]:
            if operator in validation_logic:
                parts = validation_logic.split(operator)
                if len(parts) == 2:
                    metric_path = parts[0].strip()
                    threshold = float(parts[1].strip())
                    metric_value = self._get_field(metrics, metric_path)

                    if metric_value is None:
                        return False  # No metric = no violation

                    try:
                        metric_value = float(metric_value)

                        if operator == ">":
                            return metric_value > threshold
                        elif operator == "<":
                            return metric_value < threshold
                        elif operator == ">=":
                            return metric_value >= threshold
                        elif operator == "<=":
                            return metric_value <= threshold
                        elif operator == "==":
                            return metric_value == threshold
                        elif operator == "!=":
                            return metric_value != threshold
                    except (ValueError, TypeError):
                        return False

        return False

    def evaluate_relationship(
        self,
        rule: BestPracticeRule,
        config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a relationship rule.

        Checks relationships between configurations (e.g., orphaned references).

        Args:
            rule: Rule with check_type="relationship"
            config: Configuration to check
            context: Related configurations

        Returns:
            True if relationship violation detected
        """
        validation_logic = rule.validation_logic

        # Format: "references:pipelines"
        if "references:" in validation_logic:
            ref_type = validation_logic.split("references:", 1)[1].strip()
            pipeline_ref = config.get("pipeline")

            if ref_type == "pipelines" and pipeline_ref:
                all_pipelines = context.get("pipelines", [])
                pipeline_ids = [p.get("id") for p in all_pipelines]
                return pipeline_ref not in pipeline_ids

        return False

    def _field_exists(self, obj: Dict[str, Any], path: str) -> bool:
        """
        Check if a nested field exists.

        Args:
            obj: Dictionary to search
            path: Dot-separated path (e.g., "conf.functions.0.id")

        Returns:
            True if field exists
        """
        try:
            value = self._get_field(obj, path)
            return value is not None
        except Exception:
            return False

    def _get_field(self, obj: Dict[str, Any], path: str) -> Any:
        """
        Get a nested field value.

        Args:
            obj: Dictionary to search
            path: Dot-separated path

        Returns:
            Field value or None if not found
        """
        if not path:
            return obj

        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if 0 <= index < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current
