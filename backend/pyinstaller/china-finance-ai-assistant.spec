# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


backend_root = Path(SPECPATH).resolve().parent
repo_root = backend_root.parent
frontend_dist = repo_root / "frontend" / "dist"
app_hiddenimports = collect_submodules("app")

datas = []
if frontend_dist.exists():
    datas.append((str(frontend_dist), "frontend_dist"))

a = Analysis(
    [str(backend_root / "app" / "desktop.py")],
    pathex=[str(backend_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        *app_hiddenimports,
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
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
    name="ChinaFinanceAIAssistant",
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
