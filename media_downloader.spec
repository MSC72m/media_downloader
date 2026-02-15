# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Media Downloader.

Build with:
    pyinstaller media_downloader.spec

This produces:
    dist/MediaDownloader/  (folder with .exe and all dependencies)

Playwright Strategy:
    The Playwright Python package IS bundled so that ``import playwright``
    works at runtime. However, the Chromium browser binary (~150 MB) is
    NOT bundled -- it is downloaded automatically on first launch via
    ``src.services.cookies.playwright_bootstrap.ensure_playwright_ready()``.
"""

import os
import sys
from pathlib import Path

import customtkinter

block_cipher = None

# Paths
PROJECT_ROOT = os.path.abspath(".")
CTK_PATH = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ["src/main.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Bundle the themes directory
        (os.path.join(PROJECT_ROOT, "themes"), "themes"),
        # CustomTkinter needs its own assets bundled
        (CTK_PATH, "customtkinter"),
    ],
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
        # Playwright Python package (NOT the browser binary -- that is
        # downloaded on first launch by playwright_bootstrap)
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
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    # Uncomment and set path if you have an icon file:
    # icon="assets/icon.ico",
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
