# Documentation Monitor Agent

**Type**: Background Agent  
**Trigger**: After code changes, before PR creation, on-demand  
**Purpose**: Continuously monitor codebase-documentation alignment

---

## Agent Specification

This agent runs in the background to detect documentation drift and alert the primary agent when updates are needed.

## When to Spawn This Agent

The primary agent should spawn a `doc-monitor` background task when:

1. **After implementing features** - Run after any code changes to analyzers, CLI, or API
2. **Before creating PRs** - Verify docs are complete before `gh pr create`
3. **On explicit request** - User asks to check documentation
4. **Periodic audit** - At session start on large codebases

## Agent Prompt Template

```
You are the Documentation Monitor Agent for the cribl-hc project.

TASK: Scan the codebase and verify all features are documented.

SCAN TARGETS:
1. Analyzers: src/cribl_hc/analyzers/*.py (classes ending in "Analyzer")
2. CLI Commands: src/cribl_hc/cli/*.py (@app.command decorators)
3. API Endpoints: src/cribl_hc/api/*.py (router.get/post/etc)

DOCUMENTATION LOCATIONS:
- README.md: Feature overview, analyzer count, usage examples
- docs/ANALYZERS.md: Complete analyzer reference
- docs/CLI_GUIDE.md: CLI command documentation
- docs/API_REFERENCE.md: API endpoint documentation

VALIDATION RULES:
1. Every analyzer class must be mentioned in README.md
2. Analyzer count in README must match actual count
3. Every CLI command must have an entry in CLI_GUIDE.md
4. Every API endpoint must be documented with method + path

OUTPUT FORMAT:
Return a JSON object:
{
  "status": "ok" | "drift_detected",
  "features_found": {
    "analyzers": ["HealthAnalyzer", "ConfigAnalyzer", ...],
    "cli_commands": ["analyze", "config", ...],
    "api_endpoints": ["GET /health", "POST /analyze", ...]
  },
  "documented": [...],
  "missing": [...],
  "outdated": [...],
  "recommended_actions": [
    {"file": "README.md", "action": "Update analyzer count from 17 to 19"},
    {"file": "docs/ANALYZERS.md", "action": "Add AlertingAnalyzer entry"}
  ]
}

DO NOT modify any files. Only report findings.
```

## Integration with Primary Agent

### Spawning the Monitor

```python
# In primary agent workflow, after code changes:
background_task(
    agent="explore",
    prompt=DOC_MONITOR_PROMPT,
    description="Check documentation sync"
)
```

### Handling Results

When the background task completes:

```python
result = background_output(task_id=doc_monitor_task_id)

if result["status"] == "drift_detected":
    # Alert user and offer to fix
    print(f"Documentation drift detected: {len(result['missing'])} features undocumented")
    
    # Option 1: Auto-fix
    for action in result["recommended_actions"]:
        # Apply fixes to documentation files
        
    # Option 2: Add to TODO list
    for missing in result["missing"]:
        todowrite(f"Document {missing} in appropriate doc file")
```

## Workflow Integration Points

### 1. Post-Implementation Hook

After any implementation task completes:

```
[Implementation complete]
     ↓
[Spawn doc-monitor agent]
     ↓
[Check results]
     ↓
[If drift: update docs before marking complete]
```

### 2. Pre-PR Hook

Before creating a pull request:

```
[User requests PR]
     ↓
[Spawn doc-monitor agent]
     ↓
[If drift: BLOCK PR, fix docs first]
     ↓
[Create PR with complete docs]
```

### 3. Session Start Audit

At the start of a coding session:

```
[Session starts]
     ↓
[Spawn doc-monitor agent (background)]
     ↓
[Continue with user tasks]
     ↓
[When results ready: notify if issues found]
```

## Example Scenarios

### Scenario 1: New Analyzer Added

```
User: "Add a new MemoryAnalyzer that checks memory usage patterns"

Agent Actions:
1. Create src/cribl_hc/analyzers/memory.py
2. Register in __init__.py
3. [SPAWN doc-monitor]
4. Monitor returns: {"missing": ["MemoryAnalyzer"]}
5. Update README.md with new analyzer
6. Update docs/ANALYZERS.md with full entry
7. [RE-SPAWN doc-monitor to verify]
8. Monitor returns: {"status": "ok"}
9. Complete task
```

### Scenario 2: PR Creation

```
User: "Create a PR for my changes"

Agent Actions:
1. [SPAWN doc-monitor]
2. Monitor returns: {"missing": ["AlertingAnalyzer"], "outdated": ["analyzer count"]}
3. Agent: "I found documentation issues. Fixing before PR..."
4. Update docs
5. [RE-SPAWN doc-monitor to verify]
6. Monitor returns: {"status": "ok"}
7. Create PR
```

### Scenario 3: Audit Request

```
User: "Check if our docs are up to date"

Agent Actions:
1. [SPAWN doc-monitor]
2. Present full report to user
3. Offer to fix issues
```

## Configuration

### Feature Detection Patterns

```yaml
analyzers:
  path: "src/cribl_hc/analyzers/*.py"
  pattern: "class (\\w+Analyzer)"
  exclude: ["BaseAnalyzer"]
  
cli_commands:
  path: "src/cribl_hc/cli/*.py"
  pattern: "@(app|cli)\\.command"
  
api_endpoints:
  path: "src/cribl_hc/api/*.py"
  pattern: "@?router\\.(get|post|put|delete|patch)"
```

### Documentation Mapping

```yaml
README.md:
  - analyzer_count: "\\d+ analyzer"
  - feature_list: "## Features" section
  
docs/ANALYZERS.md:
  - full_reference: complete analyzer list
  
docs/CLI_GUIDE.md:
  - command_docs: all commands with examples
  
docs/API_REFERENCE.md:
  - endpoint_docs: all endpoints with schemas
```

## Error Handling

If the agent encounters issues:

1. **File not found**: Report which expected files are missing
2. **Parse error**: Report file and continue with others
3. **Ambiguous match**: Flag for human review

## Performance Notes

- Agent runs quickly (< 10 seconds typically)
- Can run in background without blocking user
- Results are cached for session duration
- Re-runs only when code files change
