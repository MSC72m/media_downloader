# Media Downloader

![Media Downloader](assets/media_downloader.ico)

Cross-platform desktop application for downloading media content from social media platforms.

[![Version](https://img.shields.io/badge/Version-1.1.1-green.svg)](https://github.com/MSC72m/media_downloader/releases)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Windows Installer](https://img.shields.io/badge/Windows-Installer-blue?logo=windows)](https://github.com/MSC72m/media_downloader/releases/latest)

## Supported Platforms

[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtube.com)
[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://instagram.com)
[![Twitter](https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)](https://twitter.com)
[![Pinterest](https://img.shields.io/badge/Pinterest-%23E60023.svg?&style=for-the-badge&logo=Pinterest&logoColor=white)](https://pinterest.com)
[![SoundCloud](https://img.shields.io/badge/SoundCloud-FF5500?style=for-the-badge&logo=soundcloud&logoColor=white)](https://soundcloud.com)
[![Spotify](https://img.shields.io/badge/Spotify-1DB954?style=for-the-badge&logo=spotify&logoColor=white)](https://spotify.com)
[![TikTok](https://img.shields.io/badge/TikTok-000000?style=for-the-badge&logo=tiktok&logoColor=white)](https://tiktok.com)
[![RadioJavan](https://img.shields.io/badge/RadioJavan-00AEEF?style=for-the-badge&logo=musicbrainz&logoColor=white)](https://radiojavan.com)

### Platform Capabilities

| Platform | Content Types | Features |
|----------|--------------|----------|
| **YouTube** | Videos, Playlists, Shorts, Music | Quality selection (144p-8K), audio extraction, subtitle support, auto-cookie generation for age-restricted content |
| **Instagram** | Posts, Reels | Authentication required, caption preservation, carousel handling |
| **Twitter/X** | Tweets | Image and video extraction from tweets |
| **Pinterest** | Pins | High-quality image retrieval, automated file naming |
| **SoundCloud** | Tracks, Sets | Best available audio, metadata and thumbnail support, free tracks only (premium/Go+ tracks not supported) |
| **Spotify** | Tracks, Albums, Playlists, Artists | Metadata extraction and YouTube-backed audio downloads with match selection |
| **TikTok** | Videos | Best available video downloads with metadata and thumbnail support |
| **RadioJavan** | Songs, Videos | Direct MP3/MP4 downloads with session cookie generation and CDN fallback |

## Features

- Multi-platform support for YouTube, Spotify, TikTok, Instagram, Twitter/X, Pinterest, SoundCloud, and RadioJavan
- Bulk download queue with concurrent processing
- Video quality selection (144p to 8K) and audio-only extraction
- Real-time theme switching between dark/light modes with 18 color themes
- Custom themes — drop a JSON file into `themes/` and it appears in the UI (see [docs/themes.md](docs/themes.md))
- Automatic cookie generation using Playwright for YouTube, SoundCloud, Spotify, and RadioJavan
- Live progress tracking with status indicators and speed metrics
- Network connectivity monitoring and validation
- Configurable retry mechanisms and error handling
- YAML/JSON configuration files with customizable settings

## Requirements

- Python 3.10 or higher _(Windows users: use the installer below — no Python needed)_
- Playwright (for YouTube cookie generation)
- Internet connection

### Development Requirements (Linting + LSP)

The local quality gates in this repo require these tools:
- `ruff` for linting (`uv run ruff check .`)
- `basedpyright` for strict editor/LSP parity (`npx basedpyright --outputjson` and `npx basedpyright tests --outputjson`)
- `pytest` for test validation (`uv run pytest -q`)

Install development dependencies with:

```bash
pip install -r requirements-dev.txt
```

If you use `uv`, the project dependencies are managed from `pyproject.toml` and `uv.lock`:

```bash
uv sync
```

For `npx basedpyright ...`, install Node.js 18+ if it is not already available.

## Installation

### Option 1: Windows Installer (Windows Only — Recommended)

The easiest way to run Media Downloader on Windows. No Python installation required.

1. **Download** the latest installer from the [Releases page](https://github.com/MSC72m/media_downloader/releases/tag/v1.1.1)
   - `MediaDownloaderSetup-1.1.1-x64.exe` for 64-bit Intel/AMD PCs
   - `MediaDownloaderSetup-1.1.1-arm64.exe` for Windows on ARM devices

2. **Run** the installer — it will install:
   - The application (`MediaDownloader.exe`) with a Start Menu shortcut
   - **ffmpeg** (required for video processing) — downloaded automatically during setup
   - All Python dependencies (bundled by PyInstaller)

3. **Launch** from the Start Menu or desktop shortcut

**Note on Windows SmartScreen**: The installer is not code-signed, so Windows may show a blue "Windows protected your PC" warning. Click **"More info"** → **"Run anyway"** to proceed. This is normal for unsigned open-source software.

**System requirements**: Windows 10 or later, 64-bit (x64 or ARM64).

### Option 2: Using uv (Recommended — Python Required)

```bash
# Clone the repository
git clone https://github.com/MSC72m/media_downloader.git
cd media_downloader

# Install uv if not already installed
# On macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# On Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install dependencies and run
uv sync
uv run playwright install chromium
uv run -m src.main
```

### Option 3: Using pip

```bash
# Clone the repository
git clone https://github.com/MSC72m/media_downloader.git
cd media_downloader

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Launch Application

```bash
# With uv:
uv run -m src.main

# With pip:
python -m src.main
```

## Creating Desktop Shortcuts

### Windows

1. Create a batch file `media_downloader.bat` in the project directory:

```batch
@echo off
cd /d "C:\path\to\media_downloader"
call venv\Scripts\activate
python -m src.main
pause
```

Replace `C:\path\to\media_downloader` with your actual installation path.

2. Create a shortcut:
   - Right-click the batch file → "Create shortcut"
   - Move shortcut to Desktop or Start Menu
   - Right-click shortcut → Properties → Change Icon → Browse to `assets/media_downloader.ico`

### Linux

Create a `.desktop` file in `~/.local/share/applications/`:

```bash
vim ~/.local/share/applications/media_downloader.desktop
```

Add the following content (adjust paths as needed):

```ini
[Desktop Entry]
Name=Media Downloader
Exec=/path/to/venv/bin/python /path/to/media_downloader/src/main.py
Icon=/path/to/media_downloader/assets/media_downloader.ico
Type=Application
Categories=Utility;
Terminal=false
```

Make it executable:

```bash
chmod +x ~/.local/share/applications/media_downloader.desktop
```

### macOS

#### Option A: Automator App (Recommended)

1. Open **Automator** → New Application
2. Add a "Run Shell Script" action with:

```bash
cd /path/to/media_downloader && source venv/bin/activate && python -m src.main
```

3. Save as `Media Downloader.app` to `/Applications/`
4. Set the app icon:
   - Right-click the `.app` → Get Info
   - Drag `assets/media_downloader.ico` onto the icon in the top-left corner

#### Option B: Shell Alias

```bash
alias media-downloader='cd /path/to/media_downloader && source venv/bin/activate && python -m src.main'
```

Add this to your `~/.zshrc` or `~/.bash_profile` for persistence.

#### Option C: macOS Launch Agent

Create `~/Library/LaunchAgents/com.msc72m.mediadownloader.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.msc72m.mediadownloader</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>-m</string>
        <string>src.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/media_downloader</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Launch with: `launchctl load ~/Library/LaunchAgents/com.msc72m.mediadownloader.plist`

## Usage

### Basic Workflow

1. **Launch the application** using one of the methods above
2. **Paste URL** into the input field at the top
3. **Configure options** (for YouTube: quality, format, subtitles, etc.)
4. **Add to queue** or download immediately
5. **Monitor progress** in the download list with real-time status updates

### Adding Downloads

- Paste any supported platform URL into the input field
- Click "Add" button
- For YouTube: A dialog will appear with quality and format options
- For other platforms: Downloads are added directly to the queue

### Managing Queue

- **Remove Selected**: Select items in the download list (click and drag to select multiple) and click "Remove Selected"
- **Clear All**: Removes all items from the queue
- **Download All**: Starts processing all queued downloads

### Platform-Specific Instructions

#### YouTube

- Quality selection: Choose from 144p to 8K (availability depends on source)
- Format options: Video+Audio, Audio Only, or Video Only
- Playlist support: Enable "Download Playlist" option
- Subtitles: Select languages and download subtitles
- Auto-cookies: Automatically generated for age-restricted content (requires Playwright)

#### Instagram

- **Authentication required**: First Instagram URL will prompt authentication window
- After successful authentication, session is saved and reused for subsequent downloads
- Supports posts and reels
- Captions are preserved when available

#### Twitter/X

- Paste tweet URL containing images or videos
- Media is automatically extracted and added to queue
- Note: Spaces are not currently supported

#### Pinterest

- Paste pin URL
- High-quality images are retrieved automatically

#### SoundCloud

- Paste track or set URL
- Downloads at best available quality automatically (no format/quality selection)
- Only free tracks are supported (premium/Go+ subscription tracks cannot be downloaded)

#### Spotify

- Paste track, album, playlist, or artist URLs
- Spotify metadata is resolved first, then matching audio is downloaded from YouTube
- Track selection is available when multiple matches are found

#### TikTok

- Paste video URLs
- Downloads best available video quality automatically
- Metadata and thumbnails are preserved when available

#### RadioJavan

- Paste song or video URLs
- Downloads direct MP3 or MP4 media when available
- Session cookies are generated automatically using Playwright when needed

### Theme Customization

The theme switcher is located in the header:

- **Appearance toggle**: Switch between Dark and Light modes
- **Color theme dropdown**: Select from 18 color themes (Amber, Blue, Coral, Cyan, Emerald, Gold, Green, Indigo, Lime, Navy, Orange, Pink, Purple, Red, Rose, Slate, Teal, Violet)
- Changes apply instantly without restart
- Preferences are saved automatically to config file

### File Management

- Click "Manage Files" button to open file browser dialog
- Navigate and select download directory
- Selected path is saved and used for all downloads

### Network Status

- Access via Tools → Network Status menu
- Shows current connectivity status
- Displays detailed network information and diagnostics

## Configuration

Configuration files are automatically created in `~/.media_downloader/` on first run. The application supports both YAML and JSON formats:

- `config.yaml` (recommended)
- `config.json`

### Configuration Options

- **Paths**: Download directory, config directory
- **Downloads**: Concurrent download limits, retry counts, timeouts
- **Network**: Timeouts, user agents, service domains
- **YouTube**: Default quality, supported qualities, subtitle languages
- **Theme**: Appearance mode, color theme, persistence
- **Platform-specific**: YouTube, Spotify, TikTok, Instagram, Twitter/X, Pinterest, SoundCloud, and RadioJavan settings

Edit the config file directly or use the application's UI to change settings. Changes take effect on next launch (some settings may require restart).

## Known Limitations

- **Twitter Spaces** — Audio spaces are not currently supported
- **SoundCloud Premium** — Only free tracks can be downloaded (Go+ subscription tracks are blocked by SoundCloud)
- **Spotify Audio** — Audio is sourced from YouTube, so quality depends on YouTube availability
- **Instagram Auth** — First Instagram download requires browser-based authentication
- **macOS Desktop Shortcut** — No `.app` bundle provided; see [Creating Desktop Shortcuts](#creating-desktop-shortcuts) for manual setup
- **Windows SmartScreen** — The installer is unsigned; see [Windows Installer](#option-1-windows-installer-windows-only--recommended) for how to bypass
- **Windows ARM64** — Only the ARM64 installer works on ARM devices (x64 installer requires emulation)

## Troubleshooting

### Playwright Not Installed

If you see an error about Playwright not being installed:

```bash
# With uv:
uv run playwright install chromium

# With pip:
playwright install chromium
```

### Network Errors

- Check internet connection
- Verify URL is from a supported platform
- Check network status via Tools → Network Status

### Authentication Failures (Instagram)

- Authentication window appears automatically when adding first Instagram URL
- Check credentials are correct
- Wait for authentication to complete before adding more URLs
- Session is saved after successful authentication

### Download Errors

- Check application logs for detailed error messages
- Verify URL is valid and accessible
- Ensure sufficient disk space in download directory
- For YouTube, SoundCloud, Spotify, or RadioJavan: Wait for cookie generation to complete if prompted

## License

GNU General Public License v3.0 - See [LICENSE](LICENSE) file for details.

## Disclaimer

This software is for personal use only. Users are responsible for:

- Adhering to platform terms of service
- Complying with applicable copyright laws
- Using the software responsibly

The developers assume no liability for misuse of this software.
