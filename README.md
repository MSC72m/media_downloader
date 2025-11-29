# Media Downloader

Cross-platform desktop application for downloading media content from social media platforms.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

## Supported Platforms

[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtube.com)
[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://instagram.com)
[![Twitter](https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)](https://twitter.com)
[![Pinterest](https://img.shields.io/badge/Pinterest-%23E60023.svg?&style=for-the-badge&logo=Pinterest&logoColor=white)](https://pinterest.com)
[![SoundCloud](https://img.shields.io/badge/SoundCloud-FF5500?style=for-the-badge&logo=soundcloud&logoColor=white)](https://soundcloud.com)

### Platform Capabilities

| Platform | Content Types | Features |
|----------|--------------|----------|
| **YouTube** | Videos, Playlists, Shorts, Music | Quality selection (144p-8K), audio extraction, subtitle support, auto-cookie generation for age-restricted content |
| **Instagram** | Posts, Reels, Stories, TV | Authentication required, caption preservation, carousel handling |
| **Twitter/X** | Tweets | Image and video extraction from tweets |
| **Pinterest** | Pins, Boards | High-quality image retrieval, automated file naming |
| **SoundCloud** | Tracks, Sets | Downloads at best available quality, free tracks only (premium/Go+ tracks not supported) |

## Features

- Multi-platform support for YouTube, Instagram, Twitter, Pinterest, and SoundCloud
- Bulk download queue with concurrent processing
- Video quality selection (144p to 8K) and audio-only extraction
- Real-time theme switching between dark/light modes with 14 color themes
- Automatic YouTube cookie generation using Playwright for age-restricted content
- Live progress tracking with status indicators and speed metrics
- Network connectivity monitoring and validation
- Configurable retry mechanisms and error handling
- YAML/JSON configuration files with customizable settings

## Requirements

- Python 3.10 or higher
- Playwright (for YouTube cookie generation)
- Internet connection

## Installation

### Option 1: Using uv (Recommended)

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

### Option 2: Using pip

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
   - Optional: Right-click shortcut → Properties → Change icon

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
Icon=/path/to/media_downloader/icon.png
Type=Application
Categories=Utility;
Terminal=false
```

Make it executable:

```bash
chmod +x ~/.local/share/applications/media_downloader.desktop
```

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
- Supports posts, reels, stories, and TV content
- Captions are preserved when available

#### Twitter/X

- Paste tweet URL containing images or videos
- Media is automatically extracted and added to queue
- Note: Spaces are not currently supported

#### Pinterest

- Paste pin or board URL
- High-quality images are retrieved automatically

#### SoundCloud

- Paste track or set URL
- Downloads at best available quality automatically (no format/quality selection)
- Only free tracks are supported (premium/Go+ subscription tracks cannot be downloaded)

### Theme Customization

The theme switcher is located in the header:

- **Appearance toggle**: Switch between Dark and Light modes
- **Color theme dropdown**: Select from 14 color themes (Blue, Green, Purple, Orange, Teal, Pink, Indigo, Amber, Red, Cyan, Emerald, Rose, Violet, Slate)
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
- **Platform-specific**: Instagram, Twitter, Pinterest, SoundCloud settings

Edit the config file directly or use the application's UI to change settings. Changes take effect on next launch (some settings may require restart).

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
- For YouTube: Wait for cookie generation to complete if prompted

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Disclaimer

This software is for personal use only. Users are responsible for:

- Adhering to platform terms of service
- Complying with applicable copyright laws
- Using the software responsibly

The developers assume no liability for misuse of this software.
