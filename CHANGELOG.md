# Changelog

## 1.1.2 - 2026-06-18

Hotfix release fixing RadioJavan URL detection, YouTube dialog crash, disabled button contrast, and UI scaling across all screen resolutions.

### Fixed

- **Fixed RadioJavan URL detection**: Expanded URL patterns to support all RadioJavan URL families including `play.radiojavan.com/playlist/mp3/...`, `play.radiojavan.com/podcast/...`, `play.radiojavan.com/album/...`, `play.radiojavan.com/video/...`, `play.radiojavan.com/song/...`, and `rj.app/m/...`, `rj.app/v/...`, `rj.app/a/...`, `rj.app/p/...`, `rj.app/pl/...` short links. Previously only `/mp3/`, `/mp4/`, and `/song/` paths were recognized.
- **Fixed RadioJavan handler type detection**: Added detection for playlist, album, podcast, browse, video, and music_video content types in addition to mp3/mp4/artist.
- **Fixed RadioJavan media ID extraction**: Extended extraction patterns to handle all URL formats including short links with subpaths like `rj.app/m/...`.
- **Fixed YouTube dialog crash**: Added error handling in `_update_ui_with_metadata()` to prevent unhandled exceptions during UI population. Fixed `_show_error()` to pack error labels inside the scrollable frame instead of directly on the dialog window (which corrupted the layout). Added `winfo_exists()` guard to the grab_set callback to prevent crashes when the dialog is destroyed before the scheduled callback fires.
- **Fixed YouTube metadata fetch with stale cookies**: When all extraction strategies fail with `LOGIN_REQUIRED` (YouTube bot detection), the info extractor now automatically invalidates and regenerates cookies via Playwright, then retries with fresh cookies before giving up. Previously stale cookies would exhaust all strategies without attempting regeneration.
- **Fixed disabled button contrast**: Added `text_color_disabled` parameter to all CTkButton instances across the application (YouTube dialog, Spotify dialog, Network Status dialog, Main Action Buttons, File Manager Action Buttons) so disabled buttons remain readable in both light and dark themes.
- **Fixed UI scaling for all screen resolutions**: All windows (main app, YouTube/Spotify dialogs, Network Status, Login, File Manager, Loading) now use screen-aware geometry — sizes are clamped to 90% of the screen and centered automatically. `WindowCenterMixin.center_window()` now accepts optional `width`/`height` parameters and clamps to screen bounds. Main window uses `min(90% of screen, 1200x800)` initial size with `700x500` minimum. Dialogs use `min(70-90% of screen, their ideal size)` to prevent off-screen widgets on small or high-DPI displays.

## 1.1.1 - 2026-06-16

Hotfix release fixing Windows installer, PyInstaller build issues, and main-thread deadlock.

### Fixed

- **Fixed main-thread deadlock**: `StatusBar._add_message` used blocking `Queue.put()` on a bounded queue (`maxsize=20`) called from the main thread. During downloads, ~10 status updates/sec filled the queue in ~2 seconds, causing the main thread to block forever. Windows detected this as "Not Responding" (white window + blue cursor). Changed to `put_nowait()`.
- **Fixed double completion callback**: `_handle_download_failure`/`_handle_download_success` called the completion callback per-download, then `process_downloads_concurrently` called it again unconditionally — causing duplicate UI refreshes. Removed per-download calls; single batch callback at end.
- **Fixed status bar stuck on "Downloading..." after failure**: The failure path bypassed `_on_failed_event` (which updates the status bar). Added failed-download detection to `on_complete` so status bar shows "Failed: ..." instead of staying stuck.
- **Fixed progress update bypassing queue**: `update_progress` called `_update()` directly when progress >= 100, bypassing the StatusBar queue. Now always goes through the queue.
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
