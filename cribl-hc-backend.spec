# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the backend bundled into the Tauri desktop app.

Analyzers are discovered at runtime with pkgutil.iter_modules (see
cribl_hc/analyzers/__init__.py), which PyInstaller's static analysis cannot
see. Listing them by hand does not work either: the previous version of this
file named three of the fifty-six analyzer modules, and a bundle built that way
registered zero analyzers, because nothing under cribl_hc.analyzers had been
collected for iter_modules to find.

collect_submodules pulls in every module in the package, so discovery finds the
same set frozen as it does from source, and new analyzers are picked up without
touching this file. collect_data_files brings the rule and pattern YAML with
them.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("cribl_hc")

# uvicorn resolves these by string at runtime, so they need naming explicitly.
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

datas = collect_data_files("cribl_hc")

a = Analysis(
    ["run_api.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="cribl-hc-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
