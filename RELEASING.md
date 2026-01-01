# Release Process

This document describes how to create a new release of Cribl Health Check.

## Automated Multi-Platform Builds

The project uses GitHub Actions to automatically build desktop applications for all platforms when you create a release tag.

### Supported Platforms

The build process creates installers for:

- **macOS**
  - `.dmg` for Intel Macs (x86_64)
  - `.dmg` for Apple Silicon Macs (aarch64/M1/M2/M3)
- **Linux**
  - `.deb` package (Debian/Ubuntu)
  - `.AppImage` (Universal Linux)
- **Windows**
  - `.msi` installer
  - `.exe` portable executable

## Creating a Release

### 1. Prepare the Release

1. Update version in `src-tauri/tauri.conf.json`:
   ```json
   {
     "version": "1.0.0"
   }
   ```

2. Update version in `frontend/package.json`:
   ```json
   {
     "version": "1.0.0"
   }
   ```

3. Update CHANGELOG.md with release notes

4. Commit changes:
   ```bash
   git add src-tauri/tauri.conf.json frontend/package.json CHANGELOG.md
   git commit -m "chore: Bump version to 1.0.0"
   git push origin main
   ```

### 2. Create Release Tag

```bash
# Create and push tag
git tag v1.0.0
git push origin v1.0.0
```

This triggers the `build-release.yml` workflow which:
1. Builds Python backend with PyInstaller for each platform
2. Builds Tauri desktop app for each platform
3. Creates GitHub Release with all artifacts attached

### 3. Monitor Build Progress

1. Go to https://github.com/YOUR_ORG/cribl-hc/actions
2. Watch the "Build Release" workflow
3. Builds take ~15-30 minutes total

### 4. Verify Release

Once the workflow completes:

1. Go to https://github.com/YOUR_ORG/cribl-hc/releases
2. Find your release (v1.0.0)
3. Verify all platform artifacts are attached:
   - `Cribl-Health-Check_1.0.0_x64.dmg` (macOS Intel)
   - `Cribl-Health-Check_1.0.0_aarch64.dmg` (macOS M1/M2/M3)
   - `cribl-hc_1.0.0_amd64.deb` (Linux Debian/Ubuntu)
   - `Cribl-Health-Check_1.0.0_x86_64.AppImage` (Linux Universal)
   - `Cribl-Health-Check_1.0.0_x64.msi` (Windows Installer)

### 5. Test Downloads

Download and test on each platform:

**macOS:**
```bash
# Download .dmg
open Cribl-Health-Check_1.0.0_aarch64.dmg
# Drag to Applications
# Test GUI: double-click app
# Test CLI: /Applications/Cribl\ Health\ Check.app/Contents/Resources/cribl-hc --version
```

**Linux:**
```bash
# Debian/Ubuntu
sudo dpkg -i cribl-hc_1.0.0_amd64.deb

# Universal AppImage
chmod +x Cribl-Health-Check_1.0.0_x86_64.AppImage
./Cribl-Health-Check_1.0.0_x86_64.AppImage
```

**Windows:**
```powershell
# Run MSI installer
msiexec /i Cribl-Health-Check_1.0.0_x64.msi

# Test
"C:\Program Files\Cribl Health Check\cribl-hc.exe" --version
```

## CLI Access from Desktop App

Users who install the desktop app can also access the CLI:

**macOS:**
```bash
# Create symlink (one-time)
sudo ln -s "/Applications/Cribl Health Check.app/Contents/Resources/cribl-hc" /usr/local/bin/cribl-hc

# Use CLI
cribl-hc analyze prod
cribl-hc tui
```

**Linux (.deb):**
```bash
# CLI automatically in PATH
cribl-hc analyze prod
cribl-hc tui
```

**Windows:**
```powershell
# Add to PATH or use full path
"C:\Program Files\Cribl Health Check\cribl-hc.exe" analyze prod
```

## Troubleshooting

### Build Fails

1. Check GitHub Actions logs for specific error
2. Common issues:
   - Missing dependencies in requirements.txt
   - PyInstaller bundling errors
   - Tauri configuration issues

### Missing Artifacts

If some platform builds are missing:
1. Check if the build job failed for that platform
2. Re-run failed jobs from GitHub Actions UI
3. If persistent, open an issue with the error logs

### Release Not Created

Ensure the workflow has `contents: write` permission:
1. Go to Settings → Actions → General
2. Workflow permissions → Read and write permissions
3. Save

## Beta Releases

For pre-release versions:

```bash
git tag v1.0.0-beta.1
git push origin v1.0.0-beta.1
```

The release will be marked as "Pre-release" automatically.

## Manual Builds (Development)

For local testing without creating a release:

```bash
# Install PyInstaller
pip install pyinstaller

# Bundle Python backend
python -m PyInstaller --onefile --name cribl-hc-backend run_api.py

# Copy to Tauri
mkdir -p src-tauri/binaries
cp dist/cribl-hc-backend src-tauri/binaries/

# Build desktop app
npm run tauri:build
```

Output locations:
- macOS: `src-tauri/target/release/bundle/dmg/`
- Linux: `src-tauri/target/release/bundle/deb/` and `bundle/appimage/`
- Windows: `src-tauri/target/release/bundle/msi/`
