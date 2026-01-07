# Push Feature Branch to GitHub

To push the `feature/004-version-control-enhancements` branch to GitHub:

## 1. Create Personal Access Token
If you don't have a GitHub personal access token:

1. Go to GitHub.com → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with these scopes:
   - ✅ repo (full control of private repositories)
   - ✅ workflow (Update GitHub Action workflows)
3. Copy the token (you won't see it again)

## 2. Push Branch

```bash
cd /root/Projects/cribl-hc
# When prompted for credentials:
# Username: your GitHub username
# Password: your personal access token (NOT your GitHub password)
git push -u origin feature/004-version-control-enhancements
```

## 3. Create Pull Request

After successful push:
1. Go to https://github.com/KnottyDyes/cribl-hc
2. You'll see a "Compare & pull request" button for the new branch
3. Create PR with title: "feat: Implement RBAC user audit with comprehensive testing"
4. Add description from commit message

## Branch Status
- ✅ All RBAC features implemented
- ✅ 14 unit tests added
- ✅ Test infrastructure fixed (99.8% pass rate)
- ✅ Code committed locally
- 🚧 Waiting for push to GitHub

## Alternative SSH Method
If you prefer SSH:
```bash
# Generate SSH key if needed
ssh-keygen -t ed25519 -C "your_email@example.com"
# Add public key to GitHub: Settings → SSH and GPG keys
git remote set-url origin git@github.com:KnottyDyes/cribl-hc.git
git push -u origin feature/004-version-control-enhancements
```