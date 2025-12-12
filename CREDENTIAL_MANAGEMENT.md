# Credential Management Guide

## Overview

The cribl-hc tool provides **three flexible ways** to provide your Cribl Stream credentials:

1. **Stored Credentials** - Save encrypted credentials for easy reuse
2. **Command-Line Options** - Provide URL and token directly
3. **Environment Variables** - Set credentials in your shell environment

You can choose whichever method works best for your workflow!

## Method 1: Stored Credentials (RECOMMENDED)

This is the most convenient method for regular use. Your credentials are encrypted with AES-256 and stored securely.

### Step 1: Store Your Credentials

```bash
cribl-hc config set prod --url https://your-cribl-instance.com --token YOUR_TOKEN
```

You'll be prompted to enter the token securely (it won't show on screen):

```
Bearer Token: [hidden input]
✓ Saved credentials for deployment: prod
URL: https://your-cribl-instance.com
Storage: /Users/yourusername/.cribl-hc/credentials.enc
```

### Step 2: Use Your Stored Credentials

Now you can run commands without typing credentials every time:

```bash
# Test connection
cribl-hc test-connection test --deployment prod

# Run analysis
cribl-hc analyze run --deployment prod

# Run with verbose output
cribl-hc analyze run -p prod --verbose

# Save report
cribl-hc analyze run -p prod --output report.json --markdown
```

### Managing Stored Credentials

**List all stored deployments:**
```bash
cribl-hc config list
```

**View a specific deployment:**
```bash
cribl-hc config get prod
```

**Delete stored credentials:**
```bash
cribl-hc config delete prod
```

**Store multiple deployments:**
```bash
cribl-hc config set prod --url https://prod.cribl.com --token PROD_TOKEN
cribl-hc config set dev --url https://dev.cribl.com --token DEV_TOKEN
cribl-hc config set staging --url https://staging.cribl.com --token STAGING_TOKEN

# Then use any of them
cribl-hc analyze run -p prod
cribl-hc analyze run -p dev
cribl-hc analyze run -p staging
```

### Security Details

- Credentials are encrypted using **Fernet (AES-256)** encryption
- Stored in: `~/.cribl-hc/credentials.enc`
- Encryption key stored in: `~/.cribl-hc/.key`
- File permissions set to `0o600` (only you can read)
- Directory permissions set to `0o700` (only you can access)

## Method 2: Command-Line Options

Provide credentials directly on the command line:

```bash
# Test connection
cribl-hc test-connection test \
  --url https://your-cribl-instance.com \
  --token YOUR_TOKEN

# Run analysis
cribl-hc analyze run \
  --url https://your-cribl-instance.com \
  --token YOUR_TOKEN

# With additional options
cribl-hc analyze run \
  -u https://your-cribl-instance.com \
  -t YOUR_TOKEN \
  --verbose \
  --output report.json
```

**Note**: The token will be visible in your shell history. For better security, use stored credentials or environment variables.

## Method 3: Environment Variables

Set credentials once in your shell session:

```bash
# Set environment variables
export CRIBL_URL="https://your-cribl-instance.com"
export CRIBL_TOKEN="your-api-token-here"

# Now run commands without any credential flags
cribl-hc test-connection test
cribl-hc analyze run --verbose
cribl-hc analyze run --output report.json --markdown
```

### Making Environment Variables Permanent

**For bash** (add to `~/.bashrc` or `~/.bash_profile`):
```bash
echo 'export CRIBL_URL="https://your-cribl-instance.com"' >> ~/.bashrc
echo 'export CRIBL_TOKEN="your-token-here"' >> ~/.bashrc
source ~/.bashrc
```

**For zsh** (add to `~/.zshrc`):
```bash
echo 'export CRIBL_URL="https://your-cribl-instance.com"' >> ~/.zshrc
echo 'export CRIBL_TOKEN="your-token-here"' >> ~/.zshrc
source ~/.zshrc
```

**For fish** (add to `~/.config/fish/config.fish`):
```fish
set -Ux CRIBL_URL "https://your-cribl-instance.com"
set -Ux CRIBL_TOKEN "your-token-here"
```

## Credential Priority

If you provide credentials in multiple ways, they are used in this order:

1. **--deployment flag** (highest priority)
2. **--url and --token flags**
3. **Environment variables** (lowest priority)

Examples:

```bash
# This uses stored credentials for "prod"
cribl-hc analyze run --deployment prod

# This uses the explicit URL/token, even if CRIBL_URL is set
cribl-hc analyze run --url https://different.com --token DIFFERENT_TOKEN

# This uses environment variables if no flags provided
export CRIBL_URL="https://env.cribl.com"
export CRIBL_TOKEN="env-token"
cribl-hc analyze run
```

## Common Workflows

### Developer Working on Multiple Environments

```bash
# Store all environments once
cribl-hc config set local --url http://localhost:9000 --token LOCAL_TOKEN
cribl-hc config set dev --url https://dev.cribl.com --token DEV_TOKEN
cribl-hc config set prod --url https://prod.cribl.com --token PROD_TOKEN

# Switch between them easily
cribl-hc analyze run -p local --verbose
cribl-hc analyze run -p dev --output dev-report.json
cribl-hc analyze run -p prod --output prod-report.json
```

### CI/CD Pipeline

Use environment variables in your CI/CD system:

```yaml
# GitHub Actions example
- name: Run Cribl Health Check
  env:
    CRIBL_URL: ${{ secrets.CRIBL_URL }}
    CRIBL_TOKEN: ${{ secrets.CRIBL_TOKEN }}
  run: |
    cribl-hc analyze run --output report.json
```

### Quick One-Time Analysis

Use command-line options for quick, one-off checks:

```bash
cribl-hc test-connection test \
  --url https://temp-instance.com \
  --token TEMP_TOKEN
```

### Daily Health Checks

Store credentials once, then create a cron job or scheduled task:

```bash
# Store credentials
cribl-hc config set prod --url https://prod.cribl.com --token TOKEN

# Add to crontab (daily at 6 AM)
0 6 * * * /usr/local/bin/cribl-hc analyze run -p prod --output /var/reports/daily-$(date +\%Y\%m\%d).json
```

## Troubleshooting

### Error: "Missing required credentials"

You'll see this if you don't provide credentials in any way:

```
✗ Missing required credentials

You must provide credentials in one of three ways:

1. Stored credentials:
   cribl-hc config set prod --url URL --token TOKEN
   cribl-hc analyze run --deployment prod

2. Command-line options:
   cribl-hc analyze run --url URL --token TOKEN

3. Environment variables:
   export CRIBL_URL=https://cribl.example.com
   export CRIBL_TOKEN=your_token
   cribl-hc analyze run
```

**Solution**: Choose one of the three methods above.

### Error: "No credentials found for deployment: prod"

You're trying to use `--deployment prod` but haven't stored those credentials yet.

**Solution**:
```bash
# Check what's stored
cribl-hc config list

# Add the missing deployment
cribl-hc config set prod --url URL --token TOKEN
```

### Error: "Connection failed: 401 Unauthorized"

Your token is invalid or expired.

**Solution**:
1. Get a new token from Cribl Stream UI (Settings → API Tokens)
2. Update stored credentials:
   ```bash
   cribl-hc config set prod --url URL --token NEW_TOKEN
   ```

### Checking Which Credentials Are Being Used

Run with `--verbose` to see which URL is being used:

```bash
cribl-hc analyze run -p prod --verbose
```

Output:
```
Using stored credentials for: prod
URL: https://your-cribl-instance.com

Testing connection...
✓ Connected successfully (152ms)
```

## Security Best Practices

1. **Use stored credentials for regular use** - Most secure and convenient
2. **Avoid hardcoding tokens** in scripts - Use environment variables or stored credentials
3. **Rotate tokens regularly** - Update stored credentials when tokens change
4. **Use different tokens per environment** - Don't reuse production tokens in dev
5. **Protect your encryption key** - The file `~/.cribl-hc/.key` should never be shared
6. **Set proper file permissions** - The tool does this automatically, but verify:
   ```bash
   ls -la ~/.cribl-hc/
   # Should show: drwx------ (700) for directory
   #              -rw------- (600) for files
   ```

## Backup and Restore

### Backup Your Credentials

```bash
# Backup the entire config directory
tar -czf cribl-hc-backup.tar.gz ~/.cribl-hc/

# Or just backup the credentials and key
cp ~/.cribl-hc/credentials.enc ~/backup/
cp ~/.cribl-hc/.key ~/backup/
```

### Restore Credentials

```bash
# Restore from backup
mkdir -p ~/.cribl-hc
cp ~/backup/credentials.enc ~/.cribl-hc/
cp ~/backup/.key ~/.cribl-hc/
chmod 700 ~/.cribl-hc
chmod 600 ~/.cribl-hc/*
```

### Export Encryption Key

If you need to share credentials across machines:

```bash
# Export the key (keep this VERY secure!)
cribl-hc config export-key --output backup-key.txt

# On new machine, copy both files
mkdir -p ~/.cribl-hc
cp credentials.enc ~/.cribl-hc/
cp backup-key.txt ~/.cribl-hc/.key
chmod 700 ~/.cribl-hc
chmod 600 ~/.cribl-hc/*
```

## Quick Reference

| Method | Command | When to Use |
|--------|---------|-------------|
| Stored | `cribl-hc config set prod ...` then `cribl-hc analyze run -p prod` | Regular use, multiple environments |
| CLI Options | `cribl-hc analyze run --url ... --token ...` | One-time checks, testing |
| Env Vars | `export CRIBL_URL=... CRIBL_TOKEN=...` then `cribl-hc analyze run` | CI/CD, automation scripts |

## Getting Help

```bash
# See all config commands
cribl-hc config --help

# See analyze command options
cribl-hc analyze run --help

# See test-connection command options
cribl-hc test-connection test --help
```

---

**Summary**: For the best experience, store your credentials once with `cribl-hc config set`, then use `--deployment` flag for all future commands!
