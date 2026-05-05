# -*- mode: python ; coding: utf-8 -*-

import platform
from pathlib import Path

resources = list(Path("pyeclaw/resources").glob("*.png"))
datas = [(str(f), "pyeclaw/resources") for f in resources]

# include logo and icon from extras/images
extras = Path("extras/images")
for img in ("icon.png", "icon.svg", "logo.png", "logo.svg"):
    p = extras / img
    if p.exists():
        datas.append((str(p), "extras/images"))

# include certifi ca bundle for ssl in frozen builds
import certifi

datas.append((certifi.where(), "certifi"))

a = Analysis(
    ["pyeclaw/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["pyte", "certifi"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyeClaw",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=(platform.system() == "Darwin"),
    target_arch=None,
    codesign_identity=None,
    entitlements_file="entitlements.plist" if platform.system() == "Darwin" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PyeClaw",
)

# macos .app bundle
if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name="PyeClaw.app",
        icon="extras/images/icon.icns",
        bundle_identifier="com.pyeclaw.app",
        info_plist={
            "CFBundleName": "PyeClaw",
            "CFBundleDisplayName": "PyeClaw",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSAppTransportSecurity": {
                "NSAllowsLocalNetworking": True,
            },
        },
    )
