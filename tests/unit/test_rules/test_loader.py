"""
Unit tests for rule loader and evaluator.

Tests rule loading from YAML, filtering, and evaluation logic.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from cribl_hc.rules.loader import RuleLoader, RuleEvaluator
from cribl_hc.models.rule import BestPracticeRule


class TestRuleLoader:
    """Test suite for RuleLoader."""

    def test_initialization_default_dir(self):
        """Test loader initializes with default rules directory."""
        loader = RuleLoader()
        assert loader.rules_dir.exists()
        assert loader.rules_dir.name == "rules"

    def test_initialization_custom_dir(self, tmp_path):
        """Test loader initializes with custom directory."""
        custom_dir = tmp_path / "custom_rules"
        custom_dir.mkdir()

        loader = RuleLoader(rules_dir=custom_dir)
        assert loader.rules_dir == custom_dir

    def test_load_rules_from_yaml(self):
        """Test loading rules from the default cribl_rules.yaml."""
        loader = RuleLoader()
        rules = loader.load_rules_from_yaml()

        assert len(rules) > 0
        assert all(isinstance(r, BestPracticeRule) for r in rules)

        # Verify migrated rules exist
        rule_ids = [r.id for r in rules]
        assert "rule-bp-no-deprecated-regex" in rule_ids
        assert "rule-sec-no-hardcoded-password" in rule_ids

    def test_load_rules_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty list."""
        loader = RuleLoader(rules_dir=tmp_path)
        rules = loader.load_rules_from_yaml("nonexistent.yaml")

        assert rules == []

    def test_load_all_rules_with_cache(self):
        """Test load_all_rules caches results."""
        loader = RuleLoader()

        # First load
        rules1 = loader.load_all_rules(cache=True)
        assert len(rules1) > 0

        # Second load should return cached
        rules2 = loader.load_all_rules(cache=True)
        assert rules1 is rules2  # Same object reference

    def test_load_all_rules_without_cache(self):
        """Test load_all_rules without caching."""
        loader = RuleLoader()

        rules1 = loader.load_all_rules(cache=False)
        rules2 = loader.load_all_rules(cache=False)

        assert rules1 is not rules2  # Different objects
        assert len(rules1) == len(rules2)

    def test_filter_by_version_min(self):
        """Test filtering by minimum version."""
        loader = RuleLoader()

        rule = BestPracticeRule(
            id="test-rule-1",
            name="Test Rule",
            category="performance",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="medium",
            documentation_link="https://example.com",
            cribl_version_min="4.5.0",
            enabled=True
        )

        rules = [rule]

        # Version 4.5.0 should include the rule
        filtered = loader.filter_by_version(rules, "4.5.0")
        assert len(filtered) == 1

        # Version 4.4.0 should exclude the rule
        filtered = loader.filter_by_version(rules, "4.4.0")
        assert len(filtered) == 0

    def test_filter_by_version_max(self):
        """Test filtering by maximum version."""
        loader = RuleLoader()

        rule = BestPracticeRule(
            id="test-rule-2",
            name="Test Rule",
            category="performance",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="medium",
            documentation_link="https://example.com",
            cribl_version_max="4.5.0",
            enabled=True
        )

        rules = [rule]

        # Version 4.5.0 should include the rule
        filtered = loader.filter_by_version(rules, "4.5.0")
        assert len(filtered) == 1

        # Version 4.6.0 should exclude the rule
        filtered = loader.filter_by_version(rules, "4.6.0")
        assert len(filtered) == 0

    def test_filter_by_version_invalid(self):
        """Test filtering with invalid version returns all rules."""
        loader = RuleLoader()

        rule = BestPracticeRule(
            id="test-rule-3",
            name="Test Rule",
            category="performance",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="medium",
            documentation_link="https://example.com",
            enabled=True
        )

        rules = [rule]

        # Invalid version should return all rules
        filtered = loader.filter_by_version(rules, "invalid")
        assert len(filtered) == 1

    def test_filter_by_category(self):
        """Test filtering by category."""
        loader = RuleLoader()

        rules = [
            BestPracticeRule(
                id="perf-rule",
                name="Performance Rule",
                category="performance",
                description="Test",
                rationale="Test rationale",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="medium",
                documentation_link="https://example.com",
                enabled=True
            ),
            BestPracticeRule(
                id="sec-rule",
                name="Security Rule",
                category="security",
                description="Test",
                rationale="Test rationale",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="high",
                documentation_link="https://example.com",
                enabled=True
            ),
        ]

        # Filter for performance only
        filtered = loader.filter_by_category(rules, ["performance"])
        assert len(filtered) == 1
        assert filtered[0].id == "perf-rule"

        # Filter for multiple categories
        filtered = loader.filter_by_category(rules, ["performance", "security"])
        assert len(filtered) == 2

    def test_filter_enabled_only(self):
        """Test filtering enabled rules."""
        loader = RuleLoader()

        rules = [
            BestPracticeRule(
                id="enabled-rule",
                name="Enabled Rule",
                category="performance",
                description="Test",
                rationale="Test rationale",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="medium",
                documentation_link="https://example.com",
                enabled=True
            ),
            BestPracticeRule(
                id="disabled-rule",
                name="Disabled Rule",
                category="performance",
                description="Test",
                rationale="Test rationale",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="medium",
                documentation_link="https://example.com",
                enabled=False
            ),
        ]

        filtered = loader.filter_enabled_only(rules)
        assert len(filtered) == 1
        assert filtered[0].id == "enabled-rule"


class TestRuleEvaluator:
    """Test suite for RuleEvaluator."""

    def test_evaluate_disabled_rule(self):
        """Test that disabled rules are not evaluated."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="disabled-rule",
            name="Disabled Rule",
            category="performance",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="medium",
            documentation_link="https://example.com",
            enabled=False
        )

        config = {"test": "value"}
        violated = evaluator.evaluate_rule(rule, config)

        assert violated is False

    def test_evaluate_config_pattern_exists(self):
        """Test config_pattern with exists check."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="exists-rule",
            name="Field Exists Rule",
            category="security",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="exists:password",
            severity_if_violated="high",
            documentation_link="https://example.com",
            enabled=True
        )

        # Config with password field = violation
        config = {"password": "secret123"}
        violated = evaluator.evaluate_rule(rule, config)
        assert violated is False  # Field exists, so no violation

        # Config without password = no violation
        config = {"username": "user"}
        violated = evaluator.evaluate_rule(rule, config)
        assert violated is True  # Field missing, so violation

    def test_evaluate_config_pattern_equals(self):
        """Test config_pattern with equals check."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="equals-rule",
            name="Value Equals Rule",
            category="best_practice",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="status equals: enabled",
            severity_if_violated="medium",
            documentation_link="https://example.com",
            enabled=True
        )

        # Correct value = no violation
        config = {"status": "enabled"}
        violated = evaluator.evaluate_rule(rule, config)
        assert violated is False

        # Wrong value = violation
        config = {"status": "disabled"}
        violated = evaluator.evaluate_rule(rule, config)
        assert violated is True

    def test_evaluate_config_pattern_matches(self):
        """Test config_pattern with regex matches."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="matches-rule",
            name="Regex Match Rule",
            category="security",
            description="Test",
            rationale="Test rationale",
            check_type="config_pattern",
            validation_logic="url matches: ^https://",
            severity_if_violated="medium",
            documentation_link="https://example.com",
            enabled=True
        )

        # HTTPS URL = no violation
        config = {"url": "https://example.com"}
        violated = evaluator.evaluate_rule(rule, config)
        assert violated is False

        # HTTP URL = violation
        config = {"url": "http://example.com"}
        violated = evaluator.evaluate_rule(rule, config)
        assert violated is True

    def test_evaluate_metric_threshold_greater_than(self):
        """Test metric_threshold with > operator."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="threshold-rule",
            name="CPU Threshold",
            category="performance",
            description="Test",
            rationale="Test rationale",
            check_type="metric_threshold",
            validation_logic="cpu.usage > 80",
            severity_if_violated="high",
            documentation_link="https://example.com",
            enabled=True
        )

        metrics = {"cpu": {"usage": 85}}

        # CPU > 80 = violation
        violated = evaluator.evaluate_rule(rule, {}, context={"metrics": metrics})
        assert violated is True

        # CPU <= 80 = no violation
        metrics = {"cpu": {"usage": 75}}
        violated = evaluator.evaluate_rule(rule, {}, context={"metrics": metrics})
        assert violated is False

    def test_evaluate_relationship(self):
        """Test relationship check for orphaned references."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="rel-rule",
            name="Pipeline Reference",
            category="reliability",
            description="Test",
            rationale="Test rationale",
            check_type="relationship",
            validation_logic="references:pipelines",
            severity_if_violated="high",
            documentation_link="https://example.com",
            enabled=True
        )

        # Route references existing pipeline = no violation
        config = {"pipeline": "my-pipeline"}
        context = {
            "pipelines": [
                {"id": "my-pipeline"},
                {"id": "other-pipeline"}
            ]
        }
        violated = evaluator.evaluate_rule(rule, config, context=context)
        assert violated is False

        # Route references non-existent pipeline = violation
        config = {"pipeline": "missing-pipeline"}
        violated = evaluator.evaluate_rule(rule, config, context=context)
        assert violated is True

    def test_field_exists_nested(self):
        """Test _field_exists with nested paths."""
        evaluator = RuleEvaluator()

        config = {
            "conf": {
                "functions": [
                    {"id": "eval", "filter": "true"}
                ]
            }
        }

        # Test nested field access
        assert evaluator._field_exists(config, "conf.functions.0.id") is True
        assert evaluator._field_exists(config, "conf.functions.0.missing") is False
        assert evaluator._field_exists(config, "conf.missing.path") is False

    def test_get_field_nested(self):
        """Test _get_field with nested paths."""
        evaluator = RuleEvaluator()

        config = {
            "level1": {
                "level2": {
                    "level3": "value"
                },
                "array": [1, 2, 3]
            }
        }

        # Test nested object access
        assert evaluator._get_field(config, "level1.level2.level3") == "value"

        # Test array access
        assert evaluator._get_field(config, "level1.array.1") == 2

        # Test missing path
        assert evaluator._get_field(config, "missing.path") is None

    def test_evaluate_pipeline_length(self):
        """Test Phase 2B: Pipeline length check."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="rule-perf-pipeline-length",
            name="Pipeline has too many functions",
            category="performance",
            description="Pipeline contains more than 15 functions",
            rationale="Long pipelines impact performance",
            check_type="config_pattern",
            validation_logic="functions.length > 15",
            severity_if_violated="low",
            documentation_link="https://docs.cribl.io/stream/pipelines",
            enabled=True
        )

        # Pipeline with 16 functions = violation
        config_long = {"functions": [{"id": f"func-{i}"} for i in range(16)]}
        violated = evaluator.evaluate_rule(rule, config_long)
        assert violated is True

        # Pipeline with 10 functions = no violation
        config_short = {"functions": [{"id": f"func-{i}"} for i in range(10)]}
        violated = evaluator.evaluate_rule(rule, config_short)
        assert violated is False

    def test_evaluate_regex_count(self):
        """Test Phase 2B: Regex operation count check."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="rule-perf-limit-regex",
            name="Excessive regex operations",
            category="performance",
            description="Pipeline contains more than 2 regex functions",
            rationale="Regex operations are expensive",
            check_type="config_pattern",
            validation_logic="regex_count <= 2",
            severity_if_violated="medium",
            documentation_link="https://docs.cribl.io/stream/performance-tuning",
            enabled=True
        )

        # Pipeline with 3 regex functions = violation
        config_many_regex = {
            "functions": [
                {"id": "regex_extract-1"},
                {"id": "regex-2"},
                {"id": "regex_replace-3"},
                {"id": "eval-4"}
            ]
        }
        violated = evaluator.evaluate_rule(rule, config_many_regex)
        assert violated is True

        # Pipeline with 2 regex functions = no violation
        config_few_regex = {
            "functions": [
                {"id": "regex_extract-1"},
                {"id": "regex-2"},
                {"id": "eval-3"}
            ]
        }
        violated = evaluator.evaluate_rule(rule, config_few_regex)
        assert violated is False

    def test_evaluate_filter_early(self):
        """Test Phase 2B: Early filtering check."""
        evaluator = RuleEvaluator()

        rule = BestPracticeRule(
            id="rule-perf-filter-early",
            name="Filtering should occur early",
            category="performance",
            description="Pipeline should start with filtering functions",
            rationale="Early filtering improves throughput",
            check_type="config_pattern",
            validation_logic="functions.0.id matches: ^(drop|sampling|aggreg|eval)",
            severity_if_violated="low",
            documentation_link="https://docs.cribl.io/stream/pipelines-performance",
            enabled=True
        )

        # Pipeline starting with eval = no violation
        config_good = {
            "functions": [
                {"id": "eval-1", "filter": "true"},
                {"id": "mask-2"}
            ]
        }
        violated = evaluator.evaluate_rule(rule, config_good)
        assert violated is False

        # Pipeline starting with mask = violation
        config_bad = {
            "functions": [
                {"id": "mask-1"},
                {"id": "eval-2"}
            ]
        }
        violated = evaluator.evaluate_rule(rule, config_bad)
        assert violated is True
