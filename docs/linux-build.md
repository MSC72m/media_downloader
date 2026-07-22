# Linux Build

## Prerequisites

- Python 3.10+
- `uv` package manager
- PyInstaller (`uv pip install pyinstaller`)
- `tar` (for ffmpeg extraction)
- (Optional) `dpkg-deb` for `.deb` packages
- (Optional) `appimagetool` for AppImage

## Quick Build

```bash
./scripts/build_linux.sh
```

This produces a portable binary at `dist/MediaDownloader/`.

## Full Build (with dependency downloads)

```bash
./scripts/build_linux.sh full
```

Downloads ffmpeg automatically, then builds the binary.

## Installer Build

```bash
./scripts/build_linux.sh installer       # binary + .deb
./scripts/build_linux.sh full installer   # download deps + binary + .deb
```

The `.deb` package will be written to `installers/media-downloader_<version>_amd64.deb`.

## Bundle Chromium

By default, Chromium is downloaded on first app launch. To bundle it in the
package:

```bash
BUNDLE_CHROMIUM=1 ./scripts/build_linux.sh full installer
```

This increases the package size by ~150 MB but enables offline use.

## Installing the .deb

```bash
sudo dpkg -i installers/media-downloader_1.2.0_amd64.deb
sudo apt install -f   # install missing dependencies
```

After installation, launch from your app menu or run `media-downloader` from the terminal.

## Manual ffmpeg Installation

If the auto-downloader fails, install ffmpeg manually:

```bash
sudo apt update && sudo apt install ffmpeg
```

Or download a static build from [johnvansickle.com](https://johnvansickle.com/ffmpeg/)
and place it at `bin/ffmpeg` in the application directory.

## Build Output

```
dist/MediaDownloader/
├── MediaDownloader          # Main executable
├── _internal/               # PyInstaller bootstrap
└── bin/
    └── ffmpeg               # ffmpeg binary (if downloaded)
```

## CI Integration

For GitHub Actions / GitLab CI, use the `full installer` mode:

```yaml
- run: ./scripts/build_linux.sh full installer
- run: echo "ARTIFACT_PATH=installers/media-downloader_1.2.0_amd64.deb" >> $GITHUB_ENV
```
