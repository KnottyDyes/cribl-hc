# /docs.sync - Documentation Synchronization Skill

**Description**: Scan codebase for features and ensure documentation is accurate and complete.

**Scope**: project

---

## Command Instructions

When the user invokes `/docs.sync`, perform a comprehensive documentation audit and update.

## Execution Flow

### Phase 1: Feature Discovery

Scan the codebase for all documentable features:

#### 1.1 Analyzers
```bash
# Find all analyzer classes
grep -r "class.*Analyzer" src/cribl_hc/analyzers/*.py | grep -v "BaseAnalyzer"
```

For each analyzer, extract:
- Class name (e.g., `HealthAnalyzer`)
- Objective name (from `objective_name` property)
- Supported products (from `supported_products` property)
- Docstring (first line)

#### 1.2 CLI Commands
```bash
# Find all CLI commands
grep -r "@app.command\|@cli.command" src/cribl_hc/cli/*.py
```

For each command, extract:
- Command name
- Help text
- Options/arguments

#### 1.3 API Endpoints
```bash
# Find all API endpoints
grep -r "router.get\|router.post\|router.put\|router.delete\|@app.get\|@app.post" src/cribl_hc/api/*.py
```

For each endpoint, extract:
- HTTP method
- Path
- Function name

### Phase 2: Documentation Audit

Check each feature against documentation:

#### 2.1 README.md Checks
- [ ] Analyzer count matches actual count
- [ ] All analyzers listed in features section
- [ ] CLI commands have usage examples
- [ ] Product support table is accurate

#### 2.2 docs/ANALYZERS.md Checks
- [ ] All analyzers are listed
- [ ] Objectives are documented
- [ ] Supported products are listed
- [ ] Categories are correct

#### 2.3 docs/CLI_GUIDE.md Checks
- [ ] All commands documented
- [ ] Options/flags documented
- [ ] Examples provided

#### 2.4 docs/API_REFERENCE.md Checks
- [ ] All endpoints documented
- [ ] Request/response schemas included
- [ ] Example curl commands provided

### Phase 3: Generate Report

Output a summary:

```markdown
## Documentation Sync Report

### Features Found
- Analyzers: [count]
- CLI Commands: [count]  
- API Endpoints: [count]

### Documentation Status

#### ✅ Documented
[List features that are properly documented]

#### ❌ Missing Documentation
[List features missing from docs with specific locations to update]

#### ⚠️ Outdated Documentation
[List docs that need updating - wrong counts, changed APIs, etc.]

### Recommended Actions
1. [Specific action with file path]
2. [Specific action with file path]
...
```

### Phase 4: Auto-Fix (if user confirms)

If documentation issues are found, ask:

> I found [N] documentation issues. Would you like me to:
> 1. **Fix automatically** - Update docs with discovered features
> 2. **Show details** - List exactly what needs to change
> 3. **Skip** - I'll fix it manually later

If user chooses "Fix automatically":

1. **Update README.md**:
   - Fix analyzer count
   - Add missing feature mentions

2. **Update/Create docs/ANALYZERS.md**:
   ```markdown
   # Analyzers Reference
   
   ## Overview
   Total: [count] analyzers
   
   ## By Category
   
   ### Health
   | Analyzer | Objective | Products | Description |
   |----------|-----------|----------|-------------|
   | HealthAnalyzer | health | stream, edge | Overall health assessment |
   ...
   
   ### Configuration
   ...
   ```

3. **Update docs/CLI_GUIDE.md** if needed

4. **Update docs/API_REFERENCE.md** if needed

### Phase 5: Verification

After updates, re-run audit to confirm:
- All features documented
- Counts are accurate
- No broken references

## Output Format

Always output:
1. Discovery summary (what was found)
2. Audit results (what's documented vs missing)
3. Actions taken or recommended
4. Verification status

## Example Invocation

User: `/docs.sync`

Agent Response:
```
## Documentation Sync Report

### Scanning Codebase...
Found:
- 19 analyzers in src/cribl_hc/analyzers/
- 8 CLI commands in src/cribl_hc/cli/
- 5 API endpoints in src/cribl_hc/api/

### Audit Results

✅ **Documented (25)**
- HealthAnalyzer ✓ (README, ANALYZERS.md)
- ConfigAnalyzer ✓ (README, ANALYZERS.md)
- `analyze run` command ✓ (CLI_GUIDE.md)
...

❌ **Missing (3)**
- AlertingAnalyzer - Not in README.md
- VersionControlAnalyzer - Not in README.md  
- GET /api/v1/health - Not in API_REFERENCE.md

⚠️ **Outdated (1)**
- README.md says "17 analyzers" but found 19

### Recommended Actions

Would you like me to fix these issues automatically?
```

## Integration with Other Skills

- Run after `/speckit.implement` completes
- Run before creating PRs
- Can be triggered by `/speckit.analyze` for doc quality checks
