@echo off
REM ============================================================
REM  Build script for Media Downloader Windows installer
REM ============================================================
REM
REM  This script builds a complete Windows installer that includes:
REM    - Python application bundled with PyInstaller
REM    - ffmpeg for video processing
REM    - Chromium browser (optional, controlled by BUNDLE_CHROMIUM)
REM
REM  Prerequisites:
REM    1. Python 3.10+ with all dependencies installed
REM    2. PyInstaller: pip install pyinstaller
REM    3. Inno Setup 6+: https://jrsoftware.org/isinfo.php
REM       (add to PATH or set INNO_SETUP_PATH below)
REM
REM  Usage:
REM    build_windows.bat              - Build .exe only (PyInstaller)
REM    build_windows.bat installer    - Build .exe + installer (Inno Setup)
REM    build_windows.bat full         - Download deps + build everything
REM
REM  Environment Variables:
REM    BUNDLE_CHROMIUM=1  - Bundle Chromium browser (~150MB extra)
REM    BUNDLE_CHROMIUM=0  - Download Chromium on first launch (default)
REM
REM ============================================================

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
set "INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

REM Check for full mode (download dependencies)
if /i "%1"=="full" (
    set "FULL_MODE=1"
    shift
) else (
    set "FULL_MODE=0"
)

echo.
echo ============================================================
echo  Media Downloader - Windows Build
echo ============================================================
echo.

REM Step 0: Download dependencies if in full mode
if "%FULL_MODE%"=="1" (
    echo [0/5] Downloading dependencies...
    echo.

    echo       Downloading ffmpeg...
    python "%~dp0download_ffmpeg.py"
    if errorlevel 1 (
        echo WARNING: ffmpeg download failed, continuing anyway...
    )
    echo.

    if "%BUNDLE_CHROMIUM%"=="1" (
        echo       Downloading Chromium browser...
        python "%~dp0download_chromium.py"
        if errorlevel 1 (
            echo WARNING: Chromium download failed, continuing anyway...
        )
    )
    echo.
)

REM Check if ffmpeg exists (warn if not)
if not exist "%~dp0..\bin\ffmpeg.exe" (
    echo WARNING: ffmpeg.exe not found at bin\ffmpeg.exe
    echo          Video processing may not work correctly.
    echo          Run: python scripts/download_ffmpeg.py
    echo.
)

REM Step 1: Clean previous builds
echo [1/5] Cleaning previous builds...
if exist "%~dp0..\dist" rmdir /s /q "%~dp0..\dist"
if exist "%~dp0..\build" rmdir /s /q "%~dp0..\build"
echo       Done.
echo.

REM Step 2: Build with PyInstaller
echo [2/5] Building with PyInstaller...
echo       Configuration:
if "%BUNDLE_CHROMIUM%"=="1" (
    echo         - Chromium: BUNDLED (~150MB)
) else (
    echo         - Chromium: Download on first launch
)
echo       This may take several minutes...
echo.

pyinstaller "%~dp0..\media_downloader.spec" --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    echo Make sure PyInstaller is installed: pip install pyinstaller
    exit /b 1
)
echo.
echo       PyInstaller build complete.
echo       Output: dist\MediaDownloader\
echo.

REM Step 3: Verify build output
echo [3/5] Verifying build output...
if not exist "%~dp0..\dist\MediaDownloader\MediaDownloader.exe" (
    echo ERROR: MediaDownloader.exe not found in dist\MediaDownloader\
    exit /b 1
)
echo       MediaDownloader.exe found.

REM Check for ffmpeg in bundle
if exist "%~dp0..\dist\MediaDownloader\_internal\bin\ffmpeg.exe" (
    echo       ffmpeg.exe bundled.
) else (
    echo WARNING: ffmpeg.exe not found in bundle.
)

echo.

REM Step 4: Build installer (optional)
if /i "%1"=="installer" (
    echo [4/5] Building installer with Inno Setup...

    if not exist "%INNO_SETUP_PATH%" (
        echo ERROR: Inno Setup not found at: %INNO_SETUP_PATH%
        echo.
        echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
        echo Or update INNO_SETUP_PATH in this script.
        exit /b 1
    )

    if not exist "%~dp0..\installers" mkdir "%~dp0..\installers"

    REM Pass BUNDLE_CHROMIUM to Inno Setup
    set "ISCC_PARAMS="
    if "%BUNDLE_CHROMIUM%"=="1" (
        set "ISCC_PARAMS=/DBUNDLE_CHROMIUM"
    )

    "%INNO_SETUP_PATH%" %ISCC_PARAMS% "%~dp0..\installer.iss"
    if errorlevel 1 (
        echo ERROR: Inno Setup build failed!
        exit /b 1
    )
    echo.
    echo       Installer built successfully.
    echo       Output: installers\MediaDownloaderSetup-0.1.0.exe
) else (
    echo [4/5] Skipping installer build (pass "installer" argument to build it)
)

echo.
echo ============================================================
echo  Build complete!
echo ============================================================
echo.
echo  Portable app:  dist\MediaDownloader\MediaDownloader.exe
if /i "%1"=="installer" (
    echo  Installer:     installers\MediaDownloaderSetup-0.1.0.exe
)
echo.
if "%BUNDLE_CHROMIUM%"=="1" (
    echo  Chromium:      BUNDLED (ready to use immediately)
) else (
    echo  Chromium:      Will download on first launch (~150 MB)
)
echo ============================================================
echo.

endlocal
