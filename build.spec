# -*- mode: python ; coding: utf-8 -*-
#
# Build with:  pyinstaller build.spec
#
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

sys.path.insert(0, str(Path(".").resolve()))
from version import __version__

block_cipher = None

# Collect customtkinter assets (themes, images, fonts)
ctk_datas = collect_data_files("customtkinter")

# Bundle our own assets folder
app_assets = [("assets", "assets")]

a = Analysis(
    ["main.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=ctk_datas + app_assets,
    hiddenimports=[
        "customtkinter",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GitSwitcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
