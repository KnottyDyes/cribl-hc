---
name: commit-safety
description: Pre-commit safety check - validates ignore files and scans for sensitive data before commits
version: 1.0.0
author: cribl-hc
tags: [security, git, pre-commit, safety]
---

# Commit Safety Skill

**Purpose**: Ensure .gitignore, .dockerignore, and other ignore files are comprehensive and prevent accidental commits of sensitive development artifacts, credentials, logs, cache files, and documentation.

**Trigger**: Automatically run before git commit operations or manually via `/commit-safety check`

## Core Functionality

### 1. Sensitive File Detection
Scans the repository for files that should never be committed:
- API keys, tokens, passwords in config files
- Private keys (*.pem, *.key, *.p12)
- Environment files (.env*)
- Log files (*.log, logs/*)
- Cache directories (__pycache__/, node_modules/, .cache/)
- IDE/editor files (.vscode/, .idea/, *.swp, *.swo)
- OS files (.DS_Store, Thumbs.db)
- Database files (*.db, *.sqlite, *.sql with sensitive data)
- Test coverage reports (htmlcov/, .coverage)
- Build artifacts (dist/, build/, *.egg-info/)

### 2. .gitignore Validation
Checks that .gitignore contains essential patterns:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Environment
.env
.env.*
.venv/
venv/
ENV/

# IDE/Editor
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/
log/

# Database
*.db
*.sqlite
*.sqlite3

# Keys/Credentials
*.pem
*.key
*.p12
*.pfx
secrets/
credentials/

# Documentation (selective)
/docs/  # Only if docs shouldn't be in repo
development/
plans/
```

### 3. .dockerignore Validation
Ensures Docker builds are clean:
```
# Dependencies
node_modules/
__pycache__/
*.pyc

# Environment
.env*
.venv/
venv/

# IDE/Editor
.vscode/
.idea/

# OS
.DS_Store

# Git
.git/
.gitignore

# Testing
.pytest_cache/
.coverage
htmlcov/
tests/

# Documentation
docs/
development/
plans/
README.md  # Keep in image if needed

# Build artifacts
dist/
build/
*.egg-info/
```

### 4. Development Artifact Scan
Looks for common development files that indicate incomplete cleanup:
- Development notes, TODO files
- Debug/test scripts
- Local configuration overrides
- Temporary files

### 5. Auto-Fix Suggestions
When issues are found, provides specific remediation:
- Add missing patterns to .gitignore
- Add missing patterns to .dockerignore
- Suggest file removals or moves
- Generate updated ignore files

## Usage Examples

### Manual Check
```
/commit-safety check
```

### Pre-commit Hook Integration
Add to pre-commit hooks:
```bash
# In .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: commit-safety
        name: Commit Safety Check
        entry: python -m cribl_hc.cli commit-safety check
        language: system
        pass_filenames: false
```

### CI Integration
```yaml
# In GitHub Actions
- name: Commit Safety Check
  run: python -m cribl_hc.cli commit-safety check
```

## Configuration

### Default Scan Patterns
The skill includes built-in patterns for common sensitive files and development artifacts. These can be extended via configuration.

### Custom Ignore Rules
Add project-specific rules in `.specify/commit-safety-rules.yaml`:
```yaml
custom_patterns:
  - pattern: "*.custom"
    reason: "Custom sensitive files"
  - pattern: "secrets/"
    reason: "Project secrets directory"

exclude_paths:
  - "test/fixtures/"  # Allow sensitive test data
  - "docs/examples/"  # Allow example configs
```

## Output Format

### Success
```
✅ Commit Safety Check Passed
- .gitignore: Complete (42 patterns)
- .dockerignore: Complete (28 patterns)
- No sensitive files detected
- No development artifacts found
```

### Issues Found
```
⚠️  Commit Safety Issues Detected

🚨 Sensitive Files Found:
  - config/secrets.json (contains API keys)
  - .env.local (environment variables)

📝 Missing .gitignore Patterns:
  - __pycache__/
  - *.pyc
  - .pytest_cache/

🔧 Auto-fix Suggestions:
  Run: cribl-hc commit-safety fix
  This will:
    - Add missing patterns to .gitignore
    - Move sensitive files to .gitignore
    - Update .dockerignore

❌ Commit BLOCKED - Fix issues before committing
```

## Security Benefits

1. **Credential Protection**: Prevents accidental commits of API keys, tokens, passwords
2. **Clean Builds**: Ensures Docker images don't contain development artifacts
3. **Repository Hygiene**: Keeps repository focused on production code
4. **Compliance**: Helps meet security requirements for sensitive data handling
5. **Team Consistency**: Ensures all team members follow ignore best practices

## Integration Points

- **Git Hooks**: Integrate with pre-commit framework
- **CI/CD**: Add to GitHub Actions, GitLab CI, etc.
- **IDE Integration**: Could be called from VS Code extensions
- **Agent Framework**: Available as `/commit-safety` command in cribl-hc

## Performance

- **Fast Scanning**: Uses git ls-files and efficient pattern matching
- **Incremental**: Only scans changed files in pre-commit mode
- **Caching**: Remembers results to avoid redundant scans
- **Timeout Protection**: Won't block commits indefinitely