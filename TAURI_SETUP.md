# Tauri Desktop App Setup Guide

This guide will help you create a self-contained desktop application that bundles the React frontend and Python backend into a single executable.

## Why Tauri?

- **Tiny bundles**: 10-20MB vs Electron's 150MB+
- **Lower memory usage**: Uses native OS webview instead of Chromium
- **Reuses 100% of existing React code**: No UI rewrite needed
- **Easy Python integration**: Can spawn and communicate with Python backend
- **Cross-platform**: Windows, macOS, Linux

## Architecture

```
Cribl Health Check Desktop App
├── Frontend (React + Vite) - Your existing web UI
├── Tauri Core (Rust) - Native app wrapper
│   ├── Window management
│   ├── Python process manager
│   └── IPC bridge (frontend ↔ Python)
└── Backend (Python) - Embedded FastAPI server
```

## Prerequisites

### 1. Install Rust

```bash
# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Follow prompts, then reload shell
source $HOME/.cargo/env

# Verify installation
rustc --version
cargo --version
```

### 2. Install Tauri CLI

```bash
cargo install tauri-cli
```

### 3. Install System Dependencies (macOS)

```bash
# You likely already have these, but verify:
xcode-select --install
```

## Implementation Steps

### Step 1: Initialize Tauri Project

```bash
cd /Users/sarmstrong/Projects/cribl-hc
npm install --save-dev @tauri-apps/cli @tauri-apps/api
```

### Step 2: Configure Tauri

Create `src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "beforeDevCommand": "cd frontend && npm run dev",
    "beforeBuildCommand": "cd frontend && npm run build",
    "devPath": "http://localhost:5173",
    "distDir": "../frontend/dist"
  },
  "package": {
    "productName": "Cribl Health Check",
    "version": "1.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "all": false,
        "sidecar": true,
        "scope": [
          { "name": "cribl-hc-backend", "sidecar": true, "args": true }
        ]
      },
      "http": {
        "all": true,
        "request": true,
        "scope": ["http://localhost:8000/*"]
      }
    },
    "bundle": {
      "active": true,
      "identifier": "com.cribl.healthcheck",
      "resources": ["../src/**"],
      "externalBin": ["cribl-hc-backend"]
    },
    "windows": [
      {
        "title": "Cribl Health Check",
        "width": 1280,
        "height": 800
      }
    ]
  }
}
```

### Step 3: Create Python Backend Sidecar

The Python backend will be bundled as a "sidecar" - a separate executable that Tauri launches.

**Option A: PyInstaller (Recommended)**

```bash
# Install PyInstaller
pip install pyinstaller

# Create standalone executable
cd /Users/sarmstrong/Projects/cribl-hc
pyinstaller --onefile \
  --name cribl-hc-backend \
  --add-data "src:src" \
  --hidden-import cribl_hc \
  run_api.py

# This creates: dist/cribl-hc-backend
```

**Option B: Use system Python**

Alternatively, bundle the entire Python environment and use a shell script wrapper.

### Step 4: Create Rust Backend Bridge

Create `src-tauri/src/main.rs`:

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::process::{Command, Child};
use std::sync::Mutex;

struct PythonBackend(Mutex<Option<Child>>);

#[tauri::command]
fn start_backend(handle: tauri::AppHandle) -> Result<(), String> {
    let resource_path = handle
        .path_resolver()
        .resolve_resource("cribl-hc-backend")
        .ok_or("Failed to find backend binary")?;

    let child = Command::new(resource_path)
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    let state: tauri::State<PythonBackend> = handle.state();
    *state.0.lock().unwrap() = Some(child);

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(PythonBackend(Default::default()))
        .invoke_handler(tauri::generate_handler![start_backend])
        .setup(|app| {
            // Auto-start Python backend on app launch
            let handle = app.handle();
            tauri::async_runtime::spawn(async move {
                std::thread::sleep(std::time::Duration::from_secs(1));
                start_backend(handle).ok();
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Step 5: Update Frontend to Use Tauri

Update `frontend/src/api/client.ts`:

```typescript
import axios from 'axios'

// Detect if running in Tauri
const isTauri = '__TAURI__' in window

// Use localhost for embedded backend, or allow custom URL
const BASE_URL = isTauri
  ? 'http://localhost:8000'
  : import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = {
  // ... existing implementation
}
```

### Step 6: Build Desktop App

```bash
# Development mode (hot reload)
cd /Users/sarmstrong/Projects/cribl-hc
npm run tauri dev

# Production build
npm run tauri build

# Output will be in:
# - macOS: src-tauri/target/release/bundle/dmg/
# - Windows: src-tauri/target/release/bundle/msi/
# - Linux: src-tauri/target/release/bundle/appimage/
```

## Package Scripts

Add to root `package.json`:

```json
{
  "scripts": {
    "tauri": "tauri",
    "tauri:dev": "tauri dev",
    "tauri:build": "tauri build",
    "tauri:build:backend": "pyinstaller --onefile --name cribl-hc-backend run_api.py"
  }
}
```

## Distribution

The final app will be:
- **macOS**: `.dmg` file (~15-25MB)
- **Windows**: `.msi` installer (~15-25MB)
- **Linux**: `.AppImage` (~15-25MB)

Users can double-click to run - no installation of Python, Node, or dependencies required!

## Next Steps

1. Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
2. Run: `cargo install tauri-cli`
3. Initialize: `npm install --save-dev @tauri-apps/cli @tauri-apps/api`
4. Let me know when ready and I'll create the full implementation!

## Benefits Over Web GUI

- ✅ **Portable**: Single .dmg/.exe file
- ✅ **No server required**: Embedded backend
- ✅ **Native performance**: OS-level webview
- ✅ **Auto-updates**: Tauri has built-in updater
- ✅ **Offline capable**: Everything bundled
- ✅ **Professional**: Native window, menus, icons
