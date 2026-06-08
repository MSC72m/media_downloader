# Changelog

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
