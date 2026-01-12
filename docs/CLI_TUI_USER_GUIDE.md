# Cribl Health Check - CLI & TUI User Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [CLI Reference](#cli-reference)
3. [TUI Guide](#tui-guide)
4. [Common Workflows](#common-workflows)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation
```bash
pip install cribl-hc
```

### First Analysis (30 seconds)
```bash
# 1. Add credentials from curl command
cribl-hc config add-from-curl prod

# 2. Run analysis
cribl-hc analyze run --deployment prod

# 3. View results (or use TUI)
cribl-hc tui
```

---

## CLI Reference

### Credential Management

#### Add Credentials Manually
```bash
cribl-hc config set <name> --url <url> --token <token>

Example:
  cribl-hc config set prod --url https://main-myorg.cribl.cloud --token sk_live_xyz
```

#### Add Credentials from REST Call (NEW!)
```bash
cribl-hc config add-from-curl <name>

# Workflow:
1. Open browser dev tools (F12)
2. Find any API call to Cribl
3. Right-click → Copy as curl
4. Run: cribl-hc config add-from-curl prod
5. Paste curl command when prompted
6. Confirm extracted URL and token

Example:
  $ cribl-hc config add-from-curl production
  Paste curl command or URL: 
  curl -H "Authorization: Bearer sk_live_abc123" https://main-myorg.cribl.cloud/api/v1/...
  
  Extracted URL: https://main-myorg.cribl.cloud
  Extracted Token: ****...****
  Save these credentials? [Y/n]: y
  ✓ Saved credentials for deployment: production
```

#### List Credentials
```bash
cribl-hc config list

Output:
  Stored Deployments
  ┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Name    ┃ URL                    ┃ Token                ┃
  ┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
  │ prod    │ https://main.cribl... │ ****...****          │
  │ dev     │ https://dev.cribl.lo.. │ ****...****          │
  └─────────┴────────────────────────┴──────────────────────┘
```

#### Get Specific Credentials
```bash
cribl-hc config get <name>

Example:
  cribl-hc config get prod
```

#### Delete Credentials
```bash
# Delete single
cribl-hc config delete prod

# Delete all (with confirmation)
cribl-hc config delete '*'

# Delete all without confirmation
cribl-hc config delete '*' --yes
```

#### Export Encryption Key
```bash
cribl-hc config export-key
cribl-hc config export-key --output backup-key.txt
```

### Running Analysis

#### Basic Analysis
```bash
cribl-hc analyze run --deployment <name>

Example:
  cribl-hc analyze run --deployment prod
```

#### Analysis with Specific Objectives
```bash
cribl-hc analyze run --deployment prod --objectives health config security

Available objectives:
  health, config, security, performance, resources, fleet, lake, search, etc.
```

#### Analysis Options
```bash
cribl-hc analyze run --help

Options:
  --deployment TEXT              Deployment name [required]
  --objectives TEXT              Specific objectives to analyze
  --output {json,yaml,table}    Output format (default: table)
  --save                        Save results to file
  --format TEXT                 Output format details
```

### Viewing Results

#### Display Results Table
```bash
cribl-hc analyze run --deployment prod --output table
```

#### Export as JSON
```bash
cribl-hc analyze run --deployment prod --output json > results.json
```

#### Export as YAML
```bash
cribl-hc analyze run --deployment prod --output yaml > results.yaml
```

---

## TUI Guide

### Launch TUI
```bash
cribl-hc tui
```

### Main Menu
```
Cribl Health Check
Interactive Terminal Interface

1. Manage Deployments - Add, edit, delete, or test deployment credentials
2. Run Health Check - Analyze a Cribl deployment
3. View Recent Results - Browse previous analysis results
4. Settings - Configure tool preferences

Q. Quit
```

### 1. Manage Deployments

#### Add New Deployment
```
Steps:
1. Select "1. Manage Deployments"
2. Select "1. Add New Deployment"
3. Enter Deployment ID (e.g., 'prod', 'dev')
4. Choose deployment type (Cloud or Self-Hosted)
5. Paste URL and token (or use REST call extraction)
6. Connection is tested automatically
7. Credentials saved and encrypted
```

#### View Deployments
```
Modern card-based layout showing:
- Deployment name (with 📦 icon)
- URL
- Masked token
- Status (✓ connected or ✗ failed)

Example:
  📦 prod
  URL: https://main-myorg.cribl.cloud
  Token: sk_live...****
  Status: ✓
```

#### Edit Deployment
```
Steps:
1. Select "2. Edit Deployment"
2. Enter deployment ID to edit
3. Update URL (leave blank to keep current)
4. Update token if needed
5. Confirm changes
```

#### Delete Deployments
```
Three deletion modes:

1. SINGLE MODE (Default)
   - Delete one deployment by name
   - Confirmation required

2. MULTIPLE MODE (Interactive Selection) ⭐
   - Prompted for each deployment (y/n)
   - Select specific ones to delete
   - Shows confirmation list
   - Perfect for selective cleanup

3. ALL MODE (Bulk Delete)
   - Delete all credentials at once
   - Shows complete list before confirming
   - Fast cleanup after testing
```

#### Test Connection
```
Steps:
1. Select "4. Test Connection"
2. Enter deployment ID
3. Shows connection status, response time, Cribl version
4. Helps verify credentials before running analysis
```

### 2. Run Health Check

#### Select Deployment
```
Steps:
1. Select "2. Run Health Check"
2. Choose deployment from numbered list or type name
3. Press Enter for default

Supports:
- Number selection: "1" for first deployment
- Name selection: "prod" to select by name
- Default selection: Just press Enter
```

#### Analysis Progress
```
Real-time progress display:

→ Analyzing: Health Check (1/20)
████████░░░░░░░░░░░░░░░░░░░░░░ 25%

→ Analyzing: Configuration (5/20)
██████████████░░░░░░░░░░░░░░░░░ 50%

✓ Analyzing: Security (20/20)
████████████████████████████████ 100%

✓ Analysis completed
Findings: 15
Recommendations: 8
Health Score: 78.5
```

### 3. View Recent Results

**Currently: Coming soon**

Will display:
- Previous analysis results
- Deployment name and date
- Quick status summary
- Option to view detailed results

### 4. Settings

**Currently: Coming soon**

Will allow:
- Default API call limit
- Default objectives to analyze
- Output format preferences
- Logging verbosity

---

## Common Workflows

### Workflow 1: First-Time Setup
```bash
# Step 1: Add credentials using curl from browser
$ cribl-hc config add-from-curl prod

# Step 2: Verify it works
$ cribl-hc config list

# Step 3: Run first analysis
$ cribl-hc analyze run --deployment prod

# Step 4: View results interactively
$ cribl-hc tui
→ Run Health Check
→ Select 'prod'
→ View results in dashboard
```

### Workflow 2: Testing Multiple Deployments
```bash
# Add test deployments quickly
cribl-hc config add-from-curl test-1
cribl-hc config add-from-curl test-2
cribl-hc config add-from-curl test-3

# Run analysis on all
for dep in test-1 test-2 test-3; do
  cribl-hc analyze run --deployment $dep --output json > results-$dep.json
done

# Clean up all test credentials
cribl-hc config delete '*' --yes
```

### Workflow 3: Production Deployment Check
```bash
# Add production credentials
cribl-hc config add-from-curl prod

# Run comprehensive analysis
cribl-hc analyze run --deployment prod

# Save results for documentation
cribl-hc analyze run --deployment prod --output json > prod-analysis.json

# Schedule regular checks (cron)
# 0 2 * * * /usr/local/bin/cribl-hc analyze run --deployment prod --output json >> /var/log/cribl-hc.log
```

### Workflow 4: Multi-Deployment Comparison
```bash
# Add multiple deployments
cribl-hc config add-from-curl prod
cribl-hc config add-from-curl staging
cribl-hc config add-from-curl dev

# Run analysis on all and export
cribl-hc analyze run --deployment prod --output json > prod.json
cribl-hc analyze run --deployment staging --output json > staging.json
cribl-hc analyze run --deployment dev --output json > dev.json

# Compare results
diff prod.json staging.json
diff prod.json dev.json
```

### Workflow 5: Interactive Analysis with TUI
```bash
# Launch interactive TUI
cribl-hc tui

# Navigate to:
# 1. View Deployments (see all credentials with cards)
# 2. Run Health Check (real-time progress)
# 3. View results interactively
```

---

## Troubleshooting

### Connection Issues

**Problem**: "Connection failed" error
```bash
Solution:
1. Verify URL is correct: cribl-hc config get <name>
2. Check token is valid in Cribl Settings
3. Test connection: cribl-hc tui → Manage Deployments → Test Connection
4. Verify network access to Cribl deployment
5. Check firewall/proxy settings
```

**Problem**: "Invalid token"
```bash
Solution:
1. Edit deployment: cribl-hc config delete <name>
2. Re-add with new token: cribl-hc config add-from-curl <name>
3. Generate new token in Cribl Settings → API Tokens
4. Ensure token has required permissions
```

### Credential Issues

**Problem**: "Credentials not found"
```bash
Solution:
1. List saved credentials: cribl-hc config list
2. Add new credentials: cribl-hc config add-from-curl <name>
3. Check ~/.cribl-hc/credentials.enc exists
4. Verify ~/.cribl-hc/.key file exists (encryption key)
```

**Problem**: "Too many test credentials cluttering the list"
```bash
Solution:
Option 1 - Delete all at once:
  cribl-hc config delete '*' --yes

Option 2 - Delete selectively via TUI:
  cribl-hc tui
  → Manage Deployments
  → Delete Deployment
  → Select "multiple" mode
  → Choose which ones to delete
  → Confirm
```

### Analysis Issues

**Problem**: "Analysis runs but finds no issues"
```bash
This is actually good! Means:
- Health score is high
- No critical security issues
- Configuration is clean
- Resources are well-utilized

Check:
- Run with verbose: cribl-hc analyze run --deployment prod
- View specific objectives: cribl-hc analyze run --deployment prod --objectives config security
```

**Problem**: "Analysis times out or runs very slow"
```bash
Solution:
1. Check network latency: cribl-hc config list (should be <1s)
2. Reduce number of objectives analyzed
3. Check Cribl deployment is responsive
4. Try API call limit: --api-limit 50
```

### REST Call Extraction Issues

**Problem**: "URL not extracted from curl command"
```bash
Common causes:
1. Curl command missing URL - copy full command from dev tools
2. URL wrapped in quotes - the tool handles this automatically
3. Missing authorization header - ensure -H "Authorization: Bearer TOKEN"

Solution:
1. Copy full curl command from browser dev tools
2. Run: cribl-hc config add-from-curl <name>
3. Paste the entire curl command
4. If extraction fails, enter values manually
```

**Problem**: "Token not extracted"
```bash
Solution:
1. Token extraction looks for: -H "Authorization: Bearer TOKEN"
2. If not found, you'll be prompted to enter manually
3. Verify token starts with 'sk_' or similar
4. Avoid special characters - use token from Cribl Settings directly
```

---

## Tips & Best Practices

### 1. Naming Conventions
```bash
✓ Good names:
  cribl-hc config add-from-curl prod
  cribl-hc config add-from-curl staging
  cribl-hc config add-from-curl us-west-prod

✗ Avoid:
  cribl-hc config add-from-curl test123
  cribl-hc config add-from-curl my-server
```

### 2. Credential Security
```bash
✓ Do:
  - Keep ~/.cribl-hc/ secure (chmod 700)
  - Rotate tokens regularly
  - Export key backup: cribl-hc config export-key
  - Never share credentials

✗ Don't:
  - Commit ~/.cribl-hc to git
  - Share credentials in messages/logs
  - Use admin tokens for routine checks
```

### 3. Analysis Frequency
```bash
Recommended:
- Prod: Daily (2 AM UTC)
- Staging: Weekly
- Dev: On-demand

Cron example (daily at 2 AM):
0 2 * * * cribl-hc analyze run --deployment prod --output json >> /var/log/cribl-hc.log
```

### 4. Results Retention
```bash
Keep last 30 days:
find results/ -name "*.json" -mtime +30 -delete

Archive by date:
mkdir -p results/$(date +\%Y-\%m)
cribl-hc analyze run --deployment prod --output json > results/$(date +\%Y-\%m)/result-$(date +\%d).json
```

---

## Getting Help

### View Command Help
```bash
cribl-hc --help
cribl-hc config --help
cribl-hc analyze --help
cribl-hc config add-from-curl --help
```

### Check Version
```bash
cribl-hc --version
```

### Enable Debug Logging
```bash
export CRIBL_HC_LOG_LEVEL=DEBUG
cribl-hc analyze run --deployment prod
```

### Report Issues
If you encounter issues:
1. Enable debug logging (above)
2. Run command again and capture output
3. Include error message and deployment details
4. Report to: [GitHub Issues]
