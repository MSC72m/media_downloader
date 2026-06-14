# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Media Downloader.

Build with:
    pyinstaller media_downloader.spec

This produces:
    dist/MediaDownloader/  (folder with .exe and all dependencies)

Architecture:
    - Python interpreter + all packages bundled in _internal/
    - ffmpeg bundled for video processing
    - Chromium browser: EITHER bundled OR downloaded on first launch
      (controlled by BUNDLE_CHROMIUM environment variable)

Environment Variables:
    BUNDLE_CHROMIUM=1  - Bundle Chromium browser (~150MB extra)
    BUNDLE_CHROMIUM=0  - Download Chromium on first launch (default)
"""

import os

import customtkinter
import tkinter

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Paths
PROJECT_ROOT = os.path.abspath(".")
CTK_PATH = os.path.dirname(customtkinter.__file__)

# Collect Tcl/Tk library directories for the runtime hook
_tcl_data = None
_tk_data = None
_tcl_dir = os.path.dirname(tkinter.__file__)
for _entry in os.listdir(_tcl_dir):
    _full = os.path.join(_tcl_dir, _entry)
    if not os.path.isdir(_full):
        continue
    _lower = _entry.lower()
    if _lower.startswith("tcl") and _tcl_data is None:
        _tcl_data = _full
    elif _lower.startswith("tk") and _tk_data is None:
        _tk_data = _full

# Check if we should bundle Chromium
BUNDLE_CHROMIUM = os.environ.get("BUNDLE_CHROMIUM", "0") == "1"

# Collect data files
datas = [
    # Bundle the themes directory
    (os.path.join(PROJECT_ROOT, "themes"), "themes"),
    # CustomTkinter assets only (fonts, themes, icons)
    (os.path.join(CTK_PATH, "assets"), "customtkinter/assets"),
    # App assets (icon, etc.)
    (os.path.join(PROJECT_ROOT, "assets"), "assets"),
]

# Bundle Tcl/Tk libraries
if _tcl_data and os.path.isdir(_tcl_data):
    print(f"[PyInstaller] Bundling Tcl library: {_tcl_data}")
    datas.append((_tcl_data, "tcl"))
if _tk_data and os.path.isdir(_tk_data):
    print(f"[PyInstaller] Bundling Tk library: {_tk_data}")
    datas.append((_tk_data, "tk"))

# Check for ffmpeg - bundle it if available
FFMPEG_PATH = os.path.join(PROJECT_ROOT, "bin", "ffmpeg.exe")
if os.path.exists(FFMPEG_PATH):
    print(f"[PyInstaller] Bundling ffmpeg: {FFMPEG_PATH}")
    datas.append((FFMPEG_PATH, "bin"))
else:
    print("[PyInstaller] WARNING: ffmpeg.exe not found at bin/ffmpeg.exe")
    print("[PyInstaller] Video processing may not work without ffmpeg")
    print("[PyInstaller] Run: python scripts/download_ffmpeg.py")

# Check for bundled Chromium
if BUNDLE_CHROMIUM:
    CHROMIUM_PATH = os.path.join(PROJECT_ROOT, "bin", "chromium")
    if os.path.exists(CHROMIUM_PATH):
        print(f"[PyInstaller] Bundling Chromium: {CHROMIUM_PATH}")
        datas.append((CHROMIUM_PATH, "chromium"))
    else:
        print("[PyInstaller] WARNING: Chromium not found at bin/chromium")
        print("[PyInstaller] Run: python scripts/download_chromium.py")

a = Analysis(
    ["src/main.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Core GUI
        "customtkinter",
        "tkinter",
        "_tkinter",
        # Application modules (dynamic imports via service config)
        "src.main",
        "src.core",
        "src.core.config",
        "src.core.themes",
        "src.core.models",
        "src.core.type_defs",
        "src.core.interfaces",
        "src.core.enums",
        "src.core.enums.appearance_mode",
        "src.application",
        "src.application.orchestrator",
        "src.application.di_container",
        "src.application.service_factories",
        "src.application.service_factory",
        "src.coordinators",
        "src.coordinators.main_coordinator",
        "src.coordinators.download_coordinator",
        "src.coordinators.platform_dialog_coordinator",
        "src.coordinators.error_notifier",
        "src.handlers",
        "src.handlers.youtube_handler",
        "src.handlers.instagram_handler",
        "src.handlers.twitter_handler",
        "src.handlers.pinterest_handler",
        "src.handlers.soundcloud_handler",
        "src.handlers.tiktok_handler",
        "src.handlers.radiojavan_handler",
        "src.handlers.spotify_handler",
        "src.handlers.cookie_handler",
        "src.handlers.download_handler",
        "src.handlers.network_checker",
        "src.handlers.service_detector",
        "src.services",
        "src.services.youtube",
        "src.services.youtube.downloader",
        "src.services.instagram",
        "src.services.instagram.downloader",
        "src.services.twitter",
        "src.services.twitter.downloader",
        "src.services.pinterest",
        "src.services.pinterest.downloader",
        "src.services.soundcloud",
        "src.services.soundcloud.downloader",
        "src.services.tiktok",
        "src.services.tiktok.downloader",
        "src.services.radiojavan",
        "src.services.radiojavan.downloader",
        "src.services.spotify",
        "src.services.spotify.downloader",
        "src.services.cookies",
        "src.services.cookies.playwright_bootstrap",
        "src.services.detection",
        "src.services.events",
        "src.services.file",
        "src.services.network",
        "src.services.notifications",
        "src.ui",
        "src.ui.components",
        "src.ui.dialogs",
        "src.ui.utils",
        "src.ui.utils.theme_manager",
        "src.utils",
        "src.utils.logger",
        "src.utils.common",
        "src.utils.window",
        "src.utils.error_helpers",
        "src.utils.type_helpers",
        "src.utils.user_agent_rotator",
        # Third-party dependencies
        "yt_dlp",
        "instaloader",
        # Playwright Python package (browser binary is bundled separately if BUNDLE_CHROMIUM=1)
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
        "playwright._impl",
        "playwright._impl._api_types",
        "playwright._impl._connection",
        "playwright._impl._driver",
        "playwright._impl._transport",
        "pydantic",
        "pydantic.deprecated",
        "pydantic.deprecated.decorator",
        "pydantic_settings",
        "pydantic_core",
        "PIL",
        "PIL._tkinter_finder",
        "bs4",
        "yaml",
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        "json",
        "queue",
        "logging",
    ],
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=["hooks/runtime_hook_tcl.py"],
    excludes=[
        # Exclude dev/test dependencies
        "pytest",
        "pytest_cov",
        "ruff",
        "mypy",
        "pre_commit",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MediaDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, "assets", "media_downloader.ico"),
    manifest='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">'
    '<application xmlns="urn:schemas-microsoft-com:asm.v3">'
    "<windowsSettings>"
    '<dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>'
    '<dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">system</dpiAwareness>'
    "</windowsSettings>"
    "</application>"
    "</assembly>",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MediaDownloader",
)

print(f"[PyInstaller] Build complete. Chromium bundled: {BUNDLE_CHROMIUM}")
