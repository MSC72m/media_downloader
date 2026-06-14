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

First stable release of Media Downloader.

### New Platforms

- **Spotify** — Download tracks, albums, playlists, and artists with metadata from Spotify and audio from YouTube. Track selection when multiple matches found.
- **TikTok** — Best available video downloads with metadata and thumbnail preservation.
- **RadioJavan** — Direct MP3/MP4 downloads via CDN with 5-host fallback, session cookie generation, and Cloudflare challenge handling.
- **SoundCloud** — Best available audio with metadata, thumbnail, and playlist support. Free tracks only.

### Core Features

- Dependency injection container with service factory pattern
- Event-driven architecture with message queue
- Concurrent download processing with configurable workers
- Platform dialog coordinator for URL-specific UI flows
- Shared cookie manager infrastructure (YouTube, SoundCloud, Spotify, RadioJavan)

### Cookie & Session Management

- Playwright-based automatic cookie generation for YouTube, SoundCloud, Spotify, and RadioJavan
- Non-blocking background cookie initialization (no UI freeze)
- Platform-specific cookie managers with state persistence
- Chromium auto-install on first launch

### Theme System

- 18 JSON-based color themes with dark/light mode support
- Dynamic theme switching without restart
- Custom theme support (drop JSON file into `themes/`)

### Windows Build

- PyInstaller + Inno Setup installer (x64 + ARM64)
- CI/CD release workflow for automated builds
- ffmpeg bundling support

### Bug Fixes

- Fixed Spotify routing bug where downloads accidentally went through YouTubeDownloader instead of SpotifyDownloader
- Added timeout parameter to `download_file()` for per-service timeout control
- Increased SoundCloud and TikTok socket timeouts to prevent premature connection drops
- Added User-Agent headers to SoundCloud and TikTok to prevent API blocking
- Fixed RadioJavan post-download file size verification
- Fixed double-extension bug (e.g. `video.mp4.mp4`)
- Fixed thread safety and dialog cleanup issues
- Fixed PyInstaller build: Tcl/Tk init, CTK theme, fonts, and Windows emoji rendering

### Testing

- 464 tests passing (unit, integration, e2e handler flows)
- ruff linting + basedpyright type checking
- Quality gate script as single source of truth for CI and local dev
- 55% code coverage

### Changed

- Refactored theme system from enum-based to dynamic JSON files
- Refactored DI typing and removed legacy RadioJavan session manager
- Unified CI/CD quality gate between local and GitHub Actions
- Made cookie initialization non-blocking (background threads)
- Cleaned up duplicate patterns and legacy code across all downloaders

## Previous Changes (pre-1.0.0)

See git history for the full development log spanning December 2025 — June 2026.
