# Windows Build, Installer & Release Guide

This document covers **everything** you need to build, test, sign, and release
Media Downloader as a Windows `.exe` with a proper installer.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Adding an App Icon / Logo](#adding-an-app-icon--logo)
4. [Step 1 -- Build with PyInstaller](#step-1----build-with-pyinstaller)
5. [Step 2 -- Test the PyInstaller Bundle](#step-2----test-the-pyinstaller-bundle)
6. [Step 3 -- Build the Installer with Inno Setup](#step-3----build-the-installer-with-inno-setup)
7. [Step 4 -- Test the Installer](#step-4----test-the-installer)
8. [Step 5 -- Code Signing](#step-5----code-signing)
9. [Step 6 -- CI/CD Release Workflow](#step-6----cicd-release-workflow)
10. [Troubleshooting](#troubleshooting)
11. [File Reference](#file-reference)

---

## Architecture Overview

### What the Installer Contains

When a user downloads and runs `MediaDownloaderSetup.exe`, they get:

**Always Included (Standard Build):**
- Python interpreter (bundled by PyInstaller)
- All Python dependencies (yt-dlp, playwright, requests, beautifulsoup4, etc.)
- Your application code
- ffmpeg for video processing (~100 MB)
- **Total: ~150-200 MB installed**

**Release Architectures:**
- `MediaDownloaderSetup-{version}-x64.exe` for Intel/AMD Windows PCs
- `MediaDownloaderSetup-{version}-arm64.exe` for Windows on ARM devices

**Two Options for Chromium Browser:**

#### Option A: Standard (Recommended)
- **Installer size:** ~60-80 MB
- **Chromium:** Downloaded automatically on first app launch (~150 MB)
- **User experience:** First launch shows a progress dialog for 1-3 minutes
- **Benefit:** Smaller download, always gets latest Chromium

#### Option B: Full Bundle
- **Installer size:** ~200-250 MB
- **Chromium:** Included in the installer
- **User experience:** App works immediately after installation
- **Benefit:** Works offline, no wait on first launch

### Build Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Inno Setup Installer  (MediaDownloaderSetup.exe)          │
│  ├─ PyInstaller Bundle (app + Python + ffmpeg)            │
│  └─ [Optional] Chromium browser (~150 MB)                 │
│                                                             │
│  Standard:  ~60-80 MB  |  Full: ~200-250 MB               │
└────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│  Installed to C:\Program Files\Media Downloader\          │
│  ├─ MediaDownloader.exe (entry point)                     │
│  ├─ _internal\ (Python interpreter + libraries)           │
│  │   ├─ bin\ffmpeg.exe (video processing)                 │
│  │   └─ All Python packages (yt-dlp, playwright, etc.)    │
│  └─ [If not bundled] Chromium downloads to AppData        │
│                                                             │
│  No separate Python installation required!                │
└────────────────────────────────────────────────────────────┘
```

### How It Works (Standard Build)

1. **User downloads installer** (~60-80 MB)
2. **Runs installer** → Extracts files to Program Files
3. **Launches app** → App checks if Chromium exists
4. **First launch only** → Downloads Chromium (~150 MB) with progress dialog
5. **Ready to use** → All features work (downloads, cookies, etc.)

### How It Works (Full Bundle)

1. **User downloads installer** (~200-250 MB)
2. **Runs installer** → Extracts everything including Chromium
3. **Launches app** → Works immediately, no additional downloads
4. **Ready to use** → All features work from first launch

### What About Code Signing?

Without code signing, Windows SmartScreen will show a warning when users run
the installer. This is covered in detail in the [Code Signing](#step-5----code-signing)
section below. You need an **EV Code Signing Certificate** (~$300-400/year) to
completely avoid SmartScreen warnings.

---

## Prerequisites

You need the following installed on your **Windows** machine:

### 1. Python 3.10+

Download from <https://www.python.org/downloads/> or use a version manager.
Make sure `python` and `pip` are on your PATH.

```cmd
python --version
```

### 2. uv (package manager)

```cmd
pip install uv
```

### 3. Project dependencies + dev tools

From the project root:

```cmd
uv sync --dev
```

This installs all runtime deps AND dev deps (including `pyinstaller`).

### 4. Inno Setup 6+ (for the installer)

Download and install from: <https://jrsoftware.org/isinfo.php>

The default install path is `C:\Program Files (x86)\Inno Setup 6\`. The build
script expects `ISCC.exe` at that path. If you installed elsewhere, edit the
`INNO_SETUP_PATH` variable in `scripts/build_windows.bat`.

### 5. (Optional) Code signing certificate

See the [Code Signing](#step-5----code-signing) section below. You do NOT
need this for local testing.

---

## Step 0 -- Download Dependencies (ffmpeg)

Before building, you need to download **ffmpeg** which is required for video
processing. The app will not work correctly without it.

### Download ffmpeg

```cmd
python scripts\download_ffmpeg.py
```

This downloads ffmpeg (~100 MB) to `bin/ffmpeg.exe`. The build script will
automatically bundle it into the installer.

**One-time setup** -- you only need to do this once unless you delete the `bin/`
folder.

### Optional: Download Chromium (for Full Bundle)

If you want to bundle Chromium in the installer (instead of downloading it on
first launch), download it first:

```cmd
python scripts\download_chromium.py
```

This downloads Chromium (~150 MB) to `bin/chromium/`. Then build with:

```cmd
set BUNDLE_CHROMIUM=1
scripts\build_windows.bat installer
```

Or use the convenient `full` mode which downloads everything and builds:

```cmd
scripts\build_windows.bat full installer
```

---

## Adding an App Icon / Logo

The build system supports a custom app icon that appears on:
- The `.exe` file in Windows Explorer
- The taskbar and title bar when running
- The installer wizard
- Desktop/Start Menu shortcuts

### Creating the icon file

Windows `.exe` files require an `.ico` file. An `.ico` is a container that
holds multiple resolutions of the same image.

#### Option A: Convert from PNG (recommended)

1. Create or obtain a square PNG logo (ideally 1024x1024 or 512x512).

2. Use an online converter like <https://convertio.co/png-ico/> or
   <https://icoconvert.com/> to generate an `.ico` with these sizes embedded:
   - 16x16
   - 32x32
   - 48x48
   - 64x64
   - 128x128
   - 256x256

3. Alternatively, use ImageMagick from the command line:

   ```cmd
   magick convert logo.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
   ```

4. Or use the `pillow` package (already a project dependency):

   ```python
   from PIL import Image
   img = Image.open("logo.png")
   img.save(
       "assets/icon.ico",
       format="ICO",
       sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)],
   )
   ```

#### Option B: Use an `.ico` editor

Tools like [Greenfish Icon Editor](http://greenfishsoftware.org/gfie.php) or
[IcoFX](https://icofx.ro/) let you design/edit `.ico` files directly.

### Placing the icon file

Create an `assets/` directory in the project root and save your icon there:

```
media_downloader/
  assets/
    icon.ico          <-- your app icon
  src/
  ...
```

### Wiring the icon into the build

You need to update **three files**:

#### 1. `media_downloader.spec` (PyInstaller)

Uncomment the `icon=` line in the `EXE()` section (around line 181):

```python
exe = EXE(
    ...
    # Change this:
    # icon="assets/icon.ico",
    # To this:
    icon="assets/icon.ico",
)
```

This sets the icon on the built `.exe` file itself.

#### 2. `installer.iss` (Inno Setup)

Uncomment the `SetupIconFile` line in the `[Setup]` section (around line 41):

```ini
; Change this:
; SetupIconFile=assets\icon.ico
; To this:
SetupIconFile=assets\icon.ico
```

This sets the icon on the installer wizard and the installer `.exe`.

#### 3. (Optional) `src/main.py` (runtime window icon)

If you want the running application window to show your icon (in the title
bar and taskbar), add this after the window is created in `MediaDownloaderApp.__init__`:

```python
import os, sys
if sys.platform == "win32":
    icon_path = os.path.join(
        getattr(sys, "_MEIPASS", os.path.dirname(__file__)),
        "..", "assets", "icon.ico"
    )
    if os.path.exists(icon_path):
        self.iconbitmap(icon_path)
```

And add the `assets/` directory to the `datas` list in `media_downloader.spec`:

```python
datas=[
    (os.path.join(PROJECT_ROOT, "themes"), "themes"),
    (os.path.join(PROJECT_ROOT, "assets"), "assets"),  # <-- add this
    (CTK_PATH, "customtkinter"),
],
```

---

## Step 1 -- Build with PyInstaller

### Using the build script

From the project root in a **Command Prompt** (not PowerShell):

```cmd
scripts\build_windows.bat
```

This will:
1. Clean `dist/` and `build/` directories
2. Run `pyinstaller media_downloader.spec`
3. Verify `dist\MediaDownloader\MediaDownloader.exe` exists
4. Report success or failure

### Manual build (alternative)

```cmd
pyinstaller media_downloader.spec --noconfirm
```

### What gets produced

```
dist/
  MediaDownloader/
    MediaDownloader.exe        <-- the main executable
    _internal/                 <-- Python runtime + all dependencies
      customtkinter/
      themes/
      playwright/              <-- Python package only (no browser binary)
      yt_dlp/
      ...
```

### Build time

Expect 2-5 minutes depending on your machine. The output folder is typically
40-60 MB.

---

## Step 2 -- Test the PyInstaller Bundle

This is the **most critical testing step**. You must verify the built `.exe`
works correctly before creating an installer around it.

### Test Checklist

Run through each of these on your Windows machine:

#### 2.1 Basic launch

```cmd
dist\MediaDownloader\MediaDownloader.exe
```

- [ ] App window opens without errors
- [ ] Title bar shows "Media Downloader"
- [ ] UI renders correctly (theme, fonts, layout)
- [ ] No console window appears (it's a GUI app)

#### 2.2 First-run Chromium download

If Chromium hasn't been downloaded yet (or you want to re-test), delete the
Playwright browser cache first:

```cmd
rmdir /s /q "%LOCALAPPDATA%\ms-playwright"
```

Then launch the app again:

```cmd
dist\MediaDownloader\MediaDownloader.exe
```

- [ ] "First-Time Setup" dialog appears
- [ ] Progress bar shows download progress (percentage, size)
- [ ] Status text updates ("Downloading Chromium...", then "Download complete")
- [ ] Dialog auto-closes after successful install
- [ ] App continues to main window normally

#### 2.3 Second launch (Chromium already installed)

```cmd
dist\MediaDownloader\MediaDownloader.exe
```

- [ ] No download dialog appears (Chromium is already cached)
- [ ] App starts directly to the main window
- [ ] Startup is fast (< 3 seconds)

#### 2.4 Functionality tests

- [ ] Paste a YouTube URL and download a video
- [ ] Try age-restricted content (tests cookie generation via Playwright)
- [ ] Try an Instagram URL
- [ ] Try a SoundCloud URL
- [ ] Theme switching works (light/dark)
- [ ] Download progress bar updates
- [ ] File manager button opens the correct folder

#### 2.5 Offline / error scenarios

Disconnect from the internet, then launch with Chromium not installed:

```cmd
rmdir /s /q "%LOCALAPPDATA%\ms-playwright"
dist\MediaDownloader\MediaDownloader.exe
```

- [ ] Download dialog shows an error message (timeout or network error)
- [ ] "Continue" button appears to dismiss the error
- [ ] App continues without crashing (cookie features will be unavailable)

#### 2.6 Edge cases

- [ ] Launch from a path with spaces: `C:\Program Files\Test Dir\MediaDownloader.exe`
- [ ] Launch from a path with unicode characters
- [ ] Launch as a non-admin user
- [ ] Launch with antivirus active (some AV flags unsigned executables)

### Debugging a failed build

If the `.exe` crashes or doesn't work:

1. **Run from the command line** to see error output:

   ```cmd
   dist\MediaDownloader\MediaDownloader.exe
   ```

   If the app was built with `console=False` (default), you won't see
   stdout/stderr. Temporarily change `console=True` in `media_downloader.spec`
   and rebuild:

   ```python
   exe = EXE(
       ...
       console=True,   # <-- change this temporarily for debugging
   )
   ```

2. **Check the log file**: The app writes logs to the console/stdout. With
   `console=True`, you'll see all log output in the terminal.

3. **Common issues**:

   | Symptom | Likely cause | Fix |
   |---------|-------------|-----|
   | `ModuleNotFoundError` | Missing hidden import | Add to `hiddenimports` in `.spec` |
   | Themes not loading | Data files not bundled | Check `datas` in `.spec` |
   | White/blank window | CustomTkinter assets missing | Verify CTK path in `datas` |
   | `FileNotFoundError` for themes | Path resolution broken | Check `sys._MEIPASS` handling in `src/core/themes/__init__.py` |
   | Playwright import error | Package not bundled | Verify `playwright` in `hiddenimports` |
   | Chromium download fails | Network or subprocess issue | Check subprocess command uses correct Python path |

---

## Step 3 -- Build the Installer with Inno Setup

Once the PyInstaller bundle is tested and working:

### Using the build script

```cmd
scripts\build_windows.bat installer
```

This runs PyInstaller first, then Inno Setup. The installer is output to:

```
installers\MediaDownloaderSetup-0.1.0.exe
```

### Manual Inno Setup build

1. Open Inno Setup Compiler (from Start Menu)
2. File > Open > select `installer.iss`
3. Build > Compile (or press Ctrl+F9)
4. Output: `installers\MediaDownloaderSetup-0.1.0.exe`

### Command-line Inno Setup build

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## Step 4 -- Test the Installer

### 4.1 Fresh install

Run the installer on a **clean machine** (or a VM) that does NOT have
Python installed. This is important -- you need to verify the bundle is
truly standalone.

```cmd
installers\MediaDownloaderSetup-0.1.0.exe
```

Walk through the wizard:

- [ ] Welcome page displays correctly
- [ ] License page shows (if configured)
- [ ] Install directory selection works
- [ ] Desktop icon checkbox works
- [ ] Installation completes without errors
- [ ] Finish page shows the first-run note about Chromium download
- [ ] "Launch Media Downloader" checkbox works

### 4.2 Post-install verification

- [ ] Desktop shortcut was created (if selected)
- [ ] Start Menu entry exists: Start > Media Downloader
- [ ] App launches from the shortcut
- [ ] First-run Chromium download works
- [ ] App functions correctly (run through the tests from Step 2)

### 4.3 Uninstall verification

- [ ] Go to Settings > Apps > Installed apps (or Control Panel > Programs)
- [ ] "Media Downloader" appears in the list
- [ ] Uninstall completes cleanly
- [ ] Desktop shortcut is removed
- [ ] Start Menu entry is removed
- [ ] Install directory is removed

### 4.4 Upgrade / reinstall

- [ ] Install v0.1.0
- [ ] Run the installer again (same version)
- [ ] It should upgrade/overwrite without issues
- [ ] Chromium cache persists (no re-download needed)

### Testing environments

Ideally test on:

- Windows 10 (21H2+)
- Windows 11
- Fresh Windows install (VM recommended)
- Machine without Python installed
- Machine with antivirus enabled

**Virtual machine recommendation**: Use [VirtualBox](https://www.virtualbox.org/)
or [Hyper-V](https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/)
with a Windows evaluation ISO from
<https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise>.

---

## Step 5 -- Code Signing

Without a code signature, Windows SmartScreen will show a scary blue warning
("Windows protected your PC") when users try to run the installer. This
is a significant barrier to adoption.

### Options for code signing

#### Option A: EV Code Signing Certificate (recommended for production)

An Extended Validation (EV) certificate provides **immediate SmartScreen
reputation** -- no warning is shown even on the first download.

**Providers** (as of 2025):
| Provider | Price (approx.) | Notes |
|----------|----------------|-------|
| [DigiCert](https://www.digicert.com/signing/code-signing-certificates) | ~$400/year | Industry standard |
| [Sectigo](https://sectigo.com/ssl-certificates-tls/code-signing) | ~$300/year | Budget option |
| [GlobalSign](https://www.globalsign.com/en/code-signing-certificate) | ~$250/year | Good support |
| [SignPath](https://signpath.io/) | Free for OSS | Free for open-source projects |

EV certificates require a hardware token (USB key) or cloud-based HSM.

#### Option B: OV (Organization Validation) Certificate

Cheaper (~$100-200/year) but does NOT provide immediate SmartScreen reputation.
SmartScreen trust builds gradually as more users download your software.

#### Option C: Azure Trusted Signing (cloud-based)

Microsoft's own cloud signing service. Good if you already use Azure.
See: <https://learn.microsoft.com/en-us/azure/trusted-signing/>

#### Option D: Self-signed (for testing only)

A self-signed certificate does NOT help with SmartScreen. Only use this
for testing the signing process itself.

```powershell
# Create a self-signed certificate (PowerShell as Admin)
New-SelfSignedCertificate `
    -Type CodeSigning `
    -Subject "CN=Media Downloader Dev" `
    -CertStoreLocation Cert:\CurrentUser\My `
    -NotAfter (Get-Date).AddYears(3)

# Export to PFX (you'll need the thumbprint from the output above)
$cert = Get-ChildItem Cert:\CurrentUser\My\<THUMBPRINT>
$password = ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "code_signing.pfx" -Password $password
```

### How to sign

#### Sign with signtool (Windows SDK)

Install the [Windows SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/)
which includes `signtool.exe`.

```cmd
REM Sign the main .exe
signtool sign /f "code_signing.pfx" /p "YourPassword" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\MediaDownloader\MediaDownloader.exe"

REM Sign the installer
signtool sign /f "code_signing.pfx" /p "YourPassword" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "installers\MediaDownloaderSetup-0.1.0.exe"
```

**Important**: Always use a timestamp server (`/tr` flag). Without it, the
signature becomes invalid when the certificate expires.

#### Sign with an EV certificate on a hardware token

```cmd
signtool sign /n "Your Organization Name" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\MediaDownloader\MediaDownloader.exe"
```

The `/n` flag selects the certificate by subject name from the Windows
certificate store (where the hardware token registers it).

#### What to sign

Sign **both** files:

1. `dist\MediaDownloader\MediaDownloader.exe` -- the main application
2. `installers\MediaDownloaderSetup-0.1.0.exe` -- the installer

The installer is what users download, so it must be signed. The `.exe` inside
should also be signed so antivirus doesn't flag it after installation.

### Build + sign workflow

```cmd
REM 1. Build
scripts\build_windows.bat installer

REM 2. Sign the app exe
signtool sign /f cert.pfx /p PASS /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\MediaDownloader\MediaDownloader.exe"

REM 3. Rebuild the installer (so it contains the signed exe)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

REM 4. Sign the installer
signtool sign /f cert.pfx /p PASS /tr http://timestamp.digicert.com /td sha256 /fd sha256 "installers\MediaDownloaderSetup-0.1.0.exe"
```

Note: You sign the `.exe` first, then rebuild the installer so it bundles
the signed `.exe`, then sign the installer itself.

---

## Step 6 -- CI/CD Release Workflow

Once you've verified everything works locally on a Windows machine, you can
automate the build + release process with GitHub Actions.

### Overview

The release workflow (`.github/workflows/release.yml`) is triggered when you
push a git tag like `v0.1.0`. It:

1. Checks out the code on a `windows-latest` runner
2. Installs Python, uv, and dependencies
3. Runs PyInstaller to build the bundle
4. Runs Inno Setup to create the installer
5. (Optionally) Signs the executables
6. Creates a GitHub Release with the installer attached

### How to trigger a release

```bash
# Make sure all changes are committed and pushed
git add -A && git commit -m "Prepare v0.1.0 release"
git push origin main

# Create and push a tag
git tag v0.1.0
git push origin v0.1.0
```

The workflow triggers on `v*` tags and automatically:
- Builds the Windows installer
- Creates a GitHub Release named "v0.1.0"
- Attaches `MediaDownloaderSetup-0.1.0.exe` as a downloadable asset

### Setting up code signing in CI

If you have a code signing certificate, you can sign builds in CI:

1. **Export your certificate** as a base64 string:

   ```bash
   base64 -i code_signing.pfx | pbcopy   # macOS
   # or
   certutil -encode code_signing.pfx encoded.txt  # Windows
   ```

2. **Add GitHub secrets** (Settings > Secrets and variables > Actions):

   | Secret name | Value |
   |-------------|-------|
   | `CODE_SIGNING_CERT` | Base64-encoded `.pfx` file |
   | `CODE_SIGNING_PASSWORD` | Password for the `.pfx` file |

3. The release workflow already has optional signing steps that use these
   secrets. If the secrets are not set, signing is skipped (unsigned builds
   still work, they just trigger SmartScreen warnings).

### Downloading releases

Once a release is published, users can download the installer from:

```
https://github.com/<owner>/media_downloader/releases/latest
```

Or a specific version:

```
https://github.com/<owner>/media_downloader/releases/tag/v0.1.0
```

---

## Troubleshooting

### PyInstaller issues

**"No module named X"**

Add the module to `hiddenimports` in `media_downloader.spec` and rebuild.
PyInstaller uses static analysis to find imports, but it can't detect
dynamic imports (`importlib.import_module()`, lazy imports, etc.).

**Build succeeds but app crashes immediately**

Rebuild with `console=True` in the `.spec` file to see error output:

```python
exe = EXE(
    ...
    console=True,
)
```

**"Failed to execute script 'main'"**

This usually means a missing dependency or data file. Rebuild with
`console=True` and check the traceback.

**UPX errors**

If UPX causes issues, disable it in the `.spec` file:

```python
exe = EXE(
    ...
    upx=False,
)
coll = COLLECT(
    ...
    upx=False,
)
```

### Inno Setup issues

**"Source file not found: dist\MediaDownloader\*"**

You need to build with PyInstaller first. The Inno Setup script bundles
files from the `dist\MediaDownloader\` directory.

**Installer runs but app doesn't work after install**

The installer just copies files. If the PyInstaller bundle works from
`dist\MediaDownloader\` but not after installing, check:
- File permissions in the install directory
- Path-dependent code that assumes the app is in the project directory

### Playwright / Chromium issues

**Chromium download fails in the built app**

The `playwright install chromium` command uses `sys.executable` to find
Python. In a PyInstaller bundle, `sys.executable` points to the bundled
`.exe`, which may not work with `-m playwright`. If this happens, the
bootstrap module falls back to filesystem detection.

Check that the Playwright Python package is properly bundled by looking
for `playwright/` in `dist\MediaDownloader\_internal\`.

**"Playwright not installed" error on launch**

Verify `playwright` is in `hiddenimports` in the `.spec` file and that
`importlib.util.find_spec("playwright")` returns non-None in the built app.

### SmartScreen warnings

If Windows SmartScreen blocks the installer:

1. Click "More info" on the blue warning dialog
2. Click "Run anyway"
3. To prevent this for users, sign the executable (see [Code Signing](#step-5----code-signing))

### Antivirus false positives

Some antivirus software flags PyInstaller bundles as malicious (because
malware authors also use PyInstaller). Solutions:

1. **Sign the executable** -- signed apps are much less likely to be flagged
2. **Submit a false positive report** to the AV vendor
3. **Use VirusTotal** (<https://www.virustotal.com/>) to check which engines
   flag your build, then submit corrections

---

## File Reference

| File | Purpose |
|------|---------|
| `media_downloader.spec` | PyInstaller build configuration |
| `installer.iss` | Inno Setup installer script |
| `scripts/build_windows.bat` | Automated build script (PyInstaller + Inno Setup) |
| `src/services/cookies/playwright_bootstrap.py` | First-run Chromium auto-download with GUI |
| `src/core/themes/__init__.py` | Theme loading with `sys._MEIPASS` support |
| `.github/workflows/release.yml` | CI/CD release workflow (GitHub Actions) |
| `assets/icon.ico` | App icon (you need to create this) |

---

## Quick Reference: Full Build + Test Cycle

```cmd
REM 1. Install dependencies
uv sync --dev

REM 2. Run tests (make sure everything passes first)
uv run pytest

REM 3. Build the bundle
scripts\build_windows.bat

REM 4. Test the bundle
dist\MediaDownloader\MediaDownloader.exe

REM 5. Test first-run (delete Chromium cache)
rmdir /s /q "%LOCALAPPDATA%\ms-playwright"
dist\MediaDownloader\MediaDownloader.exe

REM 6. Build the installer
scripts\build_windows.bat installer

REM 7. Test the installer (ideally on a clean VM)
installers\MediaDownloaderSetup-0.1.0.exe

REM 8. Sign (if you have a certificate)
signtool sign /f cert.pfx /p PASS /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\MediaDownloader\MediaDownloader.exe"
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
signtool sign /f cert.pfx /p PASS /tr http://timestamp.digicert.com /td sha256 /fd sha256 "installers\MediaDownloaderSetup-0.1.0.exe"

REM 9. Tag and push for CI/CD release
git tag v0.1.0
git push origin v0.1.0
```
