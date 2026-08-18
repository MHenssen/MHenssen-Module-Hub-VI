# PyInstaller spec: builds the single-file PI_Portfolio_Explorer.exe.
#   pyinstaller PI_Portfolio_Explorer.spec
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[],
    datas=[("pi_portfolio/templates/dashboard.html", "pi_portfolio/templates")],
    hiddenimports=collect_submodules("flask") + collect_submodules("openpyxl") + ["tkinter"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PI_Portfolio_Explorer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
