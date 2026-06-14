# Changelog

## 1.1.1 - 2026-06-14

Hotfix release fixing Windows installer and PyInstaller build issues.

### Fixed

- Fixed Windows installer crash: `{app}` constant was expanded before install directory was initialized in `CurPageChanged`
- Fixed PyInstaller build: added Tcl/Tk runtime hook so tkinter initializes correctly in frozen app
- Fixed PyInstaller build: bundled Tcl/Tk libraries and CustomTkinter assets properly
- Fixed PyInstaller build: configured `hookspath` and `runtime_hooks` in spec file
- Fixed Twitter/X downloader: graceful handling of 404 errors from FixTweet API instead of crashing
- Fixed Spotify routing: downloads now correctly use SpotifyDownloader instead of accidentally routing through YouTubeDownloader
- Fixed RadioJavan file download timeout: added `timeout` parameter to `download_file()` for per-service timeout control
- Fixed SoundCloud and TikTok timeouts: increased defaults and added User-Agent headers to prevent API blocking

## 1.0.0 - 2026-06-08

### Added

- Added Spotify, TikTok, and RadioJavan support to the documented platform list.
- Added Playwright-based cookie generation for SoundCloud and Spotify.
- Added concurrent startup initialization for YouTube, SoundCloud, Spotify, and RadioJavan cookie managers.
- Added shared site cookie manager infrastructure for platform-specific cookie managers.
- Added full integrated downloader validation covering the app dependency-injection path.
- Added magic-byte media validation for real download test outputs.

### Changed

- Updated SoundCloud and Spotify downloaders to use generated cookie files when available.
- Updated service factory wiring so cookie managers are injected through the application container.
- Updated release metadata for the 1.0.0 Windows installer.
- Aligned `requirements.txt` with `pyproject.toml` runtime dependencies.

### Verified

- Verified concurrent cookie initialization for YouTube, SoundCloud, Spotify, and RadioJavan.
- Verified playable downloads for YouTube, SoundCloud, TikTok, RadioJavan, and Spotify-backed YouTube audio.
- Verified the unit test suite passes with the new cookie manager wiring.
