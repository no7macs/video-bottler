# -*- mode: python ; coding: utf-8 -*-
import tkinterdnd2

block_cipher = None

MediaInfo = "A:\\Documents\\MediaInfo\MediaInfo_CLI_23.04_Windows_x64\\MediaInfo.exe"
ffmpeg = "A:\\Documents\\ffmpeg\\ffmpeg-6.0-full_build\\bin\\ffmpeg.exe"
ffprobe = "A:\\Documents\\ffmpeg\\ffmpeg-6.0-full_build\\bin\\ffprobe.exe"

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(f"{tkinterdnd2.__path__[0]}", "tkinterdnd2"),
                (MediaInfo, "."),
                (ffmpeg, "."),
                (ffprobe, ".")],
    datas=[],
    hiddenimports=[],
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
    name='main',
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
