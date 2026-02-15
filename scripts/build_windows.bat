@echo off
REM ============================================================
REM  Build script for Media Downloader Windows installer
REM ============================================================
REM
REM  Prerequisites:
REM    1. Python 3.10+ with all dependencies installed
REM    2. PyInstaller: pip install pyinstaller
REM    3. Inno Setup 6+: https://jrsoftware.org/isinfo.php
REM       (add to PATH or set INNO_SETUP_PATH below)
REM
REM  Usage:
REM    build_windows.bat           Build .exe only (PyInstaller)
REM    build_windows.bat installer Build .exe + installer (Inno Setup)
REM
REM ============================================================

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
set "INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo.
echo ============================================================
echo  Media Downloader - Windows Build
echo ============================================================
echo.

REM Step 1: Clean previous builds
echo [1/4] Cleaning previous builds...
if exist "%PROJECT_ROOT%dist" rmdir /s /q "%PROJECT_ROOT%dist"
if exist "%PROJECT_ROOT%build" rmdir /s /q "%PROJECT_ROOT%build"
echo       Done.
echo.

REM Step 2: Build with PyInstaller
echo [2/4] Building with PyInstaller...
echo       This may take several minutes...
echo.
pyinstaller "%PROJECT_ROOT%media_downloader.spec" --noconfirm
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
echo [3/4] Verifying build output...
if not exist "%PROJECT_ROOT%dist\MediaDownloader\MediaDownloader.exe" (
    echo ERROR: MediaDownloader.exe not found in dist\MediaDownloader\
    exit /b 1
)
echo       MediaDownloader.exe found.
echo.

REM Step 4: Build installer (optional)
if /i "%1"=="installer" (
    echo [4/4] Building installer with Inno Setup...

    if not exist "%INNO_SETUP_PATH%" (
        echo ERROR: Inno Setup not found at: %INNO_SETUP_PATH%
        echo.
        echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
        echo Or update INNO_SETUP_PATH in this script.
        exit /b 1
    )

    if not exist "%PROJECT_ROOT%installers" mkdir "%PROJECT_ROOT%installers"

    "%INNO_SETUP_PATH%" "%PROJECT_ROOT%installer.iss"
    if errorlevel 1 (
        echo ERROR: Inno Setup build failed!
        exit /b 1
    )
    echo.
    echo       Installer built successfully.
    echo       Output: installers\MediaDownloaderSetup-0.1.0.exe
) else (
    echo [4/4] Skipping installer build (pass "installer" argument to build it)
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
echo  NOTE: On first launch, the app will download Chromium (~150 MB)
echo  for cookie generation. This requires an internet connection.
echo ============================================================
echo.

endlocal
