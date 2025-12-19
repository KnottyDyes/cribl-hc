# Best Practice Rules System

**Phase 2A: Rule-Based Architecture** provides a configuration-driven validation system for Cribl Stream and Edge deployments. Rules are defined in YAML format and automatically evaluated during configuration analysis.

## Overview

The rule system consists of three main components:

1. **Rule Loader** (`RuleLoader`): Loads rules from YAML files, supports version filtering, category filtering, and caching
2. **Rule Evaluator** (`RuleEvaluator`): Evaluates configurations against rules using pattern matching and threshold checks
3. **Rule Database** (`cribl_rules.yaml`): Contains 30+ best practice rules covering security, performance, reliability, and configuration quality

## Rule Structure

Each rule in `src/cribl_hc/rules/cribl_rules.yaml` has the following structure:

```yaml
- id: rule-perf-filter-early
  name: "Filtering should occur early in pipeline"
  category: performance
  description: "Pipeline does not start with filtering/sampling functions"
  rationale: "Early filtering reduces data volume processed by downstream functions, improving throughput by 20-50%"
  check_type: config_pattern
  validation_logic: "functions.0.id matches: ^(drop|sampling|aggreg|eval)"
  severity_if_violated: low
  documentation_link: "https://docs.cribl.io/stream/pipelines-performance"
  cribl_version_min: "4.0.0"
  cribl_version_max: null
  enabled: true
```

### Required Fields

- **id**: Unique identifier (e.g., `rule-perf-filter-early`)
- **name**: Human-readable name
- **category**: One of `performance`, `security`, `reliability`, `best_practice`
- **description**: What the rule checks
- **rationale**: Why this matters (user-facing explanation)
- **check_type**: One of `config_pattern`, `metric_threshold`, `relationship`
- **validation_logic**: Expression to evaluate (see Validation Logic section)
- **severity_if_violated**: One of `critical`, `high`, `medium`, `low`
- **documentation_link**: URL to Cribl documentation
- **enabled**: `true` or `false`

### Optional Fields

- **cribl_version_min**: Minimum Cribl version (e.g., `"4.0.0"`)
- **cribl_version_max**: Maximum Cribl version (e.g., `"5.0.0"`)

## Check Types

### 1. config_pattern

Checks configuration structure and values using pattern matching.

**Supported Patterns:**

#### Existence Checks
```yaml
validation_logic: "exists:field_name"
validation_logic: "output exists: output"
```
- **Returns violation if**: Field does NOT exist
- **Example**: `"output exists: output"` checks if route has an output field

#### Equality Checks
```yaml
validation_logic: "field_name equals: expected_value"
```
- **Returns violation if**: Field value does NOT equal expected value
- **Example**: `"function.id equals: regex"` checks if function ID is "regex"

#### Regex Pattern Matching
```yaml
validation_logic: "field_name matches: regex_pattern"
```
- **Returns violation if**: Field value does NOT match regex
- **Example**: `"functions.0.id matches: ^(drop|sampling)"` checks if first function is drop or sampling

#### Negative Regex Matching
```yaml
validation_logic: "field_name not_matches: regex_pattern"
```
- **Returns violation if**: Field value DOES match regex
- **Example**: `"id not_matches: ^(pipeline|test|temp)"` flags generic pipeline names

#### Numeric Comparisons
```yaml
validation_logic: "field_name > threshold"
validation_logic: "field_name < threshold"
validation_logic: "field_name >= threshold"
validation_logic: "field_name <= threshold"
validation_logic: "field_name == threshold"
```
- **Returns violation if**: Comparison evaluates to TRUE
- **Example**: `"functions.length > 15"` flags pipelines with more than 15 functions

#### Special: Array Length
```yaml
validation_logic: "array_field.length > 10"
```
- **Returns violation if**: Array length exceeds threshold
- **Example**: `"functions.length > 15"` checks pipeline function count

#### Special: Regex Count
```yaml
validation_logic: "regex_count <= 2"
```
- **Returns violation if**: Count of regex-based functions exceeds threshold
- **Example**: `"regex_count <= 2"` limits regex operations per pipeline

### 2. metric_threshold

Checks numeric metrics against thresholds.

```yaml
check_type: metric_threshold
validation_logic: "cpu.usage > 80"
```

- **Returns violation if**: Threshold condition is TRUE
- **Example**: `"cpu.usage > 80"` flags high CPU usage
- **Supported operators**: `>`, `<`, `>=`, `<=`, `==`

### 3. relationship

Checks cross-component relationships (e.g., orphaned references).

```yaml
check_type: relationship
validation_logic: "references:pipelines"
```

- **Returns violation if**: Referenced resource doesn't exist
- **Example**: `"references:pipelines"` checks if route references a valid pipeline
- **Format**: `references:<resource_type>` where resource_type is `pipelines`, `routes`, `inputs`, or `outputs`

## Validation Logic Syntax

### Nested Field Access

Use dot notation to access nested fields:

```yaml
# Access nested object
validation_logic: "conf.functions.0.id equals: eval"

# Access array element
validation_logic: "functions.0.id matches: ^drop"

# Access array length
validation_logic: "functions.length > 10"
```

### Field Path Resolution

The evaluator supports:
- **Nested objects**: `"level1.level2.level3"`
- **Array indices**: `"array.0"`, `"functions.1.id"`
- **Array length**: `"array.length"`

## Rule Categories

### performance

Rules that optimize data throughput and processing efficiency.

**Examples:**
- Early filtering detection
- Excessive regex operations
- Pipeline length limits
- Function ordering

### security

Rules that prevent security vulnerabilities and ensure compliance.

**Examples:**
- Hardcoded credentials detection
- Unencrypted connections
- PII field masking
- TLS version validation

### reliability

Rules that prevent data loss and ensure correct routing.

**Examples:**
- Orphaned route references
- Missing output destinations
- Missing filter expressions

### best_practice

Rules that improve maintainability and operational quality.

**Examples:**
- Pipeline complexity limits
- Clear naming conventions
- Configuration consolidation

## Version Filtering

Rules can be filtered by Cribl version using semantic versioning:

```yaml
cribl_version_min: "4.0.0"   # Only evaluate for v4.0.0+
cribl_version_max: "5.0.0"   # Only evaluate for v5.0.0 and below
```

The rule loader uses Python's `packaging.version` library for version comparisons.

## Creating Custom Rules

### Step 1: Define the Rule

Add a new rule to `src/cribl_hc/rules/cribl_rules.yaml`:

```yaml
- id: rule-custom-my-check
  name: "My Custom Check"
  category: best_practice
  description: "Pipeline should have a description field"
  rationale: "Descriptions improve team collaboration and maintainability"
  check_type: config_pattern
  validation_logic: "description exists: description"
  severity_if_violated: low
  documentation_link: "https://docs.cribl.io/stream/pipelines"
  enabled: true
```

### Step 2: Test the Rule

The rule will be automatically loaded and evaluated during the next analysis. You can verify it works by:

1. Running the full test suite: `pytest tests/unit/test_rules/`
2. Running a real analysis: `cribl-hc analyze config --url <cribl-url>`

### Step 3: Write a Unit Test (Optional)

Add a test to `tests/unit/test_rules/test_loader.py`:

```python
def test_evaluate_my_custom_check():
    """Test custom rule for pipeline descriptions."""
    evaluator = RuleEvaluator()

    rule = BestPracticeRule(
        id="rule-custom-my-check",
        name="My Custom Check",
        category="best_practice",
        check_type="config_pattern",
        validation_logic="description exists: description",
        severity_if_violated="low",
        enabled=True
    )

    # Pipeline without description - should violate
    config_no_desc = {"id": "my-pipeline", "functions": []}
    assert evaluator.evaluate_rule(rule, config_no_desc) is True

    # Pipeline with description - should not violate
    config_with_desc = {"id": "my-pipeline", "description": "My pipeline", "functions": []}
    assert evaluator.evaluate_rule(rule, config_with_desc) is False
```

## Rule Evaluation Flow

1. **Load Rules**: `RuleLoader.load_all_rules()` loads all rules from YAML
2. **Filter by Version**: Only rules applicable to the detected Cribl version are evaluated
3. **Filter by Enabled**: Only `enabled: true` rules are evaluated
4. **Evaluate by Type**:
   - Pipelines: Evaluated against `performance` and `best_practice` rules
   - Functions: Evaluated for deprecated function checks
   - Routes: Evaluated against `relationship` rules
   - Outputs: Evaluated against `security` rules
5. **Generate Findings**: Violations are converted to Finding objects with:
   - Unique ID: `{rule.id}-{component_id}`
   - Severity: From rule definition
   - Description: Combines rule description and rationale
   - Remediation: Auto-generated from rule metadata

## Example Rules

### Performance Rule

```yaml
- id: rule-perf-limit-regex
  name: "Excessive regex operations in pipeline"
  category: performance
  description: "Pipeline contains more than 2 regex-based functions"
  rationale: "Regex operations are computationally expensive and can reduce throughput by 50%+. Consider using structured parsing or field extraction functions"
  check_type: config_pattern
  validation_logic: "regex_count <= 2"
  severity_if_violated: medium
  documentation_link: "https://docs.cribl.io/stream/performance-tuning"
  cribl_version_min: "4.0.0"
  enabled: true
```

### Security Rule

```yaml
- id: rule-sec-pii-field-masking
  name: "PII field should be masked"
  category: security
  description: "Pipeline contains PII fields without masking"
  rationale: "Sensitive PII data (SSN, credit card, phone numbers, email) should be masked or redacted to prevent data leakage and ensure compliance with privacy regulations"
  check_type: config_pattern
  validation_logic: "field_name not_matches: (ssn|social_security|credit_card|cc_number|phone|email|passport|driver_license|dob|date_of_birth)"
  severity_if_violated: high
  documentation_link: "https://docs.cribl.io/stream/mask-function"
  cribl_version_min: "4.0.0"
  enabled: true
```

### Reliability Rule

```yaml
- id: rule-rel-route-output-required
  name: "Route missing output destination"
  category: reliability
  description: "Route does not specify an output destination"
  rationale: "Routes without outputs will drop events. Ensure all routes have valid output configurations"
  check_type: config_pattern
  validation_logic: "output exists: output"
  severity_if_violated: high
  documentation_link: "https://docs.cribl.io/stream/routes"
  enabled: true
```

### Relationship Rule

```yaml
- id: rule-rel-no-orphaned-routes
  name: "Route references non-existent pipeline"
  category: reliability
  description: "Route references a pipeline that doesn't exist"
  rationale: "Orphaned routes will fail at runtime. Ensure all referenced pipelines exist"
  check_type: relationship
  validation_logic: "references:pipelines"
  severity_if_violated: high
  documentation_link: "https://docs.cribl.io/stream/routes"
  enabled: false  # Example - currently disabled
```

## Disabling Rules

To disable a rule, set `enabled: false` in the YAML:

```yaml
- id: rule-perf-pipeline-length
  name: "Pipeline has too many functions"
  # ... other fields ...
  enabled: false  # Disabled
```

Disabled rules are automatically filtered out during rule loading and will not be evaluated.

## Integration with ConfigAnalyzer

The rule system is automatically integrated into the ConfigAnalyzer:

```python
# In ConfigAnalyzer.__init__()
self.rule_loader = RuleLoader()
self.rule_evaluator = RuleEvaluator()
self._rules_cache = None

# During analysis
self._evaluate_best_practice_rules(pipelines, routes, inputs, outputs, result)
```

Rule violations are converted to Finding objects and included in the analysis results alongside other validation findings.

## Testing

The rule system has comprehensive test coverage:

- **27 unit tests** covering all rule evaluation logic
- **75% code coverage** for the rule loader module
- **Integration tests** with ConfigAnalyzer

Run tests:
```bash
# Test rule system only
pytest tests/unit/test_rules/

# Test rule integration with ConfigAnalyzer
pytest tests/unit/test_analyzers/test_config.py

# Run all tests
pytest tests/
```

## Best Practices for Rule Authors

1. **Clear Rationale**: Always provide a user-facing explanation of WHY the rule matters
2. **Actionable Descriptions**: Describe WHAT the rule checks in simple terms
3. **Documentation Links**: Always link to official Cribl documentation
4. **Appropriate Severity**:
   - `critical`: Data loss, security breach, or system failure
   - `high`: Significant performance degradation or compliance violation
   - `medium`: Moderate impact on performance or maintainability
   - `low`: Minor optimization or best practice suggestion
5. **Version Awareness**: Use `cribl_version_min`/`max` for version-specific rules
6. **Test Your Rules**: Write unit tests to verify rule logic
7. **Conservative Thresholds**: Start with relaxed thresholds and tighten based on user feedback

## Troubleshooting

### Rule Not Evaluating

1. Check `enabled: true` in YAML
2. Verify rule category matches evaluation context (e.g., `performance` rules evaluate against pipelines)
3. Check version filters (`cribl_version_min`/`max`)
4. Review logs for rule parsing errors

### Unexpected Violations

1. Test the validation logic manually using the RuleEvaluator
2. Check field paths match your configuration structure
3. Verify regex patterns are correct (use `not_matches` for negation)
4. Review operator logic (remember: violation = threshold condition TRUE)

### Performance Issues

1. Disable expensive rules (`enabled: false`)
2. Reduce rule count by category
3. Use more specific field paths to reduce evaluation scope

## Future Enhancements

Potential improvements for future phases:

- **Custom Rule Files**: Load rules from user-provided YAML files
- **Rule Priorities**: Evaluate critical rules first
- **Rule Dependencies**: Skip dependent rules if parent fails
- **Dynamic Thresholds**: Adjust thresholds based on deployment size
- **Rule Templates**: Reusable rule patterns
- **Rule Testing Framework**: Interactive rule testing tool

## API Reference

### RuleLoader

```python
from cribl_hc.rules import RuleLoader

loader = RuleLoader(rules_dir=Path("custom/rules"))

# Load all rules
all_rules = loader.load_all_rules(cache=True)

# Filter by version
rules_v4 = loader.filter_by_version(all_rules, "4.5.0")

# Filter by category
perf_rules = loader.filter_by_category(all_rules, ["performance"])

# Filter enabled only
enabled_rules = loader.filter_enabled_only(all_rules)
```

### RuleEvaluator

```python
from cribl_hc.rules import RuleEvaluator
from cribl_hc.models.rule import BestPracticeRule

evaluator = RuleEvaluator()

rule = BestPracticeRule(
    id="my-rule",
    name="My Rule",
    category="performance",
    check_type="config_pattern",
    validation_logic="functions.length > 10",
    severity_if_violated="medium",
    enabled=True
)

config = {"id": "my-pipeline", "functions": [...]}  # 15 functions
context = {"pipelines": [...], "routes": [...]}

# Returns True if violated
violated = evaluator.evaluate_rule(rule, config, context)
```

## Support

For questions or issues with the rule system:

1. Check this documentation
2. Review existing rules in `src/cribl_hc/rules/cribl_rules.yaml`
3. Examine test examples in `tests/unit/test_rules/test_loader.py`
4. File an issue: [GitHub Issues](https://github.com/cribl/health-check/issues)

---

**Last Updated**: 2025-12-18 | **Phase**: 2A Complete | **Rules Count**: 30+ | **Test Coverage**: 75%
