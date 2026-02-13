from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.services.cookies.youtube_cookie_sources import (
    BrowserProbeCandidate,
    YouTubeCookieSourceCoordinator,
    YouTubeAuthConfig,
)
from src.services.youtube.downloader import YouTubeDownloader
from src.services.youtube.subtitle_extractor import YouTubeSubtitleExtractor


class _AutoCookieManagerStub:
    def __init__(self, cookie_path: str | None):
        self._cookie_path = cookie_path

    def get_cookies(self) -> str | None:
        return self._cookie_path

    def get_cookie_info_for_ytdlp(self) -> dict[str, Any] | None: ...

    def get_current_cookie_path(self) -> str | None: ...


    def needs_regeneration(self, domain: str, max_age_hours: int) -> bool: ...

    def get_cookie_file_path(self, domain: str) -> str | None: ...


class _CookieHandlerStub:
    def __init__(self, cookie_path: str | None):
        self._cookie_path = cookie_path

    def get_cookie_info_for_ytdlp(self) -> dict[str, str] | None:
        if not self._cookie_path:
            return None
        return {"cookiefile": self._cookie_path}


def test_build_auth_strategies_uses_cached_browser_winner_only(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\ttest\n",
        encoding="utf-8",
    )

    coordinator = YouTubeCookieSourceCoordinator(
        auto_cookie_manager=_AutoCookieManagerStub(str(cookie_file)),
        storage_dir=tmp_path,
    )
    coordinator.state.preferred_source = "browser"
    coordinator.state.preferred_browser = "chrome"
    coordinator.state.ttl_expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    coordinator.get_browser_candidates = lambda: [  # type: ignore[method-assign]
        BrowserProbeCandidate(name="chrome", ytdlp_browser="chrome"),
        BrowserProbeCandidate(name="chromium", ytdlp_browser="chromium"),
    ]

    labels = [strategy.label for strategy in coordinator.build_auth_strategies()]
    assert "browser-cookies-chrome" in labels
    assert "browser-cookies-chromium" not in labels


def test_build_auth_strategies_deduplicates_identical_cookiefiles(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tYSC\ttest\n",
        encoding="utf-8",
    )

    coordinator = YouTubeCookieSourceCoordinator(
        auto_cookie_manager=_AutoCookieManagerStub(str(cookie_file)),
        cookie_handler=_CookieHandlerStub(str(cookie_file)),
        storage_dir=tmp_path,
    )
    coordinator.get_browser_candidates = lambda: []  # type: ignore[method-assign]

    labels = [strategy.label for strategy in coordinator.build_auth_strategies()]
    assert labels.count("manual-cookie-file") + labels.count("generated-cookie-file") == 1


def test_verify_download_completion_accepts_discovered_media_file(tmp_path):
    downloader = YouTubeDownloader()
    base = tmp_path / "sample"

    (tmp_path / "sample.webp").write_bytes(b"thumbnail")
    (tmp_path / "sample.mp4.webm").write_bytes(b"video-bytes")

    assert downloader._verify_download_completion(str(base), preferred_ext=".mp4")


def test_verify_download_completion_accepts_bare_output_file(tmp_path):
    downloader = YouTubeDownloader()
    base = tmp_path / "sample_no_ext"
    base.write_bytes(b"video-bytes")

    assert downloader._verify_download_completion(str(base), preferred_ext=".mp4")


def test_browser_candidates_priority_order(tmp_path):
    coordinator = YouTubeCookieSourceCoordinator(storage_dir=tmp_path)

    availability = {
        "chrome": True,
        "firefox": True,
        "chromium": True,
        "brave": True,
        "edge": False,
        "vivaldi": False,
        "opera": False,
    }
    coordinator._is_browser_available = lambda name: availability.get(name, False)  # type: ignore[method-assign]
    coordinator._find_firefox_compatible_profile = lambda browser: (  # type: ignore[method-assign]
        "/tmp/zen-profile"
        if browser == "zen"
        else "/tmp/librewolf-profile"
        if browser == "librewolf"
        else None
    )

    names = [candidate.name for candidate in coordinator.get_browser_candidates()]
    assert names == ["chrome", "firefox", "zen", "chromium", "brave", "librewolf"]


def test_subtitle_extractor_skips_browser_cookie_source():
    extractor = YouTubeSubtitleExtractor()
    extractor.cookie_source_coordinator.build_auth_strategies = lambda **_kwargs: [  # type: ignore[method-assign]
        YouTubeAuthConfig(
            label="browser-cookies-chrome",
            source="browser",
            browser="chrome",
            ytdlp_options={"cookiesfrombrowser": ("chrome",)},
        ),
        YouTubeAuthConfig(
            label="generated-cookie-file",
            source="generated",
            ytdlp_options={"cookiefile": "/tmp/cookies.txt"},
        ),
    ]

    attempted_labels: list[str] = []

    def fake_extract(url: str, auth_strategy: YouTubeAuthConfig):
        _ = url
        attempted_labels.append(auth_strategy.label)
        return None

    extractor._extract_for_strategy = fake_extract  # type: ignore[method-assign]

    result = extractor.extract_subtitles("https://www.youtube.com/watch?v=jNQXAC9IVRw")

    assert result == {"subtitles": {}, "automatic_captions": {}}
    assert attempted_labels == ["generated-cookie-file"]
