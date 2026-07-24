# Media Downloader v1.2.1

Media Downloader v1.2.1 is a reliability and visual-polish release covering all eight supported platforms. It adds four distinct themes, repairs light/dark surface switching, improves dialog behavior, and resolves several downloader routing, progress, timeout, and completion issues.

## Highlights

- Four new complete light/dark themes: ⚡ Cyberpunk, ☕ Espresso, ❄️ Glacier, and 🌅 Sunset (22 bundled themes total).
- Reliable instant theme switching for central surfaces, URL controls, queue cards, and scrollbars.
- Child dialogs remain centered, reachable, transient to the main window, and foregrounded after Alt-Tab or focus changes.
- The File Manager’s “Set as Download Directory” action now fits its complete label.
- Spotify selections now download the chosen YouTube audio match directly without repeating Spotify metadata lookup.

## Downloader reliability

- Standardized progress callbacks to percentage plus MB/s across yt-dlp and shared HTTP download paths.
- Propagated all queued YouTube quality, format, playlist, subtitle, thumbnail, metadata, retry, speed-limit, and cookie options into execution.
- Enabled SoundCloud playlist mode automatically for Sets.
- Required TikTok to produce a non-empty media file before reporting success.
- Removed duplicate Instagram queue entries; bounded Instaloader requests; made carousel progress aggregate and partial failures explicit.
- Made Twitter/X metadata endpoints fall back after timeout, connection, HTTP, or JSON failures.
- Bounded Twitter Spaces ffmpeg execution, centralized ffmpeg discovery, cleaned partial files, and distinguished unavailable/private/deleted Spaces from API failures.
- Fixed RadioJavan `feat`/`featuring`/`ft` matching, including `Arash-Broken-Angel-feat-Helena`; limited resolution to short, finite probes and removed guessed unvalidated URLs.
- Hardened service detection to use parsed hostnames and added mobile YouTube, `vt.tiktok.com`, and international Pinterest routing.

## Security and dependencies

Updated Pillow, Beautiful Soup, Instaloader, Playwright, Pydantic, pydantic-settings, and Requests to address dependency security advisories. See `CHANGELOG.md` for exact versions.

## Validation

The release was checked with focused downloader/UI regressions, the complete repository test suite, Ruff, LSP diagnostics, real CustomTkinter smoke tests, and bounded metadata-only live checks against all eight services. TikTok metadata was explicitly rejected by the test environment with an upstream “IP address is blocked” response; the app now surfaces that restriction as a bounded actionable failure.

## Known limitations

- Public live and replayable Twitter Spaces are supported. Private, deleted, login-gated, and replay-disabled Spaces are unavailable.
- TikTok, Instagram, YouTube, and other services may enforce IP, region, login, or anti-bot restrictions outside the application’s control.
- SoundCloud Go+ tracks are not downloadable without platform entitlement.
- Spotify audio is sourced from the selected YouTube match.
- The Windows installers are unsigned and may trigger SmartScreen.

## Windows downloads

- `MediaDownloaderSetup-1.2.1-x64.exe` — Windows x64
- `MediaDownloaderSetup-1.2.1-arm64.exe` — Windows ARM64

For source installation and platform-specific requirements, see the README.
